from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from counting_bloom import CountingBloomFilter, tx_key
from sepolia_pending_listener import PendingTxRecord, normalize_tx_hash


RESULT_ADMIT = "admit"
RESULT_DUPLICATE = "duplicate"
RESULT_INVALID = "invalid"
RESULT_HANDOFF_FAILED = "handoff_failed"

OnAdmitFn = Callable[[PendingTxRecord], Any]


@dataclass
class IntakeCounters:
    notifications: int = 0
    admitted: int = 0
    exact_duplicates: int = 0
    bloom_possible_matches: int = 0
    false_positives: int = 0
    invalid: int = 0
    expired: int = 0
    handoff_failures: int = 0


@dataclass
class _Entry:
    admitted_ts: float
    event: PendingTxRecord


class TxIntakeGate:
    def __init__(
        self,
        *,
        bloom: Optional[CountingBloomFilter] = None,
        retain_s: float = 3600.0,
        on_admit: Optional[OnAdmitFn] = None,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        if retain_s < 0:
            raise ValueError("retain_s must be >= 0")
        self.bloom = bloom if bloom is not None else CountingBloomFilter()
        self.retain_s = retain_s
        self.on_admit = on_admit
        self.now_fn = now_fn
        self.exact: dict[str, _Entry] = {}
        self.counters = IntakeCounters()
        self.last_result: Optional[str] = None

    def handle(self, event: PendingTxRecord) -> Any:
        self.counters.notifications += 1
        if not self._valid_event(event):
            self.counters.invalid += 1
            self.last_result = RESULT_INVALID
            return RESULT_INVALID
        tx_hash = normalize_tx_hash(event.tx_hash)
        if tx_hash is None:
            self.counters.invalid += 1
            self.last_result = RESULT_INVALID
            return RESULT_INVALID
        if tx_hash in self.exact:
            self.counters.exact_duplicates += 1
            self.last_result = RESULT_DUPLICATE
            return RESULT_DUPLICATE
        key = tx_key(tx_hash)
        possible = self.bloom.maybe_contains(key)
        if possible:
            self.counters.bloom_possible_matches += 1
            self.counters.false_positives += 1
        normalized = PendingTxRecord(
            tx_hash=tx_hash,
            network=event.network,
            first_seen_ts=event.first_seen_ts,
            source=event.source,
        )
        if not self._handoff(normalized):
            self.counters.handoff_failures += 1
            self.last_result = RESULT_HANDOFF_FAILED
            return False
        admitted_ts = self.now_fn()
        self.bloom.insert(key)
        self.exact[tx_hash] = _Entry(admitted_ts=admitted_ts, event=normalized)
        self.counters.admitted += 1
        self.last_result = RESULT_ADMIT
        return RESULT_ADMIT

    def _handoff(self, event: PendingTxRecord) -> bool:
        if self.on_admit is None:
            return True
        try:
            result = self.on_admit(event)
        except Exception:
            return False
        if result is False:
            return False
        return True

    def expire(self, now: Optional[float] = None) -> int:
        current = self.now_fn() if now is None else now
        removed = 0
        stale = [
            tx_hash
            for tx_hash, entry in self.exact.items()
            if current - entry.admitted_ts >= self.retain_s
        ]
        for tx_hash in stale:
            key = tx_key(tx_hash)
            self.bloom.remove(key)
            del self.exact[tx_hash]
            removed += 1
        self.counters.expired += removed
        return removed

    def contains_exact(self, tx_hash: str) -> bool:
        normalized = normalize_tx_hash(tx_hash)
        if normalized is None:
            return False
        return normalized in self.exact

    def _valid_event(self, event: Any) -> bool:
        if not isinstance(event, PendingTxRecord):
            return False
        if not isinstance(event.network, str) or not event.network.strip():
            return False
        if not isinstance(event.source, str) or not event.source.strip():
            return False
        if not isinstance(event.first_seen_ts, (int, float)):
            return False
        return normalize_tx_hash(event.tx_hash) is not None
