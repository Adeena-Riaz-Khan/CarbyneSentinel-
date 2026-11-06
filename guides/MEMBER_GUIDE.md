# Member guide — pick up from Phase 5

Repo overview: [`README.md`](../README.md).  
Read this in order: **schema → master → locked split → features → baseline**.

FYP-1 stopped after a working **159-D feature matrix** and a **smoke logistic regression** on the locked family split (~**0.691** test macro F1). Your job is to stay on that lock and build the next models — not to rebuild the dataset from scratch unless the lead asks.

## 0. What you need on disk

Git does **not** carry heavy data. You need a local pack (from the lead) or a full rebuild:

| Need | Typical path |
|------|----------------|
| Schema (in git) | `target_schema.json` |
| Default master | `processed/master_dataset_phase2.json` |
| Locked split | `data/processed/phase4_splits.json` |
| Bytecode / source | `processed/bytecode/`, `processed/source/` |
| Phase 5 matrix (if shared) | `processed/features/phase5/feature_matrix.npz` + `meta.json` |
| Smoke result (if shared) | `processed/results/phase5/phase5_baseline_macro_f1.json` |

If the matrix is missing but bytecode + split exist, rebuild with the Phase 5 commands below.

## 1. Schema — `target_schema.json` (repo root)

Shared record shape for every contract (labels, paths, compiler flags, transform fields).  
All processed outputs should match these field names.

Key transform fields: `parent_contract_id`, `transformation_level`, `transformation_techniques`, `obfuscation_severity`, `exploit_verified_after_transform`.

## 2. Master — `processed/master_dataset_phase2.json`

**Default master** for loaders / augment / plots.  

Original gold core (SolidiFI + SmartBugs, 493 rows): `processed/master_dataset.json` — keep for Phase 1 history and Phase 2 rebuilds.

Each row: `contract_id`, vulnerability label(s), `source_code_path`, `bytecode_path`, `compiled_successfully`.

## 3. Locked split — Phases 1–4 (do not reshuffle)

| Fact | Value |
|------|--------|
| Unique seeds | 720 (9 classes × 80 cap) |
| Split | **504** train / **108** val / **108** test |
| Key | Parent **family** (children stay with parent) |
| Leakage | None across splits |

File: `data/processed/phase4_splits.json`.  
Scripts: `scripts/phase1_unique_seed_report.py` → `phase2_mine_unique_seeds.py` → `phase3_class_weights_and_cap.py` → `phase4_seed_family_split.py`.

## 4. JSONL pools — `data/processed/*.jsonl`

| File | What it is |
|------|------------|
| `defihacklabs_exploits.jsonl` | Real exploit reproductions |
| `dappscan_vulnerable.jsonl` | Audit-derived vulns |
| `dive_vulnerable.jsonl` | DIVE vulnerable set |
| `defi_intent_bench.jsonl` | Intent-bench rows |
| `benign_pool/slither_benign.jsonl` | Clean/benign pool |
| `benign_pool/dive_benign.jsonl` | Clean/benign pool |
| `obfuscation_benchmark.jsonl` | Verified obfuscation children |
| `obfuscation_failed.jsonl` | Failed verify attempts |

DIVE label CSVs: `data/DIVE/Labels/` (used by `process_dive.py` / Phase 2).

## 5. Augment — severity ladder

| Path | What it is |
|------|------------|
| `data/processed/obfuscation_benchmark.jsonl` | Verified variants |
| `processed/source/augmented/<technique>/` | Variant `.sol` |
| `processed/bytecode/augmented/<technique>/` | Compiled bins |
| `scripts/augment/` | Regenerate waves |

Obfuscation **children are not** in the Phase 5 ML matrix (seeds / locked parents only).

## 6. Phase 5 — features + smoke baseline (current tip)

Pipeline: bytecode → disasm → CFG → Fingerprint v0 + opcode ratios → **159** features → sklearn smoke train.

| Artifact | Path |
|----------|------|
| Feature tools | `scripts/features/` (`disasm`, `cfg`, `fingerprint_v0`, `opcode_freq`, …) |
| Recover missing bins | `python scripts/phase5_recover_bytecode.py` |
| Build matrix | `python scripts/phase5_build_feature_matrix.py` |
| Smoke train | `python scripts/phase5_smoke_baseline.py` |
| Matrix out | `processed/features/phase5/` |
| Metrics out | `processed/results/phase5/phase5_baseline_macro_f1.json` |

**Last logged numbers (lead machine):** 661 featurized / 59 excluded; train/val/test rows **463 / 98 / 100**; val macro F1 ~**0.690**, test macro F1 ~**0.691**.  
Stage C DAppSCAN pilots stay **out** of the matrix. `tx_origin` test support is small (7) — treat that class carefully.

### Re-run smoke only (matrix already present)

```text
python scripts/phase5_smoke_baseline.py
```

### Rebuild matrix then smoke (bytecode + phase4 split present)

```text
python scripts/phase5_build_feature_matrix.py
python scripts/phase5_smoke_baseline.py
```

Needs: `numpy`, `scikit-learn`, and the usual compile helpers if you recover bytecode (`py-solc-x`, etc.).

## 7. Frontend

```text
cd frontend
npm install
npm run dev
```

Seeded demo UI only — not live scoring.

## 8. What to work on next

1. Train stronger models on the **same** locked featurized rows / CFGs (GCN first).  
2. Do not change Phase 4 family membership without an explicit team decision.  
3. Optional data hygiene: more bytecode recovery for excluded locked ids.  
4. Keep heavy outputs under `processed/` / `data/` / `reports/` — they stay out of git.

## Raw sources

`Raw/` — original downloads (SolidiFI, SmartBugs, DIVE, …). Local only.

## Do not commit

Heavy data, docs/report LaTeX, PDFs, internal notes, `.cursor/`.  
Ship code + schema + this guide; share datasets offline.
