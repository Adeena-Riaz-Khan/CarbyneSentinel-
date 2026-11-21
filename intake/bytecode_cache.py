from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import math
import re
import threading
import time
from typing import Callable

STATUS_OK = "ok"
STATUS_NO_CODE = "no_code"

_VALID_BLOCK_TAGS: frozenset[str] = frozenset(
    {"latest", "pending", "earliest", "safe", "finalized"}
)
_ADDR_HEX_RE = re.compile(r"[0-9a-f]{40}", re.ASCII)
_HEX_RE = re.compile(r"[0-9a-f]+", re.ASCII)


def _truncate_repr(value: object, limit: int = 40) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def normalize_address(address: str) -> str:
    """Validate and normalize an Ethereum address under strict C5 / RPC rules.

    Strips outer whitespace, lowercases, and requires a '0x'/'0X' prefix followed
    by exactly 40 ASCII hexadecimal characters. Raises ValueError on missing '0x',
    wrong length, internal whitespace, non-hex/Unicode digits, or non-str input.
    """
    if not isinstance(address, str):
        raise ValueError(f"address must be a string, got {_truncate_repr(address)}")
    text = address.strip().lower()
    if not text.startswith("0x"):
        raise ValueError(
            f"address must start with '0x' prefix, got {_truncate_repr(address)}"
        )
    body = text[2:]
    if _ADDR_HEX_RE.fullmatch(body) is None:
        raise ValueError(
            f"address must be '0x' plus 40 ASCII hex characters, got {_truncate_repr(address)}"
        )
    return "0x" + body


def normalize_bytecode(bytecode: str) -> str:
    """Validate and normalize EVM runtime bytecode under strict C5 / RPC rules.

    Strips outer whitespace, lowercases, and requires a '0x'/'0X' prefix followed
    by an even number of ASCII hexadecimal characters. '0x' is valid and denotes
    empty bytecode (EOA / no_code). Raises ValueError on '', non-str, missing '0x',
    odd length, internal whitespace, or non-hex/Unicode digits.
    """
    if not isinstance(bytecode, str):
        raise ValueError(f"bytecode must be a string, got {_truncate_repr(bytecode)}")
    text = bytecode.strip().lower()
    if not text.startswith("0x"):
        raise ValueError(
            f"bytecode must start with '0x' prefix, got {_truncate_repr(bytecode)}"
        )
    if text == "0x":
        return "0x"
    body = text[2:]
    if len(body) % 2 != 0:
        raise ValueError(
            f"bytecode hex length must be even, got {_truncate_repr(bytecode)}"
        )
    # Validate ASCII hex explicitly before bytes.fromhex, which ignores whitespace.
    if _HEX_RE.fullmatch(body) is None:
        raise ValueError(
            f"bytecode must contain only ASCII hex characters, got {_truncate_repr(bytecode)}"
        )
    return "0x" + body


def normalize_block_tag(block_tag: str | int = "latest") -> str:
    """Validate and canonicalize an Ethereum JSON-RPC block tag or block number.

    Accepts:
      - Named tags (case-insensitive, stripped): 'latest', 'pending', 'earliest',
        'safe', 'finalized'.
      - Non-negative ints (excluding bool): canonicalized via hex(n) ('0x0', '0xa').
      - '0x'/'0X'-prefixed ASCII hex strings: leading zeros stripped ('0x0A' -> '0xa',
        '0x0000' -> '0x0').

    Raises ValueError on bool, negative ints, bare decimal strings, '0x' alone,
    non-ASCII/underscore hex tricks, or any invalid type/value.
    """
    if isinstance(block_tag, bool):
        raise ValueError(f"block_tag must be str or non-negative int, got {_truncate_repr(block_tag)}")
    if isinstance(block_tag, int):
        if block_tag < 0:
            raise ValueError(f"block_tag integer must be non-negative, got {block_tag}")
        return hex(block_tag)
    if isinstance(block_tag, str):
        text = block_tag.strip().lower()
        if text in _VALID_BLOCK_TAGS:
            return text
        if text.startswith("0x"):
            body = text[2:]
            if not body or _HEX_RE.fullmatch(body) is None:
                raise ValueError(
                    f"block_tag hex quantity must have 1+ ASCII hex chars, got {_truncate_repr(block_tag)}"
                )
            return "0x" + (body.lstrip("0") or "0")
        raise ValueError(f"invalid block_tag {_truncate_repr(block_tag)}")
    raise ValueError(
        f"block_tag must be str or non-negative int, got {_truncate_repr(block_tag)}"
    )


