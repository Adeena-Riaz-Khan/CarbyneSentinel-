# CarbyneSentinel — Final Evaluation Metrics and Benchmarking Results


## A. Evaluation Overview

This document records the final classification and runtime evaluation of the CarbyneSentinel Phase 5 bytecode-screening pipeline.

**What was evaluated**

- Multiclass vulnerability classification over nine seed classes on the locked, featurized test cohort.
- Runtime cost of the existing inference pipeline: feature extraction, internal end-to-end (E2E) prediction, sequential throughput, and (separately) local HTTP request latency.

**Frozen model**

- Estimator: Gradient Boosting (with `StandardScaler` in the saved pipeline).
- Feature group: `pruned155` (155 features).
- Artifact: `phase5_model_gb_pruned155.joblib`.

**Scope of this report**

Additional metrics (balanced accuracy, weighted F1, multiclass Matthews correlation coefficient, and runtime benches) were computed from the **already frozen** model and locked evaluation cohort. **No training or retraining** was performed for these metrics. Gradient Boosting remains the validation-selected product model; test scores were not used for model selection.

---

## B. Classification Evaluation Results

Evaluated on **100** usable featurized test samples (see Section D).

| Metric | Result |
|---|---:|
| Accuracy | 0.740000 (74.00%) |
| Macro-F1 | 0.754283 (75.43%) |
| Weighted F1 | 0.742387 (74.24%) |
| Balanced Accuracy | 0.753367 (75.34%) |
| Multiclass MCC | 0.709104 |

**Metric notes**

| Metric | Meaning | Why it is useful |
|---|---|---|
| **Accuracy** | Fraction of test contracts whose predicted class matches the label. | Simple overall correctness summary. |
| **Macro-F1** | Unweighted mean of per-class F1 scores. | Treats all nine vulnerability classes equally, even when support differs. |
| **Weighted F1** | F1 averaged across classes, weighted by each class’s support. | Reflects performance with more weight on classes that appear more often in the test set. |
| **Balanced accuracy (BAC)** | Average recall across the nine classes. | Reduces bias toward majority classes when class sizes differ. |
| **Multiclass MCC** | Matthews correlation coefficient over the full nine-class confusion matrix. | Single summary of agreement between labels and predictions that accounts for all cells of the confusion matrix. |

Macro-F1 and weighted F1 are not interchangeable: macro-F1 gives equal importance to every class; weighted F1 scales each class by its support.

---

## C. Per-Class Classification Results

| Vulnerability class | F1-score | Support |
|---|---:|---:|
| access_control | 0.462 | 11 |
| bad_randomness | 0.800 | 11 |
| denial_of_service | 0.815 | 12 |
| front_running | 0.696 | 12 |
| integer_overflow | 0.818 | 12 |
| reentrancy | 0.857 | 11 |
| time_manipulation | 0.783 | 12 |
| tx_origin | 0.923 | 7 |
| unchecked_call | 0.800 | 12 |

**Support total: 100** (11 + 11 + 12 + 12 + 12 + 11 + 12 + 7 + 12).

---

## D. Dataset Coverage and Test-Set Clarification

| Cohort | Count | Role |
|---|---:|---|
| Original locked test split (`phase4_splits.json`) | **108** | Designated held-out contract IDs |
| Usable featurized test cohort (feature matrix rows with `splits == "test"`) | **100** | Cohort used for all classification metrics in this document |
| Excluded from the feature matrix | **8** | Locked test IDs without a usable 155-d feature row |

**Classification metrics were calculated on 100 usable test samples, not on all 108 locked test IDs.**

### Exclusions (8 contracts)

1. **Five DAppSCAN `tx_origin` contracts** — no bytecode path available for featurization.  
2. **Two DIVE contracts** (`access_control`, `bad_randomness`) — no bytecode path available for featurization.  
3. **One SmartBugs reentrancy contract** (`SMARTBUGS_reentrancy_spank_chain_payment`) — unlinked / excluded from featurization.

The locked split size (108) remains the intended held-out partition; the evaluated cohort (100) is the subset that was successfully represented in the Phase 5 feature matrix.

---

## E. Runtime Benchmark Results

Runtime metrics measure the **existing** backend pipeline on valid bytecode. Feature extraction, internal E2E inference, and HTTP latency are **separate** measurements and must not be merged into a single latency figure.

