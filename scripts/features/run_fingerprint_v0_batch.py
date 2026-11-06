from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts" / "augment"))

from disasm import check_offsets, disassemble, parse_hex
from fingerprint_v0 import (
    extract_fingerprint_v0,
    flatten_record,
    run_fingerprint_self_checks,
    validate_fingerprint_record,
    write_batch_csv,
    write_fingerprint_json,
)
from run_batch import BATCH_IDS, load_batch_rows, read_bytecode

OUT_DIR = ROOT / "processed" / "features" / "fingerprint_v0"


def main() -> int:
    print("=== fingerprint v0 self checks ===")
    self_errors = run_fingerprint_self_checks()
    if self_errors:
        for err in self_errors:
            print("FAIL:", err)
        return 1
    print("fingerprint v0 self checks passed")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_batch_rows()
    print(f"\n=== fingerprint v0 batch size {len(rows)} ===")
    print(f"output_dir={OUT_DIR}")

    ok_count = 0
    all_errors = []
    records = []
    failures = []

    for row in rows:
        cid = row["contract_id"]
        try:
            raw = read_bytecode(row)
            data = parse_hex(raw)
            instructions = disassemble(raw)
        except ValueError as exc:
            msg = str(exc)
            all_errors.append(f"{cid}: {msg}")
            failures.append({"contract_id": cid, "error": msg})
            print(f"\n[{cid}] ERROR {msg}")
            continue

        offset_errors = check_offsets(instructions, len(data))
        record = extract_fingerprint_v0(
            contract_id=cid,
            bytecode=raw,
            instructions=instructions,
            primary_vulnerability_type=row.get("primary_vulnerability_type"),
        )
        feature_errors = validate_fingerprint_record(record, instructions)

        json_path = OUT_DIR / f"{cid}.json"
        write_fingerprint_json(record, json_path)
        records.append(record)

        extras = record["extras"]
        print(f"\n[{cid}]")
        print(
            f"  class={record.get('primary_vulnerability_type')} "
            f"bytes={record['bytecode_size_bytes']} "
            f"H_byte={record['bytecode_shannon_entropy']} "
            f"instr={record['total_instruction_count']} "
            f"jump_ratio={record['jump_ratio']}"
        )
        print(
            f"  extras: H_opcode={extras['opcode_shannon_entropy']} "
            f"cfg_blocks={extras['cfg_block_count']} "
            f"cfg_resolved={extras['cfg_resolved_jumps']} "
            f"cfg_unresolved={extras['cfg_unresolved_jumps']}"
        )
        print(f"  wrote {json_path.name}")

        if offset_errors or feature_errors:
            for err in offset_errors + feature_errors:
                print("  FAIL:", err)
                all_errors.append(f"{cid}: {err}")
        else:
            ok_count += 1
            print("  validation: ok")

    csv_path = OUT_DIR / "batch_features.csv"
    write_batch_csv(records, csv_path)

    summary = {
        "batch_size": len(rows),
        "processed_ok": ok_count,
        "error_count": len(all_errors),
        "failures": failures,
        "feature_schema": {
            "core": [
                "contract_id",
                "primary_vulnerability_type",
                "bytecode_size_bytes",
                "bytecode_shannon_entropy",
                "total_instruction_count",
                "jump_count",
                "jumpi_count",
                "total_jump_count",
                "jump_ratio",
                "conditional_jump_ratio",
                "unconditional_jump_ratio",
            ],
            "extras": [
                "opcode_shannon_entropy",
                "cfg_block_count",
                "cfg_edge_count",
                "cfg_resolved_jumps",
                "cfg_unresolved_jumps",
            ],
        },
        "contracts": [flatten_record(r) for r in records],
    }
    summary_path = OUT_DIR / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("\n=== feature table ===")
    header = (
        f"{'contract_id':<55} {'bytes':>6} {'H_byte':>8} {'instr':>6} "
        f"{'JR':>8} {'CJR':>8} {'UJR':>8} {'H_op':>8} {'blocks':>6}"
    )
    print(header)
    for r in records:
        ex = r["extras"]
        print(
            f"{r['contract_id']:<55} "
            f"{r['bytecode_size_bytes']:>6} "
            f"{r['bytecode_shannon_entropy']:>8.6f} "
            f"{r['total_instruction_count']:>6} "
            f"{r['jump_ratio']:>8.6f} "
            f"{r['conditional_jump_ratio']:>8.6f} "
            f"{r['unconditional_jump_ratio']:>8.6f} "
            f"{(ex['opcode_shannon_entropy'] or 0):>8.6f} "
            f"{ex['cfg_block_count']:>6}"
        )

    print("\n=== summary ===")
    print(f"processed_ok={ok_count}/{len(rows)}")
    print(f"error_count={len(all_errors)}")
    print(f"csv_path={csv_path}")
    print(f"summary_path={summary_path}")
    if all_errors:
        return 1
    print("fingerprint v0 batch validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
