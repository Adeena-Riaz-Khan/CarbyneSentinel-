#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comment_manipulation import apply_comment_manipulation
from common import (
    FAIL_JSONL,
    OUT_JSONL,
    append_jsonl,
    build_record,
    compile_source,
    load_master,
    make_variant_id,
    pick_imbalance_seeds,
    resolve_source_path,
    save_variant_artifacts,
)
from condition_rewriting import apply_condition_rewriting
from dead_code_insertion import insert_dead_code
from function_extraction import apply_function_extraction
from identifier_renaming import apply_identifier_renaming
from irrelevant_helper_insertion import apply_irrelevant_helper_insertion
from literal_format_rewrite import apply_literal_format_rewrite
from opaque_predicate import apply_opaque_predicate
from temp_var_introduction import apply_temp_var_introduction
from unrelated_state_var_insertion import apply_unrelated_state_var_insertion

ApplyFn = Callable[[str], tuple[str, int]]

LEVEL_RANK = {
    "lexical": 1,
    "structural": 2,
    "control_flow": 3,
    "data_flow": 4,
    "contract_level": 5,
}
SEVERITY_RANK = {"light": 1, "moderate": 2, "aggressive": 3}


def _apply_dead(source: str) -> tuple[str, int]:
    out = insert_dead_code(source)
    return out, 1 if out != source and "__aug_dead_noop_42" in out else 0


TECH_META = {
    "identifier_renaming": ("lexical", "light", apply_identifier_renaming),
    "comment_manipulation": ("lexical", "light", apply_comment_manipulation),
    "literal_format_rewrite": ("lexical", "light", apply_literal_format_rewrite),
    "dead_code_insertion": ("structural", "light", _apply_dead),
    "function_extraction": ("structural", "moderate", apply_function_extraction),
    "condition_rewriting": ("control_flow", "moderate", apply_condition_rewriting),
    "opaque_predicate": ("control_flow", "moderate", apply_opaque_predicate),
    "temp_var_introduction": ("data_flow", "moderate", apply_temp_var_introduction),
    "irrelevant_helper_insertion": ("contract_level", "aggressive", apply_irrelevant_helper_insertion),
    "unrelated_state_var_insertion": ("contract_level", "aggressive", apply_unrelated_state_var_insertion),
}

STACKS: list[tuple[str, ...]] = [
    ("comment_manipulation", "dead_code_insertion"),
    ("identifier_renaming", "dead_code_insertion"),
    ("literal_format_rewrite", "function_extraction"),
    ("dead_code_insertion", "opaque_predicate"),
    ("comment_manipulation", "condition_rewriting"),
    ("temp_var_introduction", "unrelated_state_var_insertion"),
    ("dead_code_insertion", "irrelevant_helper_insertion"),
    ("opaque_predicate", "unrelated_state_var_insertion"),
    ("identifier_renaming", "temp_var_introduction"),
    ("condition_rewriting", "irrelevant_helper_insertion"),
    ("literal_format_rewrite", "opaque_predicate"),
    ("comment_manipulation", "unrelated_state_var_insertion"),
    ("function_extraction", "unrelated_state_var_insertion"),
    ("identifier_renaming", "condition_rewriting"),
]

TRIPLE_STACKS: list[tuple[str, ...]] = [
    ("comment_manipulation", "dead_code_insertion", "opaque_predicate"),
    ("identifier_renaming", "temp_var_introduction", "unrelated_state_var_insertion"),
    ("literal_format_rewrite", "function_extraction", "irrelevant_helper_insertion"),
    ("comment_manipulation", "condition_rewriting", "unrelated_state_var_insertion"),
    ("dead_code_insertion", "opaque_predicate", "irrelevant_helper_insertion"),
]


def stack_id(techs: Sequence[str]) -> str:
    """Short filesystem-safe id (Windows MAX_PATH); full tech list lives in JSONL."""
    digest = hashlib.sha1("+".join(techs).encode("utf-8")).hexdigest()[:10]
    return f"stack{len(techs)}_{digest}"


