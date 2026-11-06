from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

TERMINALS = {"STOP", "RETURN", "REVERT", "INVALID", "SELFDESTRUCT"}
JUMP_OPS = {"JUMP", "JUMPI"}


def _is_push(opcode: str) -> bool:
    return opcode.startswith("PUSH") and opcode != "PUSH0"


def _push_immediate_value(ins: dict) -> int | None:
    if not _is_push(ins["opcode"]):
        return None
    if ins.get("incomplete"):
        return None
    immediate = ins.get("immediate") or ""
    if immediate == "":
        return None
    try:
        return int(immediate, 16)
    except ValueError:
        return None


def _static_jump_target(instructions: list[dict], jump_index: int) -> int | None:
    op = instructions[jump_index]["opcode"]
    if op not in JUMP_OPS:
        return None
    if jump_index <= 0:
        return None
    return _push_immediate_value(instructions[jump_index - 1])


def _jumpdest_offsets(instructions: list[dict]) -> set[int]:
    return {ins["offset"] for ins in instructions if ins["opcode"] == "JUMPDEST"}


def _offset_to_index(instructions: list[dict]) -> dict[int, int]:
    return {ins["offset"]: ins["index"] for ins in instructions}


def _find_leaders(instructions: list[dict]) -> list[int]:
    if not instructions:
        return []
    leaders: set[int] = {0}
    n = len(instructions)
    for i, ins in enumerate(instructions):
        op = ins["opcode"]
        if op == "JUMPDEST":
            leaders.add(i)
        if op in JUMP_OPS or op in TERMINALS:
            if i + 1 < n:
                leaders.add(i + 1)
    return sorted(leaders)


def build_cfg(instructions: list[dict]) -> dict:
    if not instructions:
        return {
            "blocks": [],
            "edges": [],
            "stats": {
                "block_count": 0,
                "edge_count": 0,
                "resolved_jumps": 0,
                "unresolved_jumps": 0,
            },
        }

    leaders = _find_leaders(instructions)
    jumpdests = _jumpdest_offsets(instructions)
    offset_index = _offset_to_index(instructions)
    index_to_block: dict[int, int] = {}
    blocks = []

    for block_id, start_i in enumerate(leaders):
        if block_id + 1 < len(leaders):
            end_i = leaders[block_id + 1] - 1
        else:
            end_i = len(instructions) - 1
        body = instructions[start_i : end_i + 1]
        for ins in body:
            index_to_block[ins["index"]] = block_id
        last = body[-1]
        end_offset = last["offset"] + last["size"] - 1
        blocks.append(
            {
                "id": block_id,
                "start_offset": body[0]["offset"],
                "end_offset": end_offset,
                "instruction_count": len(body),
                "terminal": last["opcode"],
                "instructions": [
                    {
                        "offset": ins["offset"],
                        "opcode": ins["opcode"],
                        "immediate": ins["immediate"],
                    }
                    for ins in body
                ],
            }
        )

    edges = []
    resolved_jumps = 0
    unresolved_jumps = 0

    for block in blocks:
        block_id = block["id"]
        last = block["instructions"][-1]
        op = last["opcode"]
        last_index = offset_index[last["offset"]]
        next_block_id = block_id + 1 if block_id + 1 < len(blocks) else None

        if op == "JUMP":
            target = _static_jump_target(instructions, last_index)
            if target is not None and target in jumpdests:
                dest_index = offset_index[target]
                dest_block = index_to_block[dest_index]
                edges.append(
                    {
                        "source": block_id,
                        "dest": dest_block,
                        "type": "jump",
                        "target_offset": target,
                    }
                )
                resolved_jumps += 1
            else:
                edges.append(
                    {
                        "source": block_id,
                        "dest": None,
                        "type": "unresolved_jump",
                        "target_offset": target,
                    }
                )
                unresolved_jumps += 1
        elif op == "JUMPI":
            target = _static_jump_target(instructions, last_index)
            if target is not None and target in jumpdests:
                dest_index = offset_index[target]
                dest_block = index_to_block[dest_index]
                edges.append(
                    {
                        "source": block_id,
                        "dest": dest_block,
                        "type": "jumpi_true",
                        "target_offset": target,
                    }
                )
                resolved_jumps += 1
            else:
                edges.append(
                    {
                        "source": block_id,
                        "dest": None,
                        "type": "unresolved_jump",
                        "target_offset": target,
                    }
                )
                unresolved_jumps += 1
            if next_block_id is not None:
                edges.append(
                    {
                        "source": block_id,
                        "dest": next_block_id,
                        "type": "jumpi_false",
                        "target_offset": None,
                    }
                )
        elif op in TERMINALS:
            pass
        else:
            if next_block_id is not None:
                edges.append(
                    {
                        "source": block_id,
                        "dest": next_block_id,
                        "type": "sequential",
                        "target_offset": None,
                    }
                )

    return {
        "blocks": blocks,
        "edges": edges,
        "stats": {
            "block_count": len(blocks),
            "edge_count": len(edges),
            "resolved_jumps": resolved_jumps,
            "unresolved_jumps": unresolved_jumps,
        },
    }


