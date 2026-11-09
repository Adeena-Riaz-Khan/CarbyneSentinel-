from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "features"))
sys.path.insert(0, str(ROOT / "scripts"))

from cfg import build_cfg
from disasm import disassemble, parse_hex
from fingerprint_v0 import (
    bytecode_shannon_entropy,
    jump_features,
    opcode_shannon_entropy,
)
from opcode_freq import opcode_feature_names, opcode_frequency_ratios

MASTER_PATH = ROOT / "processed" / "master_dataset_phase2.json"
SPLITS_PATH = ROOT / "data" / "processed" / "phase4_splits.json"
RECOVERY_LOG = ROOT / "processed" / "logs" / "bytecode_recovery_log.json"
OUT_DIR = ROOT / "processed" / "features" / "phase5"

STAGE_C_PILOT_IDS = {
    "DAPPSCAN_QuillAudits-Yearn_Finance-ySwaps_Keep3rV1Helper",
    "DAPPSCAN_QuillAudits-Yearn_Finance-ySwaps_StrategyCurveGUSDProxy",
}

NINE_CLASSES = [
    "access_control",
    "bad_randomness",
    "denial_of_service",
    "front_running",
    "integer_overflow",
    "reentrancy",
    "time_manipulation",
    "tx_origin",
    "unchecked_call",
]

FINGERPRINT_NAMES = [
    "bytecode_size_bytes",
    "bytecode_shannon_entropy",
    "total_instruction_count",
    "jump_count",
    "jumpi_count",
    "total_jump_count",
    "jump_ratio",
    "conditional_jump_ratio",
    "unconditional_jump_ratio",
]

EXTRA_NAMES = [
    "opcode_shannon_entropy",
    "cfg_block_count",
    "cfg_edge_count",
    "cfg_resolved_jumps",
    "cfg_unresolved_jumps",
]


def feature_names() -> list[str]:
    return FINGERPRINT_NAMES + EXTRA_NAMES + opcode_feature_names()


def load_recovery_reasons() -> dict[str, str]:
    generic_reasons = {"unknown", "unavailable_bytecode", "recovery_failed", "failed", "deferred"}
    audit_specific = {}
    run_specific = {}
    fallback = {}
    if not RECOVERY_LOG.is_file():
        return {}
    payload = json.loads(RECOVERY_LOG.read_text(encoding="utf-8"))
    for audit in payload.get("audits", []):
        for row in audit.get("unavailable", []) or []:
            cid = row.get("contract_id")
            reason = (row.get("reason") or "").strip()
            if not cid or not reason:
                continue
            if reason not in generic_reasons:
                audit_specific[cid] = reason
            elif cid not in fallback:
                fallback[cid] = reason
    for run in payload.get("runs", []):
        for entry in run.get("entries", []):
            cid = entry.get("contract_id")
            if not cid or entry.get("success"):
                continue
            fr = (entry.get("failure_reason") or entry.get("detail") or "").strip()
            st = (entry.get("status") or "").strip()
            if fr and fr not in generic_reasons:
                run_specific[cid] = fr
            elif st and cid not in fallback:
                fallback[cid] = st
    reasons = {}
    all_ids = set(fallback) | set(run_specific) | set(audit_specific)
    for cid in all_ids:
        if cid in audit_specific:
            reasons[cid] = audit_specific[cid]
        elif cid in run_specific:
            reasons[cid] = run_specific[cid]
        else:
            reasons[cid] = fallback.get(cid) or "unavailable_bytecode"
    return reasons


def split_maps(splits: dict) -> tuple[dict[str, str], dict[str, str]]:
    id_to_split = {}
    id_to_family = {}
    for name in ("train", "val", "test"):
        for cid in splits["splits"][name]:
            id_to_split[cid] = name
    family_to_split = splits.get("family_to_split") or {}
    for fam, split_name in family_to_split.items():
        id_to_family[fam] = split_name
    return id_to_split, family_to_split


def family_id(row: dict) -> str:
    parent = (row.get("parent_contract_id") or "").strip()
    if parent:
        return parent
    return (row.get("contract_id") or "").strip()


def read_bytecode(row: dict) -> str:
    rel = row.get("bytecode_path")
    if not rel:
        raise ValueError("missing_bytecode_path")
    path = ROOT / "processed" / rel
    if not path.is_file():
        raise ValueError("missing_bytecode_artifact")
    text = path.read_text(encoding="utf-8").strip()
    if text == "":
        raise ValueError("empty_bytecode")
    return text


