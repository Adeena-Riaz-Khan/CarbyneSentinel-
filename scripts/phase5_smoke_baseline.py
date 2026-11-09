from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import re
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "features"))
sys.path.insert(0, str(ROOT / "scripts"))

from cfg import build_cfg
from disasm import check_offsets, disassemble, format_listing, parse_hex
from fingerprint_v0 import (
    bytecode_shannon_entropy,
    jump_features,
    opcode_shannon_entropy,
)
from opcode_freq import opcode_feature_names, opcode_frequency_ratios

MATRIX_PATH = ROOT / "processed" / "features" / "phase5" / "feature_matrix.npz"
META_PATH = ROOT / "processed" / "features" / "phase5" / "meta.json"
MASTER_PATH = ROOT / "processed" / "master_dataset_phase2.json"
SPLITS_PATH = ROOT / "data" / "processed" / "phase4_splits.json"
OUT_DIR = ROOT / "processed" / "results" / "phase5"
CANONICAL_RESULT = "phase5_baseline_macro_f1.json"
DEFAULT_MODEL_ARTIFACT = "phase5_model_gb_pruned155.joblib"
REDUNDANT_FEATURES = {
    "op_ratio_JUMP",
    "op_ratio_JUMPI",
    "total_jump_count",
    "jump_ratio",
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


def load_split_arrays():
    if not MATRIX_PATH.is_file():
        raise SystemExit(f"missing feature matrix: {MATRIX_PATH}")
    data = np.load(MATRIX_PATH, allow_pickle=True)
    X = data["X"]
    labels = data["labels"]
    splits = data["splits"]
    contract_ids = np.array([str(c) for c in data["contract_ids"]])
    feature_names = list(data["feature_names"])

    masks = {
        "train": splits == "train",
        "val": splits == "val",
        "test": splits == "test",
    }
    return X, labels, splits, contract_ids, feature_names, masks


def parse_exclude_ids(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


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


def canonical_feature_names() -> list[str]:
    return FINGERPRINT_NAMES + EXTRA_NAMES + opcode_feature_names()


def select_feature_indices(feature_names: list[str], group: str) -> list[int]:
    if group == "all159":
        return list(range(len(feature_names)))
    if group == "pruned155":
        return [i for i, n in enumerate(feature_names) if n not in REDUNDANT_FEATURES]
    if group == "fp14":
        keep = set(FINGERPRINT_NAMES + EXTRA_NAMES)
        return [i for i, n in enumerate(feature_names) if n in keep]
    if group == "opcodes145":
        return [i for i, n in enumerate(feature_names) if n.startswith("op_ratio_")]
    raise ValueError(f"unknown feature group: {group}")


def build_estimator(model_type: str, c_val: float) -> Pipeline:
    if model_type == "lr":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        C=c_val,
                        max_iter=2000,
                        solver="lbfgs",
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )
    if model_type == "rf":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=16,
                        class_weight="balanced_subsample",
                        random_state=42,
                    ),
                ),
            ]
        )
    if model_type == "gb":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "clf",
                    GradientBoostingClassifier(
                        n_estimators=150,
                        max_depth=3,
                        learning_rate=0.08,
                        random_state=42,
                    ),
                ),
            ]
        )
    raise ValueError(f"unknown model type: {model_type}")


def validate_raw_bytecode(bytecode: str) -> list[str]:
    text = (bytecode or "").strip()
    if text == "" or text in {"0x", "0X"}:
        return ["bytecode is empty"]
    if re.search(r"__\$[A-Za-z0-9_]+\$__", text) or re.search(r"__[A-Za-z0-9_:.]{1,64}__", text):
        return ["unlinked library placeholder in runtime bytecode"]
    try:
        data = parse_hex(text)
    except ValueError as exc:
        return [str(exc)]
    if len(data) == 0:
        return ["bytecode is empty"]
    try:
        ins = disassemble(text)
    except Exception as exc:
        return [f"disassemble failed: {exc}"]
    if not ins:
        return ["disassemble produced zero instructions"]
    return check_offsets(ins, len(data))


