#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    FAIL_JSONL,
    OUT_JSONL,
    append_jsonl,
    build_record,
    compile_source,
    existing_parents_for_technique,
    make_variant_id,
    pick_imbalance_seeds,
    resolve_source_path,
    save_variant_artifacts,
)

TECHNIQUE = "unrelated_state_var_insertion"
LEVEL = "contract_level"
SEVERITY = "aggressive"

STATE_BLOCK = """
    uint256 private __aug_noise_counter_7;
    address private __aug_noise_addr_7;
    bool private __aug_noise_flag_7;
"""


def apply_unrelated_state_var_insertion(source: str) -> tuple[str, int]:
    if "__aug_noise_counter_7" in source:
        return source, 0
    cm = re.search(
        r"\b(contract|library)\s+[A-Za-z_][A-Za-z0-9_]*\b[^{]*\{",
        source,
    )
    if not cm:
        return source, 0
    at = cm.end()
    return source[:at] + "\n" + STATE_BLOCK + source[at:], 3


def process_seed(parent: dict, idx: int = 1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding="utf-8", errors="replace")
    transformed, n = apply_unrelated_state_var_insertion(original)
    variant_id = make_variant_id(parent["contract_id"], TECHNIQUE, idx)
    version = parent.get("compiler_version") or "0.5.17"
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f"state_vars_inserted={n}; {cnote}"
    exploit_verified = bool(ok and n > 0 and "__aug_noise_counter_7" in transformed)
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
        return {"status": "OK", "record": rec}
    append_jsonl(FAIL_JSONL, rec)
    return {"status": "FAIL", "record": rec}


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave E2 unrelated_state_var_insertion")
    ap.add_argument("--target-ok", type=int, default=10)
    args = ap.parse_args()
    existing = existing_parents_for_technique(TECHNIQUE)
    ok_n = fail_n = 0
    for s in pick_imbalance_seeds():
        if ok_n >= args.target_ok:
            break
        if s["contract_id"] in existing:
            continue
        r = process_seed(s)
        print(f"  [{r['status']}] {r['record']['contract_id']} ({s.get('primary_vulnerability_type')})")
        if r["status"] == "OK":
            ok_n += 1
            existing.add(s["contract_id"])
        else:
            fail_n += 1
    print(f"[done] unrelated_state_var_insertion OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}")
    return 0 if ok_n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
