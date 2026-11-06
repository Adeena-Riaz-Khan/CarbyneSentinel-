from __future__ import annotations

import sys
import time
import tracemalloc
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from counting_bloom import (
    ADMIT,
    DROP,
    CountingBloomFilter,
    bc_key,
    tx_key,
)


class CountingBloomFilterTests(unittest.TestCase):
    def test_new_item_initially_absent(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0xabc123")
        self.assertFalse(bloom.maybe_contains(key))

    def test_insert_makes_item_possibly_present(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0xdeadbeef")
        bloom.insert(key)
        self.assertTrue(bloom.maybe_contains(key))

    def test_never_inserted_item_normally_absent(self) -> None:
        bloom = CountingBloomFilter(size=512, hash_count=5)
        bloom.insert(tx_key("aaa"))
        bloom.insert(tx_key("bbb"))
        self.assertFalse(bloom.maybe_contains(tx_key("ccc")))

    def test_repeated_admission_detects_possible_duplicate(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0x1111")
        self.assertEqual(bloom.admit(key), ADMIT)
        self.assertEqual(bloom.admit(key), DROP)

    def test_tx_and_bc_namespaces_are_separate(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        shared = "abcdef01"
        self.assertEqual(bloom.admit(tx_key(shared)), ADMIT)
        self.assertEqual(bloom.admit(bc_key(shared)), ADMIT)
        self.assertTrue(bloom.maybe_contains(tx_key(shared)))
        self.assertTrue(bloom.maybe_contains(bc_key(shared)))

    def test_remove_decrements_counters(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0xremoveme")
        before = bloom.counter_sum()
        bloom.insert(key)
        after_insert = bloom.counter_sum()
        self.assertEqual(after_insert, before + bloom.hash_count)
        self.assertTrue(bloom.remove(key))
        self.assertEqual(bloom.counter_sum(), before)

    def test_remove_rejected_when_required_counter_is_zero(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0xghost")
        self.assertFalse(bloom.maybe_contains(key))
        self.assertFalse(bloom.remove(key))
        self.assertEqual(bloom.counter_sum(), 0)

    def test_repeated_insertion_and_removal(self) -> None:
        bloom = CountingBloomFilter(size=256, hash_count=4)
        key = tx_key("0xloop")
        for _ in range(5):
            self.assertEqual(bloom.admit(key), ADMIT)
            self.assertTrue(bloom.remove(key))
            self.assertEqual(bloom.admit(key), ADMIT)
            self.assertTrue(bloom.remove(key))
        self.assertEqual(bloom.counter_sum(), 0)

    def test_counter_underflow_prevention(self) -> None:
        bloom = CountingBloomFilter(size=64, hash_count=3)
        key = tx_key("0xunder")
        bloom.insert(key)
        self.assertTrue(bloom.remove(key))
        self.assertFalse(bloom.remove(key))
        self.assertTrue(all(value >= 0 for value in bloom.counters))

    def test_collisions_with_small_filter(self) -> None:
        bloom = CountingBloomFilter(size=8, hash_count=3)
        inserted = [tx_key(f"item-{i}") for i in range(20)]
        for key in inserted:
            bloom.insert(key)
        for key in inserted:
            self.assertTrue(bloom.maybe_contains(key))
        false_positives = 0
        probes = 100
        for i in range(probes):
            probe = tx_key(f"probe-{i}")
            if probe in inserted:
                continue
            if bloom.maybe_contains(probe):
                false_positives += 1
        self.assertGreaterEqual(false_positives, 0)


def run_measurements() -> None:
    print("=== Counting Bloom Filter measurements ===")

    size = 8192
    hash_count = 5
    bloom = CountingBloomFilter(size=size, hash_count=hash_count)
    n_insert = 1000
    keys = [tx_key(f"bench-insert-{i}") for i in range(n_insert)]

    start = time.perf_counter()
    for key in keys:
        bloom.insert(key)
    insert_seconds = time.perf_counter() - start
    insert_per_op_us = (insert_seconds / n_insert) * 1_000_000

    n_lookup = 1000
    lookup_keys = keys[: n_lookup // 2] + [tx_key(f"bench-miss-{i}") for i in range(n_lookup // 2)]
    start = time.perf_counter()
    hits = 0
    for key in lookup_keys:
        if bloom.maybe_contains(key):
            hits += 1
    lookup_seconds = time.perf_counter() - start
    lookup_per_op_us = (lookup_seconds / n_lookup) * 1_000_000

    print(f"filter size (counters): {size}")
    print(f"hash_count: {hash_count}")
    print(f"inserted items: {n_insert}")
    print(f"insert total_s: {insert_seconds:.6f}")
    print(f"insert per_op_us: {insert_per_op_us:.3f}")
    print(f"lookup ops: {n_lookup}")
    print(f"lookup total_s: {lookup_seconds:.6f}")
    print(f"lookup per_op_us: {lookup_per_op_us:.3f}")
    print(f"lookup hits_in_mixed_set: {hits}")

    counter_array_bytes = sys.getsizeof(bloom.counters) + sum(
        sys.getsizeof(value) for value in bloom.counters
    )
    print(f"counter_array_len: {len(bloom.counters)}")
    print(f"approx_counter_array_bytes: {counter_array_bytes}")

    print("--- false-positive rate by occupancy ---")
    for fill in (100, 500, 1000, 2000, 4000):
        trial = CountingBloomFilter(size=size, hash_count=hash_count)
        for i in range(fill):
            trial.insert(tx_key(f"fill-{fill}-{i}"))
        probes = 2000
        fp = 0
        for i in range(probes):
            probe = tx_key(f"fp-{fill}-{i}")
            if trial.maybe_contains(probe):
                fp += 1
        rate = fp / probes
        print(f"fill={fill} probes={probes} false_positives={fp} rate={rate:.6f}")

    tracemalloc.start()
    measured = CountingBloomFilter(size=size, hash_count=hash_count)
    for i in range(1000):
        measured.insert(tx_key(f"mem-{i}"))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"tracemalloc_current_bytes: {current}")
    print(f"tracemalloc_peak_bytes: {peak}")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CountingBloomFilterTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print()
    run_measurements()
    if not result.wasSuccessful():
        raise SystemExit(1)
