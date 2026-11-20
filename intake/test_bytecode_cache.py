from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import math
import sys
import threading
import time
import tracemalloc
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bytecode_cache import (
    BytecodeCache,
    CacheEntry,
    bytecode_sha256,
    normalize_address,
    normalize_bytecode,
)


class FakeClock:
    """Deterministic controllable monotonic clock for TTL tests."""

    def __init__(self, initial: float = 100.0) -> None:
        self.now = initial

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _addr(index: int) -> str:
    return f"0x{index:040x}"


class BytecodeCacheTests(unittest.TestCase):
    def test_normalize_address_valid_variants(self) -> None:
        expected = "0x" + "a" * 40
        self.assertEqual(normalize_address("A" * 40), expected)
        self.assertEqual(normalize_address("0x" + "A" * 40), expected)
        self.assertEqual(normalize_address("  0X" + "A" * 40 + "\n"), expected)

    def test_normalize_address_invalid_raises(self) -> None:
        bad_inputs: list[object] = [
            None,
            123,
            "",
            "0x",
            "0x" + "a" * 39,
            "0x" + "a" * 41,
            "0x" + "g" * 40,
            "0x" + "a" * 20 + " " + "a" * 19,
        ]
        for bad in bad_inputs:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_address(bad)  # type: ignore[arg-type]

    def test_normalize_bytecode_valid_variants(self) -> None:
        self.assertEqual(normalize_bytecode(""), "0x")
        self.assertEqual(normalize_bytecode("   "), "0x")
        self.assertEqual(normalize_bytecode("0x"), "0x")
        self.assertEqual(normalize_bytecode(" 0X \t"), "0x")
        self.assertEqual(normalize_bytecode("6080604052"), "0x6080604052")
        self.assertEqual(normalize_bytecode("  0X6080604052  "), "0x6080604052")

    def test_normalize_bytecode_invalid_raises(self) -> None:
        bad_inputs: list[object] = [
            None,
            42,
            "0x600",
            "abc",
            "0x60zz",
            "0x60 00",
            "60\n00",
        ]
        for bad in bad_inputs:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_bytecode(bad)  # type: ignore[arg-type]

    def test_bytecode_sha256_consistency(self) -> None:
        empty_digest = hashlib.sha256(b"").hexdigest()
        self.assertEqual(bytecode_sha256("0x"), empty_digest)
        self.assertEqual(bytecode_sha256(""), empty_digest)

        sample_digest = hashlib.sha256(b"\x60\x00\xfe").hexdigest()
        self.assertEqual(bytecode_sha256("0x6000fe"), sample_digest)
        self.assertEqual(bytecode_sha256("6000FE"), sample_digest)
        self.assertEqual(bytecode_sha256("  0X6000fe "), sample_digest)

        with self.assertRaises(ValueError):
            bytecode_sha256("0x60 00")

    def test_cache_entry_is_frozen(self) -> None:
        cache = BytecodeCache(max_entries=4)
        entry = cache.put(_addr(1), "0x6000")
        self.assertIsInstance(entry, CacheEntry)
        with self.assertRaises(FrozenInstanceError):
            entry.bytecode = "0x00"  # type: ignore[misc]

    def test_constructor_validation(self) -> None:
        for bad_max in (0, -1, True, False, 1.5, "10"):
            with self.subTest(max_entries=bad_max):
                with self.assertRaises(ValueError):
                    BytecodeCache(max_entries=bad_max)  # type: ignore[arg-type]
        for bad_ttl in (0, 0.0, -5.0, True, False, math.nan, math.inf, -math.inf, "10"):
            with self.subTest(ttl_seconds=bad_ttl):
                with self.assertRaises(ValueError):
                    BytecodeCache(ttl_seconds=bad_ttl)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BytecodeCache(clock="not-callable")  # type: ignore[arg-type]

    def test_put_get_and_eoa_negative_caching(self) -> None:
        cache = BytecodeCache(max_entries=8)
        addr_upper = "  " + _addr(1)[2:].upper() + " "
        eoa = cache.put(addr_upper, "")
        self.assertEqual(eoa.address, _addr(1))
        self.assertEqual(eoa.bytecode, "0x")
        self.assertEqual(eoa.code_hash, hashlib.sha256(b"").hexdigest())
        self.assertTrue(eoa.is_empty)

        contract = cache.put(_addr(2), "60806040")
        self.assertEqual(contract.bytecode, "0x60806040")
        self.assertFalse(contract.is_empty)

        fetched_eoa = cache.get(_addr(1))
        self.assertEqual(fetched_eoa, eoa)
        fetched_contract = cache.get(_addr(2).upper())
        self.assertEqual(fetched_contract, contract)
        self.assertIsNone(cache.get(_addr(999)))

        s = cache.stats()
        self.assertEqual(s["hits"], 2)
        self.assertEqual(s["misses"], 1)
        self.assertEqual(s["size"], 2)
        self.assertAlmostEqual(float(s["hit_rate"]), 2 / 3)

    def test_put_update_no_false_eviction_and_lru_order(self) -> None:
        cache = BytecodeCache(max_entries=2)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")

        # Updating an existing key at full capacity must not evict anything.
        updated = cache.put(_addr(1), "0x6011")
        self.assertEqual(updated.bytecode, "0x6011")
        self.assertEqual(cache.stats()["evictions"], 0)
        self.assertEqual(cache.stats()["size"], 2)

        # _addr(2) is now LRU, so inserting _addr(3) should evict _addr(2).
        cache.put(_addr(3), "0x6003")
        self.assertEqual(cache.stats()["evictions"], 1)
        self.assertFalse(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(3)))

        # Touching _addr(1) via get() refreshes its recency, so _addr(3) becomes LRU.
        self.assertIsNotNone(cache.get(_addr(1)))
        cache.put(_addr(4), "0x6004")
        self.assertEqual(cache.stats()["evictions"], 2)
        self.assertFalse(cache.contains(_addr(3)))
        self.assertTrue(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(4)))

    def test_ttl_expiration_lazy_get_and_reset_on_put(self) -> None:
        clock = FakeClock(initial=10.0)
        cache = BytecodeCache(max_entries=4, ttl_seconds=5.0, clock=clock)
        cache.put(_addr(1), "0x6001")

        clock.advance(4.9)
        self.assertTrue(cache.contains(_addr(1)))
        self.assertIsNotNone(cache.get(_addr(1)))

        clock.advance(0.1)  # now == 15.0 >= 10.0 + 5.0
        self.assertFalse(cache.contains(_addr(1)))
        # contains() is strictly read-only, so size & expirations are unchanged yet.
        self.assertEqual(cache.stats()["size"], 1)
        self.assertEqual(cache.stats()["expirations"], 0)

        # get() lazily removes expired entry and updates both expirations and misses.
        self.assertIsNone(cache.get(_addr(1)))
        s = cache.stats()
        self.assertEqual(s["hits"], 1)
        self.assertEqual(s["misses"], 1)
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["size"], 0)

        # Re-inserting resets TTL from the current clock.
        cache.put(_addr(1), "0x6002")
        clock.advance(4.0)
        self.assertIsNotNone(cache.get(_addr(1)))

    def test_put_at_capacity_evicts_expired_head_as_expiration(self) -> None:
        clock = FakeClock(initial=0.0)
        cache = BytecodeCache(max_entries=2, ttl_seconds=10.0, clock=clock)
        cache.put(_addr(1), "0x6001")
        clock.advance(6.0)
        cache.put(_addr(2), "0x6002")

        clock.advance(4.0)  # now == 10.0: _addr(1) expired, _addr(2) still live
        cache.put(_addr(3), "0x6003")

        s = cache.stats()
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["evictions"], 0)
        self.assertEqual(s["size"], 2)
        self.assertFalse(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(3)))

    def test_contains_does_not_mutate_lru_or_stats(self) -> None:
        cache = BytecodeCache(max_entries=2)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")

        # Repeatedly checking _addr(1) must not refresh its LRU position or stats.
        self.assertTrue(cache.contains(_addr(1)))
        self.assertFalse(cache.contains(_addr(99)))
        s_before = cache.stats()
        self.assertEqual(s_before["hits"], 0)
        self.assertEqual(s_before["misses"], 0)

        # _addr(1) must still be the LRU entry and get evicted by _addr(3).
        cache.put(_addr(3), "0x6003")
        self.assertFalse(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(3)))

    def test_invalid_address_raises_in_get_contains_delete_without_mutating_stats(self) -> None:
        cache = BytecodeCache(max_entries=4)
        cache.put(_addr(1), "0x6001")
        for fn in (cache.get, cache.contains, cache.delete):
            with self.subTest(fn=fn.__name__):
                with self.assertRaises(ValueError):
                    fn("not-an-address")
        s = cache.stats()
        self.assertEqual(s["hits"], 0)
        self.assertEqual(s["misses"], 0)
        self.assertEqual(s["size"], 1)

    def test_delete_present_absent_and_expired(self) -> None:
        clock = FakeClock(initial=0.0)
        cache = BytecodeCache(max_entries=4, ttl_seconds=5.0, clock=clock)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")

        self.assertTrue(cache.delete(_addr(1).upper()))
        self.assertFalse(cache.contains(_addr(1)))
        self.assertFalse(cache.delete(_addr(1)))
        self.assertFalse(cache.delete(_addr(99)))

        clock.advance(5.0)
        # Deleting an already-expired entry returns False and records expiration.
        self.assertFalse(cache.delete(_addr(2)))
        s = cache.stats()
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["size"], 0)

    def test_clear_resets_entries_and_stats(self) -> None:
        cache = BytecodeCache(max_entries=2)
        self.assertEqual(cache.stats()["hit_rate"], 0.0)

        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")
        cache.put(_addr(3), "0x6003")
        cache.get(_addr(2))
        cache.get(_addr(999))
        self.assertEqual(cache.stats()["size"], 2)
        self.assertEqual(cache.stats()["evictions"], 1)

        cache.clear()
        s = cache.stats()
        self.assertEqual(
            s,
            {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "expirations": 0,
                "size": 0,
                "max_entries": 2,
                "hit_rate": 0.0,
            },
        )
        self.assertIsNone(cache.get(_addr(2)))

    def test_multithreaded_concurrent_access(self) -> None:
        cache = BytecodeCache(max_entries=64, ttl_seconds=1.0)
        errors: list[BaseException] = []
        stop_barrier = threading.Barrier(8)

        def worker(tid: int) -> None:
            try:
                stop_barrier.wait(timeout=5.0)
                for i in range(250):
                    key = _addr((tid * 37 + i) % 128)
                    op = (tid + i) % 5
                    if op in (0, 1):
                        cache.put(key, f"0x{i + 1:04x}")
                    elif op == 2:
                        cache.get(key)
                    elif op == 3:
                        cache.contains(key)
                    elif op == 4:
                        cache.delete(key)
                    if i % 25 == 0:
                        st = cache.stats()
                        self.assertGreaterEqual(int(st["size"]), 0)
                        self.assertLessEqual(int(st["size"]), 64)
            except BaseException as exc:  # pragma: no cover - captured for assertion
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            self.assertFalse(t.is_alive())

        self.assertEqual(errors, [])
        final_stats = cache.stats()
        self.assertLessEqual(int(final_stats["size"]), 64)
        self.assertGreaterEqual(float(final_stats["hit_rate"]), 0.0)
        self.assertLessEqual(float(final_stats["hit_rate"]), 1.0)


