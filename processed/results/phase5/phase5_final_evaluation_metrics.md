# CarbyneSentinel — Final Evaluation Metrics and Benchmarking Results

## 1. Evaluation Overview and Scope

This report consolidates the measured evaluation of the CarbyneSentinel Phase 5 bytecode-screening pipeline.

**What was measured**

1. Multiclass vulnerability classification on the locked, featurized test cohort.
2. One-vs-rest per-class rates derived from the saved Gradient Boosting confusion matrix.
3. Laboratory runtime cost of feature extraction, internal inference, and local HTTP inference.
4. Standalone Counting Bloom Filter microbenchmarks and unit tests.
5. An OBFPROBE-inspired paired obfuscation robustness experiment on locked-test parents and their generated children.

**Frozen model**

| Item | Value |
|---|---|
| Estimator | Gradient Boosting inside a `StandardScaler` pipeline |
| Feature group | `pruned155` (155 features) |
| Artifact | `phase5_model_gb_pruned155.joblib` |
| Selection basis | Validation performance; test scores were **not** used for model selection |

**What this report does not claim**

- Live Ethereum mempool ingestion performance.
- Benign-versus-malicious detection (no benign class exists in this evaluation).
- A reproduction of OBFPROBE transfer-obfuscation features F1–F7.
- General robustness of the detector to arbitrary obfuscation.

**Integrity**

- No training, retraining, fitting, or hyperparameter tuning was performed for the metrics in this document.
- Historical GB/RF/baseline JSON artifacts were not overwritten.
- Additional JSON results are stored in `phase5_extra_metrics_gb_pruned155.json`.

---

## 2. Dataset and Evaluated Cohort

| Cohort | Count | Role |
|---|---:|---|
| Locked test split (`data/processed/phase4_splits.json`) | **108** | Designated held-out contract IDs |
| Usable featurized test cohort (`feature_matrix.npz`, `splits == "test"`) | **100** | Cohort for classification metrics |
| Excluded from the feature matrix | **8** | Locked test IDs without a usable 155-d feature row |

**Classification metrics use 100 usable test samples, not all 108 locked test IDs.**

### Exclusions (8 contracts)

1. Five DAppSCAN `tx_origin` contracts — no bytecode path for featurization.
2. Two DIVE contracts (`access_control`, `bad_randomness`) — no bytecode path for featurization.
3. One SmartBugs reentrancy contract (`SMARTBUGS_reentrancy_spank_chain_payment`) — unlinked / excluded from featurization.

Obfuscation children are **not** rows in the Phase 5 training/evaluation feature matrix. They appear only in the paired robustness experiment below.

---

## 3. Classification Performance

**What was measured:** overall correctness of the frozen Gradient Boosting model on the 100-sample featurized test cohort.

**How:** metrics already recorded for the frozen GB evaluation (`phase5_test_gb_pruned155.json` / `phase5_extra_metrics_gb_pruned155.json`). Balanced accuracy, weighted F1, and multiclass MCC were added later by frozen-model prediction on the same locked matrix; they were not used for model selection.

| Metric | Result | Meaning |
|---|---:|---|
| Accuracy | 0.740000 (74.00%) | Fraction of contracts whose predicted class matches the label |
| Macro-F1 | 0.754283 (75.43%) | Unweighted mean of per-class F1 |
| Weighted F1 | 0.742387 (74.24%) | Support-weighted mean of per-class F1 |
| Balanced Accuracy | 0.753367 (75.34%) | Mean recall across the nine classes |
| Multiclass MCC | 0.709104 | Agreement over the full 9×9 confusion matrix |

Macro-F1 treats every class equally; weighted F1 weights classes by support. They are not interchangeable.

**What this does not establish:** performance on live contracts, benign traffic, or obfuscated bytecode (see Section 7).

---

## 4. Per-Class One-vs-Rest Metrics

**What was measured:** per-vulnerability-class TP, FP, TN, FN, precision, recall (TPR), FPR, FNR, F1, and support.

**How:** derived from the saved 9×9 confusion matrix in `phase5_test_gb_pruned155.json` only. No model load and no prediction for this table. Zero-denominator convention: rate = **0.0**.

FPR and FNR are **one-vs-rest, per-vulnerability-class** rates. They are **not** benign-versus-malicious rates.

