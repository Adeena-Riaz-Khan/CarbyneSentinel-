#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, IDENT_RE, OUT_JSONL, SEED_MANIFEST, SOLIDITY_KEYWORDS, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, pick_minority_seeds, read_parent_bytecode, resolve_source_path, save_variant_artifacts, strip_comments_and_strings, write_seed_manifest
TECHNIQUE = 'identifier_renaming'
LEVEL = 'lexical'
SEVERITY = 'light'
TYPE_PREFIXES = ('uint', 'int', 'bytes', 'fixed', 'ufixed')

def _is_skippable(name: str) -> bool:
    if name in SOLIDITY_KEYWORDS:
        return True
    if len(name) <= 1:
        return True
    if name.startswith('__'):
        return True
    low = name.lower()
    if any((low.startswith(p) and low[len(p):].isdigit() for p in TYPE_PREFIXES)):
        return True
    if name.startswith('0x'):
        return True
    return False

def collect_renamable(source: str) -> list[str]:
    masked = strip_comments_and_strings(source)
    contract_names = set(re.findall('\\b(?:contract|library|interface)\\s+([A-Za-z_][A-Za-z0-9_]*)', masked))
    public_fns = set(re.findall('\\bfunction\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\([^;]*\\)\\s*(?:public|external)\\b', masked))
    found: list[str] = []
    seen: set[str] = set()
    for m in IDENT_RE.finditer(masked):
        name = m.group(1)
        if _is_skippable(name) or name in seen:
            continue
        if name in contract_names or name in public_fns:
            continue
        if name[0].isupper() or '_' in name or len(name) >= 6:
            seen.add(name)
            found.append(name)
    found.sort(key=len, reverse=True)
    return found

def apply_identifier_renaming(source: str, max_rename: int=40) -> tuple[str, int]:
    names = collect_renamable(source)[:max_rename]
    if not names:
        return (source, 0)
    mapping = {n: f'aug_{i}' for i, n in enumerate(names)}
    text = source
    for old, new in mapping.items():
        text = re.sub(f'\\b{re.escape(old)}\\b', new, text)
    return (text, len(mapping))

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed, n_renamed = apply_identifier_renaming(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    parent_bc = read_parent_bytecode(parent)
    new_bc_norm = (bytecode or '').replace('0x', '').lower() if bytecode else None
    notes = f'renamed={n_renamed}; {cnote}'
    if ok and parent_bc and new_bc_norm:
        if parent_bc == new_bc_norm:
            notes += '; bytecode_identical_to_parent=true (pure lexical)'
        else:
            notes += '; bytecode_identical_to_parent=false (likely public selector/name)'
    elif ok:
        notes += '; no_parent_bytecode_compare'
    exploit_verified = bool(ok and n_renamed > 0)
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
    ap = argparse.ArgumentParser(description='Wave A1 identifier_renaming')
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--write-seeds', action='store_true', help='Refresh seed manifest first')
    args = ap.parse_args()
    if args.write_seeds or not SEED_MANIFEST.is_file():
        seeds = pick_minority_seeds()
        write_seed_manifest(seeds)
        print(f'[info] wrote seed manifest ({len(seeds)})')
    seeds = load_seed_manifest()
    seeds = [s for s in seeds if s.get('primary_vulnerability_type') != 'reentrancy']
    if args.limit is not None:
        seeds = seeds[:args.limit]
    ok_n = fail_n = 0
    for s in seeds:
        result = process_seed(s)
        cid = result['record']['contract_id']
        print(f"  [{result['status']}] {cid}")
        if result['status'] == 'OK':
            ok_n += 1
        else:
            fail_n += 1
    print(f'[done] identifier_renaming OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
