#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional
ROOT = Path(__file__).resolve().parent.parent
PRAGMA_RE = re.compile('pragma\\s+solidity\\s+([^;]+);', re.IGNORECASE)
LINE_RE = re.compile('L?\\s*(\\d+)(?:\\s*[-–]\\s*L?\\s*(\\d+))?', re.IGNORECASE)
SWC_CATEGORY_MAP: dict[str, str] = {'107': 'Reentrancy', '101': 'Arithmetic', '104': 'UncheckedReturn', '105': 'AccessControl', '106': 'AccessControl', '115': 'AccessControl', '118': 'AccessControl', '124': 'AccessControl'}
KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [('Reentrancy', ('reentranc', 'swc-107', 'cross-function reentrancy')), ('AccessControl', ('access control', 'access-control', 'authorization', 'onlyowner', 'privileged', 'unprotected', 'tx.origin', 'swc-105', 'swc-106', 'swc-115', 'swc-118', 'swc-124', 'arbitrary storage', 'missing.?auth')), ('Arithmetic', ('overflow', 'underflow', 'integer', 'arithmetic', 'swc-101', 'precision loss')), ('UncheckedReturn', ('unchecked.?call', 'unchecked.?return', 'return value', 'swc-104', 'call stack', 'low-level call'))]
CATEGORY_ORDER = ['Reentrancy', 'AccessControl', 'Arithmetic', 'UncheckedReturn', 'OtherVulnerability']

def setup_logging(verbose: bool) -> logging.Logger:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    return logging.getLogger('process_dappscan')

def resolve_root(explicit: Optional[str], log: logging.Logger) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    for name in ('DAppSCAN', 'dappscan', 'dapscan', 'Dappscan'):
        candidates.append(ROOT / 'data' / name)
    for name in ('dapscan', 'DAppSCAN', 'Dappscan', 'dappscan'):
        candidates.append(ROOT / 'Raw' / name)
        candidates.append(ROOT / 'raw' / name)
    for c in candidates:
        if not c.is_dir():
            continue
        if (c / 'DAppSCAN-source').is_dir() or (c / 'contracts').is_dir():
            log.info('DAppSCAN root: %s', c)
            return c.resolve()
        if c.name.lower() in {'dappscan-source'} or (c / 'SWCsource').is_dir():
            log.info('DAppSCAN root: %s', c)
            return c.resolve()
    raise FileNotFoundError('DAppSCAN directory not found. Tried data/DAppSCAN and Raw/dapscan (etc.).')

def find_source_base(root: Path) -> Path:
    if (root / 'DAppSCAN-source').is_dir():
        return root / 'DAppSCAN-source'
    if (root / 'contracts').is_dir():
        return root
    for child in root.iterdir():
        if child.is_dir() and (child / 'contracts').is_dir():
            return child
    raise FileNotFoundError(f'No contracts/ under {root}')

def sanitize(s: str, max_len: int=80) -> str:
    s = re.sub('[^A-Za-z0-9_.-]+', '_', s.strip())
    s = re.sub('_+', '_', s).strip('_')
    return (s or 'unknown')[:max_len]

def parse_line_numbers(raw: str) -> list[int]:
    nums: list[int] = []
    for m in LINE_RE.finditer(raw or ''):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        lo, hi = (min(a, b), max(a, b))
        if hi - lo > 20:
            for n in (lo, hi):
                if n not in nums:
                    nums.append(n)
        else:
            for n in range(lo, hi + 1):
                if n not in nums:
                    nums.append(n)
    return nums

def swc_id_from_category(cat: str) -> Optional[str]:
    m = re.search('SWC-(\\d+)', cat or '', re.IGNORECASE)
    return m.group(1) if m else None

def categories_from_swcs(swcs: list[dict[str, Any]]) -> tuple[list[str], list[str], list[int]]:
    cats: set[str] = set()
    swc_ids: list[str] = []
    lines: list[int] = []
    for item in swcs:
        cat_str = str(item.get('category') or '')
        sid = swc_id_from_category(cat_str)
        if sid:
            mapped = None
            for key, val in SWC_CATEGORY_MAP.items():
                if sid.lstrip('0') == key.lstrip('0'):
                    mapped = val
                    break
            if mapped:
                cats.add(mapped)
            else:
                cats.update(categories_from_text(cat_str))
            tag = f'SWC-{int(sid):03d}' if sid.isdigit() else f'SWC-{sid}'
            if tag not in swc_ids:
                swc_ids.append(tag)
        else:
            cats.update(categories_from_text(cat_str))
        lines.extend(parse_line_numbers(str(item.get('lineNumber') or '')))
    if not cats:
        cats.add('OtherVulnerability')
    ordered = [c for c in CATEGORY_ORDER if c in cats]
    return (ordered, swc_ids, sorted(set(lines)))

def categories_from_text(text: str) -> set[str]:
    low = (text or '').lower()
    found: set[str] = set()
    for label, patterns in KEYWORD_RULES:
        for pat in patterns:
            if re.search(pat, low, re.IGNORECASE):
                found.add(label)
                break
    return found

