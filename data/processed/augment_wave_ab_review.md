# Wave A-E + stacks batch review

- Verified variants: 401
- Of which stacked (2+ techniques): 192
- Of which triple stacks: 21
- Failed log rows: 142

### By technique / stack
- comment_manipulation+dead_code_insertion: 59
- dead_code_insertion: 24
- comment_manipulation: 24
- identifier_renaming: 22
- literal_format_rewrite: 19
- identifier_renaming+dead_code_insertion: 19
- literal_format_rewrite+function_extraction: 19
- dead_code_insertion+opaque_predicate: 19
- comment_manipulation+condition_rewriting: 19
- independent_stmt_reorder: 15
- function_extraction: 15
- condition_rewriting: 15
- opaque_predicate: 15
- temp_var_introduction: 15
- equiv_expr_decomposition: 15
- temp_var_introduction+unrelated_state_var_insertion: 15
- control_flow_flattening: 10
- irrelevant_helper_insertion: 10
- unrelated_state_var_insertion: 10
- dead_code_insertion+irrelevant_helper_insertion: 10
- comment_manipulation+dead_code_insertion+opaque_predicate: 9
- opaque_predicate+unrelated_state_var_insertion: 6
- identifier_renaming+temp_var_introduction: 5
- identifier_renaming+temp_var_introduction+unrelated_state_var_insertion: 3
- literal_format_rewrite+function_extraction+irrelevant_helper_insertion: 3
- comment_manipulation+condition_rewriting+unrelated_state_var_insertion: 3
- dead_code_insertion+opaque_predicate+irrelevant_helper_insertion: 3

### Augment variants by class
- tx_origin: 132
- time_manipulation: 105
- front_running: 67
- bad_randomness: 37
- denial_of_service: 31
- access_control: 20
- short_address: 5
- reentrancy: 4

### By level
- structural: 151
- control_flow: 87
- lexical: 65
- contract_level: 63
- data_flow: 35

### Class imbalance: master vs combined

| class | master | combined | delta |
|---|---:|---:|---:|
| tx_origin | 50 | 182 | +132 |
| time_manipulation | 55 | 160 | +105 |
| unchecked_call | 152 | 152 | +0 |
| front_running | 54 | 121 | +67 |
| reentrancy | 81 | 85 | +4 |
| integer_overflow | 65 | 65 | +0 |
| bad_randomness | 8 | 45 | +37 |
| access_control | 18 | 38 | +20 |
| denial_of_service | 6 | 37 | +31 |
| short_address | 1 | 6 | +5 |
| other | 3 | 3 | +0 |

Singles A-E + 2/3-technique stacks for minority rebalance and evasion stress.

Outputs: `C:\Users\adeen\Desktop\dataset\data\processed\obfuscation_benchmark.jsonl`
