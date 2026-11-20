# Severity-ladder augmentation (Waves A/B first)

## Commands

```bash
# Pick seeds only
python scripts/augment/list_seeds.py --with-reentrancy 5

# A1 only
python scripts/augment/identifier_renaming.py --write-seeds

# B1 only
python scripts/augment/dead_code_insertion.py --write-seeds --reentrancy 5

# Full first milestone (A1 + B1 + review markdown) — resets JSONL
python scripts/augment/run_wave_ab.py

# Next waves (append-only; keeps A1+B1 rows)
python scripts/augment/run_wave_a2_b3.py

# Level 3 control-flow (C1+C2+C3, append-only)
python scripts/augment/run_wave_c.py

# Level 4-5 data-flow + contract-level (thin-class-first seeding)
python scripts/augment/run_wave_de.py

# Stacked 2/3-technique variants (append-only)
python scripts/augment/stack_augment.py --target-ok 40 --max-per-stack 6
python scripts/augment/stack_augment.py --classes time_manipulation,front_running,access_control --target-ok 45 --max-per-stack 5
python scripts/augment/stack_augment.py --triples-only --classes time_manipulation,front_running,tx_origin --max-per-stack 4

# Or one technique at a time
python scripts/augment/comment_manipulation.py
python scripts/augment/literal_format_rewrite.py
python scripts/augment/independent_stmt_reorder.py --limit 15
python scripts/augment/function_extraction.py --limit 15
python scripts/augment/condition_rewriting.py
python scripts/augment/opaque_predicate.py
python scripts/augment/control_flow_flattening.py
```

## Outputs

- `data/processed/augment_seeds_wave_ab.json` — seed manifest
- `data/processed/obfuscation_benchmark.jsonl` — verified variants
- `data/processed/obfuscation_failed.jsonl` — compile/verify failures
- `data/processed/augment_wave_ab_review.md` — batch review
- `processed/source/augmented/<technique>/` — variant `.sol` files
- `processed/bytecode/augmented/<technique>/` — compiled bins when available

## Advisor note

Level 1 (`identifier_renaming`, `comment_manipulation`, `literal_format_rewrite`) = lexical / LLM track.  
Level 2 (`dead_code_insertion`, `independent_stmt_reorder`, `function_extraction`) = structural / GCN+fingerprint track.  
Level 3 (`condition_rewriting`, `opaque_predicate`, `control_flow_flattening`) = control-flow / GCN hard stress.
