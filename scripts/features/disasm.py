from __future__ import annotations

from opcodes import OPCODES


def parse_hex(bytecode: str) -> bytes:
    if bytecode is None:
        raise ValueError("bytecode is empty")
    text = bytecode.strip().replace(" ", "")
    if text.startswith("0x") or text.startswith("0X"):
        text = text[2:]
    if text == "":
        raise ValueError("bytecode is empty")
    if len(text) % 2 != 0:
        raise ValueError("bytecode hex length is odd")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("bytecode is not valid hex") from exc


def disassemble(bytecode: str) -> list[dict]:
    data = parse_hex(bytecode)
    instructions = []
    pc = 0
    index = 0
    while pc < len(data):
        value = data[pc]
        if value in OPCODES:
            name, push_n = OPCODES[value]
        else:
            name, push_n = (f"UNKNOWN_0x{value:02x}", 0)

        immediate = ""
        incomplete = False
        size = 1

        if push_n > 0:
            start = pc + 1
            end = start + push_n
            if end > len(data):
                chunk = data[start:]
                immediate = chunk.hex()
                incomplete = True
                size = 1 + len(chunk)
            else:
                chunk = data[start:end]
                immediate = chunk.hex()
                size = 1 + push_n

        instructions.append(
            {
                "index": index,
                "offset": pc,
                "opcode": name,
                "opcode_value": value,
                "immediate": immediate,
                "size": size,
                "incomplete": incomplete,
            }
        )
        index += 1
        pc += size
        if incomplete:
            break

    return instructions


def format_instruction(ins: dict) -> str:
    line = f"{ins['index']:5d}  0x{ins['offset']:04x}  {ins['opcode_value']:02x}  {ins['opcode']}"
    if ins["immediate"]:
        line += f"  0x{ins['immediate']}"
    if ins["incomplete"]:
        line += "  [truncated_push]"
    return line


def format_listing(instructions: list[dict], limit: int | None = None) -> str:
    rows = instructions if limit is None else instructions[:limit]
    lines = [format_instruction(ins) for ins in rows]
    if limit is not None and len(instructions) > limit:
        lines.append(f"... ({len(instructions) - limit} more instructions)")
    return "\n".join(lines)


def check_offsets(instructions: list[dict], bytecode_len: int) -> list[str]:
    errors = []
    if not instructions:
        return errors
    expected = 0
    for ins in instructions:
        if ins["offset"] != expected:
            errors.append(
                f"offset mismatch at index {ins['index']}: got {ins['offset']} expected {expected}"
            )
        expected = ins["offset"] + ins["size"]
    last = instructions[-1]
    end = last["offset"] + last["size"]
    if last["incomplete"]:
        if end > bytecode_len:
            errors.append("truncated push end exceeds bytecode length")
    elif end != bytecode_len:
        errors.append(f"final boundary {end} != bytecode length {bytecode_len}")
    return errors
