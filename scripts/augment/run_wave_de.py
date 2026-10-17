#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FAIL_JSONL, OUT_JSONL, PROCESSED, load_master
from equiv_expr_decomposition import main as run_d2
from irrelevant_helper_insertion import main as run_e1
from temp_var_introduction import main as run_d1
from unrelated_state_var_insertion import main as run_e2


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_review(path: Path, ok_rows: list[dict], fail_rows: list[dict]) -> None:
    by_tech = Counter((r.get("transformation_techniques") or ["?"])[0] for r in ok_rows)
    by_cls = Counter(r.get("primary_vulnerability_type") for r in ok_rows)
    by_level = Counter(r.get("transformation_level") for r in ok_rows)
    master = load_master()
    m = Counter(r.get("primary_vulnerability_type") for r in master)
    combined = m + by_cls
    lines = [
        "# Wave A-E batch review (full severity ladder singles)",
        "",
        f"- Verified variants: {len(ok_rows)}",
        f"- Failed log rows: {len(fail_rows)}",
        "",
        "### By technique",
    ]
    for k, v in by_tech.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### Augment variants by class")
    for k, v in by_cls.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### By level")
    for k, v in by_level.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### Class imbalance: master vs combined (master + variants)")
    lines.append("")
    lines.append("| class | master | combined | delta |")
    lines.append("|---|---:|---:|---:|")
    for cls, cv in combined.most_common():
        mv = m.get(cls, 0)
        lines.append(f"| {cls} | {mv} | {cv} | +{cv - mv} |")
    lines += [
        "",
        "Thin classes were seeded first for D/E waves.",
        "Singles ladder A-E complete; stacked techniques are optional next.",
        "",
        f"Outputs: `{OUT_JSONL}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print("=== D1 temp_var_introduction ===")
    run_d1()
    print("=== D2 equiv_expr_decomposition ===")
    run_d2()
    print("=== E1 irrelevant_helper_insertion ===")
    run_e1()
    print("=== E2 unrelated_state_var_insertion ===")
    run_e2()

    ok_rows = load_jsonl(OUT_JSONL)
    fail_rows = load_jsonl(FAIL_JSONL)
    review = Path(__file__).resolve().parents[2] / "data" / "processed" / "augment_wave_ab_review.md"
    write_review(review, ok_rows, fail_rows)
    print()
    print("=== SUMMARY ===")
    print(f"benchmark rows: {len(ok_rows)}")
    print(review.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
