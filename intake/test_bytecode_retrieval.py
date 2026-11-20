from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bytecode_cache import BytecodeCache
from bytecode_retrieval import (
    STATUS_AWAITING_CREATION,
    STATUS_INVALID_ADDRESS,
    STATUS_INVALID_RESPONSE,
    STATUS_NO_CODE,
    STATUS_RETRIEVED,
    STATUS_RPC_FAILURE,
    awaiting_creation_result,
    block_id_for_record,
    retrieve_contract_bytecode,
    validate_bytecode_hex,
)
from tx_lifecycle import JsonRpcError


ADDR = "0x" + ("1" * 40)
CODE = "0x60806040"
CODE_B = "0xdeadbeef"
CODE_AFTER = "0xcafebabe"
BLOCK_HASH = "0x" + ("ab" * 32)


class FakeClock:
    def __init__(self, initial: float = 100.0) -> None:
        self.now = initial

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRpc:
    def __init__(self) -> None:
        self.codes: dict[str, Any] = {}
        self.code_by_block: dict[tuple[str, str], Any] = {}
        self.errors: dict[str, Exception] = {}
        self.calls: list[tuple[str, list[Any]]] = []
        self.fail_times: dict[str, int] = {}
        self._fail_counts: dict[str, int] = {}

    def __call__(self, method: str, params: list[Any]) -> Any:
        self.calls.append((method, params))
        key = method + ":" + (params[0] if params else "")
        if key in self.fail_times:
            seen = self._fail_counts.get(key, 0)
            self._fail_counts[key] = seen + 1
            if seen < self.fail_times[key]:
                raise JsonRpcError("transient")
        if key in self.errors:
            raise self.errors[key]
        if method == "eth_getCode":
            addr = params[0]
            block = params[1] if len(params) > 1 else "latest"
            if (addr, block) in self.code_by_block:
                return self.code_by_block[(addr, block)]
            return self.codes.get(addr, "0x")
        raise JsonRpcError(f"unexpected {method}")


class ValidationTests(unittest.TestCase):
    def test_successful_hex(self) -> None:
        status, code, size, err = validate_bytecode_hex(CODE)
        self.assertEqual(status, STATUS_RETRIEVED)
        self.assertEqual(code, CODE)
        self.assertEqual(size, 4)
        self.assertIsNone(err)

    def test_empty_code(self) -> None:
        status, code, size, err = validate_bytecode_hex("0x")
        self.assertEqual(status, STATUS_NO_CODE)
        self.assertEqual(code, "0x")
        self.assertEqual(size, 0)

    def test_malformed_non_hex(self) -> None:
        status, code, size, err = validate_bytecode_hex("0xzzzz")
        self.assertEqual(status, STATUS_INVALID_RESPONSE)
        self.assertIsNone(code)

    def test_odd_length(self) -> None:
        status, code, size, err = validate_bytecode_hex("0xabc")
        self.assertEqual(status, STATUS_INVALID_RESPONSE)
        self.assertIn("odd", err or "")

    def test_block_id_helpers(self) -> None:
        self.assertEqual(block_id_for_record(None), "latest")
        self.assertEqual(block_id_for_record(16), "0x10")
        self.assertEqual(block_id_for_record(16, BLOCK_HASH), BLOCK_HASH)
        self.assertEqual(block_id_for_record(None, BLOCK_HASH), BLOCK_HASH)
        self.assertEqual(awaiting_creation_result(now=1.0).status, STATUS_AWAITING_CREATION)


class RetrieveTests(unittest.TestCase):
    def test_successful_get_code(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = CODE
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0)
        self.assertEqual(result.status, STATUS_RETRIEVED)
        self.assertEqual(result.bytecode, CODE)
        self.assertEqual(result.bytecode_size_bytes, 4)
        self.assertEqual(result.contract_address, ADDR)
        self.assertEqual(result.block_id, "latest")
        self.assertEqual(rpc.calls[0], ("eth_getCode", [ADDR, "latest"]))

    def test_correct_block_id_for_confirmed(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = CODE
        result = retrieve_contract_bytecode(rpc, ADDR, "0x2a", now=10.0)
        self.assertEqual(result.block_id, "0x2a")
        self.assertEqual(rpc.calls[0][1][1], "0x2a")

    def test_empty_code_eoa(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = "0x"
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0)
        self.assertEqual(result.status, STATUS_NO_CODE)
        self.assertEqual(result.bytecode_size_bytes, 0)

    def test_invalid_address(self) -> None:
        rpc = FakeRpc()
        result = retrieve_contract_bytecode(rpc, "0x1234", "latest", now=10.0)
        self.assertEqual(result.status, STATUS_INVALID_ADDRESS)
        self.assertEqual(rpc.calls, [])

    def test_malformed_response(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = "0xgg"
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0)
        self.assertEqual(result.status, STATUS_INVALID_RESPONSE)
        self.assertIsNone(result.bytecode)

    def test_odd_length_response(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = "0x123"
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0)
        self.assertEqual(result.status, STATUS_INVALID_RESPONSE)

    def test_rpc_error(self) -> None:
        rpc = FakeRpc()
        rpc.errors["eth_getCode:" + ADDR] = JsonRpcError("provider down")
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0, attempts=1)
        self.assertEqual(result.status, STATUS_RPC_FAILURE)
        self.assertIn("provider down", result.error or "")

    def test_exactly_one_retry(self) -> None:
        rpc = FakeRpc()
        rpc.fail_times["eth_getCode:" + ADDR] = 1
        rpc.codes[ADDR] = CODE
        result = retrieve_contract_bytecode(rpc, ADDR, "latest", now=10.0, attempts=2)
        self.assertEqual(result.status, STATUS_RETRIEVED)
        self.assertEqual(len([c for c in rpc.calls if c[0] == "eth_getCode"]), 2)


