from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from proxy_detection import (
    CONFIDENCE_CONFIRMED,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_NONE,
    KIND_EIP1167,
    KIND_EIP1822,
    KIND_EIP1967,
    SLOT_EIP1822_PROXIABLE,
    SLOT_EIP1967_BEACON,
    SLOT_EIP1967_IMPLEMENTATION,
    detect_proxy,
    none_detection,
)


IMPL = "bebebebebebebebebebebebebebebebebebebebe"
EIP1167 = (
    "0x363d3d373d3d3d363d73"
    + IMPL
    + "5af43d82803e903d91602b57fd5bf3"
)
ORDINARY = "0x608060405234801561001057600080fd5b50"


class ProxyDetectionTests(unittest.TestCase):
    def test_eip1167_confirmed_extracts_implementation(self) -> None:
        result = detect_proxy(EIP1167)
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.kind, KIND_EIP1167)
        self.assertEqual(result.confidence, CONFIDENCE_CONFIRMED)
        self.assertEqual(result.implementation_address, "0x" + IMPL)
        self.assertEqual(result.implementation_source, "bytecode")
        self.assertFalse(result.needs_storage_read)
        self.assertIn("eip1167_template", result.evidence)

    def test_eip1967_slot_is_high_without_implementation(self) -> None:
        body = "7f" + SLOT_EIP1967_IMPLEMENTATION + "54"
        result = detect_proxy("0x" + body)
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.kind, KIND_EIP1967)
        self.assertEqual(result.confidence, CONFIDENCE_HIGH)
        self.assertIsNone(result.implementation_address)
        self.assertIsNone(result.implementation_source)
        self.assertTrue(result.needs_storage_read)
        self.assertIn("slot_eip1967_impl", result.evidence)
        self.assertEqual(
            result.storage_slots,
            ["0x" + SLOT_EIP1967_IMPLEMENTATION],
        )

    def test_eip1967_beacon_slot(self) -> None:
        result = detect_proxy("0x" + "7f" + SLOT_EIP1967_BEACON + "54")
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.kind, KIND_EIP1967)
        self.assertIn("slot_eip1967_beacon", result.evidence)
        self.assertTrue(result.needs_storage_read)

    def test_eip1822_slot_is_high_without_implementation(self) -> None:
        result = detect_proxy("0x" + "7f" + SLOT_EIP1822_PROXIABLE + "54")
        self.assertTrue(result.is_proxy)
        self.assertEqual(result.kind, KIND_EIP1822)
        self.assertEqual(result.confidence, CONFIDENCE_HIGH)
        self.assertIsNone(result.implementation_address)
        self.assertTrue(result.needs_storage_read)
        self.assertIn("slot_eip1822_proxiable", result.evidence)

    def test_ordinary_contract_is_none(self) -> None:
        result = detect_proxy(ORDINARY)
        self.assertFalse(result.is_proxy)
        self.assertIsNone(result.kind)
        self.assertEqual(result.confidence, CONFIDENCE_NONE)
        self.assertEqual(result.evidence, [])

    def test_empty_and_invalid(self) -> None:
        for bad in ("", "0x", "0xgg", "0xabc", None):
            with self.subTest(bad=bad):
                result = detect_proxy(bad)  # type: ignore[arg-type]
                self.assertEqual(result.confidence, CONFIDENCE_NONE)
                self.assertFalse(result.is_proxy)

    def test_delegatecall_alone_is_low_not_proxy(self) -> None:
        result = detect_proxy("0x60f4")
        self.assertFalse(result.is_proxy)
        self.assertEqual(result.confidence, CONFIDENCE_LOW)
        self.assertIn("delegatecall", result.evidence)

    def test_none_detection_helper(self) -> None:
        result = none_detection()
        self.assertEqual(result.confidence, CONFIDENCE_NONE)
        self.assertFalse(result.is_proxy)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
