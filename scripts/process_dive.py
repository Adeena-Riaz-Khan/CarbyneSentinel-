#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional
ROOT = Path(__file__).resolve().parent.parent
CATEGORY_MAP: dict[str, str] = {'Reentrancy': 'Reentrancy', 'Access Control': 'AccessControl', 'Arithmetic': 'Arithmetic', 'Unchecked Return Values': 'UncheckedReturn', 'DoS': 'OtherVulnerability', 'Bad Randomness': 'OtherVulnerability', 'Front Running': 'OtherVulnerability', 'Time manipulation': 'OtherVulnerability'}
LABEL_COLUMNS = list(CATEGORY_MAP.keys())
SKIP_DIR_NAMES = {'dapscan', 'dappscan-source', 'swcsource', 'temp_dive', '__macosx', 'defihacklabs', 'solidifi', 'smartbugs', 'slither_hf'}
HEX_BYTECODE_RE = re.compile('^(0x)?[0-9a-fA-F]{2,}$')

def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    return logging.getLogger('process_dive')

@dataclass
class DivePaths:
    root: Path
    labels_csv: Path
    code_based_csv: Optional[Path]
    source_dir: Optional[Path]
    samples_csv: Optional[Path]
    creation_opcode_jsonl: Optional[Path]
    runtime_opcode_jsonl: Optional[Path]
    skipped_trees: list[str]

def _is_contaminated_path(path: Path) -> bool:
    parts_lower = {p.lower() for p in path.parts}
    if parts_lower & SKIP_DIR_NAMES:
        return True
    joined = str(path).lower().replace('\\', '/')
    if '/dapscan/' in joined or '/dappscan' in joined:
        return True
    if 'dappscan-source' in joined:
        return True
    return False

def _first_existing(candidates: list[Path]) -> Optional[Path]:
    for p in candidates:
        if p.is_file():
            return p
    return None

def _first_existing_dir(candidates: list[Path]) -> Optional[Path]:
    for p in candidates:
        if p.is_dir():
            return p
    return None

def resolve_dive_paths(dive_root: Optional[Path], log: logging.Logger) -> DivePaths:
    skipped: list[str] = []
    preferred = (dive_root or ROOT / 'data' / 'DIVE').resolve()
    search_roots: list[Path] = []
    if preferred.exists():
        search_roots.append(preferred)
    search_roots.extend([ROOT / 'Raw', ROOT / 'raw', ROOT / 'DIVE_Labels', ROOT])
    for probe in [preferred, ROOT / 'Raw' / 'dive', ROOT / 'raw' / 'dive']:
        if not probe.is_dir():
            continue
        for child in probe.iterdir():
            if child.is_dir() and _is_contaminated_path(child):
                skipped.append(str(child.relative_to(ROOT)) if child.is_relative_to(ROOT) else str(child))
                log.warning('Skipping non-DIVE / contaminated tree: %s', child)
    labels = _first_existing([preferred / 'DIVE_Labels.csv', preferred / 'Labels' / 'DIVE_Labels.csv', ROOT / 'DIVE_Labels' / 'Labels' / 'DIVE_Labels.csv', ROOT / 'data' / 'DIVE' / 'Labels' / 'DIVE_Labels.csv'])
    if labels is None:
        raise FileNotFoundError('Could not find DIVE_Labels.csv. Place it under data/DIVE/ or DIVE_Labels/Labels/.')
    code_based = _first_existing([preferred / 'PRE' / 'Code-based.csv', preferred / 'Code-based.csv', ROOT / 'Raw' / 'PRE' / 'Code-based.csv', ROOT / 'raw' / 'PRE' / 'Code-based.csv'])
    source_dir = _first_existing_dir([preferred / 'PRE' / 'Source codes', preferred / 'Source codes', preferred / 'sources', ROOT / 'Raw' / 'PRE' / 'Source codes', ROOT / 'raw' / 'PRE' / 'Source codes'])
    samples = _first_existing([preferred / 'DIVE_Samples.csv', preferred / 'Samples' / 'DIVE_Samples.csv', ROOT / 'Raw' / 'DIVE_Samples.csv', ROOT / 'raw' / 'DIVE_Samples.csv', ROOT / 'Raw' / 'dive' / 'Raw' / 'DIVE_Samples.csv'])
    creation = _first_existing([preferred / 'PRE' / 'Creation_Opcode.jsonl', preferred / 'Creation_Opcode.jsonl', ROOT / 'Raw' / 'PRE' / 'Creation_Opcode.jsonl', ROOT / 'raw' / 'PRE' / 'Creation_Opcode.jsonl'])
    runtime = _first_existing([preferred / 'POST' / 'Runtime_Opcode.jsonl', preferred / 'Runtime_Opcode.jsonl', ROOT / 'Raw' / 'POST' / 'Runtime_Opcode.jsonl', ROOT / 'raw' / 'POST' / 'Runtime_Opcode.jsonl'])
    if _is_contaminated_path(labels):
        raise RuntimeError(f'Labels path looks contaminated (DAppSCAN): {labels}')
    root_used = preferred if preferred.exists() else ROOT / 'Raw'
    log.info('DIVE root in use: %s', root_used)
    log.info('Labels: %s', labels)
    log.info('Code-based.csv: %s', code_based)
    log.info('Source dir: %s', source_dir)
    log.info('Samples: %s', samples)
    log.info('Creation_Opcode: %s', creation)
    log.info('Runtime_Opcode: %s', runtime)
    return DivePaths(root=root_used, labels_csv=labels, code_based_csv=code_based, source_dir=source_dir, samples_csv=samples, creation_opcode_jsonl=creation, runtime_opcode_jsonl=runtime, skipped_trees=skipped)

