from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

from bytecode_cache import BytecodeCache
from bytecode_retrieval import (
    STATUS_AWAITING_CREATION,
    STATUS_INVALID_ADDRESS,
    STATUS_NO_CODE,
    STATUS_RETRIEVED,
    BytecodeRetrieval,
    awaiting_creation_result,
    block_id_for_record,
    normalize_block_hash,
    retrieve_contract_bytecode,
)
from cfg import build_cfg
from disasm import disassemble
from proxy_detection import ProxyDetection, detect_proxy
from selector_extraction import SelectorExtraction, extract_selectors
from sepolia_pending_listener import (
    ENV_WS_URL,
    PendingTxRecord,
    load_ws_url,
    normalize_tx_hash,
)


ENV_HTTP_URL = "SEPOLIA_HTTP_URL"
DEFAULT_GETCODE_TIMEOUT_S = 10.0

STATE_PENDING = "pending"
STATE_REPLACED = "replaced"
STATE_CONFIRMED = "confirmed"
STATE_SUSPECTED_DROPPED = "suspected_dropped"


RpcCall = Callable[[str, list[Any]], Any]


@dataclass(frozen=True)
class ParsedTx:
    tx_hash: str
    from_addr: str
    to_addr: Optional[str]
    nonce: int
    value: str
    gas: str
    gas_price: Optional[str]
    max_fee_per_gas: Optional[str]
    max_priority_fee_per_gas: Optional[str]
    input_data: str
    block_number: Optional[int]
    block_hash: Optional[str] = None


@dataclass
class TxLifecycleRecord:
    tx_hash: str
    state: str
    network: str
    source: str
    first_seen_ts: float
    updated_ts: float
    from_addr: Optional[str] = None
    nonce: Optional[int] = None
    parsed: Optional[ParsedTx] = None
    replaced_by: Optional[str] = None
    replaces: Optional[str] = None
    confirmed_block: Optional[int] = None
    confirmed_block_hash: Optional[str] = None
    confirmed_ts: Optional[float] = None
    receipt_status: Optional[str] = None
    last_lookup_ts: Optional[float] = None
    parse_error: Optional[str] = None
    bytecode: Optional[BytecodeRetrieval] = None
    proxy: Optional[ProxyDetection] = None
    instructions: Optional[list[dict]] = None
    cfg: Optional[dict] = None
    selectors: Optional[SelectorExtraction] = None
    created_contract_address: Optional[str] = None


class JsonRpcError(Exception):
    pass


def load_http_url(env: Optional[dict[str, str]] = None) -> str:
    source = env if env is not None else os.environ
    direct = (source.get(ENV_HTTP_URL) or "").strip()
    if direct:
        return direct
    ws = load_ws_url(source)
    if ws.lower().startswith("wss://"):
        return "https://" + ws[6:]
    if ws.lower().startswith("ws://"):
        return "http://" + ws[5:]
    return ""


def validate_http_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        raise ValueError(f"{ENV_HTTP_URL} or derivable {ENV_WS_URL} is missing")
    lower = text.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        raise ValueError(f"{ENV_HTTP_URL} must start with http:// or https://")
    return text


def _hex_to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text.startswith("0x"):
        return None
    try:
        return int(text, 16)
    except ValueError:
        return None


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


