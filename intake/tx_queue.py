from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sepolia_pending_listener import PendingTxRecord


DEFAULT_CAPACITY = 1024
DEFAULT_DRAIN_TIMEOUT_S = 10.0

ProcessFn = Callable[[PendingTxRecord], Any]


@dataclass
class QueueCounters:
    enqueue_attempts: int = 0
    enqueued: int = 0
    processed: int = 0
    queue_full: int = 0
    rejected: int = 0
    processing_failures: int = 0
    retry_attempts: int = 0
    dead_lettered: int = 0
    capacity: int = DEFAULT_CAPACITY


@dataclass
class ShutdownReport:
    drain_complete: bool
    drain_timed_out: bool
    remaining_depth: int
    dead_letter_count: int
    processed: int
    accepting: bool


class TxQueue:
    def __init__(
        self,
        *,
        capacity: int = DEFAULT_CAPACITY,
        process_fn: Optional[ProcessFn] = None,
        drain_timeout_s: float = DEFAULT_DRAIN_TIMEOUT_S,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self.process_fn = process_fn
        self.drain_timeout_s = drain_timeout_s
        self._queue: asyncio.Queue[PendingTxRecord] = asyncio.Queue(maxsize=capacity)
        self.counters = QueueCounters(capacity=capacity)
        self.dead_letters: list[PendingTxRecord] = []
        self._accepting = True
        self._consumer_stop = asyncio.Event()
        self._consumer_task: Optional[asyncio.Task[None]] = None
        self._started = False

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    def dead_letter_count(self) -> int:
        return len(self.dead_letters)

    def try_enqueue(self, event: PendingTxRecord) -> bool:
        self.counters.enqueue_attempts += 1
        if not self._accepting:
            self.counters.rejected += 1
            return False
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.counters.queue_full += 1
            self.counters.rejected += 1
            return False
        self.counters.enqueued += 1
        return True

    async def start(self) -> None:
        if self._started:
            return
        if self.process_fn is None:
            raise ValueError("process_fn is required to start the consumer")
        self._consumer_stop.clear()
        self._accepting = True
        self._consumer_task = asyncio.create_task(self._consume())
        self._started = True

    async def _consume(self) -> None:
        while True:
            if self._consumer_stop.is_set() and self._queue.empty():
                break
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                if self._consumer_stop.is_set() and self._queue.empty():
                    break
                continue
            try:
                await self._process_with_retry(event)
            finally:
                self._queue.task_done()

    async def _process_with_retry(self, event: PendingTxRecord) -> None:
        assert self.process_fn is not None
        for attempt in range(2):
            if attempt == 1:
                self.counters.retry_attempts += 1
            try:
                await asyncio.to_thread(self.process_fn, event)
                self.counters.processed += 1
                return
            except Exception:
                self.counters.processing_failures += 1
        self.dead_letters.append(event)
        self.counters.dead_lettered += 1

    def stop_accepting(self) -> None:
        self._accepting = False

    async def shutdown(self, drain_timeout_s: Optional[float] = None) -> ShutdownReport:
        timeout = self.drain_timeout_s if drain_timeout_s is None else drain_timeout_s
        self._accepting = False
        drain_complete = False
        drain_timed_out = False
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
            drain_complete = True
        except asyncio.TimeoutError:
            drain_timed_out = True
        self._consumer_stop.set()
        if self._consumer_task is not None:
            try:
                await asyncio.wait_for(self._consumer_task, timeout=1.0)
            except asyncio.TimeoutError:
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            self._consumer_task = None
        self._started = False
        return ShutdownReport(
            drain_complete=drain_complete,
            drain_timed_out=drain_timed_out,
            remaining_depth=self.depth,
            dead_letter_count=self.dead_letter_count(),
            processed=self.counters.processed,
            accepting=self._accepting,
        )

    def snapshot_counters(self) -> dict[str, int]:
        return {
            "enqueue_attempts": self.counters.enqueue_attempts,
            "enqueued": self.counters.enqueued,
            "processed": self.counters.processed,
            "queue_full": self.counters.queue_full,
            "rejected": self.counters.rejected,
            "processing_failures": self.counters.processing_failures,
            "retry_attempts": self.counters.retry_attempts,
            "dead_lettered": self.counters.dead_lettered,
            "depth": self.depth,
            "capacity": self.counters.capacity,
        }