def explain_prediction(
    pipeline: Pipeline,
    vector: np.ndarray,
    feature_names: list[str],
    predicted_class: str,
) -> tuple[str, str, list[dict]]:
    scaler = pipeline.named_steps.get("scaler")
    clf = pipeline.named_steps.get("clf")
    x_row = vector.reshape(1, -1)
    z_row = scaler.transform(x_row)[0] if scaler is not None else vector
    items = []
    if hasattr(clf, "feature_importances_"):
        imps = clf.feature_importances_
        order = np.argsort(-imps)[:8]
        for j in order:
            zv = float(z_row[int(j)])
            imp = float(imps[int(j)])
            items.append(
                {
                    "feature": feature_names[int(j)],
                    "raw_value": round(float(vector[int(j)]), 6),
                    "z_score": round(zv, 4),
                    "global_importance": round(imp, 4),
                    "weight": round(imp, 4),
                    "contribution": round(imp * abs(zv), 4),
                    "direction": "above_train_mean" if zv >= 0 else "below_train_mean",
                }
            )
        return (
            "tree_global_importance_with_contract_z_deviation",
            "Global impurity-based feature importance from Gradient Boosting paired with this contract's standardized z-score relative to the training split. Global importance indicates overall model reliance across all 9 classes, not a causal or class-specific attribution for this contract.",
            items,
        )
    if hasattr(clf, "coef_") and hasattr(clf, "classes_"):
        classes = [str(c) for c in clf.classes_]
        if predicted_class in classes:
            idx = classes.index(predicted_class)
            coefs = clf.coef_[idx]
            contribs = coefs * z_row
            order = np.argsort(-np.abs(contribs))[:8]
            for j in order:
                items.append(
                    {
                        "feature": feature_names[int(j)],
                        "raw_value": round(float(vector[int(j)]), 6),
                        "z_score": round(float(z_row[int(j)]), 4),
                        "global_importance": None,
                        "weight": round(float(coefs[int(j)]), 4),
                        "contribution": round(float(contribs[int(j)]), 4),
                        "direction": "supports_predicted_class" if contribs[int(j)] >= 0 else "opposes_predicted_class",
                    }
                )
            return (
                "linear_log_odds_contribution",
                "Linear log-odds contribution (class coefficient x standardized feature z-score) for the predicted class.",
                items,
            )
    return ("none", "No feature attribution available for this estimator.", items)


def load_saved_model_bundle(model_path: Path) -> dict | None:
    if not model_path.is_file():
        return None
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or "pipeline" not in bundle or "feature_names" not in bundle:
        return None
    pipe = bundle["pipeline"]
    fnames = list(bundle["feature_names"])
    if not hasattr(pipe, "named_steps") or "clf" not in pipe.named_steps:
        return None
    clf = pipe.named_steps["clf"]
    if hasattr(clf, "n_features_in_") and int(clf.n_features_in_) != len(fnames):
        return None
    return bundle