def max_meta(techs: Sequence[str], idx: int) -> str:
    best = TECH_META[techs[0]][idx]
    rank = LEVEL_RANK if idx == 0 else SEVERITY_RANK
    for t in techs[1:]:
        cur = TECH_META[t][idx]
        if rank[cur] > rank[best]:
            best = cur
    return best


def existing_stack_keys() -> set[str]:
    keys: set[str] = set()
    if not OUT_JSONL.is_file():
        return keys
    with OUT_JSONL.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            techs = r.get("transformation_techniques") or []
            if len(techs) >= 2:
                keys.add(f"{r.get('parent_contract_id')}::{'+'.join(techs)}")
    return keys


def pick_classes(classes: list[str], n_each: int = 30) -> list[dict]:
    master = load_master()
    out: list[dict] = []
    seen: set[str] = set()
    for cls in classes:
        rows = [
            r
            for r in master
            if r.get("primary_vulnerability_type") == cls
            and r.get("compiled_successfully")
            and resolve_source_path(r).is_file()
        ]
        for r in rows[:n_each]:
            if r["contract_id"] not in seen:
                seen.add(r["contract_id"])
                out.append(r)
    return out


def apply_stack_chain(source: str, techs: Sequence[str]) -> tuple[str, list[int]]:
    text = source
    counts: list[int] = []
    for t in techs:
        fn = TECH_META[t][2]
        new_text, n = fn(text)
        if n <= 0 or new_text == text:
            return source, counts + [0]
        counts.append(n)
        text = new_text
    return text, counts


def process_stack(parent: dict, techs: Sequence[str], idx: int = 1) -> dict:
    sid = stack_id(techs)
    src_path = resolve_source_path(parent)
    original = src_path.read_text(encoding="utf-8", errors="replace")
    transformed, counts = apply_stack_chain(original, techs)
    # Keep contract_id readable but short enough for Windows paths
    parent_short = parent["contract_id"]
    if len(parent_short) > 48:
        parent_short = parent_short[:40] + hashlib.sha1(parent_short.encode()).hexdigest()[:8]
    variant_id = make_variant_id(parent_short, sid, idx)
    level = max_meta(techs, 0)
    severity = max_meta(techs, 1)
    version = parent.get("compiler_version") or "0.5.17"
    ok, bytecode, cnote = compile_source(transformed, version)
    notes = f"stack={'+'.join(techs)}; counts={counts}; {cnote}"
    exploit_verified = bool(
        ok
        and len(counts) == len(techs)
        and all(c > 0 for c in counts)
        and transformed != original
    )
    source_rel, bytecode_rel = save_variant_artifacts(
        technique=sid,
        variant_id=variant_id,
        source_text=transformed,
        bytecode_hex=bytecode if ok else None,
    )
    rec = build_record(
        parent=parent,
        technique=sid,
        level=level,
        severity=severity,
        variant_id=variant_id,
        source_rel=source_rel,
        bytecode_rel=bytecode_rel,
        compiler_version=version,
        compiled_ok=ok,
        exploit_verified=exploit_verified,
        notes=notes,
        techniques=list(techs),
    )
    if exploit_verified:
        append_jsonl(OUT_JSONL, rec)
        return {"status": "OK", "record": rec}
    append_jsonl(FAIL_JSONL, rec)
    return {"status": "FAIL", "record": rec}


