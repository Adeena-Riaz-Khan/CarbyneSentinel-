from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from bytecode_cache import BytecodeCache


STATUS_RETRIEVED = "retrieved"
STATUS_NO_CODE = "no_code"
STATUS_AWAITING_CREATION = "awaiting_creation"
STATUS_RPC_FAILURE = "rpc_failure"
STATUS_INVALID_RESPONSE = "invalid_response"
STATUS_NOT_ATTEMPTED = "not_attempted"
STATUS_INVALID_ADDRESS = "invalid_address"

DEFAULT_GETCODE_ATTEMPTS = 2
DEFAULT_CACHE_NETWORK = "sepolia"

RpcCall = Callable[[str, list[Any]], Any]


@dataclass
class BytecodeRetrieval:
    status: str
    contract_address: Optional[str] = None
    bytecode: Optional[str] = None
    bytecode_size_bytes: Optional[int] = None
    retrieved_ts: Optional[float] = None
    block_id: Optional[str] = None
    error: Optional[str] = None


def _norm_addr(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text in ("", "0x"):
        return None
    if not text.startswith("0x") or len(text) != 42:
        return None
    try:
        int(text[2:], 16)
    except ValueError:
        return None
    return text


def validate_bytecode_hex(value: Any) -> tuple[str, Optional[str], Optional[int], Optional[str]]:
    if not isinstance(value, str):
        return STATUS_INVALID_RESPONSE, None, None, "bytecode response must be a string"
    text = value.strip()
    if not text.lower().startswith("0x"):
        return STATUS_INVALID_RESPONSE, None, None, "bytecode must start with 0x"
    body = text[2:]
    if body == "":
        return STATUS_NO_CODE, "0x", 0, None
    if len(body) % 2 != 0:
        return STATUS_INVALID_RESPONSE, None, None, "bytecode hex length is odd"
    try:
        int(body, 16)
    except ValueError:
        return STATUS_INVALID_RESPONSE, None, None, "bytecode contains non-hex characters"
    normalized = "0x" + body.lower()
    size = len(body) // 2
    return STATUS_RETRIEVED, normalized, size, None


def normalize_block_hash(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text.startswith("0x") or len(text) != 66:
        return None
    try:
        int(text[2:], 16)
    except ValueError:
        return None
    return text


def block_id_for_record(
    confirmed_block: Optional[int],
    confirmed_block_hash: Optional[str] = None,
) -> str:
    block_hash = normalize_block_hash(confirmed_block_hash)
    if block_hash is not None:
        return block_hash
    if confirmed_block is None:
        return "latest"
    return hex(confirmed_block)


def awaiting_creation_result(now: Optional[float] = None) -> BytecodeRetrieval:
    return BytecodeRetrieval(
        status=STATUS_AWAITING_CREATION,
        retrieved_ts=time.time() if now is None else now,
    )


def invalid_address_result(
    address: Optional[str] = None,
    now: Optional[float] = None,
) -> BytecodeRetrieval:
    return BytecodeRetrieval(
        status=STATUS_INVALID_ADDRESS,
        contract_address=address,
        retrieved_ts=time.time() if now is None else now,
        error="invalid contract address",
    )


def _from_cache_entry(
    entry: Any,
    addr: str,
    block_id: str,
    ts: float,
) -> BytecodeRetrieval:
    if getattr(entry, "is_empty", False):
        return BytecodeRetrieval(
            status=STATUS_NO_CODE,
            contract_address=addr,
            bytecode="0x",
            bytecode_size_bytes=0,
            retrieved_ts=ts,
            block_id=block_id,
        )
    bytecode = entry.bytecode
    size = (len(bytecode) - 2) // 2 if isinstance(bytecode, str) and bytecode.startswith("0x") else None
    return BytecodeRetrieval(
        status=STATUS_RETRIEVED,
        contract_address=addr,
        bytecode=bytecode,
        bytecode_size_bytes=size,
        retrieved_ts=ts,
        block_id=block_id,
    )


def retrieve_contract_bytecode(
    rpc_call: RpcCall,
    address: Any,
    block_id: str = "latest",
    *,
    now: Optional[float] = None,
    attempts: int = DEFAULT_GETCODE_ATTEMPTS,
    cache: Optional[BytecodeCache] = None,
    network: str = DEFAULT_CACHE_NETWORK,
) -> BytecodeRetrieval:
    ts = time.time() if now is None else now
    addr = _norm_addr(address)
    if addr is None:
        raw = None if address is None else str(address)
        return invalid_address_result(raw, now=ts)
    if cache is not None:
        hit = cache.get(addr, network=network, block_id=block_id)
        if hit is not None:
            return _from_cache_entry(hit, addr, block_id, ts)
    last_error = "rpc failure"
    tries = max(1, attempts)
    for attempt in range(tries):
        try:
            raw = rpc_call("eth_getCode", [addr, block_id])
        except Exception as exc:
            last_error = str(exc)
            if attempt + 1 < tries:
                continue
            return BytecodeRetrieval(
                status=STATUS_RPC_FAILURE,
                contract_address=addr,
                retrieved_ts=ts,
                block_id=block_id,
                error=last_error,
            )
        status, bytecode, size, error = validate_bytecode_hex(raw)
        if status == STATUS_RETRIEVED:
            if cache is not None and bytecode is not None:
                cache.put(addr, bytecode, network=network, block_id=block_id)
            return BytecodeRetrieval(
                status=STATUS_RETRIEVED,
                contract_address=addr,
                bytecode=bytecode,
                bytecode_size_bytes=size,
                retrieved_ts=ts,
                block_id=block_id,
            )
        if status == STATUS_NO_CODE:
            if cache is not None and bytecode is not None:
                cache.put(addr, bytecode, network=network, block_id=block_id)
            return BytecodeRetrieval(
                status=STATUS_NO_CODE,
                contract_address=addr,
                bytecode=bytecode,
                bytecode_size_bytes=size,
                retrieved_ts=ts,
                block_id=block_id,
            )
        return BytecodeRetrieval(
            status=STATUS_INVALID_RESPONSE,
            contract_address=addr,
            retrieved_ts=ts,
            block_id=block_id,
            error=error,
        )
    return BytecodeRetrieval(
        status=STATUS_RPC_FAILURE,
        contract_address=addr,
        retrieved_ts=ts,
        block_id=block_id,
        error=last_error,
    )
