from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import math
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bytecode_cache import (
    BytecodeCache,
    CacheEntry,
    bytecode_sha256,
    make_cache_key,
    normalize_address,
    normalize_bytecode,
)


class FakeClock:
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
        for bad in (None, 123, "", "0x", "0x" + "a" * 39, "0x" + "g" * 40):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_address(bad)  # type: ignore[arg-type]

    def test_normalize_bytecode_valid_variants(self) -> None:
        self.assertEqual(normalize_bytecode(""), "0x")
        self.assertEqual(normalize_bytecode("0x"), "0x")
        self.assertEqual(normalize_bytecode("6080604052"), "0x6080604052")
        self.assertEqual(normalize_bytecode("  0X6080604052  "), "0x6080604052")

    def test_normalize_bytecode_invalid_raises(self) -> None:
        for bad in (None, 42, "0x600", "0x60zz"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_bytecode(bad)  # type: ignore[arg-type]

    def test_bytecode_sha256_consistency(self) -> None:
        empty_digest = hashlib.sha256(b"").hexdigest()
        self.assertEqual(bytecode_sha256("0x"), empty_digest)
        sample_digest = hashlib.sha256(b"\x60\x00\xfe").hexdigest()
        self.assertEqual(bytecode_sha256("0x6000fe"), sample_digest)

    def test_make_cache_key_includes_network_and_block(self) -> None:
        key = make_cache_key("Sepolia", _addr(1), "Latest")
        self.assertEqual(key, f"sepolia|{_addr(1)}|latest")
        self.assertNotEqual(
            make_cache_key("sepolia", _addr(1), "latest"),
            make_cache_key("sepolia", _addr(1), "0x10"),
        )
        self.assertNotEqual(
            make_cache_key("sepolia", _addr(1), "latest"),
            make_cache_key("mainnet", _addr(1), "latest"),
        )

    def test_cache_entry_is_frozen(self) -> None:
        cache = BytecodeCache(max_entries=4)
        entry = cache.put(_addr(1), "0x6000")
        self.assertIsInstance(entry, CacheEntry)
        with self.assertRaises(FrozenInstanceError):
            entry.bytecode = "0x00"  # type: ignore[misc]

    def test_constructor_validation(self) -> None:
        for bad_max in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                BytecodeCache(max_entries=bad_max)  # type: ignore[arg-type]
        for bad_ttl in (0, -5.0, True, math.nan, math.inf, None):
            with self.assertRaises(ValueError):
                BytecodeCache(latest_ttl_seconds=bad_ttl)  # type: ignore[arg-type]
        for bad_ttl in (0, -5.0, True, math.nan, math.inf):
            with self.assertRaises(ValueError):
                BytecodeCache(confirmed_ttl_seconds=bad_ttl)  # type: ignore[arg-type]

    def test_put_get_and_eoa_negative_caching(self) -> None:
        cache = BytecodeCache(max_entries=8)
        eoa = cache.put(_addr(1), "")
        self.assertTrue(eoa.is_empty)
        contract = cache.put(_addr(2), "60806040", network="sepolia", block_id="0x10")
        self.assertFalse(contract.is_empty)
        self.assertEqual(cache.get(_addr(1)), eoa)
        self.assertEqual(
            cache.get(_addr(2), network="sepolia", block_id="0x10"),
            contract,
        )
        self.assertIsNone(cache.get(_addr(2), network="sepolia", block_id="latest"))
        s = cache.stats()
        self.assertEqual(s["hits"], 2)
        self.assertEqual(s["misses"], 1)

    def test_network_and_block_isolation(self) -> None:
        cache = BytecodeCache(max_entries=8)
        cache.put(_addr(1), "0x6001", network="sepolia", block_id="latest")
        cache.put(_addr(1), "0x6002", network="sepolia", block_id="0x10")
        cache.put(_addr(1), "0x6003", network="mainnet", block_id="latest")
        self.assertEqual(
            cache.get(_addr(1), network="sepolia", block_id="latest").bytecode,
            "0x6001",
        )
        self.assertEqual(
            cache.get(_addr(1), network="sepolia", block_id="0x10").bytecode,
            "0x6002",
        )
        self.assertEqual(
            cache.get(_addr(1), network="mainnet", block_id="latest").bytecode,
            "0x6003",
        )

    def test_put_update_no_false_eviction_and_lru_order(self) -> None:
        cache = BytecodeCache(max_entries=2)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")
        updated = cache.put(_addr(1), "0x6011")
        self.assertEqual(updated.bytecode, "0x6011")
        self.assertEqual(cache.stats()["evictions"], 0)
        cache.put(_addr(3), "0x6003")
        self.assertEqual(cache.stats()["evictions"], 1)
        self.assertFalse(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(1)))
        self.assertIsNotNone(cache.get(_addr(1)))
        cache.put(_addr(4), "0x6004")
        self.assertFalse(cache.contains(_addr(3)))
        self.assertTrue(cache.contains(_addr(1)))

    def test_ttl_expiration_purged_by_contains_and_get(self) -> None:
        clock = FakeClock(initial=10.0)
        cache = BytecodeCache(max_entries=4, latest_ttl_seconds=5.0, clock=clock)
        cache.put(_addr(1), "0x6001")
        clock.advance(4.9)
        self.assertTrue(cache.contains(_addr(1)))
        self.assertIsNotNone(cache.get(_addr(1)))
        clock.advance(0.1)
        self.assertFalse(cache.contains(_addr(1)))
        s = cache.stats()
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["size"], 0)
        self.assertIsNone(cache.get(_addr(1)))
        self.assertEqual(cache.stats()["misses"], 1)
        cache.put(_addr(1), "0x6002")
        clock.advance(4.0)
        self.assertIsNotNone(cache.get(_addr(1)))

    def test_latest_ttl_does_not_expire_confirmed_entries(self) -> None:
        clock = FakeClock(initial=0.0)
        cache = BytecodeCache(max_entries=8, latest_ttl_seconds=5.0, clock=clock)
        cache.put(_addr(1), "0x6001", block_id="latest")
        cache.put(_addr(1), "0x6002", block_id="0x10")
        clock.advance(5.0)
        self.assertIsNone(cache.get(_addr(1), block_id="latest"))
        self.assertIsNotNone(cache.get(_addr(1), block_id="0x10"))
        self.assertEqual(cache.get(_addr(1), block_id="0x10").bytecode, "0x6002")

    def test_put_at_capacity_evicts_expired_head_as_expiration(self) -> None:
        clock = FakeClock(initial=0.0)
        cache = BytecodeCache(max_entries=2, latest_ttl_seconds=10.0, clock=clock)
        cache.put(_addr(1), "0x6001")
        clock.advance(6.0)
        cache.put(_addr(2), "0x6002")
        clock.advance(4.0)
        cache.put(_addr(3), "0x6003")
        s = cache.stats()
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["evictions"], 0)
        self.assertFalse(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(3)))

    def test_contains_does_not_mutate_lru_or_hit_stats(self) -> None:
        cache = BytecodeCache(max_entries=2)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")
        self.assertTrue(cache.contains(_addr(1)))
        self.assertFalse(cache.contains(_addr(99)))
        self.assertEqual(cache.stats()["hits"], 0)
        self.assertEqual(cache.stats()["misses"], 0)
        cache.put(_addr(3), "0x6003")
        self.assertFalse(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(2)))

    def test_delete_present_absent_and_expired(self) -> None:
        clock = FakeClock(initial=0.0)
        cache = BytecodeCache(max_entries=4, latest_ttl_seconds=5.0, clock=clock)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")
        self.assertTrue(cache.delete(_addr(1).upper()))
        self.assertFalse(cache.delete(_addr(1)))
        clock.advance(5.0)
        self.assertFalse(cache.delete(_addr(2)))
        self.assertEqual(cache.stats()["expirations"], 1)

    def test_clear_resets_entries_and_stats(self) -> None:
        cache = BytecodeCache(max_entries=2)
        cache.put(_addr(1), "0x6001")
        cache.put(_addr(2), "0x6002")
        cache.put(_addr(3), "0x6003")
        cache.get(_addr(2))
        cache.clear()
        self.assertEqual(
            cache.stats(),
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

    def test_multithreaded_concurrent_access(self) -> None:
        cache = BytecodeCache(max_entries=64, latest_ttl_seconds=1.0)
        errors: list[BaseException] = []
        barrier = threading.Barrier(8)

        def worker(tid: int) -> None:
            try:
                barrier.wait(timeout=5.0)
                for i in range(250):
                    key = _addr((tid * 37 + i) % 128)
                    op = (tid + i) % 5
                    if op in (0, 1):
                        cache.put(key, f"0x{i + 1:04x}")
                    elif op == 2:
                        cache.get(key)
                    elif op == 3:
                        cache.contains(key)
                    else:
                        cache.delete(key)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            self.assertFalse(t.is_alive())
        self.assertEqual(errors, [])
        self.assertLessEqual(int(cache.stats()["size"]), 64)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
