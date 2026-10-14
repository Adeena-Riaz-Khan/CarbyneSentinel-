#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional
ROOT = Path(__file__).resolve().parent.parent
SEARCH_ROOTS = [ROOT / 'data' / 'SlitherHF', ROOT / 'Raw' / 'slither_hf', ROOT / 'raw' / 'slither_hf']
OUT_DEFAULT = ROOT / 'data' / 'processed' / 'benign_pool' / 'slither_benign.jsonl'
DATA_SUFFIXES = {'.parquet', '.csv', '.json', '.jsonl'}
SKIP_NAME_EXACT = {'label_mappings.json', 'dataset_infos.json', 'big-splits.csv', 'small-splits.csv', '.gitattributes'}
SKIP_DIR_NAMES = {'.git', '.cache', '__pycache__', '.huggingface'}
ADDR_RE = re.compile('^(0x)?[0-9a-fA-F]{40}$')

def discover_data_files(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            if any((part.lower() in SKIP_DIR_NAMES for part in path.parts)):
                continue
            if path.name.lower() in SKIP_NAME_EXACT:
                continue
            if path.suffix.lower() not in DATA_SUFFIXES:
                continue
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    return found

def warn_missing() -> None:
    print('[warn] No Slither HF data files (.parquet / .csv / .json / .jsonl) found.\n\nPlace the downloaded Hugging Face dataset here (either location works):\n  1) data/SlitherHF/          (preferred)\n  2) Raw/slither_hf/          (fallback — matches current clone layout)\n\nExpected contents (from mwritescode/slither-audited-smart-contracts):\n  data/raw/contracts0.parquet ... contracts8.parquet\n  data/label_mappings.json        (optional for this script)\n  data/big-splits.csv / small-splits.csv  (ignored for benign pool)\n\nQuick download (from repo root):\n  git lfs install\n  git clone https://huggingface.co/datasets/mwritescode/slither-audited-smart-contracts Raw/slither_hf\n  # or:  huggingface-cli download mwritescode/slither-audited-smart-contracts --repo-type dataset --local-dir data/SlitherHF\n\nRe-run:  python scripts/process_slither_hf.py\nExiting gracefully (status 0).', file=sys.stderr)

def _parse_slither_payload(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode('utf-8', errors='replace')
    if isinstance(raw, str):
        s = raw.strip()
        if not s or s in ('{}', 'null', 'None'):
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            if s.startswith('[') and s.endswith(']'):
                try:
                    return json.loads(s.replace("'", '"'))
                except json.JSONDecodeError:
                    return s
            return s
    return raw

def is_slither_clean(slither_field: Any) -> bool:
    parsed = _parse_slither_payload(slither_field)
    if parsed is None:
        return False
    if isinstance(parsed, list):
        if len(parsed) == 0:
            return True
        norm = []
        for x in parsed:
            if isinstance(x, str):
                norm.append(x.strip().lower())
            else:
                norm.append(x)
        if all((isinstance(x, str) for x in norm)):
            return set(norm) <= {'safe'}
        if all((isinstance(x, int) for x in norm)):
            return set(norm) == {4}
        return False
    if isinstance(parsed, str):
        return parsed.strip().lower() in ('safe', '[]', '')
    if isinstance(parsed, dict):
        if parsed.get('success') is False:
            return False
        results = parsed.get('results', parsed)
        if results is None or results == {} or results == []:
            return True
        if isinstance(results, dict):
            detectors = results.get('detectors')
            if detectors is None:
                return len(results) == 0
            if isinstance(detectors, list) and len(detectors) == 0:
                return True
            return False
        return False
    return False

def normalize_address(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s.startswith('0x'):
        body = s[2:]
    else:
        body = s
    if not ADDR_RE.match('0x' + body if not body.startswith('0x') else body):
        if re.fullmatch('[0-9a-fA-F]{40}', body):
            return '0x' + body.lower()
        return None
    return '0x' + body.lower()

def pick_field(row: dict[str, Any], *names: str) -> Any:
    lower = {str(k).lower(): v for k, v in row.items()}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def iter_parquet_rows(path: Path) -> Iterator[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        try:
            import pandas as pd
        except ImportError as e:
            raise SystemExit(f'pandas + pyarrow are required to read .parquet files.\n  pip install pandas pyarrow\nDetail: {e}') from e
        try:
            df = pd.read_parquet(path)
        except Exception as e:
            print(f'[warn] skipping unreadable parquet {path}: {e}', file=sys.stderr)
            return
        for rec in df.to_dict(orient='records'):
            yield {str(k): v for k, v in rec.items()}
        return
    try:
        pf = pq.ParquetFile(path)
    except Exception as e:
        print(f'[warn] skipping unreadable parquet {path}: {e}', file=sys.stderr)
        return
    for batch in pf.iter_batches(batch_size=1024):
        cols = batch.column_names
        as_dict = {name: batch.column(i).to_pylist() for i, name in enumerate(cols)}
        n = batch.num_rows
        for i in range(n):
            yield {name: as_dict[name][i] for name in cols}

def iter_csv_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row)

def iter_json_rows(path: Path) -> Iterator[dict[str, Any]]:
    text = path.read_text(encoding='utf-8', errors='replace').strip()
    if not text:
        return
    if path.suffix.lower() == '.jsonl' or ('\n' in text and text.lstrip().startswith('{')):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        print(f'[warn] skipping bad json {path}: {e}', file=sys.stderr)
        return
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                yield item
    elif isinstance(obj, dict):
        if any((k in obj for k in ('source_code', 'bytecode', 'address', 'contracts'))):
            yield obj
        else:
            for v in obj.values():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            yield item
                    return
            yield obj

def iter_file_rows(path: Path) -> Iterator[dict[str, Any]]:
    suf = path.suffix.lower()
    if suf == '.parquet':
        yield from iter_parquet_rows(path)
    elif suf == '.csv':
        yield from iter_csv_rows(path)
    elif suf in {'.json', '.jsonl'}:
        yield from iter_json_rows(path)

def row_to_benign(row: dict[str, Any], idx: int) -> Optional[dict[str, Any]]:
    slither = pick_field(row, 'slither', 'results', 'slither_report', 'labels')
    if not is_slither_clean(slither):
        return None
    source = pick_field(row, 'source_code', 'source', 'code', 'solidity')
    if source is None or (isinstance(source, float) and str(source) == 'nan'):
        return None
    source_s = str(source).strip()
    if not source_s or source_s.lower() == 'nan':
        return None
    addr_raw = pick_field(row, 'address', 'contracts', 'contract', 'contract_address')
    addr = normalize_address(addr_raw)
    if not addr:
        addr = f'unknown_{idx:06d}'
    bytecode = pick_field(row, 'bytecode', 'deployed_bytecode', 'runtime_bytecode')
    if bytecode is not None:
        bc = str(bytecode).strip()
        if not bc or bc.lower() == 'nan':
            bc = None
        elif not bc.startswith('0x') and re.fullmatch('[0-9a-fA-F]+', bc or ''):
            bc = '0x' + bc
    else:
        bc = None
    cid = f'SLITHERHF_{addr}' if addr.startswith('0x') else f'SLITHERHF_{idx:06d}'
    return {'id': cid, 'source_code': source_s, 'bytecode': bc, 'compiler_version': None, 'labels': {'is_vulnerable': False, 'categories': [], 'swc_ids': [], 'line_numbers': []}, 'intent_label': None, 'dataset_source': 'SlitherHF', 'target_modules': ['BENIGN_POOL'], 'address': addr if addr.startswith('0x') else None, 'slither_clean': True}

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Process Slither HF into benign_pool JSONL')
    p.add_argument('--root', type=Path, action='append', default=None, help='Extra/override search root (repeatable). Default: data/SlitherHF + Raw/slither_hf')
    p.add_argument('--out', type=Path, default=OUT_DEFAULT, help='Output JSONL path')
    p.add_argument('--limit', type=int, default=None, help='Max benign rows to write (smoke test)')
    return p.parse_args(argv)

def main(argv: Optional[list[str]]=None) -> int:
    args = parse_args(argv)
    roots = [Path(r) for r in args.root] if args.root else list(SEARCH_ROOTS)
    roots = [r if r.is_absolute() else ROOT / r for r in roots]
    files = discover_data_files(roots)
    if not files:
        warn_missing()
        return 0
    print(f'[info] found {len(files)} data file(s):')
    for f in files:
        try:
            rel = f.relative_to(ROOT)
        except ValueError:
            rel = f
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f'  - {rel}  ({size_mb:.1f} MB)')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    scanned = 0
    skipped_unclean = 0
    skipped_no_source = 0
    dedup: set[str] = set()
    errors = Counter()
    with args.out.open('w', encoding='utf-8') as out_f:
        for path in files:
            print(f'[info] reading {path.name} ...', flush=True)
            try:
                row_iter: Iterable[dict[str, Any]] = iter_file_rows(path)
            except SystemExit:
                raise
            except Exception as e:
                errors[str(e)] += 1
                print(f'[warn] failed to open {path}: {e}', file=sys.stderr)
                continue
            for row in row_iter:
                scanned += 1
                slither = pick_field(row, 'slither', 'results', 'slither_report', 'labels')
                if not is_slither_clean(slither):
                    skipped_unclean += 1
                    continue
                rec = row_to_benign(row, written)
                if rec is None:
                    skipped_no_source += 1
                    continue
                if rec['id'] in dedup:
                    continue
                dedup.add(rec['id'])
                out_f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                written += 1
                if args.limit is not None and written >= args.limit:
                    break
            if args.limit is not None and written >= args.limit:
                break
    print('\n=== Slither HF benign pool ===')
    print(f'files scanned:     {len(files)}')
    print(f'rows scanned:      {scanned}')
    print(f'skipped (findings):{skipped_unclean}')
    print(f'skipped (no src):  {skipped_no_source}')
    print(f'benign written:    {written}')
    print(f'output:            {args.out}')
    if written == 0:
        print('[warn] No clean/benign contracts extracted. Check that parquet downloads finished (git lfs pull) and results field is present.', file=sys.stderr)
    else:
        with args.out.open(encoding='utf-8') as f:
            sample = json.loads(f.readline())
        print('\n=== sample ===')
        print(f"  id:             {sample.get('id')}")
        print(f"  address:        {sample.get('address')}")
        print(f"  is_vulnerable:  {sample.get('labels', {}).get('is_vulnerable')}")
        print(f"  dataset_source: {sample.get('dataset_source')}")
        print(f"  target_modules: {sample.get('target_modules')}")
        src = (sample.get('source_code') or '')[:100].replace('\n', ' ')
        print(f'  source_code:    {src}...')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