def iter_jsonl(path: Path, log: logging.Logger) -> Iterator[dict[str, Any]]:
    bad = 0
    with path.open('r', encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                bad += 1
                if bad <= 5:
                    log.warning('Skipping corrupt JSONL %s:%d (%s)', path.name, lineno, e)
    if bad:
        log.warning('Total corrupt JSONL lines in %s: %d', path.name, bad)

def stream_code_based_meta(path: Path, log: logging.Logger) -> dict[int, dict[str, str]]:
    meta: dict[int, dict[str, str]] = {}
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(10 ** 9)
    with path.open('r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            try:
                cid = int(str(row.get('contractID', '')).strip())
            except ValueError:
                log.warning('Bad contractID in Code-based.csv row %d', i)
                continue
            meta[cid] = {'compiler_version': (row.get('CompilerVersion') or '').strip() or 'unknown', 'contract_name': (row.get('ContractName') or '').strip()}
            if i % 5000 == 0:
                log.info('  Code-based.csv progress: %d rows', i)
    log.info('Loaded metadata for %d contracts from Code-based.csv', len(meta))
    return meta

def stream_optional_bytecode(path: Optional[Path], field_candidates: tuple[str, ...], log: logging.Logger, limit_ids: Optional[set[int]]=None) -> dict[int, str]:
    if path is None:
        return {}
    if _is_contaminated_path(path):
        log.warning('Refusing contaminated opcode path: %s', path)
        return {}
    out: dict[int, str] = {}
    kept = 0
    seen = 0
    log.info('Scanning %s for hex bytecode (streaming)...', path.name)
    for obj in iter_jsonl(path, log):
        seen += 1
        try:
            cid = int(obj.get('contractID'))
        except (TypeError, ValueError):
            continue
        if limit_ids is not None and cid not in limit_ids:
            continue
        raw = None
        for key in field_candidates:
            if key in obj and obj[key]:
                raw = obj[key]
                break
        if raw is None:
            continue
        if isinstance(raw, str) and HEX_BYTECODE_RE.match(raw.replace(' ', '')):
            hex_body = raw[2:] if raw.startswith('0x') else raw
            out[cid] = hex_body if hex_body.startswith('0x') else f'0x{hex_body}'
            kept += 1
        if seen % 5000 == 0:
            log.info('  %s progress: %d lines, %d hex bytecode kept', path.name, seen, kept)
    log.info('Finished %s: %d lines scanned, %d hex bytecode entries retained', path.name, seen, kept)
    return out

def load_addresses(path: Optional[Path], log: logging.Logger) -> dict[int, str]:
    if path is None:
        return {}
    addrs: list[str] = []
    with path.open('r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        col = None
        for row in reader:
            if col is None:
                col = 'Address' if 'Address' in row else next(iter(row.keys()))
            a = (row.get(col) or '').strip().lower()
            if a:
                addrs.append(a)
    mapping = {i + 1: addrs[i] for i in range(len(addrs))}
    log.info('Loaded %d addresses from %s', len(addrs), path.name)
    return mapping

def load_labels(path: Path, log: logging.Logger) -> dict[int, dict[str, int]]:
    labels: dict[int, dict[str, int]] = {}
    with path.open('r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in LABEL_COLUMNS if c not in (reader.fieldnames or [])]
        if missing_cols:
            raise RuntimeError(f'DIVE_Labels.csv missing columns: {missing_cols}')
        for row in reader:
            try:
                cid = int(str(row['contractID']).strip())
            except ValueError:
                continue
            labels[cid] = {c: int(str(row[c]).strip() or '0') for c in LABEL_COLUMNS}
    log.info('Loaded labels for %d contracts', len(labels))
    return labels

def map_categories(label_row: dict[str, int]) -> list[str]:
    order = ['Reentrancy', 'AccessControl', 'Arithmetic', 'UncheckedReturn', 'OtherVulnerability']
    found: set[str] = set()
    for dive_col, std in CATEGORY_MAP.items():
        if label_row.get(dive_col, 0) == 1:
            found.add(std)
    return [c for c in order if c in found]

def read_source(source_dir: Optional[Path], contract_id: int, log: logging.Logger) -> Optional[str]:
    if source_dir is None:
        return None
    path = source_dir / f'{contract_id}.sol'
    if _is_contaminated_path(path):
        return None
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        log.warning('Failed reading %s: %s', path, e)
        return None

def build_record(contract_id: int, source_code: str, categories: list[str], is_vulnerable: bool, compiler_version: str, bytecode: Optional[str], address: Optional[str]) -> dict[str, Any]:
    if address:
        rid = f'DIVE_{address}'
    else:
        rid = f'DIVE_{contract_id}'
    if is_vulnerable:
        target_modules = ['GNN_TRAIN']
    else:
        target_modules = ['BENIGN_POOL']
    return {'id': rid, 'source_code': source_code, 'bytecode': bytecode, 'compiler_version': compiler_version or 'unknown', 'labels': {'is_vulnerable': is_vulnerable, 'categories': categories if is_vulnerable else [], 'swc_ids': [], 'line_numbers': []}, 'intent_label': None, 'dataset_source': 'DIVE', 'target_modules': target_modules, 'dive_contract_id': contract_id, 'dive_address': address}

def process(args: argparse.Namespace) -> int:
    log = setup_logging(args.verbose)
    paths = resolve_dive_paths(Path(args.dive_root) if args.dive_root else None, log)
    out_vuln = ROOT / 'data' / 'processed' / 'dive_vulnerable.jsonl'
    out_benign = ROOT / 'data' / 'processed' / 'benign_pool' / 'dive_benign.jsonl'
    out_vuln.parent.mkdir(parents=True, exist_ok=True)
    out_benign.parent.mkdir(parents=True, exist_ok=True)
    labels = load_labels(paths.labels_csv, log)
    addresses = load_addresses(paths.samples_csv, log)
    if addresses and labels:
        if max(addresses) != max(labels) or len(addresses) != len(labels):
            log.warning('Address list size (%d, max_id=%d) != label size (%d, max_id=%d). Will attach address only when contractID is in range.', len(addresses), max(addresses), len(labels), max(labels))
    meta: dict[int, dict[str, str]] = {}
    if paths.code_based_csv and (not _is_contaminated_path(paths.code_based_csv)):
        meta = stream_code_based_meta(paths.code_based_csv, log)
    else:
        log.warning("Code-based.csv missing or contaminated — compiler_version will be 'unknown'")
    id_set = set(labels.keys())
    if args.limit:
        id_set = set(sorted(id_set)[:args.limit])
    bytecode_map: dict[int, str] = {}
    if args.scan_opcodes:
        bytecode_map.update(stream_optional_bytecode(paths.runtime_opcode_jsonl, ('bytecode', 'RuntimeBytecode', 'bin-runtime', 'bin', 'Opcodes'), log, limit_ids=id_set if args.limit else None))
        missing = id_set - set(bytecode_map.keys()) if args.limit else None
        creation_bc = stream_optional_bytecode(paths.creation_opcode_jsonl, ('bytecode', 'CreationBytecode', 'bin', 'ExtractedOpcodes', 'Opcodes'), log, limit_ids=missing if args.limit else None)
        for cid, bc in creation_bc.items():
            bytecode_map.setdefault(cid, bc)
    else:
        log.info('Skipping multi-GB opcode JSONL scan (default). Pass --scan-opcodes to search them for hex bytecode; otherwise bytecode fields stay null.')
    stats = Counter()
    category_counts = Counter()
    skipped_no_source = 0
    skipped_contaminated = 0
    out_vuln.write_text('', encoding='utf-8')
    out_benign.write_text('', encoding='utf-8')
    sorted_ids = sorted(labels.keys())
    if args.limit:
        sorted_ids = sorted_ids[:args.limit]
        log.info('Limiting to first %d contractIDs', args.limit)
    with out_vuln.open('a', encoding='utf-8') as fv, out_benign.open('a', encoding='utf-8') as fb:
        for n, cid in enumerate(sorted_ids, start=1):
            label_row = labels[cid]
            categories = map_categories(label_row)
            is_vuln = len(categories) > 0
            source = read_source(paths.source_dir, cid, log)
            if source is None:
                skipped_no_source += 1
                stats['skipped_no_source'] += 1
                if skipped_no_source <= 10:
                    log.warning('No source for contractID=%s — skipped', cid)
                continue
            if paths.source_dir and _is_contaminated_path(paths.source_dir / f'{cid}.sol'):
                skipped_contaminated += 1
                continue
            compiler = meta.get(cid, {}).get('compiler_version', 'unknown')
            addr = addresses.get(cid)
            bc = bytecode_map.get(cid)
            rec = build_record(contract_id=cid, source_code=source, categories=categories, is_vulnerable=is_vuln, compiler_version=compiler, bytecode=bc, address=addr)
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            if is_vuln:
                fv.write(line)
                stats['vulnerable'] += 1
                for c in categories:
                    category_counts[c] += 1
            else:
                fb.write(line)
                stats['benign'] += 1
            stats['processed'] += 1
            if n % 2000 == 0:
                log.info('Progress %d/%d (vuln=%d benign=%d)', n, len(sorted_ids), stats['vulnerable'], stats['benign'])
    log.info('======== DIVE processing complete ========')
    log.info('Skipped contaminated trees: %s', paths.skipped_trees or '(none detected)')
    log.info('Total records written: %d', stats['processed'])
    log.info('Vulnerable: %d → %s', stats['vulnerable'], out_vuln)
    log.info('Benign:     %d → %s', stats['benign'], out_benign)
    log.info('Skipped (no source): %d', stats['skipped_no_source'])
    log.info('Hex bytecode attached: %d', sum((1 for _ in bytecode_map)))
    log.info('Category prevalence (vulnerable rows, multi-label): %s', dict(category_counts))
    verify_outputs(out_vuln, out_benign, log)
    return 0

def verify_outputs(out_vuln: Path, out_benign: Path, log: logging.Logger) -> None:
    log.info('======== Verification: first 2 lines of each output ========')
    for path in (out_vuln, out_benign):
        log.info('--- %s ---', path.relative_to(ROOT))
        if not path.is_file() or path.stat().st_size == 0:
            log.warning('(empty or missing)')
            continue
        with path.open('r', encoding='utf-8') as f:
            for i in range(2):
                line = f.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    print(line[:500])
                    continue
                preview = {'id': obj.get('id'), 'compiler_version': obj.get('compiler_version'), 'bytecode_is_null': obj.get('bytecode') is None, 'labels': obj.get('labels'), 'dataset_source': obj.get('dataset_source'), 'target_modules': obj.get('target_modules'), 'source_code_chars': len(obj.get('source_code') or ''), 'dive_contract_id': obj.get('dive_contract_id')}
                print(json.dumps(preview, indent=2))

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Process DIVE dataset into standardized JSONL')
    p.add_argument('--dive-root', default=None, help='Path to data/DIVE (default: <repo>/data/DIVE with Raw/ fallbacks)')
    p.add_argument('--limit', type=int, default=None, help='Process only first N labeled contractIDs')
    p.add_argument('--scan-opcodes', action='store_true', help='Stream-scan Creation/Runtime opcode JSONL for hex bytecode (slow; usually none in DIVE)')
    p.add_argument('-v', '--verbose', action='store_true')
    return p.parse_args(argv)
if __name__ == '__main__':
    try:
        raise SystemExit(process(parse_args()))
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.exception('process_dive failed')
        raise