def parse_transaction_result(result: Any) -> Optional[ParsedTx]:
    if result is None:
        return None
    if not isinstance(result, dict):
        raise ValueError("transaction result must be an object or null")
    tx_hash = normalize_tx_hash(result.get("hash"))
    if tx_hash is None:
        raise ValueError("transaction hash missing or invalid")
    from_addr = _norm_addr(result.get("from"))
    if from_addr is None:
        raise ValueError("transaction from missing or invalid")
    to_raw = result.get("to")
    if to_raw is None or to_raw == "":
        to_addr = None
    else:
        to_addr = _norm_addr(to_raw)
        if to_addr is None:
            raise ValueError("transaction to missing or invalid")
    nonce = _hex_to_int(result.get("nonce"))
    if nonce is None:
        raise ValueError("transaction nonce missing or invalid")
    value = result.get("value")
    gas = result.get("gas")
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("transaction value missing or invalid")
    if not isinstance(gas, str) or not gas.startswith("0x"):
        raise ValueError("transaction gas missing or invalid")
    input_data = result.get("input")
    if not isinstance(input_data, str):
        input_data = "0x"
    gas_price = result.get("gasPrice") if isinstance(result.get("gasPrice"), str) else None
    max_fee = result.get("maxFeePerGas") if isinstance(result.get("maxFeePerGas"), str) else None
    max_prio = (
        result.get("maxPriorityFeePerGas")
        if isinstance(result.get("maxPriorityFeePerGas"), str)
        else None
    )
    block_number = _hex_to_int(result.get("blockNumber"))
    block_hash = normalize_block_hash(result.get("blockHash"))
    return ParsedTx(
        tx_hash=tx_hash,
        from_addr=from_addr,
        to_addr=to_addr,
        nonce=nonce,
        value=value,
        gas=gas,
        gas_price=gas_price,
        max_fee_per_gas=max_fee,
        max_priority_fee_per_gas=max_prio,
        input_data=input_data,
        block_number=block_number,
        block_hash=block_hash,
    )


def parse_receipt_result(result: Any) -> Optional[dict[str, Any]]:
    if result is None:
        return None
    if not isinstance(result, dict):
        raise ValueError("receipt result must be an object or null")
    tx_hash = normalize_tx_hash(result.get("transactionHash"))
    if tx_hash is None:
        raise ValueError("receipt transactionHash missing or invalid")
    block_number = _hex_to_int(result.get("blockNumber"))
    if block_number is None:
        raise ValueError("receipt blockNumber missing or invalid")
    status = result.get("status")
    if status is not None and not isinstance(status, str):
        raise ValueError("receipt status malformed")
    contract_address = result.get("contractAddress")
    if contract_address in (None, ""):
        created = None
    else:
        created = _norm_addr(contract_address)
    return {
        "tx_hash": tx_hash,
        "block_number": block_number,
        "block_hash": normalize_block_hash(result.get("blockHash")),
        "status": status,
        "contract_address": created,
    }