| Runtime metric | Mean | p50 | p95 |
|---|---:|---:|---:|
| Feature extraction | 6.52 ms | 5.00 ms | 18.60 ms |
| Internal E2E inference | 13.52 ms | 11.75 ms | 27.72 ms |
| HTTP request latency | 31.99 ms | 28.53 ms | 46.20 ms |

**Throughput (sequential)**

- **77.66 contracts/second**
- Workload: **300** processed contracts in **3.86** seconds (100 valid contracts × 3 passes)

**Timing methodology**

| Item | Value |
|---|---|
| Feature extraction / internal E2E inputs | 100 valid test bytecodes |
| Warm-up | 3 contracts |
| Timed repetitions per contract | 2 (latency sample size n = 200) |
| HTTP timing | n = 20; local server already running |
| Timer | `time.perf_counter()` |
| Execution | Sequential (not concurrent) |
| Excluded from steady-state internal timing | Application startup and model disk load (bundle preloaded) |

**What each latency measures**

| Measurement | Includes | Excludes |
|---|---|---|
| **Feature extraction** | Bytecode validation, disassembly, CFG extraction, fingerprint/opcode features, construction/ordering of the 155-d vector | Model prediction; HTTP |
| **Internal E2E inference** | Full `analyze_runtime_bytecode` path with preloaded Gradient Boosting bundle | Per-call model reload from disk; HTTP transport |
| **HTTP request latency** | Local request/response to `/api/analyze` | Not combined with internal backend timers |

These results are laboratory sequential benchmarks. They do **not** demonstrate live Ethereum mempool latency or a production SLA.

---

## F. Experimental Environment and Configuration

Values taken from `phase5_extra_metrics_gb_pruned155.json` (`environment` block). Nothing below was invented.

| Item | Recorded value |
|---|---|
| Operating system | Windows 11 |
| CPU | Intel64 Family 6 Model 197 Stepping 2, GenuineIntel |
| Python version | 3.13.14 |
| scikit-learn version | 1.9.1 |
| NumPy version | 2.5.2 |
| Model artifact | `phase5_model_gb_pruned155.joblib` |
| Feature group | `pruned155` |
| Feature count | 155 |
| Timing method | `time.perf_counter` |
| Execution mode | sequential |
| Classification workload | 100 featurized test rows |
| Runtime latency workload | 100 valid bytecodes; warm-up 3; 2 reps (n = 200) |
| Throughput workload | 100 contracts × 3 passes = 300 processed |
| HTTP sample size | 20 |

---

## G. Evaluation Integrity

- Frozen Gradient Boosting artifact: `phase5_model_gb_pruned155.joblib`.
- Historical GB / RF / baseline JSON result files were **not** overwritten; additional results were written to `phase5_extra_metrics_gb_pruned155.json`.
- **No training or retraining** occurred for the additional metrics or runtime benches.
- Existing frozen **accuracy (0.74)** and **macro-F1 (0.754283)** match exactly (cross-check absolute deltas = 0).
- Balanced accuracy, weighted F1, and multiclass MCC were computed on the **same 100-sample** test cohort as the frozen evaluation.

---

## H. Limitations and Threats to Validity

1. **Content-level leakage risk:** Identical SolidiFI contract pairs exist across train and held-out partitions.  
2. **Source–class entanglement:** `tx_origin` examples are sourced only from SolidiFI.  
3. **No benign/clean class:** This evaluation does not establish benign-versus-malicious detection performance.  
4. **Static CFG limits:** Some dynamic stack-based jumps cannot be resolved by static CFG extraction.  
5. **Runtime scope:** Results are sequential laboratory benchmarks, not proof of production-scale or live Ethereum mempool performance.  
6. **Coverage gap:** Classification metrics cover **100** usable contracts, not the full **108**-contract locked test split.

This evaluation is **not** described as leakage-free, and no live mempool SLA is claimed.

---

## I. Reproducibility

Commands used (PowerShell):

```powershell
py -3.13 scripts/phase5_smoke_baseline.py --extra-metrics --model-artifact phase5_model_gb_pruned155.joblib --out phase5_extra_metrics_gb_pruned155.json
py -3.13 scripts/phase5_smoke_baseline.py --bench-runtime --model-artifact phase5_model_gb_pruned155.joblib --out phase5_extra_metrics_gb_pruned155.json
```

