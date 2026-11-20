from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sepolia_pending_listener import (
    ENV_WS_URL,
    NETWORK,
    SOURCE,
    PendingTxRecord,
    SepoliaPendingListener,
    load_ws_url,
    normalize_tx_hash,
    parse_notification,
    validate_ws_url,
)


VALID_HASH_A = "0x" + ("a" * 64)
VALID_HASH_B = "0x" + ("b" * 64)
VALID_HASH_A_UPPER = "0x" + ("A" * 64)


class FakeWebSocket:
    def __init__(
        self,
        *,
        sub_response: Optional[dict[str, Any]] = None,
        notifications: Optional[list[Any]] = None,
        recv_error_after: Optional[int] = None,
        close_on_enter: bool = False,
    ) -> None:
        self.sub_response = sub_response if sub_response is not None else {"jsonrpc": "2.0", "id": 1, "result": "0xsub"}
        self.notifications = list(notifications or [])
        self.recv_error_after = recv_error_after
        self.close_on_enter = close_on_enter
        self.sent: list[str] = []
        self.closed = False
        self._phase = "sub"
        self._index = 0
        self._notif_index = 0

    async def __aenter__(self) -> "FakeWebSocket":
        if self.close_on_enter:
            raise ConnectionError("connect failed")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.closed = True

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if self._phase == "sub":
            self._phase = "notify"
            return json.dumps(self.sub_response)
        if self.recv_error_after is not None and self._notif_index >= self.recv_error_after:
            raise ConnectionError("socket closed")
        if self._notif_index >= len(self.notifications):
            await asyncio.sleep(0.05)
            raise asyncio.TimeoutError()
        item = self.notifications[self._notif_index]
        self._notif_index += 1
        if isinstance(item, Exception):
            raise item
        if isinstance(item, dict):
            return json.dumps(item)
        return str(item)


class FakeConnect:
    def __init__(self, factories: list[Any]) -> None:
        self.factories = list(factories)
        self.urls: list[str] = []
        self.calls = 0

    async def __call__(self, url: str) -> FakeWebSocket:
        self.calls += 1
        self.urls.append(url)
        if not self.factories:
            raise ConnectionError("no more fake sockets")
        factory = self.factories.pop(0)
        return factory()


class ConfigTests(unittest.TestCase):
    def test_load_ws_url_from_env_map(self) -> None:
        url = load_ws_url({ENV_WS_URL: "  wss://example.test/sepolia  "})
        self.assertEqual(url, "wss://example.test/sepolia")

    def test_missing_url_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_ws_url("")

    def test_invalid_scheme_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_ws_url("https://example.test/sepolia")

    def test_valid_ws_and_wss_accepted(self) -> None:
        self.assertEqual(validate_ws_url("ws://localhost:8546"), "ws://localhost:8546")
        self.assertEqual(validate_ws_url("wss://sepolia.example/ws"), "wss://sepolia.example/ws")


class ParseTests(unittest.TestCase):
    def test_normalize_valid_hash(self) -> None:
        self.assertEqual(normalize_tx_hash(VALID_HASH_A_UPPER), VALID_HASH_A)

    def test_normalize_rejects_short_hash(self) -> None:
        self.assertIsNone(normalize_tx_hash("0xabc"))

    def test_parse_notification_extracts_hash(self) -> None:
        message = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "eth_subscription",
                "params": {"subscription": "0xsub", "result": VALID_HASH_B},
            }
        )
        self.assertEqual(parse_notification(message), VALID_HASH_B)

    def test_parse_notification_ignores_malformed(self) -> None:
        self.assertIsNone(parse_notification("not-json"))
        self.assertIsNone(parse_notification(json.dumps({"params": {"result": "0x123"}})))


class ListenerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_subscribe_and_record_pending_hash(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A},
        }

        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note])

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )

        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if listener.record_count() >= 1:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        await asyncio.sleep(0.01)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.assertTrue(listener.subscribed)
        self.assertEqual(listener.record_count(), 1)
        record = listener.records[0]
        self.assertIsInstance(record, PendingTxRecord)
        self.assertEqual(record.tx_hash, VALID_HASH_A)
        self.assertEqual(record.network, "sepolia")
        self.assertEqual(record.network, NETWORK)
        self.assertEqual(record.source, "live_ws")
        self.assertEqual(record.source, SOURCE)
        self.assertGreater(record.first_seen_ts, 0)
        self.assertEqual(len(connect.urls), 1)

    async def test_subscription_payload_sent(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A},
        }
        sockets: list[FakeWebSocket] = []

        def make_ws() -> FakeWebSocket:
            ws = FakeWebSocket(notifications=[note])
            sockets.append(ws)
            return ws

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if listener.record_count() >= 1:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.assertEqual(len(sockets), 1)
        payload = json.loads(sockets[0].sent[0])
        self.assertEqual(payload["method"], "eth_subscribe")
        self.assertEqual(payload["params"], ["newPendingTransactions"])

    async def test_duplicate_notifications_recorded_once(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A_UPPER},
        }

        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note, note, note])

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if listener.record_count() >= 1:
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
        self.assertEqual(listener.record_count(), 1)

    async def test_disconnect_triggers_reconnect(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_B},
        }

        def first() -> FakeWebSocket:
            return FakeWebSocket(recv_error_after=0)

        def second() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note])

        connect = FakeConnect([first, second])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(100):
            if listener.record_count() >= 1:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.assertGreaterEqual(listener.connect_attempts, 2)
        self.assertEqual(listener.record_count(), 1)
        self.assertEqual(listener.records[0].tx_hash, VALID_HASH_B)

    async def test_subscription_failure_reconnects(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A},
        }

        def bad() -> FakeWebSocket:
            return FakeWebSocket(sub_response={"jsonrpc": "2.0", "id": 1, "error": {"message": "denied"}})

        def good() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note])

        connect = FakeConnect([bad, good])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(100):
            if listener.record_count() >= 1:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.assertEqual(listener.record_count(), 1)

    async def test_shutdown_stops_cleanly(self) -> None:
        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[])

        connect = FakeConnect([make_ws, make_ws, make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        await asyncio.sleep(0.05)
        await listener.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass
        self.assertTrue(task.done())

    async def test_missing_config_fails_before_connect(self) -> None:
        connect = FakeConnect([])
        listener = SepoliaPendingListener(ws_url="", connect_fn=connect)
        with self.assertRaises(ValueError):
            await listener.run()
        self.assertEqual(connect.calls, 0)

    async def test_on_pending_callback_receives_schema(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A},
        }
        seen: list[PendingTxRecord] = []

        def on_pending(record: PendingTxRecord) -> None:
            seen.append(record)

        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note])

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            on_pending=on_pending,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if seen:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].tx_hash, VALID_HASH_A)
        self.assertEqual(seen[0].network, NETWORK)
        self.assertEqual(seen[0].source, SOURCE)
        self.assertGreater(seen[0].first_seen_ts, 0)
        self.assertIn(VALID_HASH_A, listener.seen)

    async def test_failed_callback_does_not_mark_seen(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_A},
        }
        calls = {"n": 0}

        def on_pending(record: PendingTxRecord) -> bool:
            calls["n"] += 1
            return False

        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note, note])

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            on_pending=on_pending,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if calls["n"] >= 2:
                break
            await asyncio.sleep(0.02)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.assertGreaterEqual(calls["n"], 2)
        self.assertNotIn(VALID_HASH_A, listener.seen)
        self.assertEqual(listener.record_count(), 0)

    async def test_successful_callback_marks_seen(self) -> None:
        note = {
            "jsonrpc": "2.0",
            "method": "eth_subscription",
            "params": {"subscription": "0xsub", "result": VALID_HASH_B},
        }

        def on_pending(record: PendingTxRecord) -> None:
            return None

        def make_ws() -> FakeWebSocket:
            return FakeWebSocket(notifications=[note, note])

        connect = FakeConnect([make_ws])
        listener = SepoliaPendingListener(
            ws_url="wss://example.test/sepolia",
            connect_fn=connect,
            on_pending=on_pending,
            initial_backoff_s=0.01,
            max_backoff_s=0.05,
        )
        task = asyncio.create_task(listener.run())
        for _ in range(50):
            if VALID_HASH_B in listener.seen:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)
        await listener.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.assertIn(VALID_HASH_B, listener.seen)
        self.assertEqual(listener.record_count(), 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
