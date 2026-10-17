"""Phase 3: class weights + majority cap for v1 train set.

Reads `processed/master_dataset_phase2.json` (Phase 2 extended master).
Does not overwrite the original master.

Outputs:
  - data/processed/phase3_train_index.json   — kept contract_ids after drop+cap
  - data/processed/phase3_class_weights.json — loss weights + sampling policy
  - docs/dataset/phase3-class-weights-and-cap.md
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER_PHASE2 = ROOT / "processed" / "master_dataset_phase2.json"
OUT_INDEX = ROOT / "data" / "processed" / "phase3_train_index.json"
OUT_WEIGHTS = ROOT / "data" / "processed" / "phase3_class_weights.json"
OUT_MD = ROOT / "docs" / "dataset" / "phase3-class-weights-and-cap.md"

# Locked in Phase 1
DROP_FROM_V1 = frozenset({"short_address", "other"})
# Cap equals unique-seed target from Phase 1/2
CAP_PER_CLASS = 80
# Effective-number beta (Cui et al.); near 1.0 → stronger re-balancing
EFFECTIVE_NUM_BETA = 0.9999

CLASS_ID = {
    "reentrancy": 0,
    "integer_overflow": 1,
    "access_control": 2,
    "unchecked_call": 3,
    "time_manipulation": 4,
    "front_running": 5,
    "bad_randomness": 6,
    "denial_of_service": 7,
    "tx_origin": 9,
}


def seed_key(row: dict[str, Any]) -> str:
    return (row.get("contract_id") or "").strip()


def select_capped(rows: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    """Deterministic undersample: prefer compiled, then stable contract_id order."""
    ranked = sorted(
        rows,
        key=lambda r: (
            0 if r.get("compiled_successfully") else 1,
            seed_key(r),
        ),
    )
    return ranked[:cap]


def balanced_weights(counts: dict[str, int]) -> dict[str, float]:
    """sklearn-style: n_samples / (n_classes * n_c)."""
    n = sum(counts.values())
    k = len(counts)
    if n == 0 or k == 0:
        return {}
    return {c: round(n / (k * n_c), 6) for c, n_c in sorted(counts.items()) if n_c > 0}


def inverse_freq_weights(counts: dict[str, int]) -> dict[str, float]:
    """w_c = (1/n_c) / mean(1/n_i)  — mean-normalized inverse frequency."""
    inv = {c: 1.0 / n for c, n in counts.items() if n > 0}
    if not inv:
        return {}
    mean_inv = sum(inv.values()) / len(inv)
    return {c: round(v / mean_inv, 6) for c, v in sorted(inv.items())}


def effective_number_weights(counts: dict[str, int], beta: float) -> dict[str, float]:
    """Cui et al. effective-number class weights, mean-normalized."""
    raw: dict[str, float] = {}
    for c, n in counts.items():
        if n <= 0:
            continue
        eff = (1.0 - beta**n) / (1.0 - beta)
        raw[c] = 1.0 / eff
    if not raw:
        return {}
    mean_w = sum(raw.values()) / len(raw)
    return {c: round(v / mean_w, 6) for c, v in sorted(raw.items())}


def main() -> None:
    if not MASTER_PHASE2.is_file():
        raise SystemExit(
            f"Missing {MASTER_PHASE2}. Run scripts/phase2_mine_unique_seeds.py first."
        )

    master: list[dict[str, Any]] = json.loads(MASTER_PHASE2.read_text(encoding="utf-8"))
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in master:
        cls = r.get("primary_vulnerability_type") or "unknown"
        by_class[cls].append(r)

    dropped: dict[str, int] = {}
    for cls in DROP_FROM_V1:
        dropped[cls] = len(by_class.pop(cls, []))

    pre_cap_counts = {c: len(rows) for c, rows in sorted(by_class.items())}

    kept_rows: list[dict[str, Any]] = []
    capped_from: dict[str, dict[str, int]] = {}
    for cls, rows in sorted(by_class.items()):
        before = len(rows)
        selected = select_capped(rows, CAP_PER_CLASS) if before > CAP_PER_CLASS else list(rows)
        removed = before - len(selected)
        capped_from[cls] = {
            "before": before,
            "kept": len(selected),
            "removed": removed,
            "compiled_kept": sum(1 for r in selected if r.get("compiled_successfully")),
        }
        kept_rows.extend(selected)

    post_counts = Counter(r["primary_vulnerability_type"] for r in kept_rows)
    post_dict = {c: post_counts[c] for c in sorted(post_counts)}

    w_balanced = balanced_weights(post_dict)
    w_inv = inverse_freq_weights(post_dict)
    w_eff = effective_number_weights(post_dict, EFFECTIVE_NUM_BETA)

    # Recommended default: balanced (post-cap nearly uniform → weights ≈ 1)
    recommended = "balanced"
    class_ids = {c: CLASS_ID[c] for c in post_dict if c in CLASS_ID}
    weight_vector = [0.0] * (max(CLASS_ID.values()) + 1)
    for c, w in w_balanced.items():
        if c in CLASS_ID:
            weight_vector[CLASS_ID[c]] = w

    train_ids = sorted(seed_key(r) for r in kept_rows)
    excluded_ids = sorted(
        seed_key(r)
        for cls, rows in by_class.items()
        for r in rows
        if seed_key(r) not in set(train_ids)
    )
    # Also list dropped-class ids
    drop_ids = []
    full_by = defaultdict(list)
    for r in master:
        full_by[r.get("primary_vulnerability_type") or "unknown"].append(r)
    for cls in DROP_FROM_V1:
        for r in full_by.get(cls, []):
            drop_ids.append(seed_key(r))

    index = {
        "source_master": MASTER_PHASE2.relative_to(ROOT).as_posix(),
        "policy": {
            "drop_classes": sorted(DROP_FROM_V1),
            "cap_per_class": CAP_PER_CLASS,
            "cap_selection": "prefer compiled_successfully=True, then contract_id asc",
        },
        "n_source_rows": len(master),
        "n_train_rows": len(kept_rows),
        "n_dropped_class_rows": sum(dropped.values()),
        "n_capped_away_rows": sum(v["removed"] for v in capped_from.values()),
        "counts_pre_cap": pre_cap_counts,
        "counts_post_cap": post_dict,
        "cap_detail": capped_from,
        "dropped_class_counts": dropped,
        "train_contract_ids": train_ids,
        "capped_away_contract_ids": excluded_ids,
        "dropped_class_contract_ids": sorted(drop_ids),
    }

    weights = {
        "source_master": MASTER_PHASE2.relative_to(ROOT).as_posix(),
        "train_index": OUT_INDEX.relative_to(ROOT).as_posix(),
        "policy": {
            "drop_classes": sorted(DROP_FROM_V1),
            "cap_per_class": CAP_PER_CLASS,
            "recommended_weight_scheme": recommended,
            "effective_number_beta": EFFECTIVE_NUM_BETA,
            "notes": [
                "Compute weights on the post-cap train index (not raw master).",
                "Augmented variants should attach to parent seeds already in the train index; "
                "do not re-introduce capped-away parents via aug.",
                "Use weight_vector_by_class_id with CrossEntropyLoss(weight=...) when class ids match CLASS_ID.",
            ],
        },
        "class_id_map": class_ids,
        "counts_post_cap": post_dict,
        "weights_balanced": w_balanced,
        "weights_inverse_freq": w_inv,
        "weights_effective_number": w_eff,
        "weight_vector_by_class_id": weight_vector,
        "max_min_ratio_pre_cap": (
            round(max(pre_cap_counts.values()) / max(min(pre_cap_counts.values()), 1), 3)
            if pre_cap_counts
            else None
        ),
        "max_min_ratio_post_cap": (
            round(max(post_dict.values()) / max(min(post_dict.values()), 1), 3)
            if post_dict
            else None
        ),
    }

    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    OUT_WEIGHTS.write_text(json.dumps(weights, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Phase 3 — Class weights & majority cap")
    lines.append("")
    lines.append("**Status:** LOCKED sampling policy for v1 train.")
    lines.append("")
    lines.append(f"**Source:** `{MASTER_PHASE2.relative_to(ROOT).as_posix()}` ({len(master)} rows)")
    lines.append(f"**Train index:** `{OUT_INDEX.relative_to(ROOT).as_posix()}` ({len(kept_rows)} rows)")
    lines.append(f"**Weights:** `{OUT_WEIGHTS.relative_to(ROOT).as_posix()}`")
    lines.append("")
    lines.append("## Locked decisions")
    lines.append("")
    lines.append("| Rule | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Drop from v1 train | `{', '.join(sorted(DROP_FROM_V1))}` |")
    lines.append(f"| Cap per class | **{CAP_PER_CLASS}** unique seeds |")
    lines.append("| Cap selection | Prefer `compiled_successfully=True`, then `contract_id` ascending (deterministic) |")
    lines.append(f"| Recommended loss weights | **{recommended}** = `n / (K · n_c)` on post-cap counts |")
    lines.append("| Augmentation | Only from parents in the train index; never revive capped-away seeds |")
    lines.append("")
    lines.append("## Why cap then weight")
    lines.append("")
    lines.append(
        f"After Phase 2, most kept classes sit at {CAP_PER_CLASS} seeds; "
        "`unchecked_call` remains at 152. Cap removes majority headroom so "
        "macro-F1 is not dominated by one class. Post-cap counts are nearly "
        "uniform, so balanced weights stay close to 1.0 — still emit the vector "
        "so the trainer has a stable contract."
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| class | pre-cap | kept | removed | compiled kept |")
    lines.append("|-------|--------:|-----:|--------:|--------------:|")
    for cls in sorted(set(pre_cap_counts) | set(post_dict)):
        d = capped_from.get(cls, {"before": 0, "kept": 0, "removed": 0, "compiled_kept": 0})
        lines.append(
            f"| `{cls}` | {d['before']} | {d['kept']} | {d['removed']} | {d['compiled_kept']} |"
        )
    for cls, n in sorted(dropped.items()):
        lines.append(f"| `{cls}` (dropped) | {n} | 0 | {n} | — |")
    lines.append("")
    lines.append(
        f"**Imbalance ratio** max/min: pre-cap "
        f"**{weights['max_min_ratio_pre_cap']}** → post-cap "
        f"**{weights['max_min_ratio_post_cap']}**"
    )
    lines.append("")
    lines.append("## Class weights (post-cap)")
    lines.append("")
    lines.append("| class | n | balanced | inverse_freq | effective_number |")
    lines.append("|-------|--:|---------:|-------------:|-----------------:|")
    for cls in sorted(post_dict):
        lines.append(
            f"| `{cls}` | {post_dict[cls]} | {w_balanced[cls]} | "
            f"{w_inv[cls]} | {w_eff[cls]} |"
        )
    lines.append("")
    lines.append("### Trainer hook")
    lines.append("")
    lines.append("```python")
    lines.append("import json")
    lines.append("from pathlib import Path")
    lines.append("cfg = json.loads(Path('data/processed/phase3_class_weights.json').read_text())")
    lines.append("idx = json.loads(Path('data/processed/phase3_train_index.json').read_text())")
    lines.append("keep = set(idx['train_contract_ids'])")
    lines.append("weight = torch.tensor(cfg['weight_vector_by_class_id'], dtype=torch.float)")
    lines.append("# CrossEntropyLoss(weight=weight)  # index = vulnerability_class_id")
    lines.append("```")
    lines.append("")
    lines.append("## Go / no-go")
    lines.append("")
    lines.append("- [x] Phase 3: drop + cap + weight config written")
    lines.append("- [ ] Phase 4: seed-family stratified split (train/val/test) using `phase3_train_index.json`")
    lines.append("- [ ] Phase 5: smoke train on unaugmented holdout (macro-F1)")
    lines.append("")
    lines.append("Regenerate: `python scripts/phase3_class_weights_and_cap.py`")
    lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_INDEX}")
    print(f"Wrote {OUT_WEIGHTS}")
    print(f"Wrote {OUT_MD}")
    print(f"Train rows: {len(kept_rows)} (dropped classes {sum(dropped.values())}, "
          f"capped away {sum(v['removed'] for v in capped_from.values())})")
    print(
        f"max/min ratio: {weights['max_min_ratio_pre_cap']} -> {weights['max_min_ratio_post_cap']}"
    )
    print("Post-cap counts:", dict(post_dict))


if __name__ == "__main__":
    main()