| Vulnerability class | TP | FP | TN | FN | Precision | Recall (TPR) | FPR | FNR | F1 | Support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| access_control | 5 | 7 | 82 | 6 | 0.416667 | 0.454545 | 0.078652 | 0.545455 | 0.434783 | 11 |
| bad_randomness | 11 | 3 | 86 | 0 | 0.785714 | 1.000000 | 0.033708 | 0.000000 | 0.880000 | 11 |
| denial_of_service | 8 | 7 | 81 | 4 | 0.533333 | 0.666667 | 0.079545 | 0.333333 | 0.592593 | 12 |
| front_running | 8 | 5 | 83 | 4 | 0.615385 | 0.666667 | 0.056818 | 0.333333 | 0.640000 | 12 |
| integer_overflow | 8 | 1 | 87 | 4 | 0.888889 | 0.666667 | 0.011364 | 0.333333 | 0.761905 | 12 |
| reentrancy | 10 | 1 | 88 | 1 | 0.909091 | 0.909091 | 0.011236 | 0.090909 | 0.909091 | 11 |
| time_manipulation | 10 | 2 | 86 | 2 | 0.833333 | 0.833333 | 0.022727 | 0.166667 | 0.833333 | 12 |
| tx_origin | 7 | 0 | 93 | 0 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 1.000000 | 7 |
| unchecked_call | 7 | 0 | 88 | 5 | 1.000000 | 0.583333 | 0.000000 | 0.416667 | 0.736842 | 12 |

Confusion-matrix total = **100**. Every class support equals its row sum.

### Macro averages (rates only; counts are not averaged)

| Macro metric | Value |
|---|---:|
| Macro precision | 0.775824 |
| Macro recall (TPR) | 0.753367 |
| Macro FPR | 0.032672 |
| Macro FNR | 0.246633 |
| Macro F1 | 0.754283 |

Precision, recall, and F1 match the saved GB `test_classification_report` (absolute deltas = 0). An earlier draft of this section incorrectly listed Random Forest F1 values; those have been replaced with the Gradient Boosting figures above.

---

## 5. Runtime Performance

**What was measured:** laboratory sequential cost of the existing inference path on valid test bytecode.

**How:** `phase5_smoke_baseline.py --bench-runtime` with the frozen GB bundle preloaded. Feature extraction, internal E2E, and HTTP latency are separate measurements.

| Runtime metric | Mean | p50 | p95 |
|---|---:|---:|---:|
| Feature extraction | 6.52 ms | 5.00 ms | 18.60 ms |
| Internal E2E inference | 13.52 ms | 11.75 ms | 27.72 ms |
| HTTP request latency | 31.99 ms | 28.53 ms | 46.20 ms |

**Throughput (sequential):** 77.66 contracts/second (300 processed contracts in 3.86 s; 100 valid contracts × 3 passes).

| Item | Value |
|---|---|
| Feature / E2E inputs | 100 valid test bytecodes |
| Warm-up | 3 contracts |
| Timed repetitions | 2 (latency n = 200) |
| HTTP sample | n = 20 |
| Timer | `time.perf_counter()` |
| Execution | Sequential |

| Measurement | Includes | Excludes |
|---|---|---|
| Feature extraction | Validation, disassembly, CFG, fingerprint/opcode features, 155-d vector | Model prediction; HTTP |
| Internal E2E | Full `analyze_runtime_bytecode` with preloaded GB bundle | Per-call model reload; HTTP |
| HTTP latency | Local `/api/analyze` request/response | Internal-only timers |

**What this does not establish:** live mempool latency, concurrent capacity, or a production SLA.

---

## 6. Counting Bloom Filter Evaluation

**What was measured:** standalone microbenchmarks and unit tests of `intake/counting_bloom.py` (`CountingBloomFilter`).

**How:** `py -3.13 intake/test_counting_bloom.py` (10 unit tests + `run_measurements`). The filter was **not** connected to the frontend, Firestore, or mempool path. Seeded UI `bloomPruneRate` is **not** a measured result.

### Benchmark parameters

| Parameter | Value |
|---|---|
| Filter size | 8192 counters |
| Hash count | 5 |
| Inserted keys (timing) | 1000 |
| Lookup ops | 1000 (500 present + 500 absent) |
| FP occupancy levels | 100, 500, 1000, 2000, 4000 inserted keys |
| Absent probes per level | 2000 |
| Repetitions / warm-up | None (single pass) |
| Timer | `time.perf_counter()` |

