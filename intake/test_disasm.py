from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm import check_offsets, disassemble, parse_hex


class DisasmTests(unittest.TestCase):
    def test_push_add_stop(self) -> None:
        ins = disassemble("0x6001600201")
        self.assertEqual(ins[0]["opcode"], "PUSH1")
        self.assertEqual(ins[0]["immediate"], "01")
        self.assertEqual(ins[0]["offset"], 0)
        self.assertEqual(ins[1]["opcode"], "PUSH1")
        self.assertEqual(ins[1]["immediate"], "02")
        self.assertEqual(ins[2]["opcode"], "ADD")
        self.assertEqual(ins[2]["offset"], 4)

    def test_truncated_push(self) -> None:
        ins = disassemble("0x63aabbcc")
        self.assertEqual(len(ins), 1)
        self.assertEqual(ins[0]["opcode"], "PUSH4")
        self.assertTrue(ins[0]["incomplete"])

    def test_check_offsets_ok(self) -> None:
        raw = "6001600201"
        data = parse_hex(raw)
        ins = disassemble(raw)
        self.assertEqual(check_offsets(ins, len(data)), [])

    def test_invalid_hex(self) -> None:
        with self.assertRaises(ValueError):
            disassemble("0xgg")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
