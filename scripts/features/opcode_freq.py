from __future__ import annotations

from opcodes import OPCODES

PRECISION = 6


def opcode_vocabulary() -> list[str]:
    names = sorted({name for name, _push in OPCODES.values()})
    if "UNKNOWN" not in names:
        names.append("UNKNOWN")
        names = sorted(names)
    return names


def opcode_feature_names() -> list[str]:
    return [f"op_ratio_{name}" for name in opcode_vocabulary()]


def opcode_frequency_ratios(instructions: list[dict]) -> dict[str, float]:
    vocab = opcode_vocabulary()
    known = set(vocab) - {"UNKNOWN"}
    counts = {name: 0 for name in vocab}
    total = len(instructions)
    if total == 0:
        return {f"op_ratio_{name}": 0.0 for name in vocab}

    for ins in instructions:
        name = ins["opcode"]
        if name in known:
            counts[name] += 1
        else:
            counts["UNKNOWN"] += 1

    ratios = {}
    for name in vocab:
        ratios[f"op_ratio_{name}"] = round(counts[name] / total, PRECISION)
    return ratios
