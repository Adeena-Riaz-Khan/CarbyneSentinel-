# CarbyneSentinel — dataset & prototype repo

Smart-contract **data factory** + **React operator console** for the CarbyneSentinel FYP.  
FYP-1 data work through **Phase 5** (features + smoke baseline) is done. Full detectors (GCN / QLoRA / live Sepolia) are FYP-2.

## Where we left off

| Milestone | Status |
|-----------|--------|
| Schema + gold core (493) + side pools | Done |
| Obfuscation ladder (~401 verified children) | Done |
| Phases 1–4 unique seeds + locked family split (720 → 504 / 108 / 108) | Done |
| Bytecode recovery for locked missing bins | Done (usable set) |
| Disasm → CFG → Fingerprint v0 → 159-D matrix | Done (**661** featurized rows) |
| Smoke baseline (`StandardScaler` + balanced logistic regression) | Done (**~0.691** test macro F1) |
| GCN / QLoRA / fusion / Sepolia | Not started (FYP-2) |

Primary smoke result (local artifact): `processed/results/phase5/phase5_baseline_macro_f1.json`.

## What git has vs what stays local

**In git (members use this):** `target_schema.json`, `scripts/`, `frontend/` source, this README, [`guides/MEMBER_GUIDE.md`](guides/MEMBER_GUIDE.md).

**Local only (too large / private — share offline or rebuild):** `Raw/`, `data/`, `processed/` bytecode·source·features·masters, `reports/`, `docs/`.  
Without those local folders you can read the code, but you cannot re-run Phase 5 until the lead shares the data pack or you rebuild from Raw.

## Quick layout

| Path | What it is |
|------|------------|
| `target_schema.json` | Shared contract record schema (do not rename) |
| `scripts/` | Processors, augment, Phases 1–5, `scripts/features/` |
| `frontend/` | React + Vite operator console prototype |
| `guides/MEMBER_GUIDE.md` | Dataset map + how to continue |
| `Raw/` | Original corpora *(local)* |
| `data/processed/` | JSONL pools, obfuscation bench, phase4 splits *(local)* |
| `processed/` | Masters, compiled bins, Phase 5 matrix/results *(local)* |

## Start here

1. Read [`guides/MEMBER_GUIDE.md`](guides/MEMBER_GUIDE.md) — schema, paths, Phase 5 commands.
2. Confirm you have the local data pack (or rebuild steps from the lead).
3. Frontend demo: `cd frontend && npm install && npm run dev`.

## Do not move without updating scripts

- `processed/master_dataset_phase2.json` (default master)
- `processed/master_dataset.json` (493 gold core)
- `data/processed/phase4_splits.json` and other phase JSON / JSONL
- `target_schema.json`
- `processed/features/phase5/` (matrix the smoke baseline reads)

## Next for the team

1. Stronger models on the locked split (CFG → GCN, then QLoRA / fusion).  
2. Optional: recover more of the ~59 locked ids still without features.  
3. Keep evaluation on the same 504 / 108 / 108 family lock — do not reshuffle.
