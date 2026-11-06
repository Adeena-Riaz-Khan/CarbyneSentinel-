from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "processed" / "features" / "phase5" / "feature_matrix.npz"
META_PATH = ROOT / "processed" / "features" / "phase5" / "meta.json"
OUT_DIR = ROOT / "processed" / "results" / "phase5"

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
    contract_ids = data["contract_ids"]
    feature_names = list(data["feature_names"])

    masks = {
        "train": splits == "train",
        "val": splits == "val",
        "test": splits == "test",
    }
    return X, labels, splits, contract_ids, feature_names, masks


def main() -> int:
    X, labels, splits, contract_ids, feature_names, masks = load_split_arrays()
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    X_train = X[masks["train"]]
    y_train = labels[masks["train"]]
    X_val = X[masks["val"]]
    y_val = labels[masks["val"]]
    X_test = X[masks["test"]]
    y_test = labels[masks["test"]]

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    solver="lbfgs",
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)

    val_macro = float(
        f1_score(
            y_val,
            val_pred,
            labels=NINE_CLASSES,
            average="macro",
            zero_division=0,
        )
    )
    test_macro = float(
        f1_score(
            y_test,
            test_pred,
            labels=NINE_CLASSES,
            average="macro",
            zero_division=0,
        )
    )

    report = classification_report(
        y_test,
        test_pred,
        labels=NINE_CLASSES,
        zero_division=0,
        output_dict=True,
    )
    cm = confusion_matrix(y_test, test_pred, labels=NINE_CLASSES)

    result = {
        "model": "StandardScaler+LogisticRegression",
        "sklearn_pipeline": True,
        "logistic_regression": {
            "max_iter": 2000,
            "solver": "lbfgs",
            "class_weight": "balanced",
            "random_state": 42,
        },
        "preprocessing": "StandardScaler fitted on training split only via Pipeline",
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "counts": {
            "train": int(masks["train"].sum()),
            "val": int(masks["val"].sum()),
            "test": int(masks["test"].sum()),
        },
        "val_macro_f1": val_macro,
        "test_macro_f1": test_macro,
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "phase5_baseline_macro_f1.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("=== phase5 smoke baseline ===")
    print(f"train={result['counts']['train']} val={result['counts']['val']} test={result['counts']['test']}")
    print(f"val_macro_f1={val_macro:.6f}")
    print(f"test_macro_f1={test_macro:.6f}")
    print(f"tx_origin_test_count={result['limitations']['tx_origin_test_count']}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
