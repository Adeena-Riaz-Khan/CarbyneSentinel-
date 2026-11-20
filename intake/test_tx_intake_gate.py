from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from counting_bloom import CountingBloomFilter, tx_key
from sepolia_pending_listener import (
    NETWORK,
    SOURCE,
    PendingTxRecord,
    SepoliaPendingListener,
)
from tx_intake_gate import (
    RESULT_ADMIT,
    RESULT_DUPLICATE,
    RESULT_HANDOFF_FAILED,
    RESULT_INVALID,
    TxIntakeGate,
)
from tx_lifecycle import TxLifecycleManager


HASH_A = "0x" + ("a" * 64)
HASH_B = "0x" + ("b" * 64)
HASH_C = "0x" + ("c" * 64)
ADDR_1 = "0x" + ("1" * 40)
ADDR_2 = "0x" + ("2" * 40)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_event(tx_hash: str, ts: float = 1000.0) -> PendingTxRecord:
    return PendingTxRecord(
        tx_hash=tx_hash,
        network=NETWORK,
        first_seen_ts=ts,
        source=SOURCE,
    )


class FakeRpc:
    def __init__(self) -> None:
        self.txs: dict[str, Any] = {}

    def __call__(self, method: str, params: list[Any]) -> Any:
        if method == "eth_getTransactionByHash":
            return self.txs.get(params[0])
        if method == "eth_getTransactionReceipt":
            return None
        return None


def tx_obj(tx_hash: str) -> dict[str, Any]:
    return {
        "hash": tx_hash,
        "from": ADDR_1,
        "to": ADDR_2,
        "nonce": "0x1",
        "value": "0x0",
        "gas": "0x5208",
        "gasPrice": "0x1",
        "input": "0x",
    }


class FakeWebSocket:
    def __init__(self, notifications: list[Any]) -> None:
        self.notifications = list(notifications)
        self.sent: list[str] = []
        self._phase = "sub"
        self._i = 0

    async def __aenter__(self) -> "FakeWebSocket":
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if self._phase == "sub":
            self._phase = "notify"
            return json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xsub"})
        if self._i >= len(self.notifications):
            await asyncio.sleep(0.05)
            raise asyncio.TimeoutError()
        item = self.notifications[self._i]
        self._i += 1
        return json.dumps(item)


