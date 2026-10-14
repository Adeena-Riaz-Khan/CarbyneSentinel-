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

# Or one technique at a time
python scripts/augment/comment_manipulation.py
python scripts/augment/literal_format_rewrite.py
python scripts/augment/independent_stmt_reorder.py --limit 15
python scripts/augment/function_extraction.py --limit 15
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
Do not start Level 3 until Level 1-2 review is accepted.
