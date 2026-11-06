from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts" / "augment"))

from disasm import check_offsets, disassemble, format_listing, parse_hex
import common

BATCH_IDS = [
    "SMARTBUGS_reentrancy_reentrancy_insecure",
    "SOLIDIFI_Re-entrancy_buggy_50",
    "SMARTBUGS_unchecked_low_level_calls_unchecked_return_value",
    "SOLIDIFI_Unhandled-Exceptions_buggy_15",
    "SOLIDIFI_tx.origin_buggy_10",
    "SOLIDIFI_tx.origin_buggy_7",
    "SMARTBUGS_time_manipulation_timed_crowdsale",
    "SOLIDIFI_Timestamp-Dependency_buggy_44",
    "SMARTBUGS_access_control_mycontract",
    "SMARTBUGS_access_control_arbitrary_location_write_simple",
]


def load_batch_rows():
    master = common.load_master()
    by_id = {row["contract_id"]: row for row in master}
    rows = []
    for cid in BATCH_IDS:
        row = by_id.get(cid)
        if row is None:
            raise SystemExit(f"missing contract in master: {cid}")
        rows.append(row)
    return rows


def read_bytecode(row: dict) -> str:
    rel = row.get("bytecode_path")
    if not rel:
        raise ValueError(f"{row['contract_id']}: no bytecode_path")
    path = ROOT / "processed" / rel
    if not path.is_file():
        raise ValueError(f"{row['contract_id']}: missing file {path}")
    return path.read_text(encoding="utf-8").strip()


def run_self_checks() -> list[str]:
    errors = []

    try:
        parse_hex("0xzz")
        errors.append("invalid hex was accepted")
    except ValueError:
        pass

    try:
        parse_hex("abc")
        errors.append("odd-length hex was accepted")
    except ValueError:
        pass

    try:
        parse_hex("")
        errors.append("empty hex was accepted")
    except ValueError:
        pass

    ins = disassemble("6001600201")
    if len(ins) != 3:
        errors.append(f"PUSH demo length expected 3 got {len(ins)}")
    else:
        if ins[0]["opcode"] != "PUSH1" or ins[0]["immediate"] != "01" or ins[0]["offset"] != 0:
            errors.append("PUSH1 decode failed on 6001600201")
        if ins[1]["opcode"] != "PUSH1" or ins[1]["immediate"] != "02" or ins[1]["offset"] != 2:
            errors.append("second PUSH1 decode failed on 6001600201")
        if ins[2]["opcode"] != "ADD" or ins[2]["offset"] != 4:
            errors.append("ADD decode failed on 6001600201")
        if ins[1]["opcode_value"] == 0x02:
            errors.append("PUSH immediate 02 was treated as an opcode")

    truncated = disassemble("63aabb")
    if len(truncated) != 1 or not truncated[0]["incomplete"]:
        errors.append("truncated PUSH was not marked incomplete")
    if truncated[0]["opcode"] != "PUSH4":
        errors.append("truncated PUSH opcode name wrong")

    unknown = disassemble("0c")
    if unknown[0]["opcode"] != "UNKNOWN_0x0c":
        errors.append("unknown opcode not handled explicitly")

    return errors


def manual_check_against_file(row: dict, instructions: list[dict]) -> list[str]:
    errors = []
    raw = read_bytecode(row)
    data = parse_hex(raw)
    for ins in instructions[:40]:
        if data[ins["offset"]] != ins["opcode_value"]:
            errors.append(
                f"{row['contract_id']}: byte at {ins['offset']} is "
                f"{data[ins['offset']]:02x} but opcode_value is {ins['opcode_value']:02x}"
            )
            break
        if ins["immediate"]:
            start = ins["offset"] + 1
            end = start + len(ins["immediate"]) // 2
            got = data[start:end].hex()
            if got != ins["immediate"]:
                errors.append(
                    f"{row['contract_id']}: immediate mismatch at {ins['offset']}"
                )
                break
            for pos in range(start, end):
                if any(other["offset"] == pos for other in instructions):
                    errors.append(
                        f"{row['contract_id']}: PUSH data byte at {pos} also used as instruction offset"
                    )
                    break
    return errors


def main() -> int:
    print("=== self checks ===")
    self_errors = run_self_checks()
    if self_errors:
        for err in self_errors:
            print("FAIL:", err)
        return 1
    print("self checks passed")

    rows = load_batch_rows()
    print(f"\n=== batch size {len(rows)} ===")
    ok_count = 0
    all_errors = []

    for row in rows:
        cid = row["contract_id"]
        try:
            raw = read_bytecode(row)
            data = parse_hex(raw)
            instructions = disassemble(raw)
        except ValueError as exc:
            all_errors.append(f"{cid}: {exc}")
            print(f"\n[{cid}] ERROR {exc}")
            continue

        offset_errors = check_offsets(instructions, len(data))
        manual_errors = manual_check_against_file(row, instructions)
        names = {ins["opcode"] for ins in instructions}

        print(f"\n[{cid}]")
        print(f"  class={row.get('primary_vulnerability_type')} bytes={len(data)} instructions={len(instructions)}")
        print(f"  has_JUMP={'JUMP' in names} has_JUMPI={'JUMPI' in names} has_SLOAD={'SLOAD' in names} has_CALL={'CALL' in names}")
        print("  first instructions:")
        print(format_listing(instructions, limit=12))

        if offset_errors or manual_errors:
            for err in offset_errors + manual_errors:
                print("  FAIL:", err)
                all_errors.append(err)
        else:
            ok_count += 1
            print("  validation: ok")

    print("\n=== summary ===")
    print(f"processed_ok={ok_count}/{len(rows)}")
    print(f"error_count={len(all_errors)}")
    if all_errors:
        return 1
    print("batch validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
