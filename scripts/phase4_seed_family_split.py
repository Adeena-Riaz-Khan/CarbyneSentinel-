"""Phase 4: seed-family stratified train/val/test split.

Uses Phase 3 train index (capped, dropped classes removed).
Entire seed families stay in one split; aug variants inherit parent split.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER_PHASE2 = ROOT / "processed" / "master_dataset_phase2.json"
PHASE3_INDEX = ROOT / "data" / "processed" / "phase3_train_index.json"
AUG_JSONL = ROOT / "data" / "processed" / "obfuscation_benchmark.jsonl"

OUT_SPLITS = ROOT / "data" / "processed" / "phase4_splits.json"
OUT_MD = ROOT / "docs" / "dataset" / "phase4-seed-family-split.md"

# Locked ratios (exact on 80 seeds/class → 56 / 12 / 12)
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# test = remainder
RNG_SEED = 42


def seed_family_id(row: dict[str, Any]) -> str:
    parent = (row.get("parent_contract_id") or "").strip()
    if parent:
        return parent
    return (row.get("contract_id") or row.get("id") or "").strip()


def stable_shuffle(items: list[str], seed: int) -> list[str]:
    """Deterministic shuffle independent of Python hash randomization."""
    def key(x: str) -> str:
        return hashlib.sha256(f"{seed}:{x}".encode()).hexdigest()

    return sorted(items, key=key)


def split_sizes(n: int) -> tuple[int, int, int]:
    n_train = int(round(TRAIN_FRAC * n))
    n_val = int(round(VAL_FRAC * n))
    # Keep exact sum
    if n_train + n_val > n:
        n_val = max(0, n - n_train)
    n_test = n - n_train - n_val
    # Prefer at least 1 in val/test when n is large enough
    if n >= 10 and n_test == 0 and n_train > 1:
        n_train -= 1
        n_test = 1
    if n >= 10 and n_val == 0 and n_train > 1:
        n_train -= 1
        n_val = 1
    return n_train, n_val, n_test


def main() -> None:
    index = json.loads(PHASE3_INDEX.read_text(encoding="utf-8"))
    keep = set(index["train_contract_ids"])
    master: list[dict[str, Any]] = json.loads(MASTER_PHASE2.read_text(encoding="utf-8"))

    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in master:
        cid = (r.get("contract_id") or "").strip()
        if cid not in keep:
            continue
        cls = r.get("primary_vulnerability_type") or "unknown"
        by_class[cls].append(r)

    family_to_split: dict[str, str] = {}
    family_to_class: dict[str, str] = {}
    splits: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    per_class: dict[str, dict[str, list[str]]] = {}

    for cls in sorted(by_class):
        rows = by_class[cls]
        families = [seed_family_id(r) for r in rows]
        # Each Phase 3 seed is its own family (no parent)
        assert len(families) == len(set(families)), f"duplicate families in {cls}"
        ordered = stable_shuffle(families, RNG_SEED)
        n_train, n_val, n_test = split_sizes(len(ordered))
        train_f = ordered[:n_train]
        val_f = ordered[n_train : n_train + n_val]
        test_f = ordered[n_train + n_val :]
        assert len(train_f) + len(val_f) + len(test_f) == len(ordered)

        per_class[cls] = {"train": train_f, "val": val_f, "test": test_f}
        for fid in train_f:
            family_to_split[fid] = "train"
            family_to_class[fid] = cls
            splits["train"].append(fid)
        for fid in val_f:
            family_to_split[fid] = "val"
            family_to_class[fid] = cls
            splits["val"].append(fid)
        for fid in test_f:
            family_to_split[fid] = "test"
            family_to_class[fid] = cls
            splits["test"].append(fid)

    for name in splits:
        splits[name] = sorted(splits[name])

    # Augmentation: inherit parent split; exclude if parent not in Phase 3 index
    aug_by_split: dict[str, list[dict[str, str]]] = {"train": [], "val": [], "test": []}
    aug_excluded: list[dict[str, str]] = []
    aug_total = 0
    if AUG_JSONL.is_file():
        with AUG_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                aug_total += 1
                fam = seed_family_id(o)
                cid = (o.get("contract_id") or "").strip()
                split = family_to_split.get(fam)
                if split is None:
                    aug_excluded.append(
                        {
                            "contract_id": cid,
                            "seed_family_id": fam,
                            "reason": "parent_not_in_phase3_train_index",
                        }
                    )
                    continue
                aug_by_split[split].append(
                    {
                        "contract_id": cid,
                        "seed_family_id": fam,
                        "primary_vulnerability_type": o.get("primary_vulnerability_type")
                        or family_to_class.get(fam, ""),
                        "split": split,
                    }
                )

    # Leakage check: no family in >1 split
    seen: dict[str, str] = {}
    leakage: list[str] = []
    for split_name, fams in splits.items():
        for fam in fams:
            if fam in seen and seen[fam] != split_name:
                leakage.append(f"{fam}: {seen[fam]} vs {split_name}")
            seen[fam] = split_name
    for split_name, rows in aug_by_split.items():
        for row in rows:
            fam = row["seed_family_id"]
            if fam in seen and seen[fam] != split_name:
                leakage.append(f"aug {row['contract_id']}: family {fam} in {seen[fam]} vs {split_name}")

    # Counts
    seed_counts = {s: len(splits[s]) for s in ("train", "val", "test")}
    class_split_counts: dict[str, dict[str, int]] = {}
    for cls, parts in per_class.items():
        class_split_counts[cls] = {s: len(parts[s]) for s in ("train", "val", "test")}

    aug_counts = {s: len(aug_by_split[s]) for s in ("train", "val", "test")}

    payload = {
        "policy": {
            "train_frac": TRAIN_FRAC,
            "val_frac": VAL_FRAC,
            "test_frac": round(1.0 - TRAIN_FRAC - VAL_FRAC, 4),
            "rng_seed": RNG_SEED,
            "shuffle": "sha256(seed:family_id) sort key (deterministic)",
            "unit": "seed_family_id (= contract_id for Phase 3 seeds; parent_contract_id for aug)",
            "stratify_by": "primary_vulnerability_type",
            "aug_rule": "variant inherits parent split; excluded if parent not in Phase 3 index",
        },
        "source_phase3_index": PHASE3_INDEX.relative_to(ROOT).as_posix(),
        "source_master": MASTER_PHASE2.relative_to(ROOT).as_posix(),
        "source_aug": AUG_JSONL.relative_to(ROOT).as_posix() if AUG_JSONL.is_file() else None,
        "n_seed_families": sum(seed_counts.values()),
        "seed_counts": seed_counts,
        "class_split_counts": class_split_counts,
        "splits": splits,
        "family_to_split": family_to_split,
        "augmentation": {
            "n_aug_rows_total": aug_total,
            "n_assigned": sum(aug_counts.values()),
            "n_excluded": len(aug_excluded),
            "counts_by_split": aug_counts,
            "by_split": {k: sorted(v, key=lambda r: r["contract_id"]) for k, v in aug_by_split.items()},
            "excluded_sample": aug_excluded[:50],
            "n_excluded_listed_in_sample": min(50, len(aug_excluded)),
        },
        "leakage_violations": leakage,
        "leakage_ok": len(leakage) == 0,
    }

    OUT_SPLITS.parent.mkdir(parents=True, exist_ok=True)
    OUT_SPLITS.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Phase 4 — Seed-family stratified split")
    lines.append("")
    lines.append("**Status:** LOCKED for v1 train/val/test.")
    lines.append("")
    lines.append(f"**Seeds:** `{PHASE3_INDEX.relative_to(ROOT).as_posix()}` → `{OUT_SPLITS.relative_to(ROOT).as_posix()}`")
    lines.append(
        f"**Ratios:** train {TRAIN_FRAC:.0%} / val {VAL_FRAC:.0%} / "
        f"test {1.0 - TRAIN_FRAC - VAL_FRAC:.0%} (remainder)"
    )
    lines.append(f"**RNG seed:** {RNG_SEED} (deterministic family shuffle)")
    lines.append("")
    lines.append("## Rules")
    lines.append("")
    lines.append("1. Split unit = **seed family** (`contract_id` for unaugmented seeds).")
    lines.append("2. Stratify by `primary_vulnerability_type` (same ratios inside each class).")
    lines.append("3. Augmented rows inherit the **parent** family's split.")
    lines.append("4. Aug rows whose parent was capped away / dropped are **excluded** from v1 splits.")
    lines.append("5. No family may appear in more than one of train/val/test.")
    lines.append("")
    lines.append("## Seed counts")
    lines.append("")
    lines.append(
        f"| split | families | share |"
    )
    lines.append("|-------|---------:|------:|")
    total = sum(seed_counts.values()) or 1
    for s in ("train", "val", "test"):
        lines.append(f"| `{s}` | {seed_counts[s]} | {seed_counts[s] / total:.1%} |")
    lines.append(f"| **total** | **{total}** | 100% |")
    lines.append("")
    lines.append("## Per-class seed split (target 56 / 12 / 12 on n=80)")
    lines.append("")
    lines.append("| class | train | val | test |")
    lines.append("|-------|------:|----:|-----:|")
    for cls in sorted(class_split_counts):
        c = class_split_counts[cls]
        lines.append(f"| `{cls}` | {c['train']} | {c['val']} | {c['test']} |")
    lines.append("")
    lines.append("## Augmentation attachment")
    lines.append("")
    lines.append(
        f"Benchmark rows: **{aug_total}** → assigned **{sum(aug_counts.values())}** "
        f"(train {aug_counts['train']}, val {aug_counts['val']}, test {aug_counts['test']}); "
        f"**{len(aug_excluded)}** excluded (parent not in Phase 3 index)."
    )
    lines.append("")
    lines.append("## Leakage check")
    lines.append("")
    if leakage:
        lines.append(f"- **FAIL:** {len(leakage)} violation(s)")
        for v in leakage[:20]:
            lines.append(f"  - {v}")
    else:
        lines.append("- **PASS:** no seed family spans multiple splits (seeds + assigned aug).")
    lines.append("")
    lines.append("## Trainer hook")
    lines.append("")
    lines.append("```python")
    lines.append("import json")
    lines.append("from pathlib import Path")
    lines.append("sp = json.loads(Path('data/processed/phase4_splits.json').read_text())")
    lines.append("train_ids = set(sp['splits']['train'])")
    lines.append("val_ids = set(sp['splits']['val'])")
    lines.append("test_ids = set(sp['splits']['test'])")
    lines.append("# unaugmented: row.contract_id in *_ids")
    lines.append("# augmented: sp['family_to_split'][row.parent_contract_id]")
    lines.append("```")
    lines.append("")
    lines.append("## Go / no-go")
    lines.append("")
    lines.append(f"- [{'x' if not leakage else ' '}] Phase 4: stratified seed-family split locked")
    lines.append("- [ ] Phase 5: smoke train on unaugmented holdout (macro-F1)")
    lines.append("")
    lines.append("Regenerate: `python scripts/phase4_seed_family_split.py`")
    lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_SPLITS}")
    print(f"Wrote {OUT_MD}")
    print(f"Seeds train/val/test: {seed_counts}")
    print(f"Aug assigned/excluded: {sum(aug_counts.values())}/{len(aug_excluded)}")
    print(f"Leakage OK: {not leakage}")


if __name__ == "__main__":
    main()