def analyze_runtime_bytecode(
    bytecode: str,
    model_path: Path | None = None,
    contract_id: str | None = None,
    preloaded_bundle: dict | None = None,
) -> dict:
    errors = validate_raw_bytecode(bytecode)
    if errors:
        return {
            "validation": {
                "ok": False,
                "errors": errors,
            },
            "contract_id": contract_id,
            "limitations": [
                "Input failed static EVM runtime bytecode validation; disassembly, CFG, and ML inference were not executed.",
                "Contracts containing unlinked Solidity library placeholders (__$...$__ or __Lib__) cannot be executed or featurized until linked.",
            ],
        }

    data = parse_hex(bytecode)
    instructions = disassemble(bytecode)
    size, byte_entropy = bytecode_shannon_entropy(bytecode)
    jumps = jump_features(instructions)
    op_entropy = opcode_shannon_entropy(instructions)
    cfg = build_cfg(instructions)
    cfg_stats = cfg["stats"]
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

    names = canonical_feature_names()
    vector_list = []
    for name in names:
        if name not in values:
            raise ValueError(f"missing_feature_column: {name}")
        val = values[name]
        if not math.isfinite(val):
            raise ValueError(f"non_finite_feature: {name}")
        vector_list.append(val)
    full_vector = np.array(vector_list, dtype=float)

    top_opcodes = sorted(
        [(k.replace("op_ratio_", ""), v) for k, v in ratios.items() if v > 0],
        key=lambda x: -x[1],
    )[:10]

    has_truncated_push = bool(instructions[-1]["incomplete"])
    unknown_op_count = sum(1 for ins in instructions if ins["opcode"].startswith("UNKNOWN_"))

    resolved_model_path = model_path or (OUT_DIR / DEFAULT_MODEL_ARTIFACT)
    bundle = preloaded_bundle if preloaded_bundle is not None else load_saved_model_bundle(resolved_model_path)
    artifact_name = resolved_model_path.name

    prediction_section = {
        "model_available": False,
        "artifact_path": artifact_name,
        "status": "model_artifact_missing_or_incompatible",
        "predicted_class": None,
        "confidence": None,
        "class_probabilities": None,
        "explanation_method": None,
        "explanation_note": None,
        "top_feature_evidence": [],
    }

    if bundle is not None:
        expected_names = list(bundle["feature_names"])
        idx_map = {n: i for i, n in enumerate(names)}
        if all(n in idx_map for n in expected_names):
            sub_vec = np.array([full_vector[idx_map[n]] for n in expected_names], dtype=float)
            pipe = bundle["pipeline"]
            clf = pipe.named_steps["clf"]
            pred_cls = str(pipe.predict(sub_vec.reshape(1, -1))[0])
            probs_dict = None
            conf = None
            if hasattr(pipe, "predict_proba"):
                probs = pipe.predict_proba(sub_vec.reshape(1, -1))[0]
                classes = [str(c) for c in clf.classes_]
                probs_dict = {c: round(float(p), 4) for c, p in zip(classes, probs)}
                conf = round(float(max(probs)), 4)
            exp_method, exp_note, evidence = explain_prediction(pipe, sub_vec, expected_names, pred_cls)
            prediction_section = {
                "model_available": True,
                "artifact_path": artifact_name,
                "model_name": bundle.get("model_name", f"StandardScaler+{type(clf).__name__}"),
                "estimator_type": type(clf).__name__,
                "feature_group": bundle.get("feature_group", "pruned155"),
                "feature_count": len(expected_names),
                "status": "ok",
                "predicted_class": pred_cls,
                "confidence": conf,
                "class_probabilities": probs_dict,
                "explanation_method": exp_method,
                "explanation_note": exp_note,
                "top_feature_evidence": evidence,
            }

    limitations = [
        "Predictions are statistical multi-class vulnerability indicators over 9 seed classes, not formal verification or proof of exploitability.",
        f"Static CFG extraction resolves immediate PUSH+JUMP/JUMPI targets ({cfg_stats['resolved_jumps']} resolved) and accounts for dynamic stack-derived jumps ({cfg_stats['unresolved_jumps']} unresolved, e.g., return-address POP+JUMP).",
        "All 720 seed contracts in the training cohort are labelled vulnerable across 9 classes; the classifier ranks the most likely vulnerability class rather than certifying a contract as clean or malicious.",
        "Evaluation caveats on the locked split: GB pruned155 achieved 0.7956 validation macro-F1 and 0.7543 locked-test macro-F1 (0.74 test accuracy); tx_origin seeds originate solely from SolidiFI, and 4 SolidiFI buggy_22/buggy_36 content-duplicate pairs cross train/held-out splits.",
    ]
    if has_truncated_push or unknown_op_count > 0:
        limitations.append(
            f"Runtime bytecode includes {unknown_op_count} unknown/data bytes and truncated_push={has_truncated_push} (typical of appended CBOR metadata at the end of runtime bytecode)."
        )

    selected_feature_names = list(bundle["feature_names"]) if bundle is not None else [names[i] for i in select_feature_indices(names, "pruned155")]
    idx_map_all = {n: i for i, n in enumerate(names)}
    selected_values = [round(float(full_vector[idx_map_all[n]]), 6) for n in selected_feature_names]

    return {
        "contract_id": contract_id,
        "validation": {
            "ok": True,
            "errors": [],
            "bytecode_size_bytes": size,
            "instruction_count": len(instructions),
            "truncated_push_at_tail": has_truncated_push,
            "unknown_opcode_count": unknown_op_count,
        },
        "disassembly": {
            "instruction_count": len(instructions),
            "preview_listing": format_listing(instructions, limit=25),
            "top_opcode_ratios": [{"opcode": k, "ratio": v} for k, v in top_opcodes],
        },
        "cfg": {
            "block_count": cfg_stats["block_count"],
            "edge_count": cfg_stats["edge_count"],
            "resolved_jumps": cfg_stats["resolved_jumps"],
            "unresolved_jumps": cfg_stats["unresolved_jumps"],
            "dynamic_jump_note": "Unresolved jumps occur when JUMP/JUMPI target is computed on the stack (such as POP+JUMP function returns) rather than an immediate preceding PUSH.",
        },
        "fingerprint": {
            "bytecode_size_bytes": size,
            "bytecode_shannon_entropy": byte_entropy,
            "opcode_shannon_entropy": op_entropy,
            "total_instruction_count": jumps["total_instruction_count"],
            "jump_count": jumps["jump_count"],
            "jumpi_count": jumps["jumpi_count"],
            "total_jump_count": jumps["total_jump_count"],
            "jump_ratio": jumps["jump_ratio"],
            "conditional_jump_ratio": jumps["conditional_jump_ratio"],
            "unconditional_jump_ratio": jumps["unconditional_jump_ratio"],
        },
        "feature_vector": {
            "dimension": len(selected_feature_names),
            "feature_group": bundle.get("feature_group", "pruned155") if bundle is not None else "pruned155",
            "feature_names": selected_feature_names,
            "values": selected_values,
            "full_159_dimension": len(names),
        },
        "prediction": prediction_section,
        "limitations": limitations,
    }