def validate_cfg(instructions: list[dict], cfg: dict) -> list[str]:
    errors = []
    blocks = cfg["blocks"]
    edges = cfg["edges"]

    if not instructions:
        if blocks:
            errors.append("empty instructions but non-empty blocks")
        return errors

    if not blocks:
        errors.append("no basic blocks for non-empty instructions")
        return errors

    if blocks[0]["start_offset"] != instructions[0]["offset"]:
        errors.append("first instruction is not in the first basic block")

    covered = []
    for block in blocks:
        for ins in block["instructions"]:
            covered.append(ins["offset"])

    expected_offsets = [ins["offset"] for ins in instructions]
    if covered != expected_offsets:
        errors.append("instruction coverage mismatch between CFG and disassembly")

    for block in blocks:
        body = block["instructions"]
        if not body:
            errors.append(f"block {block['id']} has no instructions")
            continue
        if body[0]["offset"] != block["start_offset"]:
            errors.append(f"block {block['id']} start_offset mismatch")
        last = body[-1]
        expected_end = last["offset"] + next(
            ins["size"] for ins in instructions if ins["offset"] == last["offset"]
        ) - 1
        if block["end_offset"] != expected_end:
            errors.append(f"block {block['id']} end_offset mismatch")
        if block["instruction_count"] != len(body):
            errors.append(f"block {block['id']} instruction_count mismatch")
        for i in range(len(body) - 1):
            cur = next(ins for ins in instructions if ins["offset"] == body[i]["offset"])
            nxt = body[i + 1]
            if cur["offset"] + cur["size"] != nxt["offset"]:
                errors.append(f"block {block['id']} instructions are not continuous")
                break

    block_ids = {block["id"] for block in blocks}
    jumpdests = _jumpdest_offsets(instructions)

    for edge in edges:
        if edge["source"] not in block_ids:
            errors.append(f"edge source {edge['source']} is not a block id")
        if edge["dest"] is not None and edge["dest"] not in block_ids:
            errors.append(f"edge dest {edge['dest']} is not a block id")
        if edge["type"] in {"jump", "jumpi_true"}:
            target = edge.get("target_offset")
            if target not in jumpdests:
                errors.append(f"resolved jump target {target} is not a JUMPDEST")
        if edge["type"] == "jump":
            src = blocks[edge["source"]]
            if src["terminal"] != "JUMP":
                errors.append(f"jump edge from non-JUMP block {edge['source']}")
        if edge["type"] in {"jumpi_true", "jumpi_false"}:
            src = blocks[edge["source"]]
            if src["terminal"] != "JUMPI":
                errors.append(f"jumpi edge from non-JUMPI block {edge['source']}")

    for block in blocks:
        op = block["terminal"]
        outs = [e for e in edges if e["source"] == block["id"]]
        if op in TERMINALS:
            if any(e["type"] == "sequential" for e in outs):
                errors.append(f"terminal block {block['id']} has sequential fall-through")
        if op == "JUMP":
            if any(e["type"] in {"sequential", "jumpi_false"} for e in outs):
                errors.append(f"JUMP block {block['id']} has incorrect fall-through")
        if op == "JUMPI":
            if block["id"] + 1 < len(blocks):
                if not any(e["type"] == "jumpi_false" for e in outs):
                    errors.append(f"JUMPI block {block['id']} missing fall-through")

    return errors


def cfg_to_record(contract_id: str, instructions: list[dict], cfg: dict) -> dict:
    return {
        "contract_id": contract_id,
        "instruction_count": len(instructions),
        "blocks": cfg["blocks"],
        "edges": cfg["edges"],
        "stats": cfg["stats"],
    }


def write_cfg_json(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def cfg_to_dot(record: dict) -> str:
    lines = []
    lines.append("digraph CFG {")
    lines.append("  rankdir=TB;")
    lines.append('  node [shape=box, fontname="Courier"];')
    lines.append('  edge [fontname="Courier", fontsize=10];')

    for block in record["blocks"]:
        label_ops = []
        for ins in block["instructions"][:6]:
            text = ins["opcode"]
            if ins["immediate"]:
                text += " 0x" + ins["immediate"]
            label_ops.append(text)
        if block["instruction_count"] > 6:
            label_ops.append("...")
        label = (
            f"B{block['id']}\\n"
            f"0x{block['start_offset']:04x}-0x{block['end_offset']:04x}\\n"
            f"n={block['instruction_count']} term={block['terminal']}\\n"
            + "\\n".join(label_ops)
        )
        lines.append(f'  B{block["id"]} [label="{label}"];')

    style = {
        "sequential": 'color="gray40", label="seq"',
        "jump": 'color="blue", label="jump"',
        "jumpi_true": 'color="darkgreen", label="jumpi_true"',
        "jumpi_false": 'color="orange", label="jumpi_false"',
        "unresolved_jump": 'color="red", style="dashed", label="unresolved"',
    }

    unresolved_nodes = 0
    for edge in record["edges"]:
        attrs = style.get(edge["type"], 'label="' + edge["type"] + '"')
        if edge["dest"] is None:
            name = f"UNRES_{unresolved_nodes}"
            unresolved_nodes += 1
            lines.append(f'  {name} [shape=ellipse, color="red", label="unresolved"];')
            lines.append(f"  B{edge['source']} -> {name} [{attrs}];")
        else:
            lines.append(f"  B{edge['source']} -> B{edge['dest']} [{attrs}];")

    lines.append("}")
    return "\n".join(lines) + "\n"


def write_cfg_dot(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cfg_to_dot(record), encoding="utf-8")


def _find_dot_binary() -> str | None:
    found = shutil.which("dot")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files\Graphviz\bin\dot.exe"),
        Path(r"C:\Program Files (x86)\Graphviz\bin\dot.exe"),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def render_cfg_png(dot_path: Path, png_path: Path) -> bool:
    dot_bin = _find_dot_binary()
    if not dot_bin:
        return False
    png_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [dot_bin, "-Tpng", str(dot_path), "-o", str(png_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and png_path.is_file()