def bytecode_sha256(normalized_bytecode: str) -> str:
    """Return the SHA-256 hex digest over decoded raw bytecode bytes."""
    norm = normalize_bytecode(normalized_bytecode)
    raw = b"" if norm == "0x" else bytes.fromhex(norm[2:])
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """Immutable cached bytecode record keyed by (address, block_tag)."""

    address: str
    bytecode: str
    code_hash: str
    is_empty: bool
    block_tag: str = "latest"
    status: str = STATUS_OK


class BytecodeCache:
    """Thread-safe block-aware LRU cache for EVM runtime bytecode with optional lazy TTL.

    Entries are keyed by (normalized_address, normalized_block_tag) so 'pending',
    'latest', and specific block heights never collide. Note that 'no_code' ('0x')
    EOA entries share ttl_seconds; because an address can later receive code via
    CREATE/CREATE2, live screeners should configure a finite ttl_seconds.
    """

    def __init__(
        self,
        max_entries: int = 4096,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
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
        self._entries: OrderedDict[tuple[str, str], tuple[CacheEntry, float | None]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    @staticmethod
    def _is_expired(expires_at: float | None, now: float) -> bool:
        return expires_at is not None and now >= expires_at

    def get(self, address: str, block_tag: str | int = "latest") -> CacheEntry | None:
        """Fetch entry by (address, block_tag), updating LRU recency and stats."""
        key = (normalize_address(address), normalize_block_tag(block_tag))
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
        block_tag: str | int = "latest",
    ) -> CacheEntry:
        """Validate and store bytecode under (address, block_tag), evicting LRU if full."""
        norm_addr = normalize_address(address)
        norm_block = normalize_block_tag(block_tag)
        norm_bc = normalize_bytecode(bytecode)
        is_empty = norm_bc == "0x"
        entry = CacheEntry(
            address=norm_addr,
            bytecode=norm_bc,
            code_hash=bytecode_sha256(norm_bc),
            is_empty=is_empty,
            block_tag=norm_block,
            status=STATUS_NO_CODE if is_empty else STATUS_OK,
        )
        key = (norm_addr, norm_block)
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

    def get_or_fetch(
        self,
        address: str,
        fetcher: Callable[[str, str], str],
        block_tag: str | int = "latest",
    ) -> CacheEntry:
        """Return cached bytecode or fetch via RPC without holding the cache lock.

        Strict execution order:
          1. Validate & normalize address and block_tag (and verify fetcher is callable)
             upfront; ValueError raises before any stats update or RPC call.
          2. Check cache via get(norm_addr, norm_block); return immediately on hit.
          3. On miss, call fetcher(norm_addr, norm_block) OUTSIDE self._lock so slow
             RPC I/O never blocks other threads. Two concurrent threads missing the
             same key will each call fetcher (last write wins on put()).
          4. Never-cache-failures guarantee: any exception raised by fetcher propagates
             unwrapped and leaves the cache unmodified; invalid return values fail
             normalize_bytecode() with ValueError and are never cached.
          5. Only valid responses (including '0x' for no_code) are stored via put().
        """
        norm_addr = normalize_address(address)
        norm_block = normalize_block_tag(block_tag)
        if not callable(fetcher):
            raise ValueError(f"fetcher must be callable, got {_truncate_repr(fetcher)}")

        cached = self.get(norm_addr, norm_block)
        if cached is not None:
            return cached

        raw_bytecode = fetcher(norm_addr, norm_block)
        norm_bc = normalize_bytecode(raw_bytecode)
        return self.put(norm_addr, norm_bc, norm_block)

    def contains(self, address: str, block_tag: str | int = "latest") -> bool:
        """Check non-expired presence for (address, block_tag) without mutating LRU or stats."""
        key = (normalize_address(address), normalize_block_tag(block_tag))
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return False
            _, expires_at = item
            if self._is_expired(expires_at, self._clock()):
                return False
            return True

    def delete(self, address: str, block_tag: str | int = "latest") -> bool:
        """Remove (address, block_tag); returns True only if a live entry was removed."""
        key = (normalize_address(address), normalize_block_tag(block_tag))
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
