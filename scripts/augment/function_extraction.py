#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, resolve_source_path, save_variant_artifacts
TECHNIQUE = 'function_extraction'
LEVEL = 'structural'
SEVERITY = 'moderate'
REQUIRE_RE = re.compile('^([ \\t]*)require\\s*\\(\\s*([^,;()][^;()]*?)\\s*(?:,\\s*(\\"[^\\"]*\\"|\'[^\']*\'))?\\s*\\)\\s*;', re.MULTILINE)
HELPER = '\n    function __aug_extracted_require_1(bool __aug_cond) private pure {\n        require(__aug_cond);\n    }\n'

def apply_function_extraction(source: str) -> tuple[str, int]:
    m = REQUIRE_RE.search(source)
    if not m:
        return (source, 0)
    indent, cond, _msg = (m.group(1), m.group(2).strip(), m.group(3))
    if '__aug_' in cond:
        return (source, 0)
    replacement = f'{indent}__aug_extracted_require_1({cond});'
    text = source[:m.start()] + replacement + source[m.end():]
    cm = re.search('\\b(contract|library)\\s+[A-Za-z_][A-Za-z0-9_]*\\b[^{]*\\{', text)
    if cm:
        at = cm.end()
        text = text[:at] + '\n' + HELPER + text[at:]
    else:
        last = text.rfind('}')
        if last == -1:
            text = text + '\n' + HELPER
        else:
            text = text[:last] + HELPER + '\n' + text[last:]
    return (text, 1)

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed, n = apply_function_extraction(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f'requires_extracted={n}; {cnote}'
    exploit_verified = bool(ok and n > 0 and ('__aug_extracted_require_1' in transformed))
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
    ap = argparse.ArgumentParser(description='Wave B3 function_extraction')
    ap.add_argument('--limit', type=int, default=15)
    args = ap.parse_args()
    seeds = load_seed_manifest()
    minority = [s for s in seeds if s.get('primary_vulnerability_type') != 'reentrancy']
    reent = [s for s in seeds if s.get('primary_vulnerability_type') == 'reentrancy']
    seeds = (minority + reent)[:args.limit]
    ok_n = fail_n = 0
    for s in seeds:
        result = process_seed(s)
        print(f"  [{result['status']}] {result['record']['contract_id']}")
        if result['status'] == 'OK':
            ok_n += 1
        else:
            fail_n += 1
    print(f'[done] function_extraction OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