### Measured throughput

| Operation | Approx. operations/sec |
|---|---:|
| Insert | 922,509 |
| Lookup | 806,452 |

### Empirical false-positive rate (absent probes)

| Inserted keys | False positives / probes | Observed FPR |
|---:|---|---:|
| 100 | 0 / 2000 | 0.00% |
| 500 | 2 / 2000 | 0.10% |
| 1000 | 27 / 2000 | 1.35% |
| 2000 | 287 / 2000 | 14.35% |
| 4000 | 1216 / 2000 | 60.80% |

### Memory (two different Python accounting methods)

| Method | Value | What it is |
|---|---:|---|
| `sys.getsizeof` estimate | 294,968 bytes | Approximate size of the Python list of unbounded ints |
| `tracemalloc` current | 65,752 bytes | Traced allocations after constructing/filling 1000 keys |
| `tracemalloc` peak | 66,244 bytes | Peak traced allocation in that window |

These figures are **not** packed production-filter memory. They reflect CPython object overhead and are not interchangeable with each other or with a fixed-width counter array.

### Correctness tests

- Unit tests: **10/10 passed**.
- Removal after insert and underflow-protection tests passed (second remove rejected; counters remain ≥ 0).
- No fixed-width counter saturation test exists (counters are unbounded Python ints).
- False negatives for inserted keys: none observed in the unit tests.

**Theoretical vs observed:** classic Bloom filters can false-positive and (while items remain inserted) should not false-negative; rising FPR with load was **observed**. Throughput and memory numbers above are **observed on this machine for one pass**, not theoretical guarantees.

**What this does not establish:** production mempool prune rate, live duplicate suppression, or system-level ingest behaviour.

---

## 7. Paired Obfuscation Robustness Evaluation

**What was measured:** prediction stability and label retention when the frozen Gradient Boosting model scores generated obfuscated children of locked-test parents.

**How:** `phase5_smoke_baseline.py --paired-obfuscation` using:

- Parent/child map: `data/processed/obfuscation_benchmark.jsonl`
- Feature extraction: `phase5_build_feature_matrix.extract_vector` with the frozen model’s exact `pruned155` feature order
- Frozen model: `phase5_model_gb_pruned155.joblib` (`predict` / `predict_proba` only; no `fit`)
- Locked split: `data/processed/phase4_splits.json`

This is an **OBFPROBE-inspired paired obfuscation robustness experiment**. It does **not** implement OBFPROBE features F1–F7.

### Verified cohort

| Item | Count |
|---|---:|
| Locked-test parents with children | **5** |
| Obfuscated children of those parents | **26** |
| Parents present in featurized test matrix | **5 / 5** |
| Child bytecodes available on disk | **26 / 26** |
| Feature-extraction failures | **0** |
| Label mismatches (child vs parent) | **0** |

Skew: **20 of 26** variants belong to `SOLIDIFI_Timestamp-Dependency_buggy_2` (`time_manipulation`). The remaining 6 are `tx_origin` SolidiFI variants across four parents.

### Metric definitions

| Metric | Definition |
|---|---|
| Parent correct | Parent prediction equals parent ground-truth label |
| Child correct | Child prediction equals child ground-truth label |
| Prediction agreement | Child prediction equals parent prediction |
| Label retention | Child prediction equals the known vulnerability label |
| Prediction changed | Child prediction differs from parent prediction |
| Confidence delta | Child minus parent `predict_proba` on the known label |

**Aggregation**

- **Variant-level:** unweighted mean across all 26 children (skewed toward the large parent).
- **Parent-level:** unweighted mean of the five per-parent rates (each parent counts equally).

### Per-parent results

| Parent | Label | Parent correct | Variants | Child correct | Agreement | Label retention | Change rate | Mean true-label prob Δ (child − parent) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| SOLIDIFI_Timestamp-Dependency_buggy_2 | time_manipulation | Yes | 20 | 1.000 | 1.000 | 1.000 | 0.000 | −0.000209 |
| SOLIDIFI_tx.origin_buggy_19 | tx_origin | Yes | 2 | 1.000 | 1.000 | 1.000 | 0.000 | −0.000006 |
| SOLIDIFI_tx.origin_buggy_22 | tx_origin | Yes | 1 | 1.000 | 1.000 | 1.000 | 0.000 | ≈ 0 |
| SOLIDIFI_tx.origin_buggy_24 | tx_origin | Yes | 2 | 1.000 | 1.000 | 1.000 | 0.000 | −0.000014 |
| SOLIDIFI_tx.origin_buggy_25 | tx_origin | Yes | 1 | 1.000 | 1.000 | 1.000 | 0.000 | −0.000008 |

