# Dataset map (1 page for members)

Read files in this order: **schema → master → JSONL → augment**.

## 1. Schema — `target_schema.json`

Defines the shared record shape for every contract (labels, paths, compiler flags, transform fields).  
All processed outputs should match these field names.

Key transform fields: `parent_contract_id`, `transformation_level`, `transformation_techniques`, `obfuscation_severity`, `exploit_verified_after_transform`.

## 2. Master — `processed/master_dataset.json`

Primary labeled set from SolidiFI + SmartBugs (~493 contracts).  
Each row: `contract_id`, vulnerability label(s), `source_code_path`, `bytecode_path`, `compiled_successfully`.

Quick summary: `processed/summary.md`  
Class counts chart/data: `reports/class_counts.csv`

## 3. JSONL pools — `data/processed/*.jsonl`

Extra / side datasets in the same schema style (one JSON object per line):

| File | What it is |
|---|---|
| `defihacklabs_exploits.jsonl` | Real exploit reproductions |
| `dappscan_vulnerable.jsonl` | Audit-derived vulns |
| `dive_vulnerable.jsonl` | DIVE vulnerable set |
| `defi_intent_bench.jsonl` | Intent-bench rows |
| `benign_pool/slither_benign.jsonl` | Clean/benign pool |
| `benign_pool/dive_benign.jsonl` | Clean/benign pool |

## 4. Augment — severity-ladder variants

Custom obfuscation track (one technique per variant; same vuln label as parent):

| File / folder | What it is |
|---|---|
| `data/processed/augment_seeds_wave_ab.json` | Seed contracts used for Waves A/B |
| `data/processed/obfuscation_benchmark.jsonl` | Verified variants (use this) |
| `data/processed/obfuscation_failed.jsonl` | Compile/verify rejects |
| `data/processed/augment_wave_ab_review.md` | Counts + LLM vs bytecode lesson |
| `processed/source/augmented/<technique>/` | Variant `.sol` sources |
| `processed/bytecode/augmented/<technique>/` | Compiled bins when available |
| `scripts/augment/` | Scripts to regenerate waves |

Done so far: Level 1–2 (A1–A3, B1–B3). Level 3+ not started.

## Raw sources

`Raw/` — original downloads (SolidiFI, SmartBugs, DIVE, etc.).  
`README_DATASETS.md` — short notes on each raw source.

## Do not commit (see `.gitignore`)

`docs/`, `*.pdf`, `*.tex`, `NOTES.md`, and other personal notes.
