from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import disassemble
from proxy_detection import detect_proxy
from selector_extraction import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    ROLE_PROXY,
    ROLE_RUNTIME,
    extract_selectors,
)


def _dispatcher_hex() -> str:
    # CALLDATALOAD; PUSH4 deadbeef; EQ; PUSH1 dest; JUMPI; STOP; JUMPDEST; STOP
    return (
        "35"
        "63deadbeef"
        "14"
        "600b"
        "57"
        "00"
        "5b"
        "00"
    )


class SelectorExtractionTests(unittest.TestCase):
    def test_dispatcher_push4_is_high(self) -> None:
        ins = disassemble(_dispatcher_hex())
        result = extract_selectors(ins)
        self.assertEqual(result.bytecode_role, ROLE_RUNTIME)
        self.assertFalse(result.implementation_selectors_available)
        self.assertEqual(len(result.selectors), 1)
        sel = result.selectors[0]
        self.assertEqual(sel.selector, "0xdeadbeef")
        self.assertEqual(sel.confidence, CONFIDENCE_HIGH)
        self.assertIn("push4", sel.evidence)
        self.assertIn("eq", sel.evidence)
        self.assertIn("jumpi", sel.evidence)

    def test_bare_push4_not_emitted(self) -> None:
        ins = disassemble("63cafebabe00")
        result = extract_selectors(ins)
        self.assertEqual(result.selectors, [])

    def test_push4_eq_without_jumpi_is_low(self) -> None:
        ins = disassemble("63aabbccdd1400")
        result = extract_selectors(ins)
        self.assertEqual(len(result.selectors), 1)
        self.assertEqual(result.selectors[0].confidence, CONFIDENCE_LOW)

    def test_proxy_role_does_not_claim_implementation_selectors(self) -> None:
        impl = "bebebebebebebebebebebebebebebebebebebebe"
        eip1167 = (
            "0x363d3d373d3d3d363d73"
            + impl
            + "5af43d82803e903d91602b57fd5bf3"
        )
        proxy = detect_proxy(eip1167)
        ins = disassemble(eip1167)
        result = extract_selectors(ins, proxy=proxy)
        self.assertEqual(result.bytecode_role, ROLE_PROXY)
        self.assertFalse(result.implementation_selectors_available)
        self.assertIn("implementation_selectors_require_implementation_bytecode", result.notes)
        self.assertTrue(proxy.implementation_address)
        self.assertFalse(any(s.selector.startswith("0xbebe") for s in result.selectors))

    def test_dedup_keeps_high(self) -> None:
        hex_code = (
            "35"
            "63deadbeef"
            "14"
            "6012"
            "57"
            "63deadbeef"
            "00"
            "5b"
            "00"
        )
        ins = disassemble(hex_code)
        result = extract_selectors(ins)
        matches = [s for s in result.selectors if s.selector == "0xdeadbeef"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].confidence, CONFIDENCE_HIGH)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