def load_demo_examples() -> list[dict]:
    master = {r["contract_id"]: r for r in json.loads(MASTER_PATH.read_text(encoding="utf-8"))}
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    id_to_split = {}
    for s_name in ("train", "val", "test"):
        for cid in splits["splits"][s_name]:
            id_to_split[cid] = s_name

    demos = []
    curated = [
        (
            "SMARTBUGS_reentrancy_reentrancy_insecure",
            "Known Vulnerable — Reentrancy (Exact Compiler)",
            "Labelled dataset contract from SmartBugs (reentrancy, test split, solc 0.4.26).",
        ),
        (
            "SOLIDIFI_tx.origin_buggy_10",
            "Known Vulnerable — tx.origin (Exact Compiler)",
            "Labelled dataset contract from SolidiFI (tx_origin, test split, solc 0.5.17).",
        ),
        (
            "SMARTBUGS_access_control_parity_wallet_bug_2",
            "Fallback-Recovered — Access Control (Wave 1)",
            "Recovered in Batch B Wave 1 via approved fallback compiler (recorded 0.4.9 -> compiled 0.4.11, train split).",
        ),
        (
            "SMARTBUGS_reentrancy_spank_chain_payment",
            "Unlinked Library Placeholder (Excluded Contract)",
            "Compiled artifact from SmartBugs containing unresolved __Library__ placeholders in runtime bytecode.",
        ),
    ]
    for cid, title, desc in curated:
        row = master.get(cid)
        if not row:
            continue
        bp = row.get("bytecode_path")
        raw = ""
        if bp and (ROOT / "processed" / bp).is_file():
            raw = (ROOT / "processed" / bp).read_text(encoding="utf-8").strip()
        rec = row.get("bytecode_recovery") or {}
        demos.append(
            {
                "id": cid,
                "title": title,
                "description": desc,
                "ground_truth_label": row.get("primary_vulnerability_type"),
                "dataset_source": row.get("source_dataset"),
                "split": id_to_split.get(cid, "unassigned"),
                "compiler_version": row.get("compiler_version"),
                "recovery_status": rec.get("status", "original_dataset_bytecode"),
                "used_fallback": bool(rec.get("used_fallback", False)),
                "bytecode": raw,
            }
        )

    demos.append(
        {
            "id": "SYNTHETIC_MALFORMED_ODD_HEX",
            "title": "Malformed Bytecode — Odd Hex / Invalid Input",
            "description": "Synthetic malformed runtime hex string to demonstrate input validation failure handling.",
            "ground_truth_label": None,
            "dataset_source": "synthetic_validation_case",
            "split": None,
            "compiler_version": None,
            "recovery_status": "synthetic_invalid",
            "used_fallback": False,
            "bytecode": "0x6080604052348015610010576",
        }
    )
    return demos


