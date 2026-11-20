from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import math
import threading
import time
from typing import Callable


def normalize_address(address: str) -> str:
    if not isinstance(address, str):
        raise ValueError("address must be a string")
    text = address.strip().lower()
    body = text[2:] if text.startswith("0x") else text
    if len(body) != 40:
        raise ValueError("address must be 40 hex characters with optional 0x prefix")
    try:
        int(body, 16)
    except ValueError as exc:
        raise ValueError("address must be 40 hex characters with optional 0x prefix") from exc
    return "0x" + body


def normalize_bytecode(bytecode: str) -> str:
    if not isinstance(bytecode, str):
        raise ValueError("bytecode must be a string")
    text = bytecode.strip().lower()
    if text == "" or text == "0x":
        return "0x"
    if not text.startswith("0x"):
        body = text
        text = "0x" + body
    else:
        body = text[2:]
    if body == "":
        return "0x"
    if len(body) % 2 != 0:
        raise ValueError("bytecode hex length must be even")
    try:
        int(body, 16)
    except ValueError as exc:
        raise ValueError("bytecode must contain only valid hex characters") from exc
    return "0x" + body


def bytecode_sha256(normalized_bytecode: str) -> str:
    norm = normalize_bytecode(normalized_bytecode)
    raw = b"" if norm == "0x" else bytes.fromhex(norm[2:])
    return hashlib.sha256(raw).hexdigest()


def make_cache_key(network: str, address: str, block_id: str) -> str:
    net = (network or "").strip().lower()
    if not net:
        raise ValueError("network must be a non-empty string")
    addr = normalize_address(address)
    block = (block_id or "latest").strip().lower()
    if not block:
        raise ValueError("block_id must be a non-empty string")
    return f"{net}|{addr}|{block}"


@dataclass(frozen=True)
class CacheEntry:
    address: str
    bytecode: str
    code_hash: str
    is_empty: bool
    network: str
    block_id: str


DEFAULT_LATEST_TTL_SECONDS = 30.0


def _validate_ttl(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a finite number > 0 or None")
    return float(value)


class BytecodeCache:
    def __init__(
        self,
        max_entries: int = 4096,
        latest_ttl_seconds: float = DEFAULT_LATEST_TTL_SECONDS,
        confirmed_ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be an integer >= 1")
        latest_ttl = _validate_ttl(latest_ttl_seconds, "latest_ttl_seconds")
        if latest_ttl is None:
            raise ValueError("latest_ttl_seconds must be a finite number > 0")
        confirmed_ttl = _validate_ttl(confirmed_ttl_seconds, "confirmed_ttl_seconds")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self.max_entries = max_entries
        self.latest_ttl_seconds = latest_ttl
        self.confirmed_ttl_seconds = confirmed_ttl
        self._clock = clock
        self._entries: OrderedDict[str, tuple[CacheEntry, float | None]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    def _ttl_for_block(self, block_id: str) -> float | None:
        if block_id == "latest":
            return self.latest_ttl_seconds
        return self.confirmed_ttl_seconds

    @staticmethod
    def _is_expired(expires_at: float | None, now: float) -> bool:
        return expires_at is not None and now >= expires_at

    def get(
        self,
        address: str,
        *,
        network: str = "sepolia",
        block_id: str = "latest",
    ) -> CacheEntry | None:
        key = make_cache_key(network, address, block_id)
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

    def put(
        self,
        address: str,
        bytecode: str,
        *,
        network: str = "sepolia",
        block_id: str = "latest",
    ) -> CacheEntry:
        key = make_cache_key(network, address, block_id)
        norm_bc = normalize_bytecode(bytecode)
        addr = normalize_address(address)
        block = (block_id or "latest").strip().lower()
        net = (network or "").strip().lower()
        entry = CacheEntry(
            address=addr,
            bytecode=norm_bc,
            code_hash=bytecode_sha256(norm_bc),
            is_empty=(norm_bc == "0x"),
            network=net,
            block_id=block,
        )
        with self._lock:
            now = self._clock()
            ttl = self._ttl_for_block(block)
            expires_at = (now + ttl) if ttl is not None else None
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

    def contains(
        self,
        address: str,
        *,
        network: str = "sepolia",
        block_id: str = "latest",
    ) -> bool:
        key = make_cache_key(network, address, block_id)
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return False
            _, expires_at = item
            if self._is_expired(expires_at, self._clock()):
                del self._entries[key]
                self._expirations += 1
                return False
            return True

    def delete(
        self,
        address: str,
        *,
        network: str = "sepolia",
        block_id: str = "latest",
    ) -> bool:
        key = make_cache_key(network, address, block_id)
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
        with self._lock:
            self._entries.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0

    def stats(self) -> dict[str, int | float]:
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
