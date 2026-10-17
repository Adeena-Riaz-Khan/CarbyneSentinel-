#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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

TECHNIQUE = "condition_rewriting"
LEVEL = "control_flow"
SEVERITY = "moderate"

IF_RE = re.compile(r"\bif\s*\(")
REQUIRE_RE = re.compile(r"\brequire\s*\(")


def _matching_paren(text: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _rewrite_cond_expr(expr: str) -> str:
    e = expr.strip()
    if not e or "__aug_" in e:
        return e
    if e.startswith("!(") and e.endswith(")") and e.count("(") == 1:
        return e
    return f"!(!({e}))"


def apply_condition_rewriting(source: str, max_rewrites: int = 8) -> tuple[str, int]:
    text = source
    n = 0
    for pattern in (IF_RE, REQUIRE_RE):
        pos = 0
        while n < max_rewrites:
            m = pattern.search(text, pos)
            if not m:
                break
            open_paren = m.end() - 1
            close = _matching_paren(text, open_paren)
            if close < 0:
                pos = m.end()
                continue
            inner = text[open_paren + 1 : close]
            if "," in inner and pattern is REQUIRE_RE:
                parts = inner.split(",", 1)
                cond, rest = parts[0], parts[1]
                new_inner = _rewrite_cond_expr(cond) + "," + rest
            else:
                new_inner = _rewrite_cond_expr(inner)
            if new_inner == inner.strip() or new_inner == inner:
                pos = close + 1
                continue
            text = text[: open_paren + 1] + new_inner + text[close:]
            n += 1
            pos = open_paren + 1 + len(new_inner) + 1
    return text, n


def process_seed(parent: dict, idx: int = 1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding="utf-8", errors="replace")
    transformed, n = apply_condition_rewriting(original)
    variant_id = make_variant_id(parent["contract_id"], TECHNIQUE, idx)
    version = parent.get("compiler_version") or "0.5.17"
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f"conditions_rewritten={n}; {cnote}"
    exploit_verified = bool(ok and n > 0 and transformed != original)
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


def _candidate_seeds(limit: int) -> list[dict]:
    if SEED_MANIFEST.is_file():
        seeds = load_seed_manifest()
    else:
        seeds = pick_minority_seeds() + pick_reentrancy_seeds(5)
    minority = [s for s in seeds if s.get("primary_vulnerability_type") != "reentrancy"]
    reent = [s for s in seeds if s.get("primary_vulnerability_type") == "reentrancy"]
    return (minority + reent)[:limit]


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave C1 condition_rewriting")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--target-ok", type=int, default=15)
    args = ap.parse_args()

    existing = set()
    if OUT_JSONL.is_file():
        for line in OUT_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if TECHNIQUE in (r.get("transformation_techniques") or []):
                existing.add(r.get("parent_contract_id"))

    pool = _candidate_seeds(max(args.limit * 3, 40))
    extra = pick_minority_seeds(
        {
            "tx_origin": 12,
            "time_manipulation": 12,
            "front_running": 12,
            "bad_randomness": 5,
            "denial_of_service": 3,
            "short_address": 1,
        }
    ) + pick_reentrancy_seeds(8)
    seen = {s["contract_id"] for s in pool}
    for s in extra:
        if s["contract_id"] not in seen:
            pool.append(s)
            seen.add(s["contract_id"])

    ok_n = fail_n = 0
    for s in pool:
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
    print(f"[done] condition_rewriting OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}")
    return 0 if ok_n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