### Overall results

| Aggregation | Parent correct | Child correct | Agreement | Label retention | Prediction change |
|---|---:|---:|---:|---:|---:|
| Variant-level (n=26) | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| Parent-level (n=5) | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

Across all 26 variants, true-label probability deltas were small (min ≈ −0.0025, mean ≈ −0.00016, max ≈ +0.00008). Hard class predictions did not change.

**What the result means:** on this tiny, class-skewed locked-test subset, the frozen GB model retained the known label and agreed with the parent prediction for every evaluated child.

**What it does not establish:**

- General robustness to obfuscation.
- Semantics-preserving behaviour of the transforms (see limitations).
- Coverage beyond two vulnerability classes (`time_manipulation`, `tx_origin`).
- An OBFPROBE F1–F7 analysis of funds-transfer obfuscation.

---

## 8. Limitations and Interpretation

1. **Content-level leakage risk:** identical SolidiFI contract pairs exist across train and held-out partitions.
2. **Source–class entanglement:** usable `tx_origin` seeds are SolidiFI-only.
3. **No benign class:** FPR/FNR here are one-vs-rest class rates, not malware-style false alarms on clean code.
4. **Static CFG limits:** some dynamic jumps remain unresolved.
5. **Runtime scope:** sequential laboratory benches only.
6. **Coverage gap:** classification uses 100 of 108 locked test IDs.
7. **CBF scope:** standalone Python microbenchmark; not production ingest telemetry.
8. **Paired obfuscation validity:**
   - Transforms are generated/compiled variants, not proven semantics-preserving equivalents.
   - `exploit_verified_after_transform` reflects compile success and transform markers, not differential execution or fork-replay.
   - Only five test parents; 20/26 children from one parent.
   - Perfect retention on this sample must not be generalized.

This evaluation is **not** described as leakage-free, and no live mempool SLA is claimed.

---

## 9. Reproducibility and Artifact References

### Environment (from `phase5_extra_metrics_gb_pruned155.json`)

| Item | Value |
|---|---|
| OS | Windows 11 |
| CPU | Intel64 Family 6 Model 197 Stepping 2, GenuineIntel |
| Python | 3.13.14 |
| scikit-learn | 1.9.1 |
| NumPy | 2.5.2 |
| Model | `phase5_model_gb_pruned155.joblib` |
| Features | `pruned155`, 155 |

### Commands (PowerShell)

```powershell
py -3.13 scripts/phase5_smoke_baseline.py --cm-class-metrics --out phase5_extra_metrics_gb_pruned155.json
py -3.13 scripts/phase5_smoke_baseline.py --extra-metrics --model-artifact phase5_model_gb_pruned155.joblib --out phase5_extra_metrics_gb_pruned155.json
py -3.13 scripts/phase5_smoke_baseline.py --bench-runtime --model-artifact phase5_model_gb_pruned155.joblib --out phase5_extra_metrics_gb_pruned155.json
py -3.13 intake/test_counting_bloom.py
py -3.13 scripts/phase5_smoke_baseline.py --paired-obfuscation --model-artifact phase5_model_gb_pruned155.joblib --out phase5_extra_metrics_gb_pruned155.json
```

### Key artifacts

| Artifact | Path |
|---|---|
| Extra metrics JSON | `processed/results/phase5/phase5_extra_metrics_gb_pruned155.json` |
| Historical GB test report / CM | `processed/results/phase5/phase5_test_gb_pruned155.json` |
| Frozen model | `processed/results/phase5/phase5_model_gb_pruned155.joblib` |
| Feature matrix | `processed/features/phase5/feature_matrix.npz` |
| Locked split | `data/processed/phase4_splits.json` |
| Obfuscation benchmark | `data/processed/obfuscation_benchmark.jsonl` |
| CBF implementation / tests | `intake/counting_bloom.py`, `intake/test_counting_bloom.py` |