def write_review(path: Path) -> None:
    ok_rows = []
    fail_n = 0
    if OUT_JSONL.is_file():
        for line in OUT_JSONL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ok_rows.append(json.loads(line))
    if FAIL_JSONL.is_file():
        fail_n = sum(1 for line in FAIL_JSONL.read_text(encoding="utf-8").splitlines() if line.strip())

    by_tech = Counter()
    stacks = 0
    triples = 0
    for r in ok_rows:
        techs = r.get("transformation_techniques") or ["?"]
        if len(techs) >= 2:
            stacks += 1
            if len(techs) >= 3:
                triples += 1
            by_tech["+".join(techs)] += 1
        else:
            by_tech[techs[0]] += 1
    by_cls = Counter(r.get("primary_vulnerability_type") for r in ok_rows)
    by_level = Counter(r.get("transformation_level") for r in ok_rows)
    master = load_master()
    m = Counter(r.get("primary_vulnerability_type") for r in master)
    combined = m + by_cls

    lines = [
        "# Wave A-E + stacks batch review",
        "",
        f"- Verified variants: {len(ok_rows)}",
        f"- Of which stacked (2+ techniques): {stacks}",
        f"- Of which triple stacks: {triples}",
        f"- Failed log rows: {fail_n}",
        "",
        "### By technique / stack",
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
    lines.append("### Class imbalance: master vs combined")
    lines.append("")
    lines.append("| class | master | combined | delta |")
    lines.append("|---|---:|---:|---:|")
    for cls, cv in combined.most_common():
        mv = m.get(cls, 0)
        lines.append(f"| {cls} | {mv} | {cv} | +{cv - mv} |")
    lines += [
        "",
        "Singles A-E + 2/3-technique stacks for minority rebalance and evasion stress.",
        "",
        f"Outputs: `{OUT_JSONL}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_stacks(
    seeds: list[dict],
    stack_list: list[tuple[str, ...]],
    *,
    target_ok: int,
    max_per_stack: int,
    done: set[str],
) -> tuple[int, int]:
    ok_n = fail_n = 0
    for techs in stack_list:
        if ok_n >= target_ok:
            break
        stack_ok = 0
        for s in seeds:
            if ok_n >= target_ok or stack_ok >= max_per_stack:
                break
            key = f"{s['contract_id']}::{'+'.join(techs)}"
            if key in done:
                continue
            r = process_stack(s, techs)
            cls = s.get("primary_vulnerability_type")
            print(f"  [{r['status']}] {r['record']['contract_id']} ({cls})")
            if r["status"] == "OK":
                ok_n += 1
                stack_ok += 1
                done.add(key)
            else:
                fail_n += 1
    return ok_n, fail_n


def main() -> int:
    ap = argparse.ArgumentParser(description="Stacked multi-technique augmentation")
    ap.add_argument("--target-ok", type=int, default=40)
    ap.add_argument("--max-per-stack", type=int, default=6)
    ap.add_argument(
        "--classes",
        type=str,
        default="",
        help="Comma-separated class filter (default: imbalance seeds)",
    )
    ap.add_argument("--triples", action="store_true", help="Also run 3-technique stacks")
    ap.add_argument("--triples-only", action="store_true")
    args = ap.parse_args()

    if args.classes:
        class_list = [c.strip() for c in args.classes.split(",") if c.strip()]
        seeds = pick_classes(class_list, n_each=40)
    else:
        seeds = pick_imbalance_seeds(extra_minority=25, reentrancy=5)
        seeds = seeds + pick_classes(["access_control"], n_each=15)

    seen = set()
    uniq = []
    for s in seeds:
        cid = s["contract_id"]
        if cid not in seen:
            seen.add(cid)
            uniq.append(s)

    done = existing_stack_keys()
    total_ok = total_fail = 0

    if not args.triples_only:
        print(f"[info] 2-tech stacks seeds={len(uniq)} target={args.target_ok}")
        ok, fail = run_stacks(
            uniq,
            STACKS,
            target_ok=args.target_ok,
            max_per_stack=args.max_per_stack,
            done=done,
        )
        total_ok += ok
        total_fail += fail

    if args.triples or args.triples_only:
        t_target = 15 if args.triples_only else max(15, args.target_ok // 2)
        print(f"[info] 3-tech stacks seeds={len(uniq)} target={t_target}")
        ok, fail = run_stacks(
            uniq,
            TRIPLE_STACKS,
            target_ok=t_target,
            max_per_stack=max(3, args.max_per_stack // 2),
            done=done,
        )
        total_ok += ok
        total_fail += fail

    review = Path(__file__).resolve().parents[2] / "data" / "processed" / "augment_wave_ab_review.md"
    write_review(review)
    print()
    print(f"[done] OK={total_ok} FAIL={total_fail}")
    print(f"review: {review}")
    return 0 if total_ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
