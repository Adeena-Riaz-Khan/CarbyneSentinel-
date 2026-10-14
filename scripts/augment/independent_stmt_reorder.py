#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, append_jsonl, build_record, compile_source, load_seed_manifest, make_variant_id, resolve_source_path, save_variant_artifacts
TECHNIQUE = 'independent_stmt_reorder'
LEVEL = 'structural'
SEVERITY = 'light'
STATE_VAR_RE = re.compile('^[ \\t]+(?:address|bool|string|byte|bytes\\d*|u?int\\d*|int\\d*)(?:\\s+(?:public|private|internal))?\\s+[A-Za-z_][A-Za-z0-9_]*(?:\\s*=\\s*[^;]+)?\\s*;[ \\t]*$')

def _extract_function_blocks(source: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for m in re.finditer('\\bfunction\\b', source):
        start = m.start()
        brace = source.find('{', start)
        semi = source.find(';', start)
        if brace == -1:
            continue
        if semi != -1 and semi < brace:
            continue
        i = brace
        depth = 0
        while i < len(source):
            ch = source[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    spans.append((start, i + 1))
                    break
            i += 1
    return spans

def _reorder_adjacent_functions(source: str) -> tuple[str, int]:
    spans = _extract_function_blocks(source)
    if len(spans) < 2:
        return (source, 0)
    for a, b in zip(spans, spans[1:]):
        between = source[a[1]:b[0]]
        if between.strip() == '':
            fa = source[a[0]:a[1]]
            fb = source[b[0]:b[1]]
            new = source[:a[0]] + fb + between + fa + source[b[1]:]
            return (new, 1)
    return (source, 0)

def _reorder_state_vars(source: str) -> tuple[str, int]:
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    runs = 0
    while i < len(lines):
        line = lines[i]
        bare = line.rstrip('\r\n')
        if STATE_VAR_RE.match(bare):
            run = [line]
            j = i + 1
            while j < len(lines):
                bare_j = lines[j].rstrip('\r\n')
                if STATE_VAR_RE.match(bare_j):
                    run.append(lines[j])
                    j += 1
                elif bare_j.strip() == '':
                    k = j + 1
                    while k < len(lines) and lines[k].strip() == '':
                        k += 1
                    if k < len(lines) and STATE_VAR_RE.match(lines[k].rstrip('\r\n')):
                        run.append(lines[j])
                        j += 1
                    else:
                        break
                else:
                    break
            decls = [ln for ln in run if ln.strip() != '']
            if len(decls) >= 2:
                out.extend(reversed(decls))
                runs += 1
                i = j
                continue
            out.extend(run)
            i = j
            continue
        out.append(line)
        i += 1
    return (''.join(out), runs)

def apply_independent_stmt_reorder(source: str) -> tuple[str, int]:
    text, runs = _reorder_state_vars(source)
    ops = runs
    if ops == 0:
        text2, n = _reorder_adjacent_functions(source)
        if n:
            return (text2, n)
    return (text, ops)

def process_seed(parent: dict, idx: int=1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding='utf-8', errors='replace')
    transformed, n_runs = apply_independent_stmt_reorder(original)
    variant_id = make_variant_id(parent['contract_id'], TECHNIQUE, idx)
    version = parent.get('compiler_version') or '0.5.17'
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f'state_var_runs_reordered={n_runs}; {cnote}'
    exploit_verified = bool(ok and n_runs > 0 and (transformed != original))
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
    ap = argparse.ArgumentParser(description='Wave B2 independent_stmt_reorder')
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
    print(f'[done] independent_stmt_reorder OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}')
    return 0 if ok_n > 0 else 1
if __name__ == '__main__':
    raise SystemExit(main())
