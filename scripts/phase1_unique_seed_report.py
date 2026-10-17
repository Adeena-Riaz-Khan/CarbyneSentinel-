"""Phase 1: unique-seed inventory (master + obfuscation_benchmark)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER_JSON = ROOT / "processed" / "master_dataset.json"
JSONL = ROOT / "data" / "processed" / "obfuscation_benchmark.jsonl"
OUT_MD = ROOT / "docs" / "dataset" / "phase1-label-policy.md"
OUT_JSON = ROOT / "data" / "processed" / "phase1_unique_seed_report.json"

# v1 policy (locked)
DROP_FROM_V1 = ("short_address", "other")
KEEP_GROW = (
    "bad_randomness",
    "denial_of_service",
    "access_control",
    "reentrancy",
)
KEEP_CAP_LATER = (
    "unchecked_call",
    "tx_origin",
    "time_manipulation",
    "front_running",
    "integer_overflow",
)
UNIQUE_SEED_TARGET = 80


def seed_family_id(row: dict) -> str:
    parent = (row.get("parent_contract_id") or "").strip()
    if parent:
        return parent
    return (row.get("contract_id") or "").strip()


def primary_class(row: dict) -> str:
    return row.get("primary_vulnerability_type") or (row.get("vulnerability_types") or ["unknown"])[0]


def v1_action(cls: str, n_seeds: int) -> str:
    if cls in DROP_FROM_V1:
        return "drop"
    if cls in KEEP_GROW or n_seeds < UNIQUE_SEED_TARGET:
        return "grow"
    if cls in KEEP_CAP_LATER:
        return "keep_cap_later"
    return "grow" if n_seeds < UNIQUE_SEED_TARGET else "keep"


def load_master() -> list[dict]:
    data = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected master format: {MASTER_JSON}")
    return data


def load_aug() -> list[dict]:
    rows: list[dict] = []
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    master_rows = load_master()
    aug_rows = load_aug()

    master_by_seeds: dict[str, set[str]] = defaultdict(set)
    master_by_rows: Counter[str] = Counter()
    master_sources: dict[str, Counter[str]] = defaultdict(Counter)
    master_compiled: dict[str, Counter] = defaultdict(Counter)
    master_dup_marked: Counter[str] = Counter()

    for r in master_rows:
        cls = primary_class(r)
        sid = seed_family_id(r)
        master_by_rows[cls] += 1
        master_by_seeds[cls].add(sid)
        master_sources[cls][r.get("source_dataset") or "unknown"] += 1
        master_compiled[cls][bool(r.get("compiled_successfully"))] += 1
        if r.get("duplicate_of"):
            master_dup_marked[cls] += 1

    aug_by_seeds: dict[str, set[str]] = defaultdict(set)
    aug_by_rows: Counter[str] = Counter()
    aug_sources: dict[str, Counter[str]] = defaultdict(Counter)

    for r in aug_rows:
        cls = primary_class(r)
        sid = seed_family_id(r)
        aug_by_rows[cls] += 1
        aug_by_seeds[cls].add(sid)
        aug_sources[cls][r.get("source_dataset") or "unknown"] += 1

    classes = sorted(set(master_by_rows) | set(aug_by_rows), key=lambda c: (-(len(master_by_seeds[c] | aug_by_seeds[c])), c))

    report: dict = {
        "unique_seed_target": UNIQUE_SEED_TARGET,
        "policy": {
            "drop_from_v1_train": list(DROP_FROM_V1),
            "keep_and_grow": list(KEEP_GROW),
            "keep_cap_at_train_time": list(KEEP_CAP_LATER),
        },
        "sources": {
            "master": MASTER_JSON.relative_to(ROOT).as_posix(),
            "augmented_benchmark": JSONL.relative_to(ROOT).as_posix(),
        },
        "totals": {
            "master_rows": len(master_rows),
            "aug_rows": len(aug_rows),
            "aug_rows_are_all_transformed": all(
                bool(r.get("transformation_techniques")) for r in aug_rows
            ),
        },
        "classes": {},
    }

    for cls in classes:
        m_seeds = master_by_seeds[cls]
        a_seeds = aug_by_seeds[cls]
        union = m_seeds | a_seeds
        n_union = len(union)
        action = v1_action(cls, n_union)
        report["classes"][cls] = {
            "master_rows": master_by_rows[cls],
            "aug_rows": aug_by_rows[cls],
            "master_unique_seeds": len(m_seeds),
            "aug_unique_seeds": len(a_seeds),
            "union_unique_seeds": n_union,
            "only_master_seeds": len(m_seeds - a_seeds),
            "only_aug_seeds": len(a_seeds - m_seeds),
            "master_compiled": dict(master_compiled[cls]),
            "master_duplicate_of_marked": master_dup_marked[cls],
            "below_target": n_union < UNIQUE_SEED_TARGET and cls not in DROP_FROM_V1,
            "v1_action": action,
            "master_sources": dict(master_sources[cls]),
            "aug_sources": dict(aug_sources[cls]),
            "seed_families_union": sorted(union),
        }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Phase 1 — Label policy & unique-seed inventory")
    lines.append("")
    lines.append("**Status:** LOCKED for v1 train set.")
    lines.append("")
    lines.append(f"**Master:** `{MASTER_JSON.relative_to(ROOT).as_posix()}` ({len(master_rows)} rows)")
    lines.append(f"**Augmented benchmark:** `{JSONL.relative_to(ROOT).as_posix()}` ({len(aug_rows)} rows)")
    lines.append(f"**Unique-seed target (kept classes):** ≥ {UNIQUE_SEED_TARGET}")
    lines.append("")
    lines.append("## Critical finding")
    lines.append("")
    lines.append(
        "- `obfuscation_benchmark.jsonl` is **100% transformed rows** (0 unaugmented masters in-file)."
    )
    lines.append(
        "- Classes `unchecked_call`, `integer_overflow`, and `other` appear in **master only** — "
        "they are absent from the augmented JSONL."
    )
    lines.append(
        "- Unique-seed inventory for training readiness uses the **union** of master `contract_id` "
        "and aug `parent_contract_id` / `contract_id`."
    )
    lines.append("")
    lines.append("## Seed identity rule")
    lines.append("")
    lines.append("- Augmented row → `seed_family_id = parent_contract_id`")
    lines.append("- Master / unaugmented row → `seed_family_id = contract_id`")
    lines.append("- Counts below use **unique seed families**, not row counts after augmentation.")
    lines.append("")
    lines.append("## Locked v1 decisions")
    lines.append("")
    lines.append("| Class | Action | Rationale |")
    lines.append("|-------|--------|-----------|")
    lines.append(
        "| `short_address` | **Drop from v1 train** (backlog) | "
        "1 master family; aug cannot create diversity |"
    )
    lines.append(
        "| `other` | **Drop from v1 train** (backlog) | "
        "3 master rows / undefined signal |"
    )
    lines.append(
        "| `bad_randomness`, `denial_of_service`, `access_control` | **Keep + grow** | "
        "Thin but salvageable with real ingest |"
    )
    lines.append(
        "| `reentrancy` | **Keep + grow unique seeds** | "
        "Master has 81 rows but still verify ≥80 distinct families after dedupe; "
        "aug added almost no new families |"
    )
    lines.append(
        "| Majors (`unchecked_call`, `tx_origin`, `time_manipulation`, "
        "`front_running`, `integer_overflow`) | **Keep; cap at train time** | "
        "Undersample / weight later (Phase 3); still grow if union < 80 |"
    )
    lines.append("")
    lines.append("## Inventory (union of master + aug)")
    lines.append("")
    lines.append(
        "| class | master rows | aug rows | master seeds | aug seeds | "
        "union seeds | only master | only aug | below target | v1 action |"
    )
    lines.append(
        "|-------|------------:|---------:|-------------:|----------:|"
        "------------:|------------:|---------:|:------------:|-----------|"
    )
    for cls in classes:
        c = report["classes"][cls]
        below = "YES" if c["below_target"] else ("—" if cls in DROP_FROM_V1 else "")
        lines.append(
            f"| `{cls}` | {c['master_rows']} | {c['aug_rows']} | "
            f"{c['master_unique_seeds']} | {c['aug_unique_seeds']} | "
            f"{c['union_unique_seeds']} | {c['only_master_seeds']} | "
            f"{c['only_aug_seeds']} | {below} | {c['v1_action']} |"
        )
    lines.append("")
    lines.append("## Dropped classes — families (for backlog)")
    lines.append("")
    for cls in DROP_FROM_V1:
        fams = report["classes"].get(cls, {}).get("seed_families_union", [])
        lines.append(f"### `{cls}` ({len(fams)} families)")
        for s in fams:
            lines.append(f"- `{s}`")
        if not fams:
            lines.append("- _(none)_")
        lines.append("")
    lines.append("## Phase 2 queue (union unique seeds < target, excluding drops)")
    lines.append("")
    grow = [
        cls
        for cls in classes
        if cls not in DROP_FROM_V1 and report["classes"][cls]["union_unique_seeds"] < UNIQUE_SEED_TARGET
    ]
    if not grow:
        lines.append("_All kept classes meet the unique-seed target._")
    else:
        lines.append("| class | union seeds | deficit | master sources | aug sources |")
        lines.append("|-------|------------:|--------:|----------------|-------------|")
        for cls in sorted(grow, key=lambda c: report["classes"][c]["union_unique_seeds"]):
            n = report["classes"][cls]["union_unique_seeds"]
            deficit = UNIQUE_SEED_TARGET - n
            msrc = ", ".join(
                f"{k}:{v}" for k, v in report["classes"][cls]["master_sources"].items()
            ) or "—"
            asrc = ", ".join(
                f"{k}:{v}" for k, v in report["classes"][cls]["aug_sources"].items()
            ) or "—"
            lines.append(f"| `{cls}` | {n} | {deficit} | {msrc} | {asrc} |")
    lines.append("")
    lines.append("## Phase 2 ingest note")
    lines.append("")
    lines.append(
        "Priority grow classes (largest deficit): mine `dappscan_vulnerable.jsonl`, "
        "`dive_vulnerable.jsonl`, `defihacklabs_exploits.jsonl` for **new** "
        "`contract_id`s not already in the union above. Do not count additional "
        "aug variants of existing parents toward the unique-seed target."
    )
    lines.append("")
    lines.append("## Go / no-go for training")
    lines.append("")
    lines.append("- [x] Phase 1 policy locked (this doc)")
    lines.append("- [ ] Phase 2: ingest distinct contracts for grow list until ≥80 unique seeds each")
    lines.append("- [ ] Phase 3: class weights + majority cap")
    lines.append("- [ ] Phase 4: seed-family stratified split")
    lines.append("- [ ] Phase 5: smoke train on unaugmented holdout (macro-F1)")
    lines.append("")
    lines.append(f"Machine-readable report: `{OUT_JSON.relative_to(ROOT).as_posix()}`")
    lines.append("")
    lines.append("Regenerate: `python scripts/phase1_unique_seed_report.py`")
    lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print("\nBelow-target kept classes (union):")
    for cls in sorted(grow, key=lambda c: report["classes"][c]["union_unique_seeds"]):
        print(f"  {cls}: {report['classes'][cls]['union_unique_seeds']} unique seeds")
    at_target = [
        cls
        for cls in classes
        if cls not in DROP_FROM_V1
        and report["classes"][cls]["union_unique_seeds"] >= UNIQUE_SEED_TARGET
    ]
    if at_target:
        print("\nAt/above target:")
        for cls in at_target:
            print(f"  {cls}: {report['classes'][cls]['union_unique_seeds']} unique seeds")


if __name__ == "__main__":
    main()
