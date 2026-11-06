"""Phase 2: mine unique seed candidates for grow classes (target ≥80 each).

Sources:
  - DIVE_Labels.csv fine-grained flags joined to dive_vulnerable.jsonl
  - dappscan_vulnerable.jsonl via SWC → class map
  - Keyword rescue for tx_origin (tx.origin in source)

Writes master-schema seed records + sources under processed/source/phase2/.
Does NOT overwrite processed/master_dataset.json; writes an extended copy instead.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
MASTER_JSON = ROOT / "processed" / "master_dataset.json"
AUG_JSONL = ROOT / "data" / "processed" / "obfuscation_benchmark.jsonl"
DIVE_JSONL = ROOT / "data" / "processed" / "dive_vulnerable.jsonl"
DAPPSCAN_JSONL = ROOT / "data" / "processed" / "dappscan_vulnerable.jsonl"
DEFI_JSONL = ROOT / "data" / "processed" / "defihacklabs_exploits.jsonl"
# Prefer data/DIVE (organized layout); keep legacy DIVE_Labels/ fallback
_DIVE_LABEL_CANDIDATES = [
    ROOT / "data" / "DIVE" / "Labels" / "DIVE_Labels.csv",
    ROOT / "data" / "DIVE" / "DIVE_Labels.csv",
    ROOT / "DIVE_Labels" / "Labels" / "DIVE_Labels.csv",
]
DIVE_LABELS = next((p for p in _DIVE_LABEL_CANDIDATES if p.is_file()), _DIVE_LABEL_CANDIDATES[0])
PHASE1_JSON = ROOT / "data" / "processed" / "phase1_unique_seed_report.json"

OUT_CANDIDATES = ROOT / "data" / "processed" / "phase2_grow_candidates.jsonl"
OUT_EXTENDED = ROOT / "processed" / "master_dataset_phase2.json"
OUT_REPORT_JSON = ROOT / "data" / "processed" / "phase2_unique_seed_report.json"
OUT_REPORT_MD = ROOT / "docs" / "dataset" / "phase2-unique-seed-ingest.md"
SOURCE_OUT = ROOT / "processed" / "source" / "phase2"

UNIQUE_SEED_TARGET = 80
DROP_FROM_V1 = frozenset({"short_address", "other"})

# Grow classes from Phase 1 (below target in master∪aug union)
GROW_CLASSES = (
    "denial_of_service",
    "bad_randomness",
    "access_control",
    "tx_origin",
    "front_running",
    "time_manipulation",
    "integer_overflow",
)

DIVE_COL_TO_CLASS = {
    "DoS": "denial_of_service",
    "Bad Randomness": "bad_randomness",
    "Front Running": "front_running",
    "Time manipulation": "time_manipulation",
    "Access Control": "access_control",
    "Arithmetic": "integer_overflow",
    "Reentrancy": "reentrancy",
    "Unchecked Return Values": "unchecked_call",
}

# Prefer exclusive among these when mining minority grow classes
MINORITY_DIVE_COLS = ("DoS", "Bad Randomness", "Front Running", "Time manipulation")

SWC_TO_CLASS = {
    "SWC-113": "denial_of_service",
    "SWC-128": "denial_of_service",
    "SWC-120": "bad_randomness",
    "SWC-114": "time_manipulation",
    "SWC-115": "tx_origin",
    "SWC-101": "integer_overflow",
    "SWC-104": "unchecked_call",
    "SWC-105": "access_control",
    "SWC-106": "access_control",
    "SWC-107": "reentrancy",
    "SWC-118": "access_control",
    "SWC-124": "access_control",
}

POOL_CAT_TO_CLASS = {
    "AccessControl": "access_control",
    "Arithmetic": "integer_overflow",
    "UncheckedReturn": "unchecked_call",
    "Reentrancy": "reentrancy",
}

CLASS_ID = {
    "reentrancy": 0,
    "integer_overflow": 1,
    "access_control": 2,
    "unchecked_call": 3,
    "time_manipulation": 4,
    "front_running": 5,
    "bad_randomness": 6,
    "denial_of_service": 7,
    "short_address": 8,
    "tx_origin": 9,
    "other": 10,
    "none": 11,
}

TX_ORIGIN_RE = re.compile(r"\btx\.origin\b")
COMMENT_RE = re.compile(r"/\*.*?\*/|//.*?$", re.MULTILINE | re.DOTALL)
WS_RE = re.compile(r"\s+")


def seed_family_id(row: dict) -> str:
    parent = (row.get("parent_contract_id") or "").strip()
    if parent:
        return parent
    return (row.get("contract_id") or row.get("id") or "").strip()


def content_hash(source: str) -> str:
    cleaned = COMMENT_RE.sub("", source or "")
    cleaned = WS_RE.sub("", cleaned).lower()
    return hashlib.sha256(cleaned.encode("utf-8", errors="replace")).hexdigest()


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_existing_seeds() -> tuple[set[str], set[str]]:
    """Return (seed_family_ids, content_hashes) already in master∪aug."""
    ids: set[str] = set()
    hashes: set[str] = set()

    master = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    for r in master:
        sid = seed_family_id(r)
        if sid:
            ids.add(sid)
        rel = r.get("source_code_path")
        if rel:
            p = ROOT / "processed" / rel if not str(rel).startswith("processed") else ROOT / rel
            # master paths are relative to processed/
            candidates = [
                ROOT / "processed" / rel,
                ROOT / rel,
            ]
            for p in candidates:
                if p.is_file():
                    hashes.add(content_hash(p.read_text(encoding="utf-8", errors="replace")))
                    break

    if AUG_JSONL.is_file():
        for r in iter_jsonl(AUG_JSONL):
            sid = seed_family_id(r)
            if sid:
                ids.add(sid)

    return ids, hashes


def load_phase1_union_counts() -> dict[str, int]:
    if not PHASE1_JSON.is_file():
        return {}
    data = json.loads(PHASE1_JSON.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for cls, c in (data.get("classes") or {}).items():
        out[cls] = int(c.get("union_unique_seeds") or 0)
    return out


def load_dive_labels() -> dict[int, dict[str, int]]:
    import csv

    labels: dict[int, dict[str, int]] = {}
    with DIVE_LABELS.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(DIVE_COL_TO_CLASS)
        for row in reader:
            try:
                cid = int(str(row["contractID"]).strip())
            except (KeyError, ValueError):
                continue
            labels[cid] = {c: int(str(row.get(c) or "0").strip() or "0") for c in cols}
    return labels


def write_source(dataset: str, contract_id: str, source: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", contract_id)[:120]
    rel = f"source/phase2/{dataset}/{safe}.sol"
    path = ROOT / "processed" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", errors="replace")
    return rel.replace("\\", "/")


def make_record(
    *,
    contract_id: str,
    source_dataset: str,
    source: str,
    primary: str,
    compiler_version: str,
    bytecode: str | None,
    notes: str,
    vulnerability_types: list[str] | None = None,
) -> dict[str, Any]:
    types = vulnerability_types or [primary]
    source_rel = write_source(source_dataset, contract_id, source)
    compiled = bool(bytecode)
    bytecode_rel = None
    if compiled and bytecode:
        brel = f"bytecode/phase2/{source_dataset}/{re.sub(r'[^A-Za-z0-9_.-]+', '_', contract_id)[:120]}.bin"
        bpath = ROOT / "processed" / brel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        hex_body = bytecode[2:] if str(bytecode).startswith("0x") else str(bytecode)
        bpath.write_text(hex_body + "\n", encoding="utf-8")
        bytecode_rel = brel.replace("\\", "/")
    return {
        "contract_id": contract_id,
        "source_dataset": source_dataset,
        "source_code_path": source_rel,
        "bytecode_path": bytecode_rel,
        "label": "vulnerable",
        "vulnerability_types": types,
        "primary_vulnerability_type": primary,
        "compiler_version": compiler_version or "unknown",
        "compiled_successfully": compiled,
        "duplicate_of": None,
        "notes": notes,
        "parent_contract_id": None,
        "transformation_level": "none",
        "transformation_techniques": [],
        "obfuscation_severity": "none",
        "exploit_verified_after_transform": None,
        "gnn_fields": {
            "vulnerable_function_name": None,
            "vulnerable_line_numbers": None,
            "vulnerability_class_id": CLASS_ID[primary],
        },
        "llm_fields": {
            "vulnerable_function_snippet": None,
            "explanation": None,
            "severity": None,
        },
        "_phase2": {
            "content_hash": content_hash(source),
            "ingest": "phase2_mine_unique_seeds",
        },
    }


def dive_exclusive(lab: dict[str, int], col: str) -> bool:
    if lab.get(col, 0) != 1:
        return False
    for other in MINORITY_DIVE_COLS:
        if other != col and lab.get(other, 0) == 1:
            return False
    return True


def mine_dive(
    need: dict[str, int],
    existing_ids: set[str],
    existing_hashes: set[str],
) -> list[dict[str, Any]]:
    labels = load_dive_labels()
    # Build candidate lists per class: prefer exclusive minorities
    class_to_col = {
        cls: col
        for col, cls in DIVE_COL_TO_CLASS.items()
        if cls in need
        and need[cls] > 0
        and col in MINORITY_DIVE_COLS + ("Access Control", "Arithmetic")
    }

    # Precompute eligible dive_contract_ids per class
    eligible: dict[str, list[int]] = defaultdict(list)
    for cid, lab in labels.items():
        for cls, col in class_to_col.items():
            if need[cls] <= 0:
                continue
            if cls in ("denial_of_service", "bad_randomness", "front_running", "time_manipulation"):
                if dive_exclusive(lab, col):
                    eligible[cls].append(cid)
            elif lab.get(col, 0) == 1:
                # access_control / integer_overflow: prefer fewer co-labels
                score = sum(1 for c in lab if lab[c] == 1)
                if score <= 2:  # target + at most one other
                    eligible[cls].append(cid)

    for cls in eligible:
        eligible[cls].sort()

    need_ids: set[int] = set()
    for cls, ids in eligible.items():
        # take a buffer over need
        need_ids.update(ids[: need[cls] * 3 + 50])

    picked: list[dict[str, Any]] = []
    got: Counter[str] = Counter()
    seen_hash = set(existing_hashes)

    with DIVE_JSONL.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if all(got[c] >= need[c] for c in need if need[c] > 0):
                break
            o = json.loads(line)
            cid = o.get("dive_contract_id")
            if cid is None:
                continue
            cid = int(cid)
            if cid not in need_ids:
                continue
            source = o.get("source_code") or ""
            if len(source.strip()) < 40:
                continue
            rid = o.get("id") or f"DIVE_{cid}"
            if rid in existing_ids:
                continue
            h = content_hash(source)
            if h in seen_hash:
                continue

            lab = labels.get(cid) or {}
            # Assign to first grow class still needing that this row qualifies for
            assigned = None
            for cls in GROW_CLASSES:
                if cls not in need or got[cls] >= need[cls]:
                    continue
                col = class_to_col.get(cls)
                if not col:
                    continue
                if cls in ("denial_of_service", "bad_randomness", "front_running", "time_manipulation"):
                    if not dive_exclusive(lab, col):
                        continue
                elif lab.get(col, 0) != 1:
                    continue
                assigned = cls
                break
            if not assigned:
                continue

            rec = make_record(
                contract_id=rid,
                source_dataset="dive",
                source=source,
                primary=assigned,
                compiler_version=str(o.get("compiler_version") or "unknown"),
                bytecode=o.get("bytecode"),
                notes=f"phase2 ingest from DIVE; dive_contract_id={cid}; exclusive_minority={assigned in ('denial_of_service','bad_randomness','front_running','time_manipulation')}",
            )
            picked.append(rec)
            got[assigned] += 1
            seen_hash.add(h)
            existing_ids.add(rid)

    return picked


def mine_dappscan_swc(
    need: dict[str, int],
    existing_ids: set[str],
    existing_hashes: set[str],
) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    got: Counter[str] = Counter()
    seen_hash = set(existing_hashes)

    for o in iter_jsonl(DAPPSCAN_JSONL):
        if all(got[c] >= need[c] for c in need if need[c] > 0):
            break
        labs = o.get("labels") or {}
        swcs = labs.get("swc_ids") or []
        mapped = []
        for s in swcs:
            cls = SWC_TO_CLASS.get(str(s).upper() if str(s).startswith("SWC") else f"SWC-{s}")
            # normalize
            key = str(s).upper()
            if not key.startswith("SWC-"):
                key = f"SWC-{key}"
            cls = SWC_TO_CLASS.get(key)
            if cls and cls in need and got[cls] < need[cls]:
                mapped.append(cls)
        if not mapped:
            # category fallback for access_control / integer_overflow
            for cat in labs.get("categories") or []:
                cls = POOL_CAT_TO_CLASS.get(str(cat))
                if cls in need and got[cls] < need[cls]:
                    mapped.append(cls)
        if not mapped:
            continue
        # prefer single mapped class = first by GROW_CLASSES order
        assigned = None
        for cls in GROW_CLASSES:
            if cls in mapped and got[cls] < need[cls]:
                assigned = cls
                break
        if not assigned:
            continue
        source = o.get("source_code") or ""
        if len(source.strip()) < 40:
            continue
        rid = o.get("id") or ""
        if not rid or rid in existing_ids:
            continue
        h = content_hash(source)
        if h in seen_hash:
            continue
        rec = make_record(
            contract_id=rid,
            source_dataset="dapscan",
            source=source,
            primary=assigned,
            compiler_version=str(o.get("compiler_version") or "unknown"),
            bytecode=o.get("bytecode"),
            notes=f"phase2 ingest from DAppSCAN; swc_ids={swcs}; categories={labs.get('categories')}",
        )
        picked.append(rec)
        got[assigned] += 1
        seen_hash.add(h)
        existing_ids.add(rid)

    return picked


def mine_tx_origin_keyword(
    need_n: int,
    existing_ids: set[str],
    existing_hashes: set[str],
) -> list[dict[str, Any]]:
    """Rescue tx_origin via tx.origin occurrences in pool sources."""
    if need_n <= 0:
        return []
    picked: list[dict[str, Any]] = []
    seen_hash = set(existing_hashes)

    pools: list[tuple[Path, str]] = [
        (DAPPSCAN_JSONL, "dapscan"),
        (DIVE_JSONL, "dive"),
        (DEFI_JSONL, "defihacklabs"),
    ]
    for path, dataset in pools:
        if len(picked) >= need_n:
            break
        for o in iter_jsonl(path):
            if len(picked) >= need_n:
                break
            source = o.get("source_code") or ""
            if not TX_ORIGIN_RE.search(source):
                continue
            # Prefer auth-related labels when present
            labs = o.get("labels") or {}
            cats = [str(c) for c in (labs.get("categories") or [])]
            if cats and not any(
                c in ("AccessControl", "OtherVulnerability") or "access" in c.lower() for c in cats
            ):
                # still allow if tx.origin present — weak but scarce class
                pass
            rid = o.get("id") or ""
            if not rid or rid in existing_ids:
                continue
            if len(source.strip()) < 40:
                continue
            h = content_hash(source)
            if h in seen_hash:
                continue
            # Skip if already clearly another primary we care about exclusively
            if "Reentrancy" in cats and "AccessControl" not in cats:
                continue
            rec = make_record(
                contract_id=rid,
                source_dataset=dataset,
                source=source,
                primary="tx_origin",
                compiler_version=str(o.get("compiler_version") or "unknown"),
                bytecode=o.get("bytecode"),
                notes=f"phase2 ingest keyword tx.origin; categories={cats}",
            )
            picked.append(rec)
            seen_hash.add(h)
            existing_ids.add(rid)
    return picked


def main() -> None:
    phase1 = load_phase1_union_counts()
    existing_ids, existing_hashes = load_existing_seeds()

    need: dict[str, int] = {}
    for cls in GROW_CLASSES:
        have = phase1.get(cls, 0)
        deficit = max(0, UNIQUE_SEED_TARGET - have)
        need[cls] = deficit

    print("Phase 2 deficits (to reach 80):")
    for cls in GROW_CLASSES:
        print(f"  {cls}: have={phase1.get(cls, 0)} need={need[cls]}")

    selected: list[dict[str, Any]] = []
    by_source: dict[str, Counter[str]] = defaultdict(Counter)

    # 1) DIVE fine-grained (best signal for minorities)
    dive_need = {k: v for k, v in need.items() if v > 0 and k != "tx_origin"}
    dive_picked = mine_dive(dive_need, existing_ids, existing_hashes)
    for r in dive_picked:
        selected.append(r)
        cls = r["primary_vulnerability_type"]
        need[cls] = max(0, need[cls] - 1)
        by_source[cls]["dive"] += 1
        existing_hashes.add(r["_phase2"]["content_hash"])

    print(f"After DIVE: picked={len(dive_picked)} remaining={dict(need)}")

    # 2) DAppSCAN SWC / category fill
    dap_need = {k: v for k, v in need.items() if v > 0}
    dap_picked = mine_dappscan_swc(dap_need, existing_ids, existing_hashes)
    for r in dap_picked:
        selected.append(r)
        cls = r["primary_vulnerability_type"]
        need[cls] = max(0, need[cls] - 1)
        by_source[cls]["dapscan"] += 1
        existing_hashes.add(r["_phase2"]["content_hash"])

    print(f"After DAppSCAN: picked={len(dap_picked)} remaining={dict(need)}")

    # 3) tx_origin keyword rescue
    if need.get("tx_origin", 0) > 0:
        tx_picked = mine_tx_origin_keyword(need["tx_origin"], existing_ids, existing_hashes)
        for r in tx_picked:
            selected.append(r)
            need["tx_origin"] = max(0, need["tx_origin"] - 1)
            by_source["tx_origin"][r["source_dataset"]] += 1
            existing_hashes.add(r["_phase2"]["content_hash"])
        print(f"After tx.origin keyword: picked={len(tx_picked)} remaining tx_origin={need['tx_origin']}")

    # Strip internal helper before writing candidates (keep hash in notes via _phase2 for report)
    OUT_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CANDIDATES.open("w", encoding="utf-8") as f:
        for r in selected:
            slim = {k: v for k, v in r.items() if k != "_phase2"}
            f.write(json.dumps(slim) + "\n")

    # Extended master = original + new seeds (strip _phase2)
    master = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    extended = list(master)
    for r in selected:
        slim = {k: v for k, v in r.items() if k != "_phase2"}
        extended.append(slim)
    OUT_EXTENDED.parent.mkdir(parents=True, exist_ok=True)
    OUT_EXTENDED.write_text(json.dumps(extended, indent=2), encoding="utf-8")

    # Final inventory on extended
    by_cls_seeds: dict[str, set[str]] = defaultdict(set)
    for r in extended:
        cls = r.get("primary_vulnerability_type") or "unknown"
        by_cls_seeds[cls].add(seed_family_id(r))

    added_by_cls = Counter(r["primary_vulnerability_type"] for r in selected)
    report = {
        "unique_seed_target": UNIQUE_SEED_TARGET,
        "added_seeds": len(selected),
        "added_by_class": dict(added_by_cls),
        "by_source": {k: dict(v) for k, v in by_source.items()},
        "remaining_deficit": {k: v for k, v in need.items()},
        "extended_master": OUT_EXTENDED.relative_to(ROOT).as_posix(),
        "candidates_jsonl": OUT_CANDIDATES.relative_to(ROOT).as_posix(),
        "inventory_extended_unique_seeds": {
            cls: len(by_cls_seeds[cls]) for cls in sorted(by_cls_seeds)
        },
        "grow_class_status": {},
    }
    for cls in GROW_CLASSES:
        n = len(by_cls_seeds[cls])
        report["grow_class_status"][cls] = {
            "phase1_union": phase1.get(cls, 0),
            "added": added_by_cls[cls],
            "extended_unique_seeds": n,
            "meets_target": n >= UNIQUE_SEED_TARGET,
            "deficit": max(0, UNIQUE_SEED_TARGET - n),
        }

    OUT_REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Phase 2 — Unique-seed ingest")
    lines.append("")
    lines.append("**Status:** Candidates mined; extended master written (original master unchanged).")
    lines.append("")
    lines.append(f"**Added seeds:** {len(selected)}")
    lines.append(f"**Candidates:** `{OUT_CANDIDATES.relative_to(ROOT).as_posix()}`")
    lines.append(f"**Extended master:** `{OUT_EXTENDED.relative_to(ROOT).as_posix()}`")
    lines.append(f"**Target:** ≥ {UNIQUE_SEED_TARGET} unique seeds per kept class")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("1. **DIVE** — rejoin `DIVE_Labels.csv` fine-grained flags (DoS, Bad Randomness, Front Running, Time manipulation, Access Control, Arithmetic) to `dive_vulnerable.jsonl`; prefer exclusive minority flags.")
    lines.append("2. **DAppSCAN** — SWC → class map (`SWC-113/128` DoS, `SWC-120` randomness, `SWC-114` time, `SWC-115` tx.origin, `SWC-101` overflow, access-control SWCs) plus category fallback.")
    lines.append("3. **tx_origin rescue** — keyword `tx.origin` in pool sources (DAppSCAN → DIVE → DeFiHackLabs).")
    lines.append("4. Dedup by existing master∪aug `contract_id` / `parent_contract_id` and normalized source content hash.")
    lines.append("5. Write `.sol` under `processed/source/phase2/<dataset>/`.")
    lines.append("")
    lines.append("## Grow-class status (extended master unique seeds)")
    lines.append("")
    lines.append("| class | phase1 union | added | extended seeds | meets target | deficit |")
    lines.append("|-------|-------------:|------:|---------------:|:------------:|--------:|")
    for cls in GROW_CLASSES:
        s = report["grow_class_status"][cls]
        lines.append(
            f"| `{cls}` | {s['phase1_union']} | {s['added']} | {s['extended_unique_seeds']} | "
            f"{'YES' if s['meets_target'] else 'NO'} | {s['deficit']} |"
        )
    lines.append("")
    lines.append("## Added by source")
    lines.append("")
    lines.append("| class | sources |")
    lines.append("|-------|---------|")
    for cls in GROW_CLASSES:
        src = report["by_source"].get(cls) or {}
        if not src:
            lines.append(f"| `{cls}` | — |")
        else:
            lines.append(f"| `{cls}` | {', '.join(f'{k}:{v}' for k,v in src.items())} |")
    lines.append("")
    lines.append("## Promote to training master")
    lines.append("")
    lines.append("Original `processed/master_dataset.json` is **unchanged**.")
    lines.append("To promote after review:")
    lines.append("")
    lines.append("```bash")
    lines.append("cp processed/master_dataset.json processed/master_dataset.pre_phase2.json")
    lines.append("cp processed/master_dataset_phase2.json processed/master_dataset.json")
    lines.append("```")
    lines.append("")
    lines.append("## Go / no-go")
    lines.append("")
    all_ok = all(report["grow_class_status"][c]["meets_target"] for c in GROW_CLASSES)
    lines.append(f"- [{'x' if all_ok else ' '}] Phase 2: all grow classes ≥ {UNIQUE_SEED_TARGET} unique seeds")
    lines.append("- [ ] Promote `master_dataset_phase2.json` → `master_dataset.json` (explicit)")
    lines.append("- [ ] Phase 3: class weights + majority cap")
    lines.append("")
    lines.append(f"Machine-readable: `{OUT_REPORT_JSON.relative_to(ROOT).as_posix()}`")
    lines.append("")
    lines.append("Regenerate: `python scripts/phase2_mine_unique_seeds.py`")
    lines.append("")

    OUT_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {OUT_CANDIDATES} ({len(selected)} rows)")
    print(f"Wrote {OUT_EXTENDED} ({len(extended)} rows)")
    print(f"Wrote {OUT_REPORT_MD}")
    print(f"Wrote {OUT_REPORT_JSON}")
    print("\nGrow status:")
    for cls in GROW_CLASSES:
        s = report["grow_class_status"][cls]
        flag = "OK" if s["meets_target"] else f"SHORT {s['deficit']}"
        print(f"  {cls}: {s['extended_unique_seeds']} ({flag})")


if __name__ == "__main__":
    main()
