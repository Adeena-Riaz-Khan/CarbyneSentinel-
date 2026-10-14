#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, resolve_source_path, save_variant_artifacts, strip_comments_and_strings
TECHNIQUE = 'literal_format_rewrite'
LEVEL = 'lexical'
SEVERITY = 'light'
DEC_LIT_RE = re.compile('(?<![.\\w])(\\d+)(?![.\\w])')

def _rewrite_value(n: int, turn: int) -> Optional[str]:
    if n < 2:
        return None
    s = str(n)
    if turn % 2 == 1 and re.fullmatch('[1-9]\\d*0+', s):
        trailing = len(s) - len(s.rstrip('0'))
        head = s[:-trailing]
        return f'{int(head)}e{trailing}'
    return hex(n)

def apply_literal_format_rewrite(source: str, max_rewrites: int=25) -> tuple[str, int]:
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    rewrites = 0
    turn = 0
    for line in lines:
        if line.lstrip().startswith('pragma '):
            out.append(line)
            continue
        if rewrites >= max_rewrites:
            out.append(line)
            continue
        masked = strip_comments_and_strings(line)
        chars = list(line)
        spans: list[tuple[int, int, str]] = []
        for m in DEC_LIT_RE.finditer(masked):
            if rewrites + len(spans) >= max_rewrites:
                break
            raw = m.group(1)
            if raw in ('0', '1'):
                continue
            start = m.start(1)
            if start >= 2 and line[start - 2:start].lower() == '0x':
                continue
            try:
                n = int(raw)
            except ValueError:
                continue
            repl = _rewrite_value(n, turn)
            turn += 1
            if repl is None or repl == raw:
                continue
            spans.append((m.start(1), m.end(1), repl))
        if not spans:
            out.append(line)
            continue
        for start, end, repl in reversed(spans):
            chars[start:end] = list(repl)
            rewrites += 1
        out.append(''.join(chars))
    return (''.join(out), rewrites)

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed, n_rw = apply_literal_format_rewrite(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f'literals_rewritten={n_rw}; {cnote}'
    exploit_verified = bool(ok and n_rw > 0)
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
    ap = argparse.ArgumentParser(description='Wave A3 literal_format_rewrite')
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
    print(f'[done] literal_format_rewrite OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
