from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sepolia_pending_listener import NETWORK, SOURCE, PendingTxRecord
from bytecode_cache import BytecodeCache
from bytecode_retrieval import (
    STATUS_AWAITING_CREATION,
    STATUS_NO_CODE,
    STATUS_RETRIEVED,
)
from proxy_detection import (
    CONFIDENCE_CONFIRMED,
    CONFIDENCE_NONE,
    KIND_EIP1167,
)
from selector_extraction import CONFIDENCE_HIGH, ROLE_PROXY, ROLE_RUNTIME
from tx_lifecycle import (
    ENV_HTTP_URL,
    STATE_CONFIRMED,
    STATE_PENDING,
    STATE_REPLACED,
    STATE_SUSPECTED_DROPPED,
    JsonRpcError,
    TxLifecycleManager,
    load_http_url,
    parse_receipt_result,
    parse_transaction_result,
    validate_http_url,
)


HASH_A = "0x" + ("a" * 64)
HASH_B = "0x" + ("b" * 64)
HASH_C = "0x" + ("c" * 64)
ADDR_1 = "0x" + ("1" * 40)
ADDR_2 = "0x" + ("2" * 40)


def event(tx_hash: str, ts: float = 1000.0) -> PendingTxRecord:
    return PendingTxRecord(
        tx_hash=tx_hash,
        network=NETWORK,
        first_seen_ts=ts,
        source=SOURCE,
    )


def tx_obj(
    tx_hash: str,
    *,
    from_addr: str = ADDR_1,
    to_addr: Optional[str] = ADDR_2,
    nonce: str = "0x1",
    block_number: Optional[str] = None,
    input_data: str = "0x",
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "hash": tx_hash,
        "from": from_addr,
        "to": to_addr,
        "nonce": nonce,
        "value": "0x0",
        "gas": "0x5208",
        "gasPrice": "0x1",
        "input": input_data,
    }
    if block_number is not None:
        data["blockNumber"] = block_number
    return data


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRpc:
    def __init__(self) -> None:
        self.txs: dict[str, Any] = {}
        self.receipts: dict[str, Any] = {}
        self.codes: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}
        self.calls: list[tuple[str, list[Any]]] = []

    def __call__(self, method: str, params: list[Any]) -> Any:
        self.calls.append((method, params))
        key = method + ":" + (params[0] if params else "")
        if key in self.errors:
            raise self.errors[key]
        if method == "eth_getTransactionByHash":
            return self.txs.get(params[0])
        if method == "eth_getTransactionReceipt":
            return self.receipts.get(params[0])
        if method == "eth_getCode":
            return self.codes.get(params[0], "0x")
        raise JsonRpcError(f"unexpected method {method}")


class ConfigTests(unittest.TestCase):
    def test_http_url_from_explicit_env(self) -> None:
        url = load_http_url({ENV_HTTP_URL: "https://example.test/v2/key"})
        self.assertEqual(url, "https://example.test/v2/key")

    def test_http_url_derived_from_ws(self) -> None:
        url = load_http_url({"SEPOLIA_WS_URL": "wss://example.test/v2/key"})
        self.assertEqual(url, "https://example.test/v2/key")

    def test_invalid_http_scheme(self) -> None:
        with self.assertRaises(ValueError):
            validate_http_url("wss://example.test/v2/key")


class ParseTests(unittest.TestCase):
    def test_valid_transaction_parsing(self) -> None:
        parsed = parse_transaction_result(tx_obj(HASH_A, nonce="0x5"))
        assert parsed is not None
        self.assertEqual(parsed.tx_hash, HASH_A)
        self.assertEqual(parsed.from_addr, ADDR_1)
        self.assertEqual(parsed.to_addr, ADDR_2)
        self.assertEqual(parsed.nonce, 5)
        self.assertEqual(parsed.value, "0x0")
        self.assertEqual(parsed.gas, "0x5208")

    def test_contract_creation_to_null(self) -> None:
        parsed = parse_transaction_result(tx_obj(HASH_A, to_addr=None))
        assert parsed is not None
        self.assertIsNone(parsed.to_addr)

    def test_missing_transaction_response(self) -> None:
        self.assertIsNone(parse_transaction_result(None))

    def test_malformed_transaction_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_transaction_result({"hash": HASH_A})

    def test_receipt_success_and_failure_status(self) -> None:
        ok = parse_receipt_result(
            {
                "transactionHash": HASH_A,
                "blockNumber": "0x10",
                "status": "0x1",
            }
        )
        bad = parse_receipt_result(
            {
                "transactionHash": HASH_A,
                "blockNumber": "0x11",
                "status": "0x0",
            }
        )
        assert ok is not None and bad is not None
        self.assertEqual(ok["status"], "0x1")
        self.assertEqual(bad["status"], "0x0")
        self.assertEqual(ok["block_number"], 16)