def load_audit_text_for_project(project_dir: Path, audit_roots: list[Path], log: logging.Logger) -> str:
    chunks: list[str] = []
    for pattern in ('**/*.md', '**/*.txt', '**/*.json'):
        for f in project_dir.glob(pattern):
            if f.suffix.lower() == '.json' and 'node_modules' in f.parts:
                continue
            try:
                if f.stat().st_size > 2000000:
                    continue
                chunks.append(f.read_text(encoding='utf-8', errors='replace')[:100000])
            except OSError:
                continue
    proj_name = project_dir.name
    for ar in audit_roots:
        twin = ar / proj_name
        if not twin.is_dir():
            continue
        for pattern in ('**/*.md', '**/*.txt', '**/*.json'):
            for f in twin.glob(pattern):
                try:
                    if f.stat().st_size > 2000000:
                        continue
                    chunks.append(f.read_text(encoding='utf-8', errors='replace')[:100000])
                except OSError:
                    continue
    return '\n'.join(chunks)

def index_swc_jsons(swc_root: Path, log: logging.Logger) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    count = 0
    bad = 0
    if not swc_root.is_dir():
        log.warning('No SWCsource at %s', swc_root)
        return index
    for jf in swc_root.rglob('*.json'):
        try:
            data = json.loads(jf.read_text(encoding='utf-8', errors='replace'))
        except (json.JSONDecodeError, OSError) as e:
            bad += 1
            if bad <= 5:
                log.warning('Bad SWC JSON %s: %s', jf, e)
            continue
        swcs = data.get('SWCs') or data.get('swcs') or []
        if not isinstance(swcs, list):
            swcs = []
        fp = str(data.get('filePath') or '').replace('\\', '/')
        keys = {jf.stem.lower()}
        if fp:
            keys.add(fp.lower())
            if fp.lower().startswith('dappscan-source/'):
                keys.add(fp.split('/', 1)[1].lower())
            keys.add(Path(fp).stem.lower())
            m = re.search('(contracts/.+)$', fp.replace('\\', '/'), re.IGNORECASE)
            if m:
                keys.add(m.group(1).lower())
        for k in keys:
            index[k].extend(swcs)
        count += 1
    log.info('Indexed %d SWC JSON files (%d bad) → %d lookup keys', count, bad, len(index))
    return index

