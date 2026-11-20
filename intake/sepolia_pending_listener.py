from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed


NETWORK = "sepolia"
SOURCE = "live_ws"
ENV_WS_URL = "SEPOLIA_WS_URL"
TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

ConnectFn = Callable[[str], Awaitable[Any]]
OnPendingFn = Callable[["PendingTxRecord"], Union[None, Awaitable[None]]]


@dataclass(frozen=True)
class PendingTxRecord:
    tx_hash: str
    network: str
    first_seen_ts: float
    source: str


def load_ws_url(env: Optional[dict[str, str]] = None) -> str:
    source = env if env is not None else os.environ
    return (source.get(ENV_WS_URL) or "").strip()


def validate_ws_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        raise ValueError(f"{ENV_WS_URL} is missing or empty")
    lower = text.lower()
    if not (lower.startswith("ws://") or lower.startswith("wss://")):
        raise ValueError(f"{ENV_WS_URL} must start with ws:// or wss://")
    return text


def normalize_tx_hash(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not TX_HASH_RE.match(text):
        return None
    return text.lower()


def parse_notification(message: str) -> Optional[str]:
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    params = payload.get("params")
    if not isinstance(params, dict):
        return None
    return normalize_tx_hash(params.get("result"))


def default_connect(url: str) -> Awaitable[Any]:
    return websockets.connect(url)


class SepoliaPendingListener:
    def __init__(
        self,
        ws_url: Optional[str] = None,
        *,
        connect_fn: Optional[ConnectFn] = None,
        on_pending: Optional[OnPendingFn] = None,
        max_backoff_s: float = 30.0,
        initial_backoff_s: float = 1.0,
        max_records: int = 10_000,
    ) -> None:
        self.ws_url = ws_url if ws_url is not None else load_ws_url()
        self.connect_fn = connect_fn or default_connect
        self.on_pending = on_pending
        self.max_backoff_s = max_backoff_s
        self.initial_backoff_s = initial_backoff_s
        self.max_records = max_records
        self.records: list[PendingTxRecord] = []
        self.seen: set[str] = set()
        self.subscribed = False
        self.connect_attempts = 0
        self._stop = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None

    def record_count(self) -> int:
        return len(self.records)

    def request_stop(self) -> None:
        self._stop.set()

    async def stop(self) -> None:
        self.request_stop()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def run(self) -> None:
        url = validate_ws_url(self.ws_url)
        backoff = self.initial_backoff_s
        while not self._stop.is_set():
            self.connect_attempts += 1
            try:
                await self._session(url)
                backoff = self.initial_backoff_s
            except asyncio.CancelledError:
                raise
            except Exception:
                if self._stop.is_set():
                    break
                await self._wait_backoff(backoff)
                backoff = min(backoff * 2.0, self.max_backoff_s)

    async def _wait_backoff(self, delay: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            return

    async def _session(self, url: str) -> None:
        self.subscribed = False
        async with await self.connect_fn(url) as ws:
            await self._subscribe(ws)
            self.subscribed = True
            while not self._stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except ConnectionClosed:
                    raise
                await self._handle_message(raw)

    async def _subscribe(self, ws: Any) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newPendingTransactions"],
        }
        await ws.send(json.dumps(request))
        raw = await ws.recv()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("subscription response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("subscription response was not an object")
        if payload.get("error") is not None:
            raise RuntimeError(f"subscription failed: {payload.get('error')}")
        if payload.get("result") in (None, ""):
            raise RuntimeError("subscription failed: missing result id")

    async def _handle_message(self, raw: Any) -> None:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not isinstance(raw, str):
            return
        tx_hash = parse_notification(raw)
        if tx_hash is None:
            return
        if tx_hash in self.seen:
            return
        record = PendingTxRecord(
            tx_hash=tx_hash,
            network=NETWORK,
            first_seen_ts=time.time(),
            source=SOURCE,
        )
        if self.on_pending is None:
            self._commit_seen(tx_hash, record)
            return
        try:
            result = self.on_pending(record)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            return
        if result is False:
            return
        self._commit_seen(tx_hash, record)

    def _commit_seen(self, tx_hash: str, record: PendingTxRecord) -> None:
        if tx_hash in self.seen:
            return
        self.seen.add(tx_hash)
        self.records.append(record)
        if len(self.records) > self.max_records:
            overflow = len(self.records) - self.max_records
            self.records = self.records[overflow:]


async def run_listener_forever(ws_url: Optional[str] = None) -> SepoliaPendingListener:
    listener = SepoliaPendingListener(ws_url=ws_url)
    await listener.run()
    return listener


def main() -> None:
    listener = SepoliaPendingListener()
    try:
        asyncio.run(listener.run())
    except KeyboardInterrupt:
        listener.request_stop()


if __name__ == "__main__":
    main()
