from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


CONFIDENCE_HIGH = "high"
CONFIDENCE_LOW = "low"

ROLE_PROXY = "proxy"
ROLE_RUNTIME = "runtime"

WINDOW = 8


@dataclass(frozen=True)
class FunctionSelector:
    selector: str
    offset: int
    confidence: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SelectorExtraction:
    selectors: list[FunctionSelector]
    bytecode_role: str
    implementation_selectors_available: bool
    notes: list[str] = field(default_factory=list)


def _norm_selector(immediate: str) -> Optional[str]:
    text = (immediate or "").strip().lower()
    if len(text) != 8:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return "0x" + text


def _window_ops(instructions: list[dict], start: int, end: int) -> set[str]:
    ops: set[str] = set()
    lo = max(0, start)
    hi = min(len(instructions), end)
    for i in range(lo, hi):
        ops.add(instructions[i]["opcode"])
    return ops


def _score_push4(instructions: list[dict], index: int) -> tuple[Optional[str], list[str]]:
    ins = instructions[index]
    if ins["opcode"] != "PUSH4" or ins.get("incomplete"):
        return None, []
    selector = _norm_selector(ins.get("immediate") or "")
    if selector is None:
        return None, []

    before = _window_ops(instructions, index - WINDOW, index)
    after = _window_ops(instructions, index + 1, index + 1 + WINDOW)
    nearby = before | after
    evidence: list[str] = ["push4"]

    has_eq = "EQ" in nearby
    has_jumpi = "JUMPI" in nearby
    has_calldata = "CALLDATALOAD" in nearby or "CALLDATASIZE" in nearby

    if has_eq:
        evidence.append("eq")
    if has_jumpi:
        evidence.append("jumpi")
    if has_calldata:
        evidence.append("calldata")

    if has_eq and has_jumpi:
        return CONFIDENCE_HIGH, evidence
    if has_eq and has_calldata:
        return CONFIDENCE_HIGH, evidence
    if has_eq:
        return CONFIDENCE_LOW, evidence
    return None, evidence


def extract_selectors(
    instructions: list[dict],
    *,
    proxy: Any = None,
) -> SelectorExtraction:
    is_proxy = bool(getattr(proxy, "is_proxy", False)) if proxy is not None else False
    role = ROLE_PROXY if is_proxy else ROLE_RUNTIME
    notes: list[str] = []
    if is_proxy:
        notes.append("selectors_from_proxy_bytecode_only")
        notes.append("implementation_selectors_require_implementation_bytecode")

    by_sel: dict[str, FunctionSelector] = {}
    for i, ins in enumerate(instructions):
        if ins["opcode"] != "PUSH4":
            continue
        confidence, evidence = _score_push4(instructions, i)
        if confidence is None:
            continue
        selector = _norm_selector(ins.get("immediate") or "")
        if selector is None:
            continue
        entry = FunctionSelector(
            selector=selector,
            offset=ins["offset"],
            confidence=confidence,
            evidence=evidence,
        )
        prev = by_sel.get(selector)
        if prev is None:
            by_sel[selector] = entry
        elif confidence == CONFIDENCE_HIGH and prev.confidence != CONFIDENCE_HIGH:
            by_sel[selector] = entry
        elif confidence == prev.confidence and ins["offset"] < prev.offset:
            by_sel[selector] = entry

    ordered = sorted(by_sel.values(), key=lambda s: s.offset)
    return SelectorExtraction(
        selectors=ordered,
        bytecode_role=role,
        implementation_selectors_available=False,
        notes=notes,
    )


def extract_selectors_from_bytecode(
    bytecode: str,
    instructions: Optional[list[dict]] = None,
    *,
    proxy: Any = None,
) -> SelectorExtraction:
    if instructions is None:
        from disasm import disassemble

        try:
            instructions = disassemble(bytecode)
        except ValueError:
            return SelectorExtraction(
                selectors=[],
                bytecode_role=ROLE_PROXY if getattr(proxy, "is_proxy", False) else ROLE_RUNTIME,
                implementation_selectors_available=False,
                notes=["disassembly_failed"],
            )
    return extract_selectors(instructions, proxy=proxy)