class CacheIntegrationTests(unittest.TestCase):
    def test_cache_miss_then_hit(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = CODE
        cache = BytecodeCache(max_entries=8)
        first = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=10.0, cache=cache, network="sepolia"
        )
        self.assertEqual(first.status, STATUS_RETRIEVED)
        self.assertEqual(len(rpc.calls), 1)
        second = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=11.0, cache=cache, network="sepolia"
        )
        self.assertEqual(second.status, STATUS_RETRIEVED)
        self.assertEqual(second.bytecode, CODE)
        self.assertEqual(len(rpc.calls), 1)
        self.assertEqual(cache.stats()["hits"], 1)
        self.assertEqual(cache.stats()["misses"], 1)

    def test_expired_latest_entry_triggers_fresh_rpc(self) -> None:
        clock = FakeClock(100.0)
        rpc = FakeRpc()
        rpc.codes[ADDR] = CODE
        cache = BytecodeCache(max_entries=8, latest_ttl_seconds=5.0, clock=clock)
        first = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia"
        )
        self.assertEqual(first.status, STATUS_RETRIEVED)
        self.assertEqual(first.bytecode, CODE)
        self.assertEqual(len(rpc.calls), 1)
        hit = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.5, cache=cache, network="sepolia"
        )
        self.assertEqual(hit.bytecode, CODE)
        self.assertEqual(len(rpc.calls), 1)
        clock.advance(5.0)
        rpc.codes[ADDR] = CODE_AFTER
        after = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=2.0, cache=cache, network="sepolia"
        )
        self.assertEqual(after.status, STATUS_RETRIEVED)
        self.assertEqual(after.bytecode, CODE_AFTER)
        self.assertEqual(len(rpc.calls), 2)
        self.assertEqual(cache.stats()["expirations"], 1)
        self.assertEqual(cache.stats()["misses"], 2)

    def test_confirmed_entry_survives_latest_ttl(self) -> None:
        clock = FakeClock(100.0)
        rpc = FakeRpc()
        rpc.code_by_block[(ADDR, "latest")] = CODE
        rpc.code_by_block[(ADDR, BLOCK_HASH)] = CODE_B
        cache = BytecodeCache(max_entries=8, latest_ttl_seconds=5.0, clock=clock)
        retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia"
        )
        retrieve_contract_bytecode(
            rpc, ADDR, BLOCK_HASH, now=1.0, cache=cache, network="sepolia"
        )
        clock.advance(5.0)
        latest = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=2.0, cache=cache, network="sepolia"
        )
        confirmed = retrieve_contract_bytecode(
            rpc, ADDR, BLOCK_HASH, now=2.0, cache=cache, network="sepolia"
        )
        self.assertEqual(latest.bytecode, CODE)
        self.assertEqual(confirmed.bytecode, CODE_B)
        self.assertEqual(len(rpc.calls), 3)

    def test_block_specific_entries_do_not_collide(self) -> None:
        rpc = FakeRpc()
        rpc.code_by_block[(ADDR, "latest")] = CODE
        rpc.code_by_block[(ADDR, "0x10")] = CODE_B
        cache = BytecodeCache(max_entries=8)
        latest = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia"
        )
        confirmed = retrieve_contract_bytecode(
            rpc, ADDR, "0x10", now=2.0, cache=cache, network="sepolia"
        )
        self.assertEqual(latest.bytecode, CODE)
        self.assertEqual(confirmed.bytecode, CODE_B)
        self.assertEqual(len(rpc.calls), 2)
        again_latest = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=3.0, cache=cache, network="sepolia"
        )
        again_confirmed = retrieve_contract_bytecode(
            rpc, ADDR, "0x10", now=4.0, cache=cache, network="sepolia"
        )
        self.assertEqual(again_latest.bytecode, CODE)
        self.assertEqual(again_confirmed.bytecode, CODE_B)
        self.assertEqual(len(rpc.calls), 2)

    def test_no_code_is_cached(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = "0x"
        cache = BytecodeCache(max_entries=8)
        first = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia"
        )
        self.assertEqual(first.status, STATUS_NO_CODE)
        second = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=2.0, cache=cache, network="sepolia"
        )
        self.assertEqual(second.status, STATUS_NO_CODE)
        self.assertEqual(len(rpc.calls), 1)

    def test_rpc_failure_not_cached(self) -> None:
        rpc = FakeRpc()
        rpc.errors["eth_getCode:" + ADDR] = JsonRpcError("provider down")
        cache = BytecodeCache(max_entries=8)
        failed = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia", attempts=1
        )
        self.assertEqual(failed.status, STATUS_RPC_FAILURE)
        self.assertEqual(cache.stats()["size"], 0)
        del rpc.errors["eth_getCode:" + ADDR]
        rpc.codes[ADDR] = CODE
        ok = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=2.0, cache=cache, network="sepolia", attempts=1
        )
        self.assertEqual(ok.status, STATUS_RETRIEVED)
        self.assertEqual(len([c for c in rpc.calls if c[0] == "eth_getCode"]), 2)

    def test_invalid_response_not_cached(self) -> None:
        rpc = FakeRpc()
        rpc.codes[ADDR] = "0xgg"
        cache = BytecodeCache(max_entries=8)
        bad = retrieve_contract_bytecode(
            rpc, ADDR, "latest", now=1.0, cache=cache, network="sepolia"
        )
        self.assertEqual(bad.status, STATUS_INVALID_RESPONSE)
        self.assertEqual(cache.stats()["size"], 0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
