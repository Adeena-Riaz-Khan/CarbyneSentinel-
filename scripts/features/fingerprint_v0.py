from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from cfg import build_cfg
from disasm import parse_hex


PRECISION = 6


def round_feature(value: float) -> float:
    return round(float(value), PRECISION)


def shannon_entropy(values: list[int] | bytes) -> float:
    if len(values) == 0:
        raise ValueError("cannot compute entropy of empty sequence")
    counts = Counter(values)
    total = len(values)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round_feature(entropy)


def bytecode_shannon_entropy(bytecode: str) -> tuple[int, float]:
    data = parse_hex(bytecode)
    return len(data), shannon_entropy(data)


def opcode_shannon_entropy(instructions: list[dict]) -> float:
    if not instructions:
        raise ValueError("cannot compute opcode entropy of empty instruction list")
    values = [ins["opcode_value"] for ins in instructions]
    return shannon_entropy(values)


def jump_features(instructions: list[dict]) -> dict:
    total = len(instructions)
    jump_count = 0
    jumpi_count = 0
    for ins in instructions:
        if ins["opcode"] == "JUMP":
            jump_count += 1
        elif ins["opcode"] == "JUMPI":
            jumpi_count += 1
    total_jump_count = jump_count + jumpi_count
    if total == 0:
        jump_ratio = 0.0
        conditional_jump_ratio = 0.0
        unconditional_jump_ratio = 0.0
    else:
        jump_ratio = total_jump_count / total
        conditional_jump_ratio = jumpi_count / total
        unconditional_jump_ratio = jump_count / total
    return {
        "total_instruction_count": total,
        "jump_count": jump_count,
        "jumpi_count": jumpi_count,
        "total_jump_count": total_jump_count,
        "jump_ratio": round_feature(jump_ratio),
        "conditional_jump_ratio": round_feature(conditional_jump_ratio),
        "unconditional_jump_ratio": round_feature(unconditional_jump_ratio),
    }


def cfg_extra_features(instructions: list[dict]) -> dict:
    cfg = build_cfg(instructions)
    stats = cfg["stats"]
    return {
        "cfg_block_count": stats["block_count"],
        "cfg_edge_count": stats["edge_count"],
        "cfg_resolved_jumps": stats["resolved_jumps"],
        "cfg_unresolved_jumps": stats["unresolved_jumps"],
    }


def extract_fingerprint_v0(
    contract_id: str,
    bytecode: str,
    instructions: list[dict],
    primary_vulnerability_type: str | None = None,
) -> dict:
    size, byte_entropy = bytecode_shannon_entropy(bytecode)
    jumps = jump_features(instructions)
    extras = {
        "opcode_shannon_entropy": opcode_shannon_entropy(instructions)
        if instructions
        else None,
        **cfg_extra_features(instructions),
    }
    return {
        "contract_id": contract_id,
        "primary_vulnerability_type": primary_vulnerability_type,
        "bytecode_size_bytes": size,
        "bytecode_shannon_entropy": byte_entropy,
        **jumps,
        "extras": extras,
    }


def flatten_record(record: dict) -> dict:
    flat = {
        "contract_id": record["contract_id"],
        "primary_vulnerability_type": record.get("primary_vulnerability_type"),
        "bytecode_size_bytes": record["bytecode_size_bytes"],
        "bytecode_shannon_entropy": record["bytecode_shannon_entropy"],
        "total_instruction_count": record["total_instruction_count"],
        "jump_count": record["jump_count"],
        "jumpi_count": record["jumpi_count"],
        "total_jump_count": record["total_jump_count"],
        "jump_ratio": record["jump_ratio"],
        "conditional_jump_ratio": record["conditional_jump_ratio"],
        "unconditional_jump_ratio": record["unconditional_jump_ratio"],
        "extras_opcode_shannon_entropy": record["extras"]["opcode_shannon_entropy"],
        "extras_cfg_block_count": record["extras"]["cfg_block_count"],
        "extras_cfg_edge_count": record["extras"]["cfg_edge_count"],
        "extras_cfg_resolved_jumps": record["extras"]["cfg_resolved_jumps"],
        "extras_cfg_unresolved_jumps": record["extras"]["cfg_unresolved_jumps"],
    }
    return flat