def extract_vector(row: dict) -> tuple[list[float], dict]:
    bytecode = read_bytecode(row)
    data = parse_hex(bytecode)
    if len(data) == 0:
        raise ValueError("empty_bytecode")
    instructions = disassemble(bytecode)
    if not instructions:
        raise ValueError("disassembly_empty")

    size, byte_entropy = bytecode_shannon_entropy(bytecode)
    jumps = jump_features(instructions)
    if jumps["total_jump_count"] != jumps["jump_count"] + jumps["jumpi_count"]:
        raise ValueError("jump_count_inconsistency")

    try:
        op_entropy = opcode_shannon_entropy(instructions)
    except ValueError as exc:
        raise ValueError(f"opcode_entropy_failure: {exc}") from exc

    try:
        cfg = build_cfg(instructions)
        cfg_stats = cfg["stats"]
    except Exception as exc:
        raise ValueError(f"cfg_extraction_failure: {exc}") from exc

    ratios = opcode_frequency_ratios(instructions)

    values = {
        "bytecode_size_bytes": float(size),
        "bytecode_shannon_entropy": float(byte_entropy),
        "total_instruction_count": float(jumps["total_instruction_count"]),
        "jump_count": float(jumps["jump_count"]),
        "jumpi_count": float(jumps["jumpi_count"]),
        "total_jump_count": float(jumps["total_jump_count"]),
        "jump_ratio": float(jumps["jump_ratio"]),
        "conditional_jump_ratio": float(jumps["conditional_jump_ratio"]),
        "unconditional_jump_ratio": float(jumps["unconditional_jump_ratio"]),
        "opcode_shannon_entropy": float(op_entropy),
        "cfg_block_count": float(cfg_stats["block_count"]),
        "cfg_edge_count": float(cfg_stats["edge_count"]),
        "cfg_resolved_jumps": float(cfg_stats["resolved_jumps"]),
        "cfg_unresolved_jumps": float(cfg_stats["unresolved_jumps"]),
        **{k: float(v) for k, v in ratios.items()},
    }

    names = feature_names()
    vector = []
    for name in names:
        if name not in values:
            raise ValueError(f"missing_feature_column: {name}")
        value = values[name]
        if not math.isfinite(value):
            raise ValueError(f"non_finite_feature: {name}")
        vector.append(value)

    meta = {
        "instruction_count": len(instructions),
        "bytecode_bytes": len(data),
    }
    return vector, meta


