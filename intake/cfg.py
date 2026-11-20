from __future__ import annotations

from typing import Any, Optional


TERMINALS = {"STOP", "RETURN", "REVERT", "INVALID", "SELFDESTRUCT"}
JUMP_OPS = {"JUMP", "JUMPI"}

REASON_DYNAMIC = "dynamic"
REASON_INVALID_DEST = "invalid_dest"
REASON_TRUNCATED = "truncated"


def _is_push(opcode: str) -> bool:
    return opcode.startswith("PUSH") and opcode != "PUSH0"


def _push_immediate_value(ins: dict) -> Optional[int]:
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


def _static_jump_info(
    instructions: list[dict], jump_index: int
) -> tuple[Optional[int], Optional[str]]:
    op = instructions[jump_index]["opcode"]
    if op not in JUMP_OPS:
        return None, None
    if jump_index <= 0:
        return None, REASON_DYNAMIC
    prev = instructions[jump_index - 1]
    if prev.get("incomplete"):
        return None, REASON_TRUNCATED
    target = _push_immediate_value(prev)
    if target is None:
        return None, REASON_DYNAMIC
    return target, None


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


def build_cfg(instructions: list[dict]) -> dict[str, Any]:
    if not instructions:
        return {
            "blocks": [],
            "edges": [],
            "stats": {
                "block_count": 0,
                "edge_count": 0,
                "resolved_jumps": 0,
                "unresolved_jumps": 0,
                "unresolved_dynamic": 0,
                "unresolved_invalid_dest": 0,
                "unresolved_truncated": 0,
            },
        }

    leaders = _find_leaders(instructions)
    jumpdests = _jumpdest_offsets(instructions)
    offset_index = _offset_to_index(instructions)
    index_to_block: dict[int, int] = {}
    blocks: list[dict[str, Any]] = []

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

    edges: list[dict[str, Any]] = []
    resolved_jumps = 0
    unresolved_jumps = 0
    unresolved_dynamic = 0
    unresolved_invalid_dest = 0
    unresolved_truncated = 0

    def add_unresolved(
        block_id: int,
        target: Optional[int],
        reason: str,
    ) -> None:
        nonlocal unresolved_jumps, unresolved_dynamic, unresolved_invalid_dest, unresolved_truncated
        edges.append(
            {
                "source": block_id,
                "dest": None,
                "type": "unresolved_jump",
                "target_offset": target,
                "reason": reason,
            }
        )
        unresolved_jumps += 1
        if reason == REASON_DYNAMIC:
            unresolved_dynamic += 1
        elif reason == REASON_INVALID_DEST:
            unresolved_invalid_dest += 1
        elif reason == REASON_TRUNCATED:
            unresolved_truncated += 1

    for block in blocks:
        block_id = block["id"]
        last = block["instructions"][-1]
        op = last["opcode"]
        last_index = offset_index[last["offset"]]
        next_block_id = block_id + 1 if block_id + 1 < len(blocks) else None

        if op == "JUMP":
            target, reason = _static_jump_info(instructions, last_index)
            if target is not None and target in jumpdests:
                dest_index = offset_index[target]
                dest_block = index_to_block[dest_index]
                edges.append(
                    {
                        "source": block_id,
                        "dest": dest_block,
                        "type": "jump",
                        "target_offset": target,
                        "reason": None,
                    }
                )
                resolved_jumps += 1
            elif target is not None:
                add_unresolved(block_id, target, REASON_INVALID_DEST)
            else:
                add_unresolved(block_id, None, reason or REASON_DYNAMIC)
        elif op == "JUMPI":
            target, reason = _static_jump_info(instructions, last_index)
            if target is not None and target in jumpdests:
                dest_index = offset_index[target]
                dest_block = index_to_block[dest_index]
                edges.append(
                    {
                        "source": block_id,
                        "dest": dest_block,
                        "type": "jumpi_true",
                        "target_offset": target,
                        "reason": None,
                    }
                )
                resolved_jumps += 1
            elif target is not None:
                add_unresolved(block_id, target, REASON_INVALID_DEST)
            else:
                add_unresolved(block_id, None, reason or REASON_DYNAMIC)
            if next_block_id is not None:
                edges.append(
                    {
                        "source": block_id,
                        "dest": next_block_id,
                        "type": "jumpi_false",
                        "target_offset": None,
                        "reason": None,
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
                        "reason": None,
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
            "unresolved_dynamic": unresolved_dynamic,
            "unresolved_invalid_dest": unresolved_invalid_dest,
            "unresolved_truncated": unresolved_truncated,
        },
    }


def validate_cfg(instructions: list[dict], cfg: dict) -> list[str]:
    errors: list[str] = []
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

    offset_to_ins = {ins["offset"]: ins for ins in instructions}
    for block in blocks:
        body = block["instructions"]
        if not body:
            errors.append(f"block {block['id']} has no instructions")
            continue
        if body[0]["offset"] != block["start_offset"]:
            errors.append(f"block {block['id']} start_offset mismatch")
        last = body[-1]
        expected_end = last["offset"] + offset_to_ins[last["offset"]]["size"] - 1
        if block["end_offset"] != expected_end:
            errors.append(f"block {block['id']} end_offset mismatch")

    jumpdests = _jumpdest_offsets(instructions)
    for edge in edges:
        if edge["type"] in {"jump", "jumpi_true"}:
            target = edge.get("target_offset")
            if target not in jumpdests:
                errors.append(f"resolved jump target {target} is not a JUMPDEST")
        if edge["type"] == "unresolved_jump":
            if edge.get("dest") is not None:
                errors.append("unresolved_jump must not have a dest block")
            if edge.get("reason") not in {
                REASON_DYNAMIC,
                REASON_INVALID_DEST,
                REASON_TRUNCATED,
            }:
                errors.append(f"unresolved_jump missing valid reason: {edge.get('reason')}")
            if edge.get("reason") == REASON_INVALID_DEST:
                target = edge.get("target_offset")
                if target is None or target in jumpdests:
                    errors.append("invalid_dest edge has inconsistent target_offset")
    return errors