def run_measurements() -> None:
    print("=== Bytecode Cache measurements ===")

    max_entries = 4096
    n_ops = 2000
    cache = BytecodeCache(max_entries=max_entries, ttl_seconds=60.0)
    sample_bytecode = "0x" + ("6080604052" * 51) + "00"  # 256 bytes
    hit_addrs = [_addr(i) for i in range(n_ops)]
    miss_addrs = [_addr(n_ops + i) for i in range(n_ops)]

    start = time.perf_counter()
    for addr in hit_addrs:
        cache.put(addr, sample_bytecode)
    put_seconds = time.perf_counter() - start
    put_per_op_us = (put_seconds / n_ops) * 1_000_000

    start = time.perf_counter()
    for addr in hit_addrs:
        cache.get(addr)
    get_hit_seconds = time.perf_counter() - start
    get_hit_per_op_us = (get_hit_seconds / n_ops) * 1_000_000

    start = time.perf_counter()
    for addr in miss_addrs:
        cache.get(addr)
    get_miss_seconds = time.perf_counter() - start
    get_miss_per_op_us = (get_miss_seconds / n_ops) * 1_000_000

    s = cache.stats()
    print(f"max_entries: {max_entries}")
    print(f"put ops: {n_ops}")
    print(f"put total_s: {put_seconds:.6f}")
    print(f"put_per_op_us: {put_per_op_us:.3f}")
    print(f"get hit ops: {n_ops}")
    print(f"get_hit total_s: {get_hit_seconds:.6f}")
    print(f"get_hit_per_op_us: {get_hit_per_op_us:.3f}")
    print(f"get miss ops: {n_ops}")
    print(f"get_miss total_s: {get_miss_seconds:.6f}")
    print(f"get_miss_per_op_us: {get_miss_per_op_us:.3f}")
    print(f"size: {s['size']}")
    print(f"hit_rate: {float(s['hit_rate']):.6f}")

    tracemalloc.start()
    measured = BytecodeCache(max_entries=max_entries, ttl_seconds=60.0)
    for i in range(1000):
        measured.put(_addr(i), sample_bytecode)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"tracemalloc_current_bytes: {current}")
    print(f"tracemalloc_peak_bytes: {peak}")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BytecodeCacheTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print()
    run_measurements()
    if not result.wasSuccessful():
        raise SystemExit(1)
