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
    STATUS_NO_CODE,
    STATUS_OK,
    BytecodeCache,
    CacheEntry,
    bytecode_sha256,
    normalize_address,
    normalize_block_tag,
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


class FakeEthGetCode:
    """Mocked eth_getCode RPC fetcher recording calls and arguments."""

    def __init__(self, responses: dict[tuple[str, str], object] | None = None) -> None:
        self.responses: dict[tuple[str, str], object] = dict(responses or {})
        self.default_response: object = "0x60806040"
        self.calls: list[tuple[str, str]] = []

    def __call__(self, address: str, block_tag: str) -> str:
        self.calls.append((address, block_tag))
        outcome = self.responses.get((address, block_tag), self.default_response)
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome(address, block_tag)
        return outcome  # type: ignore[return-value]


def _addr(index: int) -> str:
    return f"0x{index:040x}"


class BytecodeCacheTests(unittest.TestCase):
    # --- C. Strict validation ---

    def test_normalize_address_valid_variants(self) -> None:
        expected = "0x" + "a" * 40
        self.assertEqual(normalize_address("0x" + "A" * 40), expected)
        self.assertEqual(normalize_address("0X" + "aA" * 20), expected)
        self.assertEqual(normalize_address("  0X" + "A" * 40 + "\n"), expected)

    def test_normalize_address_invalid_raises(self) -> None:
        bad_inputs: list[object] = [
            None,
            123,
            "",
            "   ",
            "0x",
            "a" * 40,  # missing 0x prefix
            "A" * 40,  # missing 0x prefix
            "0x" + "a" * 39,
            "0x" + "a" * 41,
            "0x" + "g" * 40,
            "0x" + "a" * 20 + " " + "a" * 19,
            "0x" + "a" * 20 + "\n" + "a" * 19,
            "0x" + "\u0660" * 40,  # Unicode Arabic-Indic digits
        ]
        for bad in bad_inputs:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_address(bad)  # type: ignore[arg-type]

    def test_normalize_bytecode_valid_variants(self) -> None:
        self.assertEqual(normalize_bytecode("0x"), "0x")
        self.assertEqual(normalize_bytecode(" 0X \t\n"), "0x")
        self.assertEqual(normalize_bytecode("0x6080604052"), "0x6080604052")
        self.assertEqual(normalize_bytecode("  0X6080604052\n"), "0x6080604052")
        self.assertEqual(normalize_bytecode("0xDeAdBeEf"), "0xdeadbeef")

    def test_normalize_bytecode_invalid_raises(self) -> None:
        bad_inputs: list[object] = [
            None,
            42,
            {"error": "rpc"},
            "",
            "   ",
            "6080604052",  # missing 0x prefix
            "0x600",       # odd length
            "0x60zz",      # non-hex
            "0x60 00",     # internal space
            "0x60\n00",    # internal newline
            "0x\u0660\u0660",  # Unicode digits
        ]
        for bad in bad_inputs:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_bytecode(bad)  # type: ignore[arg-type]

    def test_normalize_block_tag_valid_variants(self) -> None:
        self.assertEqual(normalize_block_tag(), "latest")
        for tag in ("latest", "pending", "earliest", "safe", "finalized"):
            self.assertEqual(normalize_block_tag(tag), tag)
            self.assertEqual(normalize_block_tag(f"  {tag.upper()}\n"), tag)

        self.assertEqual(normalize_block_tag(0), "0x0")
        self.assertEqual(normalize_block_tag("0x0"), "0x0")
        self.assertEqual(normalize_block_tag("0X0000"), "0x0")
        self.assertEqual(normalize_block_tag(10), "0xa")
        self.assertEqual(normalize_block_tag("0xa"), "0xa")
        self.assertEqual(normalize_block_tag("0xA"), "0xa")
        self.assertEqual(normalize_block_tag("0x0A"), "0xa")
        self.assertEqual(normalize_block_tag("  0X000a \n"), "0xa")
        self.assertEqual(normalize_block_tag(255), "0xff")

    def test_normalize_block_tag_invalid_raises(self) -> None:
        bad_tags: list[object] = [
            "",
            "   ",
            None,
            -1,
            -100,
            True,
            False,
            1.5,
            "bogus",
            "10",      # bare decimal string without 0x
            "0x",      # empty hex quantity
            "0xzz",    # non-hex
            "0x1_0",   # Python int underscore trick
            "0x+1",    # sign trick
            "0x1 0",   # internal space
            "0x\u0661",  # Unicode digit
            ["latest"],
        ]
        for bad in bad_tags:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_block_tag(bad)  # type: ignore[arg-type]

    def test_bytecode_sha256_consistency(self) -> None:
        empty_digest = hashlib.sha256(b"").hexdigest()
        self.assertEqual(bytecode_sha256("0x"), empty_digest)
        self.assertEqual(bytecode_sha256(" 0X "), empty_digest)

        sample_digest = hashlib.sha256(b"\x60\x00\xfe").hexdigest()
        self.assertEqual(bytecode_sha256("0x6000fe"), sample_digest)
        self.assertEqual(bytecode_sha256("  0X6000FE "), sample_digest)

        for bad in ("", "6000FE", "0x60 00", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    bytecode_sha256(bad)  # type: ignore[arg-type]

    def test_cache_entry_is_frozen_and_has_slots(self) -> None:
        cache = BytecodeCache(max_entries=4)
        entry = cache.put(_addr(1), "0x6000", block_tag="pending")
        self.assertIsInstance(entry, CacheEntry)
        self.assertEqual(entry.block_tag, "pending")
        self.assertEqual(entry.status, STATUS_OK)
        self.assertFalse(hasattr(entry, "__dict__"))
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

    # --- A. Migrated core behavior (LRU, TTL, EOA, stats, clear, concurrency) ---

    def test_put_get_and_eoa_negative_caching(self) -> None:
        cache = BytecodeCache(max_entries=8)
        addr_upper = "  0X" + _addr(1)[2:].upper() + " "
        eoa = cache.put(addr_upper, "0x")
        self.assertEqual(eoa.address, _addr(1))
        self.assertEqual(eoa.bytecode, "0x")
        self.assertEqual(eoa.code_hash, hashlib.sha256(b"").hexdigest())
        self.assertTrue(eoa.is_empty)
        self.assertEqual(eoa.status, STATUS_NO_CODE)
        self.assertEqual(eoa.block_tag, "latest")

        contract = cache.put(_addr(2), "0x60806040")
        self.assertEqual(contract.bytecode, "0x60806040")
        self.assertFalse(contract.is_empty)
        self.assertEqual(contract.status, STATUS_OK)
        self.assertEqual(contract.block_tag, "latest")

        self.assertEqual(cache.get(_addr(1)), eoa)
        self.assertEqual(cache.get(_addr(2).upper()), contract)
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

        updated = cache.put(_addr(1), "0x6011")
        self.assertEqual(updated.bytecode, "0x6011")
        self.assertEqual(cache.stats()["evictions"], 0)
        self.assertEqual(cache.stats()["size"], 2)

        cache.put(_addr(3), "0x6003")
        self.assertEqual(cache.stats()["evictions"], 1)
        self.assertFalse(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(3)))

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
        self.assertEqual(cache.stats()["size"], 1)
        self.assertEqual(cache.stats()["expirations"], 0)

        self.assertIsNone(cache.get(_addr(1)))
        s = cache.stats()
        self.assertEqual(s["hits"], 1)
        self.assertEqual(s["misses"], 1)
        self.assertEqual(s["expirations"], 1)
        self.assertEqual(s["size"], 0)

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

        self.assertTrue(cache.contains(_addr(1)))
        self.assertFalse(cache.contains(_addr(99)))
        s_before = cache.stats()
        self.assertEqual(s_before["hits"], 0)
        self.assertEqual(s_before["misses"], 0)

        cache.put(_addr(3), "0x6003")
        self.assertFalse(cache.contains(_addr(1)))
        self.assertTrue(cache.contains(_addr(2)))
        self.assertTrue(cache.contains(_addr(3)))

    def test_invalid_inputs_raise_without_mutating_stats(self) -> None:
        cache = BytecodeCache(max_entries=4)
        cache.put(_addr(1), "0x6001")
        for fn in (cache.get, cache.contains, cache.delete):
            with self.subTest(fn=fn.__name__, kind="bad_addr"):
                with self.assertRaises(ValueError):
                    fn("not-an-address")
            with self.subTest(fn=fn.__name__, kind="bad_block"):
                with self.assertRaises(ValueError):
                    fn(_addr(1), block_tag="bogus")
        with self.assertRaises(ValueError):
            cache.put(_addr(2), "")
        with self.assertRaises(ValueError):
            cache.put(_addr(2), "0x6000", block_tag=-1)

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
        tags: tuple[str | int, ...] = ("latest", "pending", 10, "0xff")

        def worker(tid: int) -> None:
            try:
                stop_barrier.wait(timeout=5.0)
                for i in range(250):
                    key = _addr((tid * 37 + i) % 64)
                    tag = tags[(tid + i) % len(tags)]
                    op = (tid + i) % 5
                    if op in (0, 1):
                        cache.put(key, f"0x{i + 1:04x}", block_tag=tag)
                    elif op == 2:
                        cache.get(key, block_tag=tag)
                    elif op == 3:
                        cache.contains(key, block_tag=tag)
                    elif op == 4:
                        cache.delete(key, block_tag=tag)
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

    # --- B. Block-aware isolation ---

    def test_block_aware_isolation_and_canonical_equivalents(self) -> None:
        cache = BytecodeCache(max_entries=8)
        addr = _addr(7)

        e_pending = cache.put(addr, "0x6001", block_tag="pending")
        e_latest = cache.put(addr, "0x6002", block_tag="latest")
        e_block10 = cache.put(addr, "0x600a", block_tag=10)

        self.assertEqual(cache.stats()["size"], 3)
        self.assertEqual(cache.get(addr, block_tag="pending"), e_pending)
        self.assertEqual(cache.get(addr), e_latest)  # default block_tag == "latest"
        self.assertEqual(cache.get(addr, block_tag="latest"), e_latest)

        # 10, "0xa", "0xA", "0x00a" all resolve to the exact same key.
        for alias in (10, "0xa", "0xA", "0x00a", " 0X000A "):
            with self.subTest(alias=alias):
                self.assertEqual(cache.get(addr, block_tag=alias), e_block10)

        # Deleting one block tag leaves the others intact.
        self.assertTrue(cache.delete(addr, block_tag="pending"))
        self.assertFalse(cache.contains(addr, block_tag="pending"))
        self.assertTrue(cache.contains(addr, block_tag="latest"))
        self.assertTrue(cache.contains(addr, block_tag="0xa"))

    def test_lru_eviction_counts_address_block_pairs_separately(self) -> None:
        cache = BytecodeCache(max_entries=2)
        addr = _addr(1)

        cache.put(addr, "0x6001", block_tag="pending")
        cache.put(addr, "0x6002", block_tag="latest")
        self.assertEqual(cache.stats()["size"], 2)
        self.assertEqual(cache.stats()["evictions"], 0)

        # Adding a third tag for the same address evicts the LRU (addr, "pending").
        cache.put(addr, "0x6003", block_tag=10)
        self.assertEqual(cache.stats()["evictions"], 1)
        self.assertFalse(cache.contains(addr, block_tag="pending"))
        self.assertTrue(cache.contains(addr, block_tag="latest"))
        self.assertTrue(cache.contains(addr, block_tag="0xa"))

    # --- D. Mocked RPC integration suite (get_or_fetch) ---

    def test_get_or_fetch_miss_then_hit(self) -> None:
        cache = BytecodeCache(max_entries=8)
        rpc = FakeEthGetCode({(_addr(1), "latest"): "0x6080604052"})

        first = cache.get_or_fetch(_addr(1), rpc)
        self.assertEqual(first.bytecode, "0x6080604052")
        self.assertEqual(first.status, STATUS_OK)
        self.assertFalse(first.is_empty)
        self.assertEqual(len(rpc.calls), 1)

        second = cache.get_or_fetch(_addr(1), rpc)
        self.assertEqual(second, first)
        self.assertEqual(len(rpc.calls), 1)
        self.assertEqual(cache.stats()["misses"], 1)
        self.assertEqual(cache.stats()["hits"], 1)

    def test_get_or_fetch_ttl_expiry_refetches(self) -> None:
        clock = FakeClock(initial=50.0)
        cache = BytecodeCache(max_entries=8, ttl_seconds=10.0, clock=clock)
        rpc = FakeEthGetCode({(_addr(1), "latest"): "0x6001"})

        first = cache.get_or_fetch(_addr(1), rpc)
        self.assertEqual(first.bytecode, "0x6001")
        self.assertEqual(len(rpc.calls), 1)

        clock.advance(10.0)
        rpc.responses[(_addr(1), "latest")] = "0x6002"
        refreshed = cache.get_or_fetch(_addr(1), rpc)
        self.assertEqual(refreshed.bytecode, "0x6002")
        self.assertEqual(len(rpc.calls), 2)
        self.assertEqual(cache.stats()["expirations"], 1)

    def test_get_or_fetch_no_code_cached(self) -> None:
        cache = BytecodeCache(max_entries=8)
        rpc = FakeEthGetCode({(_addr(5), "latest"): "0x"})

        entry = cache.get_or_fetch(_addr(5), rpc)
        self.assertTrue(entry.is_empty)
        self.assertEqual(entry.status, STATUS_NO_CODE)
        self.assertEqual(entry.bytecode, "0x")
        self.assertEqual(entry.code_hash, hashlib.sha256(b"").hexdigest())
        self.assertEqual(len(rpc.calls), 1)

        cached = cache.get_or_fetch(_addr(5), rpc)
        self.assertEqual(cached, entry)
        self.assertEqual(len(rpc.calls), 1)

    def test_get_or_fetch_rpc_exceptions_never_cached_and_recover(self) -> None:
        for exc_cls in (TimeoutError, RuntimeError):
            with self.subTest(exc=exc_cls.__name__):
                cache = BytecodeCache(max_entries=8)
                rpc = FakeEthGetCode({(_addr(1), "latest"): exc_cls("rpc down")})

                with self.assertRaises(exc_cls) as ctx:
                    cache.get_or_fetch(_addr(1), rpc)
                self.assertEqual(str(ctx.exception), "rpc down")
                self.assertEqual(cache.stats()["size"], 0)
                self.assertFalse(cache.contains(_addr(1)))

                # Recovery on subsequent call
                rpc.responses[(_addr(1), "latest")] = "0x6000"
                recovered = cache.get_or_fetch(_addr(1), rpc)
                self.assertEqual(recovered.bytecode, "0x6000")
                self.assertEqual(cache.stats()["size"], 1)
                self.assertEqual(len(rpc.calls), 2)

    def test_get_or_fetch_invalid_rpc_responses_never_cached(self) -> None:
        bad_payloads: list[object] = [None, "", "not-hex", "0x123", {"code": "0x00"}, 1234]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                cache = BytecodeCache(max_entries=8)
                rpc = FakeEthGetCode({(_addr(1), "latest"): payload})

                with self.assertRaises(ValueError):
                    cache.get_or_fetch(_addr(1), rpc)
                self.assertEqual(cache.stats()["size"], 0)
                self.assertFalse(cache.contains(_addr(1)))

    def test_get_or_fetch_passes_normalized_args_to_fetcher(self) -> None:
        cache = BytecodeCache(max_entries=8)
        rpc = FakeEthGetCode()
        raw_addr = "  0X" + _addr(3)[2:].upper() + " "

        entry = cache.get_or_fetch(raw_addr, rpc, block_tag=" 0X000A ")
        self.assertEqual(rpc.calls, [(_addr(3), "0xa")])
        self.assertEqual(entry.address, _addr(3))
        self.assertEqual(entry.block_tag, "0xa")

    def test_get_or_fetch_invalid_input_never_calls_rpc(self) -> None:
        cache = BytecodeCache(max_entries=8)
        rpc = FakeEthGetCode()

        with self.assertRaises(ValueError):
            cache.get_or_fetch("bad-address", rpc)
        with self.assertRaises(ValueError):
            cache.get_or_fetch(_addr(1), rpc, block_tag="invalid-tag")
        with self.assertRaises(ValueError):
            cache.get_or_fetch(_addr(1), "not-callable")  # type: ignore[arg-type]
        self.assertEqual(rpc.calls, [])
        self.assertEqual(cache.stats()["misses"], 0)

    def test_get_or_fetch_block_isolation(self) -> None:
        cache = BytecodeCache(max_entries=8)
        addr = _addr(9)
        rpc = FakeEthGetCode(
            {
                (addr, "pending"): "0x60aa",
                (addr, "latest"): "0x60bb",
            }
        )

        e_pending = cache.get_or_fetch(addr, rpc, block_tag="pending")
        e_latest = cache.get_or_fetch(addr, rpc, block_tag="latest")
        self.assertEqual(e_pending.bytecode, "0x60aa")
        self.assertEqual(e_latest.bytecode, "0x60bb")
        self.assertEqual(rpc.calls, [(addr, "pending"), (addr, "latest")])

        # Subsequent calls hit their respective block entries without new RPC calls.
        self.assertEqual(cache.get_or_fetch(addr, rpc, block_tag="pending"), e_pending)
        self.assertEqual(cache.get_or_fetch(addr, rpc, block_tag="latest"), e_latest)
        self.assertEqual(len(rpc.calls), 2)

    def test_get_or_fetch_does_not_hold_lock_during_fetch(self) -> None:
        cache = BytecodeCache(max_entries=8)
        cache.put(_addr(2), "0x6002")
        reentrant_results: list[object] = []
        errors: list[BaseException] = []

        def reentrant_fetcher(address: str, block_tag: str) -> str:
            # Would deadlock immediately if BytecodeCache held self._lock across fetcher().
            reentrant_results.append(cache.contains(_addr(2)))
            reentrant_results.append(cache.get(_addr(2)))
            return "0x6001"

        def run_fetch() -> None:
            try:
                cache.get_or_fetch(_addr(1), reentrant_fetcher)
            except BaseException as exc:  # pragma: no cover - captured for assertion
                errors.append(exc)

        thread = threading.Thread(target=run_fetch)
        thread.start()
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive(), "Deadlock detected: lock was held across fetcher()")
        self.assertEqual(errors, [])
        self.assertEqual(reentrant_results[0], True)
        self.assertIsNotNone(reentrant_results[1])
        self.assertTrue(cache.contains(_addr(1)))


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
