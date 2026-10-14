#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional
ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / 'data' / 'processed'
BENIGN_POOL = PROCESSED / 'benign_pool'
REQUIRED_KEYS = ('id', 'source_code', 'labels', 'intent_label', 'dataset_source', 'target_modules')

def discover_jsonl() -> list[Path]:
    files: list[Path] = []
    if PROCESSED.is_dir():
        files.extend(sorted(PROCESSED.glob('*.jsonl')))
    if BENIGN_POOL.is_dir():
        files.extend(sorted(BENIGN_POOL.glob('*.jsonl')))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out

def schema_ok(row: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = [k for k in REQUIRED_KEYS if k not in row]
    return (len(missing) == 0, missing)

def is_vulnerable(row: dict[str, Any]) -> Optional[bool]:
    labels = row.get('labels')
    if isinstance(labels, dict) and 'is_vulnerable' in labels:
        return bool(labels['is_vulnerable'])
    return None

def summarize_file(path: Path) -> dict[str, Any]:
    total = 0
    vuln = 0
    benign = 0
    unknown = 0
    modules: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    fail_rows = 0
    missing_key_counts: Counter[str] = Counter()
    sample_fail_id: Optional[str] = None
    with path.open(encoding='utf-8', errors='replace') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                fail_rows += 1
                missing_key_counts['<invalid_json>'] += 1
                if sample_fail_id is None:
                    sample_fail_id = f'line:{line_no}'
                continue
            if not isinstance(row, dict):
                fail_rows += 1
                missing_key_counts['<not_object>'] += 1
                continue
            total += 1
            ok, missing = schema_ok(row)
            if not ok:
                fail_rows += 1
                for k in missing:
                    missing_key_counts[k] += 1
                if sample_fail_id is None:
                    sample_fail_id = str(row.get('id', f'line:{line_no}'))
            v = is_vulnerable(row)
            if v is True:
                vuln += 1
            elif v is False:
                benign += 1
            else:
                unknown += 1
            src = row.get('dataset_source')
            if isinstance(src, str) and src:
                sources[src] += 1
            tm = row.get('target_modules')
            if isinstance(tm, list):
                for m in tm:
                    modules[str(m)] += 1
            elif tm is not None:
                modules[str(tm)] += 1
    if sources:
        dataset_name = sources.most_common(1)[0][0]
    else:
        dataset_name = path.stem
    if modules:
        target_module = ', '.join((m for m, _ in modules.most_common()))
    else:
        target_module = '—'
    status = 'PASS' if fail_rows == 0 and total > 0 else 'FAIL' if total > 0 or fail_rows else 'EMPTY'
    return {'path': path, 'dataset_name': dataset_name, 'target_module': target_module, 'records': total, 'vulnerable': vuln, 'benign': benign, 'unknown_label': unknown, 'schema_status': status, 'fail_rows': fail_rows, 'missing_keys': dict(missing_key_counts), 'sample_fail_id': sample_fail_id}

def md_escape(s: str) -> str:
    return s.replace('|', '\\|')

def print_markdown(rows: list[dict[str, Any]]) -> None:
    print('| Dataset Name | Target Module | Record Count | Vulnerable vs Benign | Schema Status |')
    print('|---|---|---:|---|---|')
    for r in rows:
        vb = f"{r['vulnerable']} vuln / {r['benign']} benign"
        if r['unknown_label']:
            vb += f" / {r['unknown_label']} unknown"
        print(f"| {md_escape(r['dataset_name'])} | {md_escape(r['target_module'])} | {r['records']} | {vb} | **{r['schema_status']}** |")
    print()
    print(f'**Files checked:** {len(rows)}')
    print(f"**Total records:** {sum((r['records'] for r in rows))}")
    fails = [r for r in rows if r['schema_status'] == 'FAIL']
    if fails:
        print()
        print('### Schema FAIL details')
        for r in fails:
            try:
                rel = r['path'].relative_to(ROOT)
            except ValueError:
                rel = r['path']
            print(f"- `{rel}`: {r['fail_rows']} bad row(s); missing keys {r['missing_keys']}; sample id `{r['sample_fail_id']}`")

def main() -> int:
    files = discover_jsonl()
    if not files:
        print(f'[warn] No .jsonl files under {PROCESSED} or {BENIGN_POOL}', file=sys.stderr)
        return 0
    print(f'# Dataset verification - `{PROCESSED.relative_to(ROOT).as_posix()}`\n')
    summaries = [summarize_file(p) for p in files]
    print_markdown(summaries)
    if any((r['schema_status'] == 'FAIL' for r in summaries)):
        return 1
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