def write_fingerprint_json(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def write_batch_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    rows = [flatten_record(r) for r in records]
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        cells = []
        for key in headers:
            value = row[key]
            if value is None:
                cells.append("")
            else:
                cells.append(str(value))
        lines.append(",".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_fingerprint_record(record: dict, instructions: list[dict]) -> list[str]:
    errors = []
    jumps = jump_features(instructions)
    for key in (
        "total_instruction_count",
        "jump_count",
        "jumpi_count",
        "total_jump_count",
        "jump_ratio",
        "conditional_jump_ratio",
        "unconditional_jump_ratio",
    ):
        if record[key] != jumps[key]:
            errors.append(f"{key} mismatch with recomputed jump features")

    if record["total_jump_count"] != record["jump_count"] + record["jumpi_count"]:
        errors.append("total_jump_count is not jump_count + jumpi_count")

    for key in ("jump_ratio", "conditional_jump_ratio", "unconditional_jump_ratio"):
        value = record[key]
        if value < 0 or value > 1:
            errors.append(f"{key} out of range: {value}")
        if math.isnan(value) or math.isinf(value):
            errors.append(f"{key} is NaN or Inf")

    entropy = record["bytecode_shannon_entropy"]
    if entropy < 0 or entropy > 8:
        errors.append(f"bytecode_shannon_entropy out of range: {entropy}")

    opcode_entropy = record["extras"]["opcode_shannon_entropy"]
    if opcode_entropy is not None and (opcode_entropy < 0 or opcode_entropy > 8):
        errors.append(f"opcode_shannon_entropy out of range: {opcode_entropy}")

    if record["total_instruction_count"] != len(instructions):
        errors.append("total_instruction_count does not match disassembly length")

    cfg_extras = cfg_extra_features(instructions)
    for key, value in cfg_extras.items():
        if record["extras"][key] != value:
            errors.append(f"extras.{key} mismatch with recomputed CFG stats")

    return errors


def run_fingerprint_self_checks() -> list[str]:
    errors = []

    try:
        shannon_entropy(b"")
        errors.append("empty entropy was accepted")
    except ValueError:
        pass

    if shannon_entropy(b"\x00\x00\x00\x00") != 0.0:
        errors.append("repeated single byte entropy should be 0")

    if shannon_entropy(b"\x00\xff\x00\xff") != 1.0:
        errors.append("two equal bytes entropy should be 1")

    if shannon_entropy(b"\x00\x01\x02\x03") != 2.0:
        errors.append("four equal bytes entropy should be 2")

    try:
        parse_hex("0xzz")
        errors.append("invalid hex was accepted")
    except ValueError:
        pass

    try:
        parse_hex("")
        errors.append("empty hex was accepted")
    except ValueError:
        pass

    from disasm import disassemble

    push_demo = disassemble("6001600201")
    if len(push_demo) != 3:
        errors.append("PUSH demo instruction count wrong")
    jumps = jump_features(push_demo)
    if jumps["total_instruction_count"] != 3:
        errors.append("jump_features total_instruction_count wrong on PUSH demo")
    if jumps["total_jump_count"] != 0:
        errors.append("PUSH demo should have zero jumps")

    jump_ins = disassemble("60055600005b00")
    jumps2 = jump_features(jump_ins)
    if jumps2["jump_count"] != 1 or jumps2["jumpi_count"] != 0:
        errors.append("JUMP toy counts wrong")
    if jumps2["total_jump_count"] != 1:
        errors.append("JUMP toy total_jump_count wrong")

    jumpi_ins = disassemble("6001600657005b00")
    jumps3 = jump_features(jumpi_ins)
    if jumps3["jumpi_count"] != 1 or jumps3["jump_count"] != 0:
        errors.append("JUMPI toy counts wrong")
    expected_ratio = round_feature(1 / len(jumpi_ins))
    if jumps3["conditional_jump_ratio"] != expected_ratio:
        errors.append("JUMPI toy conditional_jump_ratio wrong")

    empty_jumps = jump_features([])
    if empty_jumps["jump_ratio"] != 0.0:
        errors.append("empty instruction jump_ratio should be 0")
    if math.isnan(empty_jumps["jump_ratio"]) or math.isinf(empty_jumps["jump_ratio"]):
        errors.append("empty instruction jump_ratio is NaN/Inf")

    return errors
