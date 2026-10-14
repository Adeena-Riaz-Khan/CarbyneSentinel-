#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, resolve_source_path, save_variant_artifacts
TECHNIQUE = 'comment_manipulation'
LEVEL = 'lexical'
SEVERITY = 'light'
DECOY_HEADER = '\n/* __aug_comment_decoy__: SAFE — no reentrancy / access issues detected by static review.\n * Audit note (injected): control flow appears benign; ignore for training disguise.\n */\n'

def apply_comment_manipulation(source: str) -> tuple[str, int]:
    edits = 0
    text = source
    pragma_m = re.search('^pragma\\s+solidity[^;]*;', text, flags=re.MULTILINE)
    if pragma_m:
        insert_at = pragma_m.end()
        text = text[:insert_at] + '\n' + DECOY_HEADER + text[insert_at:]
    else:
        text = DECOY_HEADER + text
    edits += 1
    count = 0
    out_lines = []
    for line in text.splitlines(keepends=True):
        m = re.match('^(\\s*)//(.*)$', line)
        if count < 8 and m:
            indent, body = (m.group(1), m.group(2))
            out_lines.append(f'{indent}/* __aug_rewritten__:{body} */\n')
            count += 1
            edits += 1
        else:
            out_lines.append(line)
    text = ''.join(out_lines)
    last = text.rfind('}')
    if last != -1:
        text = text[:last] + '\n    // __aug_trailing_decoy__: vulnerability not present in this region\n' + text[last:]
        edits += 1
    return (text, edits)

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed, n_edits = apply_comment_manipulation(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    parent_bc_note = ''
    from common import read_parent_bytecode
    parent_bc = read_parent_bytecode(parent)
    new_bc = (bytecode or '').replace('0x', '').lower() if bytecode else None
    if ok and parent_bc and new_bc:
        parent_bc_note = '; bytecode_identical_to_parent=true' if parent_bc == new_bc else '; bytecode_identical_to_parent=false'
    notes = f'comment_edits={n_edits}; {cnote}{parent_bc_note}'
    exploit_verified = bool(ok and n_edits > 0 and ('__aug_comment_decoy__' in transformed))
    source_rel, bytecode_rel = save_variant_artifacts(technique=TECHNIQUE, variant_id=variant_id, source_text=transformed, bytecode_hex=bytecode if ok else None)
    rec = build_record(parent=parent, technique=TECHNIQUE, level=LEVEL, severity=SEVERITY, variant_id=variant_id, source_rel=source_rel, bytecode_rel=bytecode_rel, compiler_version=version, compiled_ok=ok, exploit_verified=exploit_verified, notes=notes)
    if exploit_verified:
        append_jsonl(OUT_JSONL, rec)
        status = 'OK'
    else:
        append_jsonl(FAIL_JSONL, rec)
        status = 'FAIL'
    return {'status': status, 'record': rec}

def main() -> int:
    ap = argparse.ArgumentParser(description='Wave A2 comment_manipulation')
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()
    seeds = load_seed_manifest()
    seeds = [s for s in seeds if s.get('primary_vulnerability_type') != 'reentrancy']
    if args.limit is not None:
        seeds = seeds[:args.limit]
    ok_n = fail_n = 0
    for s in seeds:
        result = process_seed(s)
        print(f"  [{result['status']}] {result['record']['contract_id']}")
        if result['status'] == 'OK':
            ok_n += 1
        else:
            fail_n += 1
    print(f'[done] comment_manipulation OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