def validate_matrix(
    X: np.ndarray,
    feature_name_list: list[str],
    records: list[dict],
    exclusions: list[dict],
    splits: dict,
    master_by_id: dict[str, dict],
) -> dict:
    issues = []
    locked = []
    for name in ("train", "val", "test"):
        locked.extend(splits["splits"][name])
    locked_set = set(locked)
    if len(locked) != 720:
        issues.append(f"locked_count_expected_720_got_{len(locked)}")
    if len(locked_set) != 720:
        issues.append("duplicate_or_cross_split_locked_ids")

    id_to_split = {}
    for name in ("train", "val", "test"):
        for cid in splits["splits"][name]:
            if cid in id_to_split:
                issues.append(f"id_in_multiple_splits:{cid}")
            id_to_split[cid] = name

    featurized_ids = [r["contract_id"] for r in records]
    if len(featurized_ids) != len(set(featurized_ids)):
        issues.append("duplicate_featurized_ids")

    for cid in featurized_ids:
        if cid not in locked_set:
            issues.append(f"outside_locked_split:{cid}")
        if cid in STAGE_C_PILOT_IDS:
            issues.append(f"stage_c_pilot_included:{cid}")

    accounted = set(featurized_ids) | {e["contract_id"] for e in exclusions}
    missing_accounted = sorted(locked_set - accounted)
    extra_accounted = sorted(accounted - locked_set)
    if missing_accounted:
        issues.append(f"unaccounted_locked_ids:{len(missing_accounted)}")
    if extra_accounted:
        issues.append(f"extra_nonlocked_ids:{len(extra_accounted)}")

    if X.shape[0] != len(records):
        issues.append("matrix_row_count_mismatch")
    if X.shape[1] != len(feature_name_list):
        issues.append("matrix_col_count_mismatch")

    if not np.isfinite(X).all():
        issues.append("non_finite_values_present")

    op_names = [n for n in feature_name_list if n.startswith("op_ratio_")]
    op_idx = [feature_name_list.index(n) for n in op_names]
    entropy_idx = feature_name_list.index("bytecode_shannon_entropy")
    op_ent_idx = feature_name_list.index("opcode_shannon_entropy")
    jump_idx = feature_name_list.index("jump_count")
    jumpi_idx = feature_name_list.index("jumpi_count")
    total_jump_idx = feature_name_list.index("total_jump_count")
    jump_ratio_idx = feature_name_list.index("jump_ratio")
    instr_idx = feature_name_list.index("total_instruction_count")

    range_issues = 0
    ratio_sum_issues = 0
    for i in range(X.shape[0]):
        row = X[i]
        if row[entropy_idx] < 0 or row[entropy_idx] > 8:
            range_issues += 1
        if row[op_ent_idx] < 0 or row[op_ent_idx] > 8:
            range_issues += 1
        if abs(row[total_jump_idx] - (row[jump_idx] + row[jumpi_idx])) > 1e-9:
            range_issues += 1
        for j in op_idx:
            if row[j] < 0 or row[j] > 1:
                range_issues += 1
        if row[instr_idx] > 0:
            op_sum = float(np.sum(row[op_idx]))
            if abs(op_sum - 1.0) > 1e-3:
                ratio_sum_issues += 1
        for name in (
            "jump_ratio",
            "conditional_jump_ratio",
            "unconditional_jump_ratio",
        ):
            idx = feature_name_list.index(name)
            if row[idx] < 0 or row[idx] > 1:
                range_issues += 1

    if range_issues:
        issues.append(f"invalid_feature_ranges:{range_issues}")
    if ratio_sum_issues:
        issues.append(f"opcode_ratio_sum_issues:{ratio_sum_issues}")

    family_to_split = splits.get("family_to_split") or {}
    leakage = []
    for cid in featurized_ids:
        row = master_by_id[cid]
        fam = family_id(row)
        expected = family_to_split.get(fam)
        actual = id_to_split[cid]
        if expected is not None and expected != actual:
            leakage.append({"contract_id": cid, "family": fam, "expected": expected, "actual": actual})

    vectors = [tuple(X[i].tolist()) for i in range(X.shape[0])]
    counts = Counter(vectors)
    duplicate_groups = sum(1 for _v, c in counts.items() if c > 1)
    duplicate_rows = sum(c for _v, c in counts.items() if c > 1)

    class_dist = {}
    for name in ("train", "val", "test"):
        class_dist[name] = dict(
            sorted(
                Counter(
                    r["label"] for r in records if r["split"] == name
                ).items()
            )
        )

    test_missing = [c for c in NINE_CLASSES if class_dist["test"].get(c, 0) == 0]
    stage_c_excluded = all(cid not in featurized_ids for cid in STAGE_C_PILOT_IDS)

    return {
        "ok": len(issues) == 0 and len(leakage) == 0 and not test_missing,
        "issues": issues,
        "family_leakage_rows": leakage,
        "leakage_ok_file_flag": splits.get("leakage_ok"),
        "duplicate_feature_vector_groups": duplicate_groups,
        "duplicate_feature_vector_rows": duplicate_rows,
        "class_distribution": class_dist,
        "test_classes_missing": test_missing,
        "stage_c_pilot_excluded": stage_c_excluded,
        "accounted_locked_ids": len(accounted),
        "featurized": len(records),
        "excluded": len(exclusions),
        "nan_inf_present": bool(issues and any("non_finite" in x for x in issues)),
        "opcode_ratio_sum_issues": ratio_sum_issues,
        "invalid_feature_range_rows": range_issues,
    }