class GateTests(unittest.TestCase):
    def test_first_time_admission(self) -> None:
        clock = FakeClock()
        gate = TxIntakeGate(now_fn=clock, retain_s=3600)
        result = gate.handle(make_event(HASH_A, ts=clock.now))
        self.assertEqual(result, RESULT_ADMIT)
        self.assertEqual(gate.counters.admitted, 1)
        self.assertEqual(gate.counters.notifications, 1)
        self.assertTrue(gate.contains_exact(HASH_A))

    def test_repeated_notification_suppressed(self) -> None:
        clock = FakeClock()
        gate = TxIntakeGate(now_fn=clock, retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        clock.advance(10)
        self.assertEqual(gate.handle(make_event(HASH_A, ts=clock.now)), RESULT_DUPLICATE)
        self.assertEqual(gate.counters.exact_duplicates, 1)
        self.assertEqual(gate.counters.admitted, 1)
        self.assertEqual(gate.exact[HASH_A].admitted_ts, 1000.0)

    def test_duplicate_does_not_refresh_retention(self) -> None:
        clock = FakeClock(1000.0)
        gate = TxIntakeGate(now_fn=clock, retain_s=100.0)
        self.assertEqual(gate.handle(make_event(HASH_A, ts=1000.0)), RESULT_ADMIT)
        clock.advance(50)
        self.assertEqual(gate.handle(make_event(HASH_A, ts=1050.0)), RESULT_DUPLICATE)
        self.assertEqual(gate.exact[HASH_A].admitted_ts, 1000.0)
        clock.advance(50)
        removed = gate.expire(now=clock.now)
        self.assertEqual(removed, 1)
        self.assertFalse(gate.contains_exact(HASH_A))

    def test_bloom_false_positive_still_admits(self) -> None:
        bloom = CountingBloomFilter(size=8, hash_count=3)
        probe_key = tx_key(HASH_A)
        for i in range(500):
            if bloom.maybe_contains(probe_key):
                break
            bloom.insert(tx_key(f"fill-{i}"))
        else:
            self.fail("unable to create deterministic bloom false positive")
        self.assertTrue(bloom.maybe_contains(probe_key))
        clock = FakeClock()
        gate = TxIntakeGate(bloom=bloom, now_fn=clock, retain_s=3600)
        self.assertFalse(gate.contains_exact(HASH_A))
        result = gate.handle(make_event(HASH_A))
        self.assertEqual(result, RESULT_ADMIT)
        self.assertEqual(gate.counters.bloom_possible_matches, 1)
        self.assertEqual(gate.counters.false_positives, 1)
        self.assertEqual(gate.counters.exact_duplicates, 0)
        self.assertTrue(gate.contains_exact(HASH_A))

    def test_multiple_unique_hashes(self) -> None:
        gate = TxIntakeGate(retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertEqual(gate.handle(make_event(HASH_B)), RESULT_ADMIT)
        self.assertEqual(gate.handle(make_event(HASH_C)), RESULT_ADMIT)
        self.assertEqual(gate.counters.admitted, 3)

    def test_invalid_event_rejected(self) -> None:
        gate = TxIntakeGate(retain_s=3600)
        bad = PendingTxRecord(
            tx_hash="0x1234",
            network=NETWORK,
            first_seen_ts=1.0,
            source=SOURCE,
        )
        self.assertEqual(gate.handle(bad), RESULT_INVALID)
        self.assertEqual(gate.counters.invalid, 1)
        self.assertEqual(gate.counters.admitted, 0)

    def test_expire_removes_cbf_and_exact_together(self) -> None:
        clock = FakeClock(1000.0)
        bloom = CountingBloomFilter(size=256, hash_count=4)
        gate = TxIntakeGate(bloom=bloom, now_fn=clock, retain_s=30.0)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        key = tx_key(HASH_A)
        self.assertTrue(bloom.maybe_contains(key))
        clock.advance(30)
        removed = gate.expire(now=clock.now)
        self.assertEqual(removed, 1)
        self.assertFalse(gate.contains_exact(HASH_A))
        self.assertEqual(gate.counters.expired, 1)

    def test_reappear_after_expire_is_admitted(self) -> None:
        clock = FakeClock(1000.0)
        gate = TxIntakeGate(now_fn=clock, retain_s=20.0)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        clock.advance(20)
        gate.expire(now=clock.now)
        clock.advance(1)
        result = gate.handle(make_event(HASH_A, ts=clock.now))
        self.assertEqual(result, RESULT_ADMIT)
        self.assertEqual(gate.counters.admitted, 2)
        self.assertTrue(gate.contains_exact(HASH_A))

    def test_lifecycle_integration_on_admit(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        lifecycle = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=60)
        gate = TxIntakeGate(on_admit=lifecycle.ingest_pending_event, retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_DUPLICATE)
        self.assertIsNotNone(lifecycle.get(HASH_A))
        self.assertEqual(len(lifecycle.records), 1)

    def test_handoff_false_does_not_commit(self) -> None:
        gate = TxIntakeGate(on_admit=lambda event: False, retain_s=3600)
        self.assertFalse(gate.handle(make_event(HASH_A)))
        self.assertEqual(gate.last_result, RESULT_HANDOFF_FAILED)
        self.assertFalse(gate.contains_exact(HASH_A))
        self.assertEqual(gate.counters.admitted, 0)
        self.assertEqual(gate.counters.handoff_failures, 1)

    def test_handoff_exception_does_not_commit(self) -> None:
        def boom(event: PendingTxRecord) -> None:
            raise RuntimeError("downstream down")

        gate = TxIntakeGate(on_admit=boom, retain_s=3600)
        self.assertFalse(gate.handle(make_event(HASH_A)))
        self.assertFalse(gate.contains_exact(HASH_A))
        self.assertEqual(gate.counters.handoff_failures, 1)

    def test_handoff_none_is_success(self) -> None:
        calls: list[str] = []

        def sink(event: PendingTxRecord) -> None:
            calls.append(event.tx_hash)

        gate = TxIntakeGate(on_admit=sink, retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertEqual(calls, [HASH_A])
        self.assertTrue(gate.contains_exact(HASH_A))

    def test_failed_handoff_then_retry_admits(self) -> None:
        state = {"ok": False}

        def maybe(event: PendingTxRecord) -> bool:
            return state["ok"]

        gate = TxIntakeGate(on_admit=maybe, retain_s=3600)
        self.assertFalse(gate.handle(make_event(HASH_A)))
        state["ok"] = True
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertEqual(gate.counters.admitted, 1)
        self.assertEqual(gate.counters.handoff_failures, 1)


class ListenerGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_listener_callback_through_gate(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": HASH_A},
        }
        admitted: list[PendingTxRecord] = []
        gate = TxIntakeGate(on_admit=admitted.append, retain_s=3600)

        async def connect_fn(url: str):
            return FakeWebSocket([note, note])

        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect_fn,
            on_pending=gate.handle,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if gate.counters.notifications >= 1:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.1)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.assertGreaterEqual(gate.counters.admitted, 1)
        self.assertEqual(len(admitted), 1)
        self.assertEqual(admitted[0].tx_hash, HASH_A)
        self.assertEqual(admitted[0].network, NETWORK)
        self.assertEqual(admitted[0].source, SOURCE)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
