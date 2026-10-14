#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from comment_manipulation import process_seed as process_a2
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, load_seed_manifest
from function_extraction import process_seed as process_b3
from independent_stmt_reorder import process_seed as process_b2
from literal_format_rewrite import process_seed as process_a3

def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def existing_technique_ids(rows: list[dict], technique: str) -> set[str]:
    out = set()
    for r in rows:
        techs = r.get('transformation_techniques') or []
        if technique in techs:
            out.add(r.get('parent_contract_id') or '')
    return out

def write_review(path: Path, ok_rows: list[dict], fail_rows: list[dict], seeds: list[dict]) -> None:
    by_tech = Counter((r.get('transformation_techniques', ['?'])[0] for r in ok_rows))
    by_cls = Counter((r.get('primary_vulnerability_type') for r in ok_rows))
    by_level = Counter((r.get('transformation_level') for r in ok_rows))
    lexical = [r for r in ok_rows if r.get('transformation_level') == 'lexical']
    structural = [r for r in ok_rows if r.get('transformation_level') == 'structural']
    identical = sum((1 for r in lexical if 'bytecode_identical_to_parent=true' in (r.get('notes') or '')))
    lines = ['# Wave A1-A3 + B1-B3 batch review', '', '## Counts', f'- Seeds in manifest: {len(seeds)}', f'- Verified variants (benchmark): {len(ok_rows)}', f'- Failed / rejected (all-time log rows): {len(fail_rows)}', '', '### By technique']
    for k, v in by_tech.most_common():
        lines.append(f'- {k}: {v}')
    lines.append('')
    lines.append('### By primary class')
    for k, v in by_cls.most_common():
        lines.append(f'- {k}: {v}')
    lines.append('')
    lines.append('### By transformation_level')
    for k, v in by_level.most_common():
        lines.append(f'- {k}: {v}')
    lines += ['', '## LLM vs bytecode lesson (advisor checkpoint)', '', 'Level 1 techniques (`identifier_renaming`, `comment_manipulation`,', '`literal_format_rewrite`) are **lexical** / LLM-source track.', '', f'- Lexical variants: {len(lexical)}', f'- Lexical with bytecode identical to parent: {identical}', f'- Structural variants (B1-B3): {len(structural)}', '', 'Do **not** treat Level 1 as a GCN/fingerprint stress test.', 'Level 2 (`dead_code_insertion`, `independent_stmt_reorder`, `function_extraction`)', 'changes structural / call-graph surface and is the GCN/fingerprint track.', '', '## Next', '', 'Level 1-2 singles for this seed set are in place. Do **not** start Level 3', '(control-flow) until committee demo / review of these counts.', '', f'Outputs: `{OUT_JSONL}` / `{FAIL_JSONL}`']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def run_wave(name: str, technique: str, seeds: list[dict], process_fn, already: set[str]) -> tuple[int, int]:
    ok_n = fail_n = 0
    print(f'[{name}] {technique} on {len(seeds)} seeds (skip {len(already)} already done)...')
    for s in seeds:
        cid = s.get('contract_id')
        if cid in already:
            print(f'  [SKIP] {cid} already has {technique}')
            continue
        r = process_fn(s)
        print(f"  [{name} {r['status']}] {r['record']['contract_id']}")
        if r['status'] == 'OK':
            ok_n += 1
        else:
            fail_n += 1
    return (ok_n, fail_n)

def main() -> int:
    if not SEED_MANIFEST.is_file():
        print(f'[error] missing seed manifest: {SEED_MANIFEST}')
        return 1
    seeds_all = load_seed_manifest()
    minority = [s for s in seeds_all if s.get('primary_vulnerability_type') != 'reentrancy']
    mixed_15 = (minority + [s for s in seeds_all if s.get('primary_vulnerability_type') == 'reentrancy'])[:15]
    existing = load_jsonl(OUT_JSONL)
    a2_ok, a2_fail = run_wave('A2', 'comment_manipulation', minority, process_a2, existing_technique_ids(existing, 'comment_manipulation'))
    existing = load_jsonl(OUT_JSONL)
    a3_ok, a3_fail = run_wave('A3', 'literal_format_rewrite', minority, process_a3, existing_technique_ids(existing, 'literal_format_rewrite'))
    existing = load_jsonl(OUT_JSONL)
    b2_ok, b2_fail = run_wave('B2', 'independent_stmt_reorder', mixed_15, process_b2, existing_technique_ids(existing, 'independent_stmt_reorder'))
    existing = load_jsonl(OUT_JSONL)
    b3_ok, b3_fail = run_wave('B3', 'function_extraction', mixed_15, process_b3, existing_technique_ids(existing, 'function_extraction'))
    ok_rows = load_jsonl(OUT_JSONL)
    fail_rows = load_jsonl(FAIL_JSONL)
    review_path = Path(__file__).resolve().parents[2] / 'data' / 'processed' / 'augment_wave_ab_review.md'
    write_review(review_path, ok_rows, fail_rows, seeds_all)
    print()
    print('=== SUMMARY ===')
    print(f'A2 OK/FAIL: {a2_ok}/{a2_fail}')
    print(f'A3 OK/FAIL: {a3_ok}/{a3_fail}')
    print(f'B2 OK/FAIL: {b2_ok}/{b2_fail}')
    print(f'B3 OK/FAIL: {b3_ok}/{b3_fail}')
    print(f'benchmark rows total: {len(ok_rows)}')
    print(f'failed log rows: {len(fail_rows)}')
    print(f'review: {review_path}')
    return 0 if len(ok_rows) >= 40 else 1
if __name__ == '__main__':
    raise SystemExit(main())