def main() -> int:
    master_rows = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    master_by_id = {r["contract_id"]: r for r in master_rows}
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    recovery_reasons = load_recovery_reasons()
    names = feature_names()

    records = []
    exclusions = []
    X_rows = []

    for split_name in ("train", "val", "test"):
        for cid in splits["splits"][split_name]:
            if cid in STAGE_C_PILOT_IDS:
                exclusions.append(
                    {
                        "contract_id": cid,
                        "split": split_name,
                        "label": master_by_id.get(cid, {}).get("primary_vulnerability_type"),
                        "parent_contract_id": master_by_id.get(cid, {}).get("parent_contract_id"),
                        "reason": "stage_c_pilot_excluded_by_policy",
                        "category": "policy_exclusion",
                    }
                )
                continue

            row = master_by_id.get(cid)
            if row is None:
                exclusions.append(
                    {
                        "contract_id": cid,
                        "split": split_name,
                        "label": None,
                        "parent_contract_id": None,
                        "reason": "missing_from_master",
                        "category": "missing_master_record",
                    }
                )
                continue

            label = row.get("primary_vulnerability_type")
            parent = row.get("parent_contract_id")
            bp = row.get("bytecode_path")
            has_file = bool(bp) and (ROOT / "processed" / bp).is_file()
            if not has_file:
                reason = recovery_reasons.get(cid)
                if not reason:
                    if not bp:
                        reason = "missing_bytecode_path"
                    else:
                        reason = "missing_bytecode_artifact"
                exclusions.append(
                    {
                        "contract_id": cid,
                        "split": split_name,
                        "label": label,
                        "parent_contract_id": parent,
                        "bytecode_path": bp,
                        "reason": reason,
                        "category": "unavailable_bytecode",
                    }
                )
                continue

            try:
                vector, extract_meta = extract_vector(row)
            except ValueError as exc:
                exclusions.append(
                    {
                        "contract_id": cid,
                        "split": split_name,
                        "label": label,
                        "parent_contract_id": parent,
                        "bytecode_path": bp,
                        "reason": str(exc),
                        "category": "feature_extraction_failure",
                    }
                )
                continue
            except Exception as exc:
                exclusions.append(
                    {
                        "contract_id": cid,
                        "split": split_name,
                        "label": label,
                        "parent_contract_id": parent,
                        "bytecode_path": bp,
                        "reason": f"unexpected_extraction_error: {exc}",
                        "category": "feature_extraction_failure",
                    }
                )
                continue

            recovery = row.get("bytecode_recovery") or {}
            records.append(
                {
                    "contract_id": cid,
                    "split": split_name,
                    "label": label,
                    "parent_contract_id": parent,
                    "family_id": family_id(row),
                    "source_dataset": row.get("source_dataset"),
                    "compiler_version": row.get("compiler_version"),
                    "bytecode_path": bp,
                    "bytecode_recovery": recovery,
                    "instruction_count": extract_meta["instruction_count"],
                    "bytecode_bytes": extract_meta["bytecode_bytes"],
                }
            )
            X_rows.append(vector)

    X = np.asarray(X_rows, dtype=np.float64)
    validation = validate_matrix(X, names, records, exclusions, splits, master_by_id)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT_DIR / "feature_matrix.npz",
        X=X,
        feature_names=np.array(names, dtype=object),
        contract_ids=np.array([r["contract_id"] for r in records], dtype=object),
        labels=np.array([r["label"] for r in records], dtype=object),
        splits=np.array([r["split"] for r in records], dtype=object),
    )

    meta = {
        "locked_ids": 720,
        "usable_bytecode_expected": 662,
        "successfully_featurized": len(records),
        "excluded_total": len(exclusions),
        "excluded_unavailable_bytecode": sum(
            1 for e in exclusions if e.get("category") == "unavailable_bytecode"
        ),
        "excluded_feature_failures": sum(
            1 for e in exclusions if e.get("category") == "feature_extraction_failure"
        ),
        "excluded_policy": sum(
            1 for e in exclusions if e.get("category") == "policy_exclusion"
        ),
        "matrix_shape": [int(X.shape[0]), int(X.shape[1])],
        "feature_names": names,
        "feature_count": len(names),
        "fingerprint_features": FINGERPRINT_NAMES,
        "extra_features": EXTRA_NAMES,
        "opcode_features": opcode_feature_names(),
        "nine_classes": NINE_CLASSES,
        "stage_c_pilot_ids_excluded": sorted(STAGE_C_PILOT_IDS),
        "split_counts_featurized": {
            name: sum(1 for r in records if r["split"] == name)
            for name in ("train", "val", "test")
        },
        "records": records,
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "exclusions.json").write_text(
        json.dumps(
            {
                "count": len(exclusions),
                "by_category": dict(Counter(e.get("category") for e in exclusions)),
                "entries": exclusions,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "validation_summary.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )

    print("=== phase5 feature matrix ===")
    print(f"locked=720 usable_bytecode_inputs={meta['usable_bytecode_expected']}")
    print(f"featurized={len(records)} excluded={len(exclusions)}")
    print(f"shape={X.shape} features={len(names)}")
    print(f"split_counts={meta['split_counts_featurized']}")
    print(f"validation_ok={validation['ok']} issues={validation['issues']}")
    print(f"test_classes_missing={validation['test_classes_missing']}")
    print(f"stage_c_pilot_excluded={validation['stage_c_pilot_excluded']}")
    print(f"out_dir={OUT_DIR}")
    return 0 if validation["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
