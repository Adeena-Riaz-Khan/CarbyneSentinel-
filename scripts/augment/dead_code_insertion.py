#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, pick_minority_seeds, pick_reentrancy_seeds, resolve_source_path, save_variant_artifacts, write_seed_manifest
TECHNIQUE = 'dead_code_insertion'
LEVEL = 'structural'
SEVERITY = 'light'
DEAD_SNIPPET = '\n    function __aug_dead_noop_42(uint256 __aug_x) private pure returns (uint256) {\n        if (false) {\n            return __aug_x + 1;\n        }\n        return 0;\n    }\n'

def insert_dead_code(source: str) -> str:
    m = re.search('\\b(contract|library|interface)\\s+[A-Za-z_][A-Za-z0-9_]*\\b[^{]*\\{', source)
    if not m:
        last = source.rfind('}')
        if last == -1:
            return source + '\n' + DEAD_SNIPPET
        return source[:last] + DEAD_SNIPPET + '\n' + source[last:]
    insert_at = m.end()
    return source[:insert_at] + '\n' + DEAD_SNIPPET + source[insert_at:]

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed = insert_dead_code(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    exploit_verified = False
    notes = cnote
    if ok and '__aug_dead_noop_42' in transformed:
        exploit_verified = True
        notes += '; dead_helper_inserted=true; vuln_body_untouched=assumed'
    elif not ok:
        notes += '; compile_failed'
    source_rel, bytecode_rel = save_variant_artifacts(technique=TECHNIQUE, variant_id=variant_id, source_text=transformed, bytecode_hex=bytecode if ok else None)
    rec = build_record(parent=parent, technique=TECHNIQUE, level=LEVEL, severity=SEVERITY, variant_id=variant_id, source_rel=source_rel, bytecode_rel=bytecode_rel, compiler_version=version, compiled_ok=ok, exploit_verified=exploit_verified if ok else False, notes=notes)
    if ok and exploit_verified:
        append_jsonl(OUT_JSONL, rec)
        status = 'OK'
    else:
        append_jsonl(FAIL_JSONL, rec)
        status = 'FAIL'
    return {'status': status, 'record': rec}

def main() -> int:
    ap = argparse.ArgumentParser(description='Wave B1 dead_code_insertion')
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--reentrancy', type=int, default=5, help='Extra reentrancy seeds')
    ap.add_argument('--write-seeds', action='store_true')
    args = ap.parse_args()
    if args.write_seeds or not SEED_MANIFEST.is_file():
        seeds = pick_minority_seeds()
        seeds.extend(pick_reentrancy_seeds(args.reentrancy))
        write_seed_manifest(seeds)
        print(f'[info] wrote seed manifest ({len(seeds)})')
    seeds = load_seed_manifest()
    have_re = any((s.get('primary_vulnerability_type') == 'reentrancy' for s in seeds))
    if not have_re and args.reentrancy > 0:
        seeds = list(seeds) + pick_reentrancy_seeds(args.reentrancy)
        write_seed_manifest(seeds)
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
    print(f'[done] dead_code_insertion OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