def lookup_swcs(sol_path: Path, source_base: Path, swc_index: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rel = sol_path.relative_to(source_base).as_posix().lower()
    keys = [rel, f"contracts/{rel[len('contracts/'):]}" if rel.startswith('contracts/') else f'contracts/{rel}', sol_path.stem.lower(), f'dappscan-source/{rel}']
    found: list[dict[str, Any]] = []
    seen = set()
    for k in keys:
        for item in swc_index.get(k, []):
            sig = json.dumps(item, sort_keys=True)
            if sig not in seen:
                seen.add(sig)
                found.append(item)
    return found

def extract_pragma(source: str) -> str:
    m = PRAGMA_RE.search(source)
    return m.group(1).strip() if m else 'unknown'

def project_folder_for(sol: Path, contracts_root: Path) -> str:
    try:
        rel = sol.relative_to(contracts_root)
        return rel.parts[0] if rel.parts else contracts_root.name
    except ValueError:
        return sol.parent.name

def build_id(project: str, contract_stem: str) -> str:
    return f'DAPPSCAN_{sanitize(project)}_{sanitize(contract_stem)}'

def process(args: argparse.Namespace) -> int:
    log = setup_logging(args.verbose)
    root = resolve_root(args.root, log)
    source_base = find_source_base(root)
    contracts_root = source_base / 'contracts'
    swc_root = source_base / 'SWCsource'
    audit_roots = [source_base / 'audit_report', root / 'audit_report', ROOT / 'Raw' / 'dive' / 'dapscan' / 'DAppSCAN-source' / 'audit_report', ROOT / 'raw' / 'dive' / 'dapscan' / 'DAppSCAN-source' / 'audit_report']
    audit_roots = [p for p in audit_roots if p.is_dir()]
    if not contracts_root.is_dir():
        raise FileNotFoundError(f'Missing contracts/ at {contracts_root}')
    out_path = ROOT / 'data' / 'processed' / 'dappscan_vulnerable.jsonl'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    swc_index = index_swc_jsons(swc_root, log)
    project_dirs = [p for p in contracts_root.iterdir() if p.is_dir()]
    log.info('Projects under contracts/: %d', len(project_dirs))
    audit_cache: dict[str, str] = {}
    stats = Counter()
    category_counts = Counter()
    written_ids: set[str] = set()
    sol_files = sorted(contracts_root.rglob('*.sol'))
    log.info('Total .sol files found: %d', len(sol_files))
    if args.limit:
        sol_files = sol_files[:args.limit]
        log.info('Limiting to %d .sol files', args.limit)
    with out_path.open('w', encoding='utf-8') as out:
        for sol in sol_files:
            stats['sol_seen'] += 1
            if 'node_modules' in sol.parts:
                stats['skipped_node_modules'] += 1
                continue
            project = project_folder_for(sol, contracts_root)
            try:
                source = sol.read_text(encoding='utf-8', errors='replace')
            except OSError as e:
                stats['skipped_read_error'] += 1
                log.warning('Read fail %s: %s', sol, e)
                continue
            if len(source.strip()) < 20:
                stats['skipped_empty'] += 1
                continue
            swcs = lookup_swcs(sol, source_base, swc_index)
            if swcs:
                categories, swc_ids, line_numbers = categories_from_swcs(swcs)
                stats['linked_swc'] += 1
            else:
                if project not in audit_cache:
                    proj_dir = contracts_root / project
                    audit_cache[project] = load_audit_text_for_project(proj_dir, audit_roots, log)
                blob = f"{project}\n{audit_cache.get(project, '')}\n{source[:5000]}"
                cats = categories_from_text(blob)
                if not cats:
                    cats = {'OtherVulnerability'}
                    stats['defaulted_other'] += 1
                else:
                    stats['keyword_labeled'] += 1
                categories = [c for c in CATEGORY_ORDER if c in cats]
                swc_ids = []
                line_numbers = []
            if not categories:
                categories = ['OtherVulnerability']
            rid = build_id(project, sol.stem)
            if rid in written_ids:
                stats['id_collision'] += 1
                try:
                    rel = sol.relative_to(contracts_root).as_posix()
                except ValueError:
                    rel = sol.name
                rid = build_id(project, sanitize(rel.replace('/', '_'), 100))
            written_ids.add(rid)
            try:
                rel_path = sol.relative_to(source_base).as_posix()
            except ValueError:
                rel_path = str(sol)
            rec = {'id': rid, 'source_code': source, 'bytecode': None, 'compiler_version': extract_pragma(source), 'labels': {'is_vulnerable': True, 'categories': categories, 'swc_ids': swc_ids, 'line_numbers': line_numbers}, 'intent_label': None, 'dataset_source': 'DAppSCAN', 'target_modules': ['LLM_EVAL'], 'project': project, 'contract_name': sol.stem, 'source_path': rel_path}
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            stats['written'] += 1
            for c in categories:
                category_counts[c] += 1
            if stats['sol_seen'] % 500 == 0:
                log.info('Progress: %d/%d sol (written=%d, swc_linked=%d)', stats['sol_seen'], len(sol_files), stats['written'], stats['linked_swc'])
    log.info('======== DAppSCAN processing complete ========')
    log.info('Projects scanned: %d', len(project_dirs))
    log.info('.sol files seen: %d', stats['sol_seen'])
    log.info('Records written: %d → %s', stats['written'], out_path)
    log.info('Linked via SWC JSON: %d', stats['linked_swc'])
    log.info('Labeled via keywords: %d', stats['keyword_labeled'])
    log.info('Defaulted to OtherVulnerability: %d', stats['defaulted_other'])
    log.info('Skipped empty: %d', stats['skipped_empty'])
    log.info('Skipped read errors: %d', stats['skipped_read_error'])
    log.info('Skipped node_modules: %d', stats['skipped_node_modules'])
    log.info('ID collisions remapped: %d', stats['id_collision'])
    log.info('Category prevalence: %s', dict(category_counts))
    log.info('Audit report roots used: %s', [str(p) for p in audit_roots] or '(none)')
    verify_output(out_path, log)
    return 0

def verify_output(path: Path, log: logging.Logger) -> None:
    log.info('======== Verification: first 2 JSON lines ========')
    if not path.is_file() or path.stat().st_size == 0:
        log.warning('Output missing or empty: %s', path)
        return
    with path.open('r', encoding='utf-8') as f:
        for _ in range(2):
            line = f.readline()
            if not line:
                break
            obj = json.loads(line)
            preview = {'id': obj.get('id'), 'project': obj.get('project'), 'contract_name': obj.get('contract_name'), 'compiler_version': obj.get('compiler_version'), 'labels': obj.get('labels'), 'dataset_source': obj.get('dataset_source'), 'target_modules': obj.get('target_modules'), 'intent_label': obj.get('intent_label'), 'bytecode': obj.get('bytecode'), 'source_code_chars': len(obj.get('source_code') or ''), 'source_path': obj.get('source_path')}
            print(json.dumps(preview, indent=2))

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Process DAppSCAN into standardized JSONL')
    p.add_argument('--root', default=None, help='Path to DAppSCAN dataset root')
    p.add_argument('--limit', type=int, default=None, help='Max .sol files to process')
    p.add_argument('-v', '--verbose', action='store_true')
    return p.parse_args(argv)
if __name__ == '__main__':
    try:
        raise SystemExit(process(parse_args()))
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.exception('process_dappscan failed')
        raise