class LifecycleTests(unittest.TestCase):
    def test_pending_registration(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        clock = FakeClock()
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=clock.now))
        assert rec is not None
        self.assertEqual(rec.state, STATE_PENDING)
        self.assertEqual(rec.from_addr, ADDR_1)
        self.assertEqual(rec.nonce, 1)
        self.assertEqual(rec.network, NETWORK)
        self.assertEqual(rec.source, SOURCE)

    def test_rpc_error_on_parse(self) -> None:
        rpc = FakeRpc()
        rpc.errors["eth_getTransactionByHash:" + HASH_A] = JsonRpcError("boom")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertEqual(rec.state, STATE_PENDING)
        self.assertIn("boom", rec.parse_error or "")

    def test_duplicate_notification_noop(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        first = mgr.ingest_pending_event(event(HASH_A, ts=10))
        second = mgr.ingest_pending_event(event(HASH_A, ts=20))
        self.assertIs(first, second)
        self.assertEqual(len(mgr.records), 1)

    def test_same_sender_same_nonce_replacement(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, from_addr=ADDR_1, nonce="0x7")
        rpc.txs[HASH_B] = tx_obj(HASH_B, from_addr=ADDR_1, nonce="0x7")
        clock = FakeClock()
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        old = mgr.ingest_pending_event(event(HASH_A, ts=clock.now))
        new = mgr.ingest_pending_event(event(HASH_B, ts=clock.now))
        assert old is not None and new is not None
        self.assertEqual(old.state, STATE_REPLACED)
        self.assertEqual(old.replaced_by, HASH_B)
        self.assertEqual(new.state, STATE_PENDING)
        self.assertEqual(new.replaces, HASH_A)

    def test_different_sender_same_nonce_not_replacement(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, from_addr=ADDR_1, nonce="0x3")
        rpc.txs[HASH_B] = tx_obj(HASH_B, from_addr=ADDR_2, nonce="0x3")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        a = mgr.ingest_pending_event(event(HASH_A))
        b = mgr.ingest_pending_event(event(HASH_B))
        assert a is not None and b is not None
        self.assertEqual(a.state, STATE_PENDING)
        self.assertEqual(b.state, STATE_PENDING)
        self.assertIsNone(a.replaced_by)
        self.assertIsNone(b.replaces)

    def test_confirmation_successful_receipt(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x2a",
            "status": "0x1",
        }
        clock = FakeClock()
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=clock.now))
        mgr.reconcile()
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 42)
        self.assertEqual(rec.receipt_status, "0x1")
        self.assertIsNotNone(rec.confirmed_ts)

    def test_confirmation_failed_execution_receipt(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x2b",
            "status": "0x0",
        }
        clock = FakeClock()
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=clock.now))
        mgr.reconcile()
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.receipt_status, "0x0")

    def test_timeout_suspected_dropped(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        clock = FakeClock(1000.0)
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=1000.0))
        rpc.txs.pop(HASH_A, None)
        clock.advance(31)
        mgr.reconcile()
        assert rec is not None
        self.assertEqual(rec.state, STATE_SUSPECTED_DROPPED)

    def test_missing_tx_not_immediately_dropped(self) -> None:
        rpc = FakeRpc()
        clock = FakeClock(1000.0)
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=60)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=1000.0))
        clock.advance(10)
        mgr.reconcile()
        assert rec is not None
        self.assertEqual(rec.state, STATE_PENDING)

    def test_suspected_dropped_reappears_as_pending(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        clock = FakeClock(1000.0)
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=20)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=1000.0))
        rpc.txs.pop(HASH_A, None)
        clock.advance(21)
        mgr.reconcile()
        self.assertEqual(rec.state, STATE_SUSPECTED_DROPPED)
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        clock.advance(1)
        again = mgr.ingest_pending_event(event(HASH_A, ts=clock.now))
        assert again is not None
        self.assertEqual(again.state, STATE_PENDING)

    def test_suspected_dropped_reappears_confirmed(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1")
        clock = FakeClock(1000.0)
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=20)
        rec = mgr.ingest_pending_event(event(HASH_A, ts=1000.0))
        rpc.txs.pop(HASH_A, None)
        clock.advance(25)
        mgr.reconcile()
        self.assertEqual(rec.state, STATE_SUSPECTED_DROPPED)
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x99",
            "status": "0x1",
        }
        clock.advance(1)
        mgr.reconcile()
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 153)

    def test_clean_shutdown_stops_ingest(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        mgr.stop()
        self.assertIsNone(mgr.ingest_pending_event(event(HASH_A)))
        self.assertEqual(len(mgr.records), 0)

    def test_contract_creation_lifecycle(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_C] = tx_obj(HASH_C, to_addr=None, nonce="0x0")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_C))
        assert rec is not None
        assert rec.parsed is not None
        self.assertIsNone(rec.parsed.to_addr)
        self.assertEqual(rec.state, STATE_PENDING)

    def test_mined_at_ingest_fills_successful_receipt_status(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1", block_number="0x10")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x10",
            "status": "0x1",
        }
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 16)
        self.assertEqual(rec.receipt_status, "0x1")
        receipt_calls = [c for c in rpc.calls if c[0] == "eth_getTransactionReceipt"]
        self.assertEqual(len(receipt_calls), 1)

    def test_mined_at_ingest_fills_failed_receipt_status(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_B] = tx_obj(HASH_B, nonce="0x2", block_number="0x11")
        rpc.receipts[HASH_B] = {
            "transactionHash": HASH_B,
            "blockNumber": "0x11",
            "status": "0x0",
        }
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_B))
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 17)
        self.assertEqual(rec.receipt_status, "0x0")

    def test_mined_at_ingest_keeps_confirmed_if_receipt_missing(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1", block_number="0x12")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 18)
        self.assertIsNone(rec.receipt_status)

    def test_mined_at_ingest_keeps_confirmed_if_receipt_rpc_errors(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, nonce="0x1", block_number="0x13")
        rpc.errors["eth_getTransactionReceipt:" + HASH_A] = JsonRpcError("receipt down")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.confirmed_block, 19)
        self.assertIsNone(rec.receipt_status)

    def test_bytecode_retrieved_for_contract_call(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, input_data="0x")
        rpc.codes[ADDR_2] = "0x60806040"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_RETRIEVED)
        self.assertEqual(rec.bytecode.bytecode, "0x60806040")
        self.assertEqual(rec.bytecode.block_id, "latest")
        code_calls = [c for c in rpc.calls if c[0] == "eth_getCode"]
        self.assertEqual(code_calls[0], ("eth_getCode", [ADDR_2, "latest"]))

    def test_bytecode_eoa_no_code(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = "0x"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_NO_CODE)

    def test_contract_creation_awaits_before_confirm(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_C] = tx_obj(HASH_C, to_addr=None, nonce="0x0")
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_C))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_AWAITING_CREATION)
        self.assertEqual([c for c in rpc.calls if c[0] == "eth_getCode"], [])

    def test_contract_creation_fetches_after_receipt(self) -> None:
        created = "0x" + ("3" * 40)
        rpc = FakeRpc()
        rpc.txs[HASH_C] = tx_obj(HASH_C, to_addr=None, nonce="0x0")
        rpc.receipts[HASH_C] = {
            "transactionHash": HASH_C,
            "blockNumber": "0x20",
            "status": "0x1",
            "contractAddress": created,
        }
        rpc.codes[created] = "0xdeadbeef"
        clock = FakeClock()
        mgr = TxLifecycleManager(rpc_call=rpc, now_fn=clock, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_C, ts=clock.now))
        assert rec is not None
        self.assertEqual(rec.bytecode.status, STATUS_AWAITING_CREATION)
        mgr.reconcile()
        assert rec.bytecode is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.bytecode.status, STATUS_RETRIEVED)
        self.assertEqual(rec.bytecode.contract_address, created)
        self.assertEqual(rec.bytecode.block_id, "0x20")
        self.assertEqual(rec.created_contract_address, created)

    def test_confirmed_uses_block_id(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, block_number="0x10")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x10",
            "status": "0x1",
        }
        rpc.codes[ADDR_2] = "0x60806040"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.state, STATE_CONFIRMED)
        self.assertEqual(rec.bytecode.block_id, "0x10")

    def test_reconcile_does_not_repeat_successful_retrieval(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = "0x60806040"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        before = len([c for c in rpc.calls if c[0] == "eth_getCode"])
        mgr.reconcile()
        after = len([c for c in rpc.calls if c[0] == "eth_getCode"])
        self.assertEqual(before, after)
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_RETRIEVED)

    def test_bytecode_cache_hit_across_transactions(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.txs[HASH_B] = tx_obj(HASH_B, nonce="0x2")
        rpc.codes[ADDR_2] = "0x60806040"
        cache = BytecodeCache(max_entries=16)
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30, bytecode_cache=cache)
        first = mgr.ingest_pending_event(event(HASH_A))
        second = mgr.ingest_pending_event(event(HASH_B))
        assert first is not None and first.bytecode is not None
        assert second is not None and second.bytecode is not None
        self.assertEqual(first.bytecode.status, STATUS_RETRIEVED)
        self.assertEqual(second.bytecode.status, STATUS_RETRIEVED)
        self.assertEqual(second.bytecode.bytecode, "0x60806040")
        code_calls = [c for c in rpc.calls if c[0] == "eth_getCode"]
        self.assertEqual(len(code_calls), 1)
        self.assertEqual(cache.stats()["hits"], 1)

    def test_bytecode_cache_separates_latest_from_confirmed_block(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = "0x60806040"
        cache = BytecodeCache(max_entries=16)
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30, bytecode_cache=cache)
        pending = mgr.ingest_pending_event(event(HASH_A))
        assert pending is not None and pending.bytecode is not None
        self.assertEqual(pending.bytecode.block_id, "latest")
        rpc.txs[HASH_A] = tx_obj(HASH_A, block_number="0x10")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x10",
            "status": "0x1",
        }
        pending.bytecode = None
        mgr.reconcile()
        assert pending.bytecode is not None
        self.assertEqual(pending.state, STATE_CONFIRMED)
        self.assertEqual(pending.bytecode.block_id, "0x10")
        code_calls = [c for c in rpc.calls if c[0] == "eth_getCode"]
        self.assertEqual(len(code_calls), 2)
        self.assertEqual(code_calls[0][1][1], "latest")
        self.assertEqual(code_calls[1][1][1], "0x10")

    def test_cfg_and_selectors_attached_after_retrieve(self) -> None:
        dispatcher = (
            "0x"
            "35"
            "63deadbeef"
            "14"
            "600b"
            "57"
            "00"
            "5b"
            "00"
        )
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = dispatcher
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertIsNotNone(rec.instructions)
        self.assertIsNotNone(rec.cfg)
        assert rec.selectors is not None
        self.assertEqual(rec.selectors.bytecode_role, ROLE_RUNTIME)
        self.assertFalse(rec.selectors.implementation_selectors_available)
        self.assertTrue(any(s.selector == "0xdeadbeef" and s.confidence == CONFIDENCE_HIGH for s in rec.selectors.selectors))
        self.assertGreaterEqual(rec.cfg["stats"]["resolved_jumps"], 1)

    def test_proxy_selectors_do_not_claim_implementation(self) -> None:
        impl = "abababababababababababababababababababab"
        eip1167 = (
            "0x363d3d373d3d3d363d73"
            + impl
            + "5af43d82803e903d91602b57fd5bf3"
        )
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = eip1167
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.proxy is not None and rec.selectors is not None
        self.assertEqual(rec.proxy.kind, KIND_EIP1167)
        self.assertEqual(rec.selectors.bytecode_role, ROLE_PROXY)
        self.assertFalse(rec.selectors.implementation_selectors_available)
        self.assertIsNotNone(rec.cfg)

    def test_proxy_detection_on_eip1167_retrieval(self) -> None:
        impl = "abababababababababababababababababababab"
        eip1167 = (
            "0x363d3d373d3d3d363d73"
            + impl
            + "5af43d82803e903d91602b57fd5bf3"
        )
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = eip1167
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_RETRIEVED)
        assert rec.proxy is not None
        self.assertTrue(rec.proxy.is_proxy)
        self.assertEqual(rec.proxy.kind, KIND_EIP1167)
        self.assertEqual(rec.proxy.confidence, CONFIDENCE_CONFIRMED)
        self.assertEqual(rec.proxy.implementation_address, "0x" + impl)
        self.assertEqual(rec.proxy.implementation_source, "bytecode")

    def test_proxy_detection_none_for_ordinary_bytecode(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = "0x60806040"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.bytecode.status, STATUS_RETRIEVED)
        assert rec.proxy is not None
        self.assertFalse(rec.proxy.is_proxy)
        self.assertEqual(rec.proxy.confidence, CONFIDENCE_NONE)

    def test_proxy_detection_skipped_on_no_code(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        rpc.codes[ADDR_2] = "0x"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None
        self.assertEqual(rec.bytecode.status, STATUS_NO_CODE)
        self.assertIsNone(rec.proxy)

    def test_confirmed_prefers_block_hash_for_getcode(self) -> None:
        block_hash = "0x" + ("cd" * 32)
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A, block_number="0x10")
        rpc.receipts[HASH_A] = {
            "transactionHash": HASH_A,
            "blockNumber": "0x10",
            "blockHash": block_hash,
            "status": "0x1",
        }
        rpc.codes[ADDR_2] = "0x60806040"
        mgr = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=30)
        rec = mgr.ingest_pending_event(event(HASH_A))
        assert rec is not None and rec.bytecode is not None
        self.assertEqual(rec.confirmed_block, 16)
        self.assertEqual(rec.confirmed_block_hash, block_hash)
        self.assertEqual(rec.bytecode.block_id, block_hash)
        code_calls = [c for c in rpc.calls if c[0] == "eth_getCode"]
        self.assertEqual(code_calls[0], ("eth_getCode", [ADDR_2, block_hash]))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