def run_http_server(port: int, model_path: Path | None) -> int:
    demos = load_demo_examples()
    r_path = model_path or (OUT_DIR / DEFAULT_MODEL_ARTIFACT)
    preloaded = load_saved_model_bundle(r_path)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict) -> None:
            body = (json.dumps(payload) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            self._send_json(200, {"ok": True})

        def do_GET(self) -> None:
            if self.path.startswith("/api/health"):
                clf_name = type(preloaded["pipeline"].named_steps["clf"]).__name__ if preloaded else None
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "model_available": preloaded is not None,
                        "model_artifact": str(r_path.name),
                        "estimator_type": clf_name,
                        "feature_group": preloaded.get("feature_group") if preloaded else None,
                        "feature_count": len(preloaded["feature_names"]) if preloaded else 0,
                    },
                )
                return
            if self.path.startswith("/api/demos"):
                self._send_json(200, {"demos": demos})
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self.path.startswith("/api/analyze"):
                self._send_json(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                req = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid_json"})
                return
            bc = str(req.get("bytecode") or "")
            cid = req.get("contract_id")
            try:
                report = analyze_runtime_bytecode(
                    bc,
                    model_path=r_path,
                    contract_id=cid,
                    preloaded_bundle=preloaded,
                )
            except Exception:
                self._send_json(
                    200,
                    {
                        "contract_id": cid,
                        "validation": {"ok": False, "errors": ["runtime bytecode analysis failed"]},
                        "limitations": ["Unexpected internal error during static bytecode analysis."],
                    },
                )
                return
            self._send_json(200, report)

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"CarbyneSentinel inference API listening on http://127.0.0.1:{port}")
    server.serve_forever()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exclude-train-ids",
        type=str,
        default="",
        help="comma-separated contract_ids excluded from training only",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=CANONICAL_RESULT,
        help="output filename under processed/results/phase5/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow overwriting the canonical baseline JSON",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="lr",
        choices=["lr", "rf", "gb"],
        help="estimator family (lr, rf, gb)",
    )
    parser.add_argument(
        "--c",
        type=float,
        default=1.0,
        help="inverse regularization strength C for logistic regression",
    )
    parser.add_argument(
        "--feature-group",
        type=str,
        default="all159",
        choices=["all159", "pruned155", "fp14", "opcodes145"],
        help="feature subset to evaluate",
    )
    parser.add_argument(
        "--val-only",
        action="store_true",
        help="evaluate strictly on train and validation splits without touching test split",
    )
    parser.add_argument(
        "--save-model",
        type=str,
        default="",
        help="optional filename under processed/results/phase5/ to serialize fitted Pipeline bundle",
    )
    parser.add_argument(
        "--model-artifact",
        type=str,
        default=DEFAULT_MODEL_ARTIFACT,
        help="saved model bundle filename under processed/results/phase5/ for inference",
    )
    parser.add_argument(
        "--infer-bytecode",
        type=str,
        default="",
        help="run non-training inference on raw runtime hex string and print JSON report",
    )
    parser.add_argument(
        "--infer-file",
        type=str,
        default="",
        help="run non-training inference on a bytecode file path and print JSON report",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="start local HTTP inference server (never trains models)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for --serve HTTP inference server",
    )
    args = parser.parse_args()

    model_bundle_path = OUT_DIR / Path(args.model_artifact).name
    if args.serve:
        return run_http_server(args.port, model_bundle_path)

    if args.infer_bytecode or args.infer_file:
        raw_bc = args.infer_bytecode
        cid = None
        if args.infer_file:
            fpath = Path(args.infer_file)
            if not fpath.is_file():
                raise SystemExit(f"missing bytecode file: {fpath}")
            raw_bc = fpath.read_text(encoding="utf-8").strip()
            cid = fpath.stem
        report = analyze_runtime_bytecode(raw_bc, model_path=model_bundle_path, contract_id=cid)
        print(json.dumps(report, indent=2))
        return 0

    out_name = Path(args.out).name
    out_path = OUT_DIR / out_name
    if out_name == CANONICAL_RESULT and out_path.is_file() and not args.force:
        raise SystemExit(
            f"refusing to overwrite canonical result {out_path}; "
            "pass --force to overwrite, or use --out <other-name>.json"
        )

    exclude_ids = parse_exclude_ids(args.exclude_train_ids)
    X, labels, splits, contract_ids, feature_names, masks = load_split_arrays()
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    feat_idx = select_feature_indices(feature_names, args.feature_group)
    selected_names = [feature_names[i] for i in feat_idx]
    X_sel = X[:, feat_idx]

    train_mask = masks["train"].copy()
    id_to_split = {cid: str(sp) for cid, sp in zip(contract_ids.tolist(), splits.tolist())}
    missing = [cid for cid in exclude_ids if cid not in id_to_split]
    if missing:
        raise SystemExit(f"exclude ids not in matrix: {missing}")
    not_train = [cid for cid in exclude_ids if id_to_split[cid] != "train"]
    if not_train:
        raise SystemExit(f"exclude ids are not in training split: {not_train}")
    if exclude_ids:
        drop = np.isin(contract_ids, exclude_ids)
        train_mask = train_mask & ~drop

    X_train = X_sel[train_mask]
    y_train = labels[train_mask]
    X_val = X_sel[masks["val"]]
    y_val = labels[masks["val"]]

    model = build_estimator(args.model_type, args.c)
    model.fit(X_train, y_train)

    val_pred = model.predict(X_val)
    val_macro = float(
        f1_score(
            y_val,
            val_pred,
            labels=NINE_CLASSES,
            average="macro",
            zero_division=0,
        )
    )
    val_acc = float(accuracy_score(y_val, val_pred))
    val_report = classification_report(
        y_val,
        val_pred,
        labels=NINE_CLASSES,
        zero_division=0,
        output_dict=True,
    )
    val_cm = confusion_matrix(y_val, val_pred, labels=NINE_CLASSES)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.save_model:
        save_path = OUT_DIR / Path(args.save_model).name
        joblib.dump(
            {
                "pipeline": model,
                "feature_names": selected_names,
                "feature_group": args.feature_group,
                "model_type": args.model_type,
                "model_name": f"StandardScaler+{args.model_type.upper()}(C={args.c})",
                "classes": NINE_CLASSES,
            },
            save_path,
        )
        print(f"saved model bundle to {save_path}")

    if args.val_only:
        result = {
            "model": f"StandardScaler+{args.model_type.upper()}",
            "model_type": args.model_type,
            "c": args.c,
            "feature_group": args.feature_group,
            "val_only": True,
            "sklearn_pipeline": True,
            "preprocessing": "StandardScaler fitted on training split only via Pipeline",
            "feature_count": len(selected_names),
            "feature_names": selected_names,
            "exclude_train_ids": exclude_ids,
            "counts": {
                "train": int(train_mask.sum()),
                "val": int(masks["val"].sum()),
                "test_locked_not_evaluated": int(masks["test"].sum()),
            },
            "val_macro_f1": val_macro,
            "val_accuracy": val_acc,
            "val_classification_report": val_report,
            "val_confusion_matrix": val_cm.tolist(),
            "val_confusion_matrix_labels": NINE_CLASSES,
            "source_matrix": str(MATRIX_PATH.relative_to(ROOT)).replace("\\", "/"),
            "featurized_from_meta": meta.get("successfully_featurized"),
        }
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("=== phase5 validation-only experiment (test set untouched) ===")
        print(f"model_type={args.model_type} C={args.c} feature_group={args.feature_group} features={len(selected_names)}")
        print(f"train={result['counts']['train']} val={result['counts']['val']}")
        print(f"val_macro_f1={val_macro:.6f} val_accuracy={val_acc:.6f}")
        print("val_classification_report:")
        print(
            classification_report(
                y_val,
                val_pred,
                labels=NINE_CLASSES,
                zero_division=0,
                digits=3,
            )
        )
        print(f"wrote {out_path}")
        return 0

    X_test = X_sel[masks["test"]]
    y_test = labels[masks["test"]]
    test_pred = model.predict(X_test)

    test_macro = float(
        f1_score(
            y_test,
            test_pred,
            labels=NINE_CLASSES,
            average="macro",
            zero_division=0,
        )
    )
    test_acc = float(accuracy_score(y_test, test_pred))

    report = classification_report(
        y_test,
        test_pred,
        labels=NINE_CLASSES,
        zero_division=0,
        output_dict=True,
    )
    cm = confusion_matrix(y_test, test_pred, labels=NINE_CLASSES)

    result = {
        "model": "StandardScaler+LogisticRegression" if args.model_type == "lr" else f"StandardScaler+{args.model_type.upper()}",
        "sklearn_pipeline": True,
        "logistic_regression": {
            "C": args.c,
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "feature_group": args.feature_group,
        "preprocessing": "StandardScaler fitted on training split only via Pipeline",
        "feature_count": len(selected_names),
        "feature_names": selected_names,
        "exclude_train_ids": exclude_ids,
        "counts": {
            "train": int(train_mask.sum()),
            "val": int(masks["val"].sum()),
            "test": int(masks["test"].sum()),
        },
        "val_macro_f1": val_macro,
        "test_macro_f1": test_macro,
        "test_accuracy": test_acc,
        "test_classification_report": report,
        "test_confusion_matrix": cm.tolist(),
        "test_confusion_matrix_labels": NINE_CLASSES,
        "limitations": {
            "tx_origin_test_count": int(np.sum(y_test == "tx_origin")),
            "note": "tx_origin test support is small; all usable seed tx_origin are SolidiFI",
            "obfuscation_variants_excluded": True,
            "stage_c_pilot_excluded": True,
        },
        "source_matrix": str(MATRIX_PATH.relative_to(ROOT)).replace("\\", "/"),
        "featurized_from_meta": meta.get("successfully_featurized"),
    }

    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("=== phase5 smoke baseline ===")
    print(
        f"train={result['counts']['train']} val={result['counts']['val']} "
        f"test={result['counts']['test']}"
    )
    if exclude_ids:
        print(f"exclude_train_ids={exclude_ids}")
    print(f"val_macro_f1={val_macro:.6f}")
    print(f"test_macro_f1={test_macro:.6f}")
    print(f"test_accuracy={test_acc:.6f}")
    print(f"tx_origin_test_count={result['limitations']['tx_origin_test_count']}")
    print("test_classification_report:")
    print(
        classification_report(
            y_test,
            test_pred,
            labels=NINE_CLASSES,
            zero_division=0,
            digits=3,
        )
    )
    print("test_confusion_matrix labels=", NINE_CLASSES)
    print(cm)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
