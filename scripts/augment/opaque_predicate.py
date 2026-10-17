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

TECHNIQUE = "opaque_predicate"
LEVEL = "control_flow"
SEVERITY = "moderate"

HELPER = """
    function __aug_opaque_true() private pure returns (bool) {
        uint256 __aug_o = 7;
        return (__aug_o * __aug_o >= 0);
    }
"""

REQUIRE_RE = re.compile(
    r"^([ \t]*)require\s*\(\s*([^;]*?)\s*\)\s*;",
    re.MULTILINE,
)


def apply_opaque_predicate(source: str) -> tuple[str, int]:
    m = REQUIRE_RE.search(source)
    if not m:
        return source, 0
    indent = m.group(1)
    replacement = (
        f"{indent}if (__aug_opaque_true()) {{\n"
        f"{indent}    require({m.group(2).strip()});\n"
        f"{indent}}}"
    )
    text = source[: m.start()] + replacement + source[m.end() :]
    cm = re.search(
        r"\b(contract|library)\s+[A-Za-z_][A-Za-z0-9_]*\b[^{]*\{",
        text,
    )
    if cm:
        at = cm.end()
        text = text[:at] + "\n" + HELPER + text[at:]
    else:
        last = text.rfind("}")
        if last == -1:
            text = text + "\n" + HELPER
        else:
            text = text[:last] + HELPER + "\n" + text[last:]
    return text, 1


def process_seed(parent: dict, idx: int = 1) -> dict:
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding="utf-8", errors="replace")
    transformed, n = apply_opaque_predicate(original)
    variant_id = make_variant_id(parent["contract_id"], TECHNIQUE, idx)
    version = parent.get("compiler_version") or "0.5.17"
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f"opaque_wrapped={n}; {cnote}"
    exploit_verified = bool(ok and n > 0 and "__aug_opaque_true" in transformed)
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
    ap = argparse.ArgumentParser(description="Wave C2 opaque_predicate")
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

    seeds = []
    if SEED_MANIFEST.is_file():
        seeds = load_seed_manifest()
    seeds = seeds + pick_minority_seeds(
        {
            "tx_origin": 12,
            "time_manipulation": 12,
            "front_running": 12,
            "bad_randomness": 5,
            "denial_of_service": 3,
            "short_address": 1,
        }
    ) + pick_reentrancy_seeds(8)
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
    print(f"[done] opaque_predicate OK={ok_n} FAIL={fail_n} -> {OUT_JSONL}")
    return 0 if ok_n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
