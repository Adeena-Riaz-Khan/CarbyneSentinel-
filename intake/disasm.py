from __future__ import annotations


OPCODES: dict[int, tuple[str, int]] = {
    0x00: ("STOP", 0),
    0x01: ("ADD", 0),
    0x02: ("MUL", 0),
    0x03: ("SUB", 0),
    0x04: ("DIV", 0),
    0x05: ("SDIV", 0),
    0x06: ("MOD", 0),
    0x07: ("SMOD", 0),
    0x08: ("ADDMOD", 0),
    0x09: ("MULMOD", 0),
    0x0A: ("EXP", 0),
    0x0B: ("SIGNEXTEND", 0),
    0x10: ("LT", 0),
    0x11: ("GT", 0),
    0x12: ("SLT", 0),
    0x13: ("SGT", 0),
    0x14: ("EQ", 0),
    0x15: ("ISZERO", 0),
    0x16: ("AND", 0),
    0x17: ("OR", 0),
    0x18: ("XOR", 0),
    0x19: ("NOT", 0),
    0x1A: ("BYTE", 0),
    0x1B: ("SHL", 0),
    0x1C: ("SHR", 0),
    0x1D: ("SAR", 0),
    0x20: ("SHA3", 0),
    0x30: ("ADDRESS", 0),
    0x31: ("BALANCE", 0),
    0x32: ("ORIGIN", 0),
    0x33: ("CALLER", 0),
    0x34: ("CALLVALUE", 0),
    0x35: ("CALLDATALOAD", 0),
    0x36: ("CALLDATASIZE", 0),
    0x37: ("CALLDATACOPY", 0),
    0x38: ("CODESIZE", 0),
    0x39: ("CODECOPY", 0),
    0x3A: ("GASPRICE", 0),
    0x3B: ("EXTCODESIZE", 0),
    0x3C: ("EXTCODECOPY", 0),
    0x3D: ("RETURNDATASIZE", 0),
    0x3E: ("RETURNDATACOPY", 0),
    0x3F: ("EXTCODEHASH", 0),
    0x40: ("BLOCKHASH", 0),
    0x41: ("COINBASE", 0),
    0x42: ("TIMESTAMP", 0),
    0x43: ("NUMBER", 0),
    0x44: ("DIFFICULTY", 0),
    0x45: ("GASLIMIT", 0),
    0x46: ("CHAINID", 0),
    0x47: ("SELFBALANCE", 0),
    0x48: ("BASEFEE", 0),
    0x50: ("POP", 0),
    0x51: ("MLOAD", 0),
    0x52: ("MSTORE", 0),
    0x53: ("MSTORE8", 0),
    0x54: ("SLOAD", 0),
    0x55: ("SSTORE", 0),
    0x56: ("JUMP", 0),
    0x57: ("JUMPI", 0),
    0x58: ("PC", 0),
    0x59: ("MSIZE", 0),
    0x5A: ("GAS", 0),
    0x5B: ("JUMPDEST", 0),
    0x5F: ("PUSH0", 0),
    0x60: ("PUSH1", 1),
    0x61: ("PUSH2", 2),
    0x62: ("PUSH3", 3),
    0x63: ("PUSH4", 4),
    0x64: ("PUSH5", 5),
    0x65: ("PUSH6", 6),
    0x66: ("PUSH7", 7),
    0x67: ("PUSH8", 8),
    0x68: ("PUSH9", 9),
    0x69: ("PUSH10", 10),
    0x6A: ("PUSH11", 11),
    0x6B: ("PUSH12", 12),
    0x6C: ("PUSH13", 13),
    0x6D: ("PUSH14", 14),
    0x6E: ("PUSH15", 15),
    0x6F: ("PUSH16", 16),
    0x70: ("PUSH17", 17),
    0x71: ("PUSH18", 18),
    0x72: ("PUSH19", 19),
    0x73: ("PUSH20", 20),
    0x74: ("PUSH21", 21),
    0x75: ("PUSH22", 22),
    0x76: ("PUSH23", 23),
    0x77: ("PUSH24", 24),
    0x78: ("PUSH25", 25),
    0x79: ("PUSH26", 26),
    0x7A: ("PUSH27", 27),
    0x7B: ("PUSH28", 28),
    0x7C: ("PUSH29", 29),
    0x7D: ("PUSH30", 30),
    0x7E: ("PUSH31", 31),
    0x7F: ("PUSH32", 32),
    0x80: ("DUP1", 0),
    0x81: ("DUP2", 0),
    0x82: ("DUP3", 0),
    0x83: ("DUP4", 0),
    0x84: ("DUP5", 0),
    0x85: ("DUP6", 0),
    0x86: ("DUP7", 0),
    0x87: ("DUP8", 0),
    0x88: ("DUP9", 0),
    0x89: ("DUP10", 0),
    0x8A: ("DUP11", 0),
    0x8B: ("DUP12", 0),
    0x8C: ("DUP13", 0),
    0x8D: ("DUP14", 0),
    0x8E: ("DUP15", 0),
    0x8F: ("DUP16", 0),
    0x90: ("SWAP1", 0),
    0x91: ("SWAP2", 0),
    0x92: ("SWAP3", 0),
    0x93: ("SWAP4", 0),
    0x94: ("SWAP5", 0),
    0x95: ("SWAP6", 0),
    0x96: ("SWAP7", 0),
    0x97: ("SWAP8", 0),
    0x98: ("SWAP9", 0),
    0x99: ("SWAP10", 0),
    0x9A: ("SWAP11", 0),
    0x9B: ("SWAP12", 0),
    0x9C: ("SWAP13", 0),
    0x9D: ("SWAP14", 0),
    0x9E: ("SWAP15", 0),
    0x9F: ("SWAP16", 0),
    0xA0: ("LOG0", 0),
    0xA1: ("LOG1", 0),
    0xA2: ("LOG2", 0),
    0xA3: ("LOG3", 0),
    0xA4: ("LOG4", 0),
    0xF0: ("CREATE", 0),
    0xF1: ("CALL", 0),
    0xF2: ("CALLCODE", 0),
    0xF3: ("RETURN", 0),
    0xF4: ("DELEGATECALL", 0),
    0xF5: ("CREATE2", 0),
    0xFA: ("STATICCALL", 0),
    0xFD: ("REVERT", 0),
    0xFE: ("INVALID", 0),
    0xFF: ("SELFDESTRUCT", 0),
}


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
    instructions: list[dict] = []
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


def check_offsets(instructions: list[dict], bytecode_len: int) -> list[str]:
    errors: list[str] = []
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
