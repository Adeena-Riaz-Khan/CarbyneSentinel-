from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import math
import re
import threading
import time
from typing import Callable

_ADDR_HEX_RE = re.compile(r"[0-9a-f]{40}")
_HEX_RE = re.compile(r"[0-9a-f]+")


def normalize_address(address: str) -> str:
    """Validate and normalize an Ethereum address to lowercase 0x-prefixed hex."""
    if not isinstance(address, str):
        raise ValueError("address must be a string")
    text = address.strip().lower()
    body = text[2:] if text.startswith("0x") else text
    if _ADDR_HEX_RE.fullmatch(body) is None:
        raise ValueError("address must be 40 hex characters with optional 0x prefix")
    return "0x" + body


def normalize_bytecode(bytecode: str) -> str:
    """Validate and normalize EVM bytecode hex; maps empty/0x to '0x'."""
    if not isinstance(bytecode, str):
        raise ValueError("bytecode must be a string")
    text = bytecode.strip().lower()
    if text == "" or text == "0x":
        return "0x"
    body = text[2:] if text.startswith("0x") else text
    if len(body) % 2 != 0:
        raise ValueError("bytecode hex length must be even")
    # Validate explicitly before bytes.fromhex, which silently ignores spaces.
    if _HEX_RE.fullmatch(body) is None:
        raise ValueError("bytecode must contain only valid hex characters")
    return "0x" + body


def bytecode_sha256(normalized_bytecode: str) -> str:
    """Return the SHA-256 hex digest over raw decoded bytecode bytes."""
    norm = normalize_bytecode(normalized_bytecode)
    raw = b"" if norm == "0x" else bytes.fromhex(norm[2:])
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    """Immutable cached bytecode record keyed by normalized address."""

    address: str
    bytecode: str
    code_hash: str
    is_empty: bool


class BytecodeCache:
    """Thread-safe LRU cache for EVM runtime bytecode with optional lazy TTL."""

    def __init__(
        self,
        max_entries: int = 4096,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # Guard against bool because bool is a subclass of int in Python.
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be an integer >= 1")
        if ttl_seconds is not None:
            if (
                isinstance(ttl_seconds, bool)
                or not isinstance(ttl_seconds, (int, float))
                or not math.isfinite(ttl_seconds)
                or ttl_seconds <= 0
            ):
                raise ValueError("ttl_seconds must be a finite number > 0 or None")
            ttl_value: float | None = float(ttl_seconds)
        else:
            ttl_value = None
        if not callable(clock):
            raise ValueError("clock must be callable")

        self.max_entries = max_entries
        self.ttl_seconds = ttl_value
        self._clock = clock
        self._entries: OrderedDict[str, tuple[CacheEntry, float | None]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    @staticmethod
    def _is_expired(expires_at: float | None, now: float) -> bool:
        return expires_at is not None and now >= expires_at

    def get(self, address: str) -> CacheEntry | None:
        """Fetch entry by address, updating LRU recency, hit/miss, and expiry counters."""
        key = normalize_address(address)
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                self._misses += 1
                return None
            entry, expires_at = item
            if self._is_expired(expires_at, self._clock()):
                del self._entries[key]
                self._expirations += 1
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return entry

    def put(self, address: str, bytecode: str) -> CacheEntry:
        """Insert or update bytecode for address, evicting LRU entries if at capacity."""
        key = normalize_address(address)
        norm_bc = normalize_bytecode(bytecode)
        entry = CacheEntry(
            address=key,
            bytecode=norm_bc,
            code_hash=bytecode_sha256(norm_bc),
            is_empty=(norm_bc == "0x"),
        )
        with self._lock:
            now = self._clock() if self.ttl_seconds is not None else 0.0
            expires_at = (now + self.ttl_seconds) if self.ttl_seconds is not None else None
            if key in self._entries:
                self._entries[key] = (entry, expires_at)
                self._entries.move_to_end(key)
                return entry
            while len(self._entries) >= self.max_entries:
                _, (_, old_expires_at) = self._entries.popitem(last=False)
                if self._is_expired(old_expires_at, now):
                    self._expirations += 1
                else:
                    self._evictions += 1
            self._entries[key] = (entry, expires_at)
            return entry

    def contains(self, address: str) -> bool:
        """Check whether a non-expired entry exists without mutating order or counters."""
        key = normalize_address(address)
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return False
            _, expires_at = item
            if self._is_expired(expires_at, self._clock()):
                return False
            return True

    def delete(self, address: str) -> bool:
        """Remove an address from the cache; returns True if a live entry was removed."""
        key = normalize_address(address)
        with self._lock:
            item = self._entries.pop(key, None)
            if item is None:
                return False
            _, expires_at = item
            if self._is_expired(expires_at, self._clock()):
                self._expirations += 1
                return False
            return True

    def clear(self) -> None:
        """Remove all cached entries and reset all statistics counters."""
        with self._lock:
            self._entries.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0

    def stats(self) -> dict[str, int | float]:
        """Return a snapshot of cache counters, size, capacity, and hit rate."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "size": len(self._entries),
                "max_entries": self.max_entries,
                "hit_rate": hit_rate,
            }