def make_rpc_call(http_url: str, timeout_s: float = 30.0) -> RpcCall:
    url = validate_http_url(http_url)
    next_id = {"n": 0}

    def call(method: str, params: list[Any]) -> Any:
        next_id["n"] += 1
        payload = {
            "jsonrpc": "2.0",
            "id": next_id["n"],
            "method": method,
            "params": params,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise JsonRpcError(f"HTTP error {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise JsonRpcError(f"URL error: {exc.reason}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise JsonRpcError("RPC response was not valid JSON") from exc
        if not isinstance(data, dict):
            raise JsonRpcError("RPC response was not an object")
        if data.get("error") is not None:
            raise JsonRpcError(f"RPC error: {data.get('error')}")
        return data.get("result")

    return call


class TxLifecycleManager:
    def __init__(
        self,
        *,
        rpc_call: Optional[RpcCall] = None,
        http_url: Optional[str] = None,
        drop_timeout_s: float = 120.0,
        reconcile_interval_s: float = 5.0,
        now_fn: Callable[[], float] = time.time,
        get_code_timeout_s: float = DEFAULT_GETCODE_TIMEOUT_S,
        bytecode_cache: Optional[BytecodeCache] = None,
    ) -> None:
        if rpc_call is not None:
            self.rpc_call = rpc_call
            self.get_code_rpc = rpc_call
        else:
            resolved = http_url if http_url is not None else load_http_url()
            self.rpc_call = make_rpc_call(resolved)
            self.get_code_rpc = make_rpc_call(resolved, timeout_s=get_code_timeout_s)
        self.drop_timeout_s = drop_timeout_s
        self.reconcile_interval_s = reconcile_interval_s
        self.now_fn = now_fn
        self.bytecode_cache = bytecode_cache if bytecode_cache is not None else BytecodeCache()
        self.records: dict[str, TxLifecycleRecord] = {}
        self._pending_by_sender_nonce: dict[tuple[str, int], str] = {}
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def get(self, tx_hash: str) -> Optional[TxLifecycleRecord]:
        key = normalize_tx_hash(tx_hash)
        if key is None:
            return None
        return self.records.get(key)

    def list_by_state(self, state: str) -> list[TxLifecycleRecord]:
        return [rec for rec in self.records.values() if rec.state == state]

    def ingest_pending_event(self, event: PendingTxRecord) -> Optional[TxLifecycleRecord]:
        if self._stopped:
            return None
        tx_hash = normalize_tx_hash(event.tx_hash)
        if tx_hash is None:
            return None
        existing = self.records.get(tx_hash)
        if existing is not None:
            if existing.state == STATE_SUSPECTED_DROPPED:
                return self._recover_suspected(existing)
            return existing
        now = self.now_fn()
        rec = TxLifecycleRecord(
            tx_hash=tx_hash,
            state=STATE_PENDING,
            network=event.network,
            source=event.source,
            first_seen_ts=event.first_seen_ts,
            updated_ts=now,
        )
        self.records[tx_hash] = rec
        try:
            raw = self.rpc_call("eth_getTransactionByHash", [tx_hash])
            parsed = parse_transaction_result(raw)
        except (JsonRpcError, ValueError) as exc:
            rec.parse_error = str(exc)
            rec.updated_ts = now
            return rec
        if parsed is None:
            rec.parse_error = "transaction not found"
            rec.last_lookup_ts = now
            rec.updated_ts = now
            return rec
        self._attach_parsed(rec, parsed, now)
        self._apply_replacement(rec, now)
        self._retrieve_bytecode(rec, now)
        return rec

    def reconcile(self) -> None:
        if self._stopped:
            return
        now = self.now_fn()
        for rec in list(self.records.values()):
            if rec.state == STATE_REPLACED:
                continue
            if rec.state == STATE_CONFIRMED:
                self._retrieve_bytecode(rec, now)
                continue
            self._reconcile_one(rec, now)

    def _bytecode_complete(self, rec: TxLifecycleRecord) -> bool:
        if rec.bytecode is None:
            return False
        return rec.bytecode.status in (
            STATUS_RETRIEVED,
            STATUS_NO_CODE,
            STATUS_INVALID_ADDRESS,
        )

    def _retrieve_bytecode(
        self,
        rec: TxLifecycleRecord,
        now: float,
        *,
        contract_address: Optional[str] = None,
    ) -> None:
        if self._bytecode_complete(rec):
            return
        if contract_address is not None:
            rec.created_contract_address = contract_address
        address = contract_address
        if address is None and rec.created_contract_address is not None:
            address = rec.created_contract_address
        if address is None and rec.parsed is not None:
            address = rec.parsed.to_addr
        if address is None:
            if rec.parsed is not None and rec.parsed.to_addr is None:
                rec.bytecode = awaiting_creation_result(now=now)
                rec.updated_ts = now
            return
        block_id = block_id_for_record(rec.confirmed_block, rec.confirmed_block_hash)
        rec.bytecode = retrieve_contract_bytecode(
            self.get_code_rpc,
            address,
            block_id,
            now=now,
            cache=self.bytecode_cache,
            network=rec.network,
        )
        if (
            rec.bytecode is not None
            and rec.bytecode.status == STATUS_RETRIEVED
            and rec.bytecode.bytecode
        ):
            rec.proxy = detect_proxy(rec.bytecode.bytecode)
            try:
                instructions = disassemble(rec.bytecode.bytecode)
            except ValueError:
                instructions = []
            rec.instructions = instructions
            rec.cfg = build_cfg(instructions) if instructions else None
            rec.selectors = extract_selectors(instructions, proxy=rec.proxy)
        else:
            rec.proxy = None
            rec.instructions = None
            rec.cfg = None
            rec.selectors = None
        rec.updated_ts = now

    def _attach_parsed(
        self,
        rec: TxLifecycleRecord,
        parsed: ParsedTx,
        now: float,
        *,
        try_receipt: bool = True,
    ) -> None:
        rec.parsed = parsed
        rec.from_addr = parsed.from_addr
        rec.nonce = parsed.nonce
        rec.parse_error = None
        rec.last_lookup_ts = now
        rec.updated_ts = now
        if parsed.block_number is not None:
            block_number = parsed.block_number
            block_hash = parsed.block_hash
            receipt_status = rec.receipt_status
            created = None
            if try_receipt and receipt_status is None:
                receipt = self._try_get_receipt(rec.tx_hash)
                if receipt is not None:
                    block_number = receipt["block_number"]
                    if receipt.get("block_hash") is not None:
                        block_hash = receipt.get("block_hash")
                    receipt_status = receipt.get("status")
                    created = receipt.get("contract_address")
            self._mark_confirmed(rec, block_number, receipt_status, now, block_hash=block_hash)
            if created is not None:
                rec.created_contract_address = created

    def _try_get_receipt(self, tx_hash: str) -> Optional[dict[str, Any]]:
        try:
            receipt_raw = self.rpc_call("eth_getTransactionReceipt", [tx_hash])
            return parse_receipt_result(receipt_raw)
        except (JsonRpcError, ValueError):
            return None

    def _apply_replacement(self, rec: TxLifecycleRecord, now: float) -> None:
        if rec.from_addr is None or rec.nonce is None:
            return
        if rec.state != STATE_PENDING:
            return
        key = (rec.from_addr, rec.nonce)
        previous_hash = self._pending_by_sender_nonce.get(key)
        if previous_hash is None:
            self._pending_by_sender_nonce[key] = rec.tx_hash
            return
        if previous_hash == rec.tx_hash:
            return
        previous = self.records.get(previous_hash)
        if previous is not None and previous.state == STATE_PENDING:
            previous.state = STATE_REPLACED
            previous.replaced_by = rec.tx_hash
            previous.updated_ts = now
            rec.replaces = previous_hash
            rec.updated_ts = now
        self._pending_by_sender_nonce[key] = rec.tx_hash

    def _mark_confirmed(
        self,
        rec: TxLifecycleRecord,
        block_number: int,
        receipt_status: Optional[str],
        now: float,
        *,
        block_hash: Optional[str] = None,
    ) -> None:
        rec.state = STATE_CONFIRMED
        rec.confirmed_block = block_number
        if block_hash is not None:
            rec.confirmed_block_hash = block_hash
        rec.confirmed_ts = now
        if receipt_status is not None:
            rec.receipt_status = receipt_status
        rec.updated_ts = now
        if rec.from_addr is not None and rec.nonce is not None:
            key = (rec.from_addr, rec.nonce)
            if self._pending_by_sender_nonce.get(key) == rec.tx_hash:
                del self._pending_by_sender_nonce[key]

    def _recover_suspected(self, rec: TxLifecycleRecord) -> TxLifecycleRecord:
        now = self.now_fn()
        self._reconcile_one(rec, now)
        return rec

    def _reconcile_one(self, rec: TxLifecycleRecord, now: float) -> None:
        try:
            receipt_raw = self.rpc_call("eth_getTransactionReceipt", [rec.tx_hash])
            receipt = parse_receipt_result(receipt_raw)
        except (JsonRpcError, ValueError):
            receipt = None
        if receipt is not None:
            self._mark_confirmed(
                rec,
                receipt["block_number"],
                receipt.get("status"),
                now,
                block_hash=receipt.get("block_hash"),
            )
            created = receipt.get("contract_address")
            if created is not None:
                rec.created_contract_address = created
            self._retrieve_bytecode(rec, now, contract_address=created)
            return
        try:
            raw = self.rpc_call("eth_getTransactionByHash", [rec.tx_hash])
            parsed = parse_transaction_result(raw)
        except (JsonRpcError, ValueError) as exc:
            rec.parse_error = str(exc)
            rec.last_lookup_ts = now
            rec.updated_ts = now
            return
        rec.last_lookup_ts = now
        if parsed is not None:
            was_suspected = rec.state == STATE_SUSPECTED_DROPPED
            self._attach_parsed(rec, parsed, now, try_receipt=False)
            self._retrieve_bytecode(rec, now)
            if rec.state == STATE_CONFIRMED:
                return
            if was_suspected:
                rec.state = STATE_PENDING
                rec.updated_ts = now
            self._apply_replacement(rec, now)
            return
        age = now - rec.first_seen_ts
        if rec.state == STATE_PENDING and age >= self.drop_timeout_s:
            rec.state = STATE_SUSPECTED_DROPPED
            rec.updated_ts = now
            if rec.from_addr is not None and rec.nonce is not None:
                key = (rec.from_addr, rec.nonce)
                if self._pending_by_sender_nonce.get(key) == rec.tx_hash:
                    del self._pending_by_sender_nonce[key]
            return
        rec.updated_ts = now
