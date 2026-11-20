from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


CONFIDENCE_CONFIRMED = "confirmed"
CONFIDENCE_HIGH = "high"
CONFIDENCE_LOW = "low"
CONFIDENCE_NONE = "none"

KIND_EIP1167 = "eip1167"
KIND_EIP1967 = "eip1967"
KIND_EIP1822 = "eip1822"

EIP1167_PREFIX = "363d3d373d3d3d363d73"
EIP1167_SUFFIX = "5af43d82803e903d91602b57fd5bf3"

SLOT_EIP1967_IMPLEMENTATION = (
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
SLOT_EIP1967_BEACON = (
    "a3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
)
SLOT_EIP1967_ADMIN = (
    "b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
)
SLOT_EIP1822_PROXIABLE = (
    "c5f16f0fcc9df782989fa92170170a7cfcb56ccc7609707ef325512b785cea04"
)

DELEGATECALL_BYTE = "f4"


@dataclass(frozen=True)
class ProxyDetection:
    is_proxy: bool
    kind: Optional[str]
    confidence: str
    evidence: list[str] = field(default_factory=list)
    implementation_address: Optional[str] = None
    implementation_source: Optional[str] = None
    needs_storage_read: bool = False
    storage_slots: list[str] = field(default_factory=list)


def _body(bytecode: str) -> Optional[str]:
    if not isinstance(bytecode, str):
        return None
    text = bytecode.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    if text == "" or len(text) % 2 != 0:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _norm_addr20(hex40: str) -> Optional[str]:
    if len(hex40) != 40:
        return None
    try:
        int(hex40, 16)
    except ValueError:
        return None
    return "0x" + hex40.lower()


def _match_eip1167(body: str) -> Optional[str]:
    prefix = EIP1167_PREFIX
    suffix = EIP1167_SUFFIX
    need = len(prefix) + 40 + len(suffix)
    if len(body) < need:
        return None
    idx = 0
    while True:
        start = body.find(prefix, idx)
        if start < 0:
            return None
        addr_at = start + len(prefix)
        end = addr_at + 40
        if end + len(suffix) > len(body):
            return None
        if body[end : end + len(suffix)] != suffix:
            idx = start + 2
            continue
        addr = _norm_addr20(body[addr_at:end])
        if addr is None:
            idx = start + 2
            continue
        return addr


def _find_slots(body: str) -> tuple[list[str], list[str]]:
    evidence: list[str] = []
    slots: list[str] = []
    checks = (
        (SLOT_EIP1967_IMPLEMENTATION, "slot_eip1967_impl"),
        (SLOT_EIP1967_BEACON, "slot_eip1967_beacon"),
        (SLOT_EIP1967_ADMIN, "slot_eip1967_admin"),
        (SLOT_EIP1822_PROXIABLE, "slot_eip1822_proxiable"),
    )
    for slot, tag in checks:
        if slot in body:
            evidence.append(tag)
            slots.append("0x" + slot)
    return evidence, slots


def none_detection() -> ProxyDetection:
    return ProxyDetection(
        is_proxy=False,
        kind=None,
        confidence=CONFIDENCE_NONE,
        evidence=[],
    )


def detect_proxy(bytecode: str) -> ProxyDetection:
    body = _body(bytecode)
    if body is None or body == "":
        return none_detection()

    impl = _match_eip1167(body)
    if impl is not None:
        return ProxyDetection(
            is_proxy=True,
            kind=KIND_EIP1167,
            confidence=CONFIDENCE_CONFIRMED,
            evidence=["eip1167_template"],
            implementation_address=impl,
            implementation_source="bytecode",
            needs_storage_read=False,
            storage_slots=[],
        )

    slot_evidence, slots = _find_slots(body)
    has_1967 = any(tag.startswith("slot_eip1967_") for tag in slot_evidence)
    has_1822 = "slot_eip1822_proxiable" in slot_evidence
    has_delegate = DELEGATECALL_BYTE in body

    if has_1967 or has_1822:
        kind = KIND_EIP1967 if has_1967 else KIND_EIP1822
        evidence = list(slot_evidence)
        if has_delegate:
            evidence.append("delegatecall")
        return ProxyDetection(
            is_proxy=True,
            kind=kind,
            confidence=CONFIDENCE_HIGH,
            evidence=evidence,
            implementation_address=None,
            implementation_source=None,
            needs_storage_read=True,
            storage_slots=slots,
        )

    if has_delegate:
        return ProxyDetection(
            is_proxy=False,
            kind=None,
            confidence=CONFIDENCE_LOW,
            evidence=["delegatecall"],
            needs_storage_read=False,
        )

    return none_detection()
