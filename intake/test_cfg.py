from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (
    REASON_DYNAMIC,
    REASON_INVALID_DEST,
    REASON_TRUNCATED,
    build_cfg,
    validate_cfg,
)
from disasm import disassemble


class CfgTests(unittest.TestCase):
    def test_static_jump_resolved(self) -> None:
        ins = disassemble("60055600005b00")
        cfg = build_cfg(ins)
        self.assertEqual(validate_cfg(ins, cfg), [])
        jumps = [e for e in cfg["edges"] if e["type"] == "jump"]
        self.assertEqual(len(jumps), 1)
        self.assertEqual(jumps[0]["target_offset"], 5)
        self.assertIsNone(jumps[0]["reason"])
        self.assertEqual(cfg["stats"]["resolved_jumps"], 1)

    def test_jumpi_true_and_false(self) -> None:
        ins = disassemble("6001600657005b00")
        cfg = build_cfg(ins)
        self.assertEqual(validate_cfg(ins, cfg), [])
        true_edges = [e for e in cfg["edges"] if e["type"] == "jumpi_true"]
        false_edges = [e for e in cfg["edges"] if e["type"] == "jumpi_false"]
        self.assertEqual(len(true_edges), 1)
        self.assertEqual(true_edges[0]["target_offset"], 6)
        self.assertEqual(len(false_edges), 1)

    def test_terminal_no_edges(self) -> None:
        ins = disassemble("00")
        cfg = build_cfg(ins)
        self.assertEqual(cfg["edges"], [])
        self.assertEqual(validate_cfg(ins, cfg), [])

    def test_dynamic_unresolved(self) -> None:
        ins = disassemble("355600")
        cfg = build_cfg(ins)
        unresolved = [e for e in cfg["edges"] if e["type"] == "unresolved_jump"]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], REASON_DYNAMIC)
        self.assertEqual(cfg["stats"]["unresolved_dynamic"], 1)
        self.assertEqual(cfg["stats"]["resolved_jumps"], 0)
        self.assertFalse(any(e["type"] == "jump" for e in cfg["edges"]))

    def test_invalid_dest_unresolved(self) -> None:
        ins = disassemble("60015600")
        cfg = build_cfg(ins)
        unresolved = [e for e in cfg["edges"] if e["type"] == "unresolved_jump"]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], REASON_INVALID_DEST)
        self.assertEqual(unresolved[0]["target_offset"], 1)
        self.assertEqual(cfg["stats"]["unresolved_invalid_dest"], 1)

    def test_truncated_push_before_jump(self) -> None:
        ins = [
            {
                "index": 0,
                "offset": 0,
                "opcode": "PUSH2",
                "opcode_value": 0x61,
                "immediate": "ff",
                "size": 2,
                "incomplete": True,
            },
            {
                "index": 1,
                "offset": 2,
                "opcode": "JUMP",
                "opcode_value": 0x56,
                "immediate": "",
                "size": 1,
                "incomplete": False,
            },
        ]
        cfg = build_cfg(ins)
        unresolved = [e for e in cfg["edges"] if e["type"] == "unresolved_jump"]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], REASON_TRUNCATED)
        self.assertEqual(cfg["stats"]["unresolved_truncated"], 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
