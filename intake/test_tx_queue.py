from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sepolia_pending_listener import NETWORK, SOURCE, PendingTxRecord
from tx_intake_gate import RESULT_ADMIT, TxIntakeGate
from tx_lifecycle import STATE_PENDING, TxLifecycleManager
from tx_queue import TxQueue


HASH_A = "0x" + ("a" * 64)
HASH_B = "0x" + ("b" * 64)
HASH_C = "0x" + ("c" * 64)
ADDR_1 = "0x" + ("1" * 40)
ADDR_2 = "0x" + ("2" * 40)


def make_event(tx_hash: str, ts: float = 1.0) -> PendingTxRecord:
    return PendingTxRecord(
        tx_hash=tx_hash,
        network=NETWORK,
        first_seen_ts=ts,
        source=SOURCE,
    )


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


class FakeRpc:
    def __init__(self) -> None:
        self.txs: dict[str, Any] = {}

    def __call__(self, method: str, params: list[Any]) -> Any:
        if method == "eth_getTransactionByHash":
            return self.txs.get(params[0])
        if method == "eth_getTransactionReceipt":
            return None
        return None


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_fifo_order(self) -> None:
        order: list[str] = []

        def process(event: PendingTxRecord) -> None:
            order.append(event.tx_hash)

        q = TxQueue(capacity=8, process_fn=process)
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        self.assertTrue(q.try_enqueue(make_event(HASH_B)))
        self.assertTrue(q.try_enqueue(make_event(HASH_C)))
        report = await q.shutdown(drain_timeout_s=2.0)
        self.assertTrue(report.drain_complete)
        self.assertEqual(order, [HASH_A, HASH_B, HASH_C])
        self.assertEqual(q.counters.processed, 3)
        self.assertEqual(q.counters.enqueued, 3)

    async def test_enqueue_dequeue_success(self) -> None:
        seen: list[str] = []
        q = TxQueue(capacity=4, process_fn=lambda e: seen.append(e.tx_hash))
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        await q.shutdown(drain_timeout_s=2.0)
        self.assertEqual(seen, [HASH_A])
        self.assertEqual(q.snapshot_counters()["processed"], 1)

    async def test_capacity_and_queue_full(self) -> None:
        q = TxQueue(capacity=2, process_fn=lambda e: None)
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        self.assertTrue(q.try_enqueue(make_event(HASH_B)))
        self.assertFalse(q.try_enqueue(make_event(HASH_C)))
        self.assertEqual(q.counters.queue_full, 1)
        self.assertEqual(q.counters.rejected, 1)
        self.assertEqual(q.counters.enqueued, 2)
        self.assertEqual(q.counters.enqueue_attempts, 3)
        self.assertEqual(q.depth, 2)
        self.assertEqual(q.counters.processed, 0)

    async def test_counters_separate_from_processed(self) -> None:
        q = TxQueue(capacity=1, process_fn=lambda e: None)
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        self.assertFalse(q.try_enqueue(make_event(HASH_B)))
        snap = q.snapshot_counters()
        self.assertEqual(snap["enqueued"], 1)
        self.assertEqual(snap["queue_full"], 1)
        self.assertEqual(snap["rejected"], 1)
        self.assertEqual(snap["processed"], 0)
        self.assertLessEqual(snap["processed"], snap["enqueued"])

    async def test_consumer_lifecycle_integration(self) -> None:
        rpc = FakeRpc()
        rpc.txs[HASH_A] = tx_obj(HASH_A)
        life = TxLifecycleManager(rpc_call=rpc, drop_timeout_s=60)
        q = TxQueue(capacity=8, process_fn=life.ingest_pending_event)
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        await q.shutdown(drain_timeout_s=2.0)
        rec = life.get(HASH_A)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.state, STATE_PENDING)
        self.assertEqual(q.counters.processed, 1)

    async def test_retry_once_then_success(self) -> None:
        calls = {"n": 0}

        def process(event: PendingTxRecord) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")

        q = TxQueue(capacity=4, process_fn=process)
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        await q.shutdown(drain_timeout_s=2.0)
        self.assertEqual(q.counters.processed, 1)
        self.assertEqual(q.counters.retry_attempts, 1)
        self.assertEqual(q.counters.processing_failures, 1)
        self.assertEqual(q.dead_letter_count(), 0)

    async def test_retry_then_dead_letter(self) -> None:
        def process(event: PendingTxRecord) -> None:
            raise RuntimeError("always fail")

        q = TxQueue(capacity=4, process_fn=process)
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        await q.shutdown(drain_timeout_s=2.0)
        self.assertEqual(q.counters.processed, 0)
        self.assertEqual(q.counters.retry_attempts, 1)
        self.assertEqual(q.counters.processing_failures, 2)
        self.assertEqual(q.counters.dead_lettered, 1)
        self.assertEqual(len(q.dead_letters), 1)
        self.assertEqual(q.dead_letters[0].tx_hash, HASH_A)

    async def test_graceful_drain(self) -> None:
        seen: list[str] = []
        q = TxQueue(capacity=8, process_fn=lambda e: seen.append(e.tx_hash))
        await q.start()
        for h in (HASH_A, HASH_B, HASH_C):
            self.assertTrue(q.try_enqueue(make_event(h)))
        report = await q.shutdown(drain_timeout_s=2.0)
        self.assertTrue(report.drain_complete)
        self.assertFalse(report.drain_timed_out)
        self.assertEqual(report.remaining_depth, 0)
        self.assertEqual(sorted(seen), sorted([HASH_A, HASH_B, HASH_C]))

    async def test_drain_timeout(self) -> None:
        import threading

        hold = threading.Event()

        def slow(event: PendingTxRecord) -> None:
            hold.wait(timeout=30.0)

        q = TxQueue(capacity=2, process_fn=slow, drain_timeout_s=0.05)
        await q.start()
        self.assertTrue(q.try_enqueue(make_event(HASH_A)))
        self.assertTrue(q.try_enqueue(make_event(HASH_B)))
        await asyncio.sleep(0.02)
        report = await q.shutdown(drain_timeout_s=0.05)
        hold.set()
        self.assertTrue(report.drain_timed_out)
        self.assertFalse(report.accepting)
        self.assertLess(q.counters.processed, q.counters.enqueued)
        self.assertEqual(report.processed, q.counters.processed)

    async def test_c3_to_c4_handoff_and_reject_no_c3_commit(self) -> None:
        processed: list[str] = []
        q = TxQueue(capacity=1, process_fn=lambda e: processed.append(e.tx_hash))
        gate = TxIntakeGate(on_admit=q.try_enqueue, retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertTrue(gate.contains_exact(HASH_A))
        failed = gate.handle(make_event(HASH_B))
        self.assertFalse(failed)
        self.assertFalse(gate.contains_exact(HASH_B))
        self.assertEqual(gate.counters.handoff_failures, 1)
        self.assertEqual(gate.counters.admitted, 1)
        self.assertEqual(q.counters.queue_full, 1)
        await q.start()
        await q.shutdown(drain_timeout_s=2.0)
        self.assertEqual(processed, [HASH_A])

    async def test_failed_handoff_allows_later_retry(self) -> None:
        q = TxQueue(capacity=1, process_fn=lambda e: None)
        gate = TxIntakeGate(on_admit=q.try_enqueue, retain_s=3600)
        self.assertEqual(gate.handle(make_event(HASH_A)), RESULT_ADMIT)
        self.assertFalse(gate.handle(make_event(HASH_B)))
        await q.start()
        await q.shutdown(drain_timeout_s=2.0)
        q2 = TxQueue(capacity=2, process_fn=lambda e: None)
        gate.on_admit = q2.try_enqueue
        self.assertEqual(gate.handle(make_event(HASH_B)), RESULT_ADMIT)
        self.assertTrue(gate.contains_exact(HASH_B))
        self.assertEqual(gate.counters.admitted, 2)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
