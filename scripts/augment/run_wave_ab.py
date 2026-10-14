#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, pick_minority_seeds, pick_reentrancy_seeds, write_seed_manifest
from dead_code_insertion import process_seed as process_dead
from identifier_renaming import process_seed as process_rename

def reset_outputs() -> None:
    for p in (OUT_JSONL, FAIL_JSONL):
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            p.unlink()
        p.write_text('', encoding='utf-8')

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

def write_review(path: Path, ok_rows: list[dict], fail_rows: list[dict], seeds: list[dict]) -> None:
    by_tech = Counter((r.get('transformation_techniques', ['?'])[0] for r in ok_rows))
    by_cls = Counter((r.get('primary_vulnerability_type') for r in ok_rows))
    by_level = Counter((r.get('transformation_level') for r in ok_rows))
    lexical = [r for r in ok_rows if r.get('transformation_level') == 'lexical']
    identical = sum((1 for r in lexical if 'bytecode_identical_to_parent=true' in (r.get('notes') or '')))
    lines = ['# Wave A1 + B1 batch review', '', '## Counts', f'- Seeds used: {len(seeds)}', f'- Verified variants (benchmark): {len(ok_rows)}', f'- Failed / rejected: {len(fail_rows)}', '', '### By technique']
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
    lines += ['', '## LLM vs bytecode lesson (advisor checkpoint)', '', 'Level 1 `identifier_renaming` is **lexical**. Variable/function names are stripped when', 'Solidity compiles to EVM bytecode. Therefore:', '', f'- Lexical variants written: {len(lexical)}', f'- Of those with bytecode identical to parent: {identical}', '', 'Those Level-1 rows are for the **LLM / source** path. Even when bytecode is not', 'byte-identical (public getters/selectors, solc version drift, or residual renames),', 'do **not** treat Level 1 as a GCN/fingerprint stress test - that is the advisor lesson.', 'Level 2 `dead_code_insertion` **does** change control-structure surface and is a', 'real structural stress for GCN/fingerprint.', '', '## Next', '', 'Do **not** start Level 3 (control-flow flattening) until this lesson is clear and', 'Wave A2/A3 or B2/B3 are scheduled. First milestone A1+B1 is complete when verified', 'count is roughly 40+.', '', f'Outputs: `{OUT_JSONL}` / `{FAIL_JSONL}`']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main() -> int:
    print('[1/4] picking seeds (20 minority + 5 reentrancy)...')
    seeds_min = pick_minority_seeds()
    seeds_re = pick_reentrancy_seeds(5)
    write_seed_manifest(seeds_min + seeds_re)
    print(f'  minority={len(seeds_min)} reentrancy={len(seeds_re)} -> {SEED_MANIFEST}')
    print('[2/4] resetting output JSONL...')
    reset_outputs()
    print('[3/4] Wave A1 identifier_renaming on minority seeds...')
    a_ok = a_fail = 0
    for s in seeds_min:
        r = process_rename(s)
        print(f"  [A1 {r['status']}] {r['record']['contract_id']}")
        if r['status'] == 'OK':
            a_ok += 1
        else:
            a_fail += 1
    print('[4/4] Wave B1 dead_code_insertion on minority + reentrancy...')
    b_ok = b_fail = 0
    for s in seeds_min + seeds_re:
        r = process_dead(s)
        print(f"  [B1 {r['status']}] {r['record']['contract_id']}")
        if r['status'] == 'OK':
            b_ok += 1
        else:
            b_fail += 1
    ok_rows = load_jsonl(OUT_JSONL)
    fail_rows = load_jsonl(FAIL_JSONL)
    review_path = Path(__file__).resolve().parents[2] / 'data' / 'processed' / 'augment_wave_ab_review.md'
    write_review(review_path, ok_rows, fail_rows, seeds_min + seeds_re)
    print()
    print('=== SUMMARY ===')
    print(f'A1 OK/FAIL: {a_ok}/{a_fail}')
    print(f'B1 OK/FAIL: {b_ok}/{b_fail}')
    print(f'benchmark rows: {len(ok_rows)}')
    print(f'failed rows: {len(fail_rows)}')
    print(f'review: {review_path}')
    return 0 if len(ok_rows) >= 20 else 1
if __name__ == '__main__':
    raise SystemExit(main())
