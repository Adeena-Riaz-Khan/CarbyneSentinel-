# Wave A1-A3 + B1-B3 batch review

## Counts
- Seeds in manifest: 29
- Verified variants (benchmark): 119
- Failed / rejected (all-time log rows): 25

### By technique
- dead_code_insertion: 24
- comment_manipulation: 24
- identifier_renaming: 22
- literal_format_rewrite: 19
- independent_stmt_reorder: 15
- function_extraction: 15

### By primary class
- tx_origin: 47
- front_running: 27
- time_manipulation: 24
- bad_randomness: 11
- reentrancy: 4
- short_address: 3
- denial_of_service: 3

### By transformation_level
- lexical: 65
- structural: 54

## LLM vs bytecode lesson (advisor checkpoint)

Level 1 techniques (`identifier_renaming`, `comment_manipulation`,
`literal_format_rewrite`) are **lexical** / LLM-source track.

- Lexical variants: 65
- Lexical with bytecode identical to parent: 0
- Structural variants (B1-B3): 54

Do **not** treat Level 1 as a GCN/fingerprint stress test.
Level 2 (`dead_code_insertion`, `independent_stmt_reorder`, `function_extraction`)
changes structural / call-graph surface and is the GCN/fingerprint track.

## Next

Level 1-2 singles for this seed set are in place. Do **not** start Level 3
(control-flow) until committee demo / review of these counts.

Outputs: `C:\Users\adeen\Desktop\dataset\data\processed\obfuscation_benchmark.jsonl` / `C:\Users\adeen\Desktop\dataset\data\processed\obfuscation_failed.jsonl`
