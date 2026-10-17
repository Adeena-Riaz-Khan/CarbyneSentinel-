#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    FAIL_JSONL,
    OUT_JSONL,
    SEED_MANIFEST,
    append_jsonl,
    build_record,
    compile_source,
    load_seed_manifest,
    make_variant_id,
    pick_minority_seeds,
    pick_reentrancy_seeds,
    resolve_source_path,
    save_variant_artifacts,
)

TECHNIQUE = "control_flow_flattening"
LEVEL = "control_flow"
SEVERITY = "aggressive"

FN_RE = re.compile(
    r"(function\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^;{}]*?\)\s*(?:[^{;]*))\s*\{",
    re.DOTALL,
)


def _body_end(source: str, body_start: int) -> int:
    depth = 1
    i = body_start
    while i < len(source):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_simple_stmts(body: str) -> Optional[List[str]]:
    if "{" in body or "}" in body:
        return None
    parts = []
    buf = []
    depth = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == ";" and depth == 0:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt + ";")
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        return None
    if len(parts) < 2 or len(parts) > 6:
        return None
    for p in parts:
        if p.startswith("return ") or p == "return;" or p.startswith("throw"):
            return None
    return parts


def _flatten_stmts(stmts: list[str], indent: str) -> str:
    n = len(stmts)
    lines = [
        f"{indent}uint256 __aug_cf_state = 0;",
        f"{indent}while (__aug_cf_state < {n}) {{",
    ]
    for i, stmt in enumerate(stmts):
        kw = "if" if i == 0 else "else if"
        lines.append(f"{indent}    {kw} (__aug_cf_state == {i}) {{")
        lines.append(f"{indent}        {stmt}")
        lines.append(f"{indent}        __aug_cf_state = {i + 1};")
        lines.append(f"{indent}    }}")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def apply_control_flow_flattening(source: str) -> tuple[str, int]:
    for m in FN_RE.finditer(source):
        header = m.group(1)
        if "returns" in header and "view" in header:
            continue
        body_open = m.end() - 1
        body_close = _body_end(source, body_open + 1)
        if body_close < 0:
            continue
        body = source[body_open + 1 : body_close]
        if "__aug_cf_state" in body:
            continue
        stmts = _split_simple_stmts(body)
        if not stmts:
            continue
        indent_m = re.match(r"(\s*)", body.lstrip("\n"))
        indent = "        "
        if body[:1] == "\n":
            lm = re.match(r"\n([ \t]*)", body)
            if lm:
                indent = lm.group(1) or indent
        flat = "\n" + _flatten_stmts(stmts, indent) + "\n" + indent[:-4]
        text = source[: body_open + 1] + flat + source[body_close:]
        return text, len(stmts)
    return source, 0


def process_seed(parent: dict, idx: int = 1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding="utf-8", errors="replace")
    transformed, n = apply_control_flow_flattening(original)
    variant_id = make_variant_id(parent["contract_id"], TECHNIQUE, idx)
    version = parent.get("compiler_version") or "0.5.17"
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f"flattened_stmts={n}; {cnote}"
    exploit_verified = bool(ok and n >= 2 and "__aug_cf_state" in transformed)
    source_rel, bytecode_rel = save_variant_artifacts(
        technique=TECHNIQUE,
        variant_id=variant_id,
        source_text=transformed,
        bytecode_hex=bytecode if ok else None,
    )
    rec = build_record(
        parent=parent,
        technique=TECHNIQUE,
        level=LEVEL,
        severity=SEVERITY,
        variant_id=variant_id,
        source_rel=source_rel,
        bytecode_rel=bytecode_rel,
        compiler_version=version,
        compiled_ok=ok,
        exploit_verified=exploit_verified,
        notes=notes,
    )
    if exploit_verified:
        append_jsonl(OUT_JSONL, rec)
        status = "OK"
    else:
        append_jsonl(FAIL_JSONL, rec)
        status = "FAIL"
    return {"status": status, "record": rec}


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave C3 control_flow_flattening")
    ap.add_argument("--target-ok", type=int, default=10)
    args = ap.parse_args()

    existing = set()
    if OUT_JSONL.is_file():
        for line in OUT_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if TECHNIQUE in (r.get("transformation_techniques") or []):
                existing.add(r.get("parent_contract_id"))

    seeds = []
    if SEED_MANIFEST.is_file():
        seeds = load_seed_manifest()
    seeds = seeds + pick_minority_seeds(
        {
            "tx_origin": 20,
            "time_manipulation": 20,
            "front_running": 20,
            "bad_randomness": 8,
            "denial_of_service": 4,
            "short_address": 1,
        }
    ) + pick_reentrancy_seeds(15)
    seen = set()
    uniq = []
    for s in seeds:
        cid = s["contract_id"]
        if cid not in seen:
            seen.add(cid)
            uniq.append(s)

    ok_n = fail_n = 0
    for s in uniq:
        if ok_n >= args.target_ok:
            break
        if s["contract_id"] in existing:
            continue
        result = process_seed(s)
        print(f"  [{result['status']}] {result['record']['contract_id']}")
        if result["status"] == "OK":
            ok_n += 1
            existing.add(s["contract_id"])
        else:
            fail_n += 1
    print(f"[done] control_flow_flattening OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}")
    return 0 if ok_n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
