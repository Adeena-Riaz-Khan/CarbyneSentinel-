#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FAIL_JSONL, OUT_JSONL, SEED_MANIFEST, load_seed_manifest
from condition_rewriting import main as run_c1
from control_flow_flattening import main as run_c3
from opaque_predicate import main as run_c2


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_review(path: Path, ok_rows: list[dict], fail_rows: list[dict]) -> None:
    by_tech = Counter((r.get("transformation_techniques") or ["?"])[0] for r in ok_rows)
    by_cls = Counter(r.get("primary_vulnerability_type") for r in ok_rows)
    by_level = Counter(r.get("transformation_level") for r in ok_rows)
    lines = [
        "# Wave A–C batch review (through Level 3)",
        "",
        "## Counts",
        f"- Verified variants (benchmark): {len(ok_rows)}",
        f"- Failed / rejected log rows: {len(fail_rows)}",
        "",
        "### By technique",
    ]
    for k, v in by_tech.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### By primary class")
    for k, v in by_cls.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("### By transformation_level")
    for k, v in by_level.most_common():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "## Level meaning",
        "",
        "- Level 1 lexical = LLM/source track",
        "- Level 2 structural = GCN/fingerprint light–moderate",
        "- Level 3 control_flow = GCN hard stress (condition rewrite, opaque, flatten)",
        "",
        "## Next",
        "",
        "Level 4 data-flow (D1/D2) after demo/review of Level 3.",
        "",
        f"Outputs: `{OUT_JSONL}` / `{FAIL_JSONL}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print("=== Wave C1 condition_rewriting ===")
    run_c1()
    print("=== Wave C2 opaque_predicate ===")
    run_c2()
    print("=== Wave C3 control_flow_flattening ===")
    run_c3()

    ok_rows = load_jsonl(OUT_JSONL)
    fail_rows = load_jsonl(FAIL_JSONL)
    review = Path(__file__).resolve().parents[2] / "data" / "processed" / "augment_wave_ab_review.md"
    write_review(review, ok_rows, fail_rows)
    print()
    print("=== SUMMARY ===")
    print(f"benchmark rows: {len(ok_rows)}")
    print(f"failed rows: {len(fail_rows)}")
    print(f"review: {review}")
    c_levels = sum(1 for r in ok_rows if r.get("transformation_level") == "control_flow")
    print(f"control_flow variants: {c_levels}")
    return 0 if c_levels >= 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
