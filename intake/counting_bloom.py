from __future__ import annotations

import hashlib


ADMIT = "admit"
DROP = "drop"


def normalize_item(value: str) -> str:
    text = (value or "").strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    return text


def tx_key(tx_hash: str) -> str:
    return "tx:" + normalize_item(tx_hash)


def bc_key(bytecode_or_fingerprint: str) -> str:
    return "bc:" + normalize_item(bytecode_or_fingerprint)


class CountingBloomFilter:
    def __init__(self, size: int = 8192, hash_count: int = 5) -> None:
        if size < 1:
            raise ValueError("size must be at least 1")
        if hash_count < 1:
            raise ValueError("hash_count must be at least 1")
        self.size = size
        self.hash_count = hash_count
        self.counters = [0] * size

    def _positions(self, key: str) -> list[int]:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        h1 = int.from_bytes(digest[0:8], "big")
        h2 = int.from_bytes(digest[8:16], "big")
        if h2 % self.size == 0:
            h2 += 1
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    def insert(self, key: str) -> None:
        for index in self._positions(key):
            self.counters[index] += 1

    def maybe_contains(self, key: str) -> bool:
        return all(self.counters[index] > 0 for index in self._positions(key))

    def remove(self, key: str) -> bool:
        positions = self._positions(key)
        if any(self.counters[index] == 0 for index in positions):
            return False
        for index in positions:
            if self.counters[index] > 0:
                self.counters[index] -= 1
        return True

    def admit(self, key: str) -> str:
        if self.maybe_contains(key):
            return DROP
        self.insert(key)
        return ADMIT

    def counter_sum(self) -> int:
        return sum(self.counters)
