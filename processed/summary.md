# Processing summary — SolidiFI + SmartBugs (tonight scope)

**Total contracts:** 493

## By source dataset

- solidifi: 350
- smartbugs: 143

## By label

- vulnerable: 493

## By primary_vulnerability_type

- unchecked_call: 152
- reentrancy: 81
- integer_overflow: 65
- time_manipulation: 55
- front_running: 54
- tx_origin: 50
- access_control: 18
- bad_randomness: 8
- denial_of_service: 6
- other: 3
- short_address: 1

## Compilation

- compiled successfully: **466** / 493
- failed: **27** / 493
- solidifi success: 350 / 350
- smartbugs success: 116 / 143
- SolidiFI pin: 0.4.26; fallback: 0.5.17
- SolidiFI compiled with 0.4.26 as requested: **23** / 350
- SolidiFI contracts that needed fallback to 0.5.17: **327** / 350
- Fallback reason (systematic): injected bug snippets use `address payable`, which is a **0.5.0+** syntax. Pragma is `>=0.4.22 <0.6.0`, so 0.4.26 is within the declared range but rejects `payable` on address. **0.5.17 is the correct practical compiler for most of this set.**
- SmartBugs failures (27): mostly (a) `py-solc-x` cannot install solc **&lt;0.4.11**, or (b) Windows `0.4.15` nightly build rejects `pragma solidity ^0.4.15`. Entries kept with `compiled_successfully=false` (not dropped).

Fallback contract_ids: see `logs/compile_log.json` (`used_fallback: true`). First few: SOLIDIFI_Re-entrancy_buggy_1 … (327 total).

## Compile failures (all)

- `SMARTBUGS_access_control_parity_wallet_bug_1` (solc 0.4.9): compile error with solc 0.4.9: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_access_control_parity_wallet_bug_2` (solc 0.4.9): compile error with solc 0.4.9: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_access_control_rubixi` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:8:2: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
 pragma solidity ^0.4.15;
 ^----------------------^
<stdin>:83:42: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
                 if (collectedFees == 0) throw;
                                         ^---^
<stdin>:93:42: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
                 if (collectedFees == 0) throw;
                                         ^---^
<stdin>:100:58: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
                 if (collectedFees == 0 || _pcent > 100) throw;
                                                         ^---^
<stdin>:113:50: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
                 if (_mult > 300 || _mult < 120) throw;
                                                 ^---^
<stdin>:119:33: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
                 if (_fee > 10) throw;
                                ^---^
<stdin>:74:26: Warning: Failure condition of 'send' ignored. Consider using 'transfer' instead.
                         participants[payoutOrder].etherAddress.send(payoutToSend);
                         ^-------------------------------------------------------^
<stdin>:85:18: Warning: Failure condition of 'send' ignored. Consider using 'transfer' instead.
                 creator.send(collectedFees);
                 ^-------------------------^
<stdin>:95:18: Warning: Failure condition of 'send' ignored. Consider using 'transfer' instead.
                 creator.send(_amt);
                 ^----------------^
<stdin>:103:18: Warning: Failure condition of 'send' ignored. Consider using 'transfer' instead.
                 creator.send(feesToCollect);
                 ^-------------------------^
- `SMARTBUGS_access_control_simple_suicide` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_access_control_unprotected0` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:7:2: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
 pragma solidity ^0.4.15;
 ^----------------------^
- `SMARTBUGS_arithmetic_insecure_transfer` (solc 0.4.10): compile error with solc 0.4.10: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_arithmetic_integer_overflow_1` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:7:2: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
 pragma solidity ^0.4.15;
 ^----------------------^
- `SMARTBUGS_arithmetic_timelock` (solc 0.4.10): compile error with solc 0.4.10: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_bad_randomness_blackjack` (solc 0.4.9): compile error with solc 0.4.9: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_bad_randomness_lottery` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_bad_randomness_lucky_doubler` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_denial_of_service_auction` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:7:1: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
pragma solidity ^0.4.15;
^----------------------^
- `SMARTBUGS_denial_of_service_list_dos` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_front_running_odds_and_evens` (solc 0.4.2): compile error with solc 0.4.2: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_other_name_registrar` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:7:1: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
pragma solidity ^0.4.15;
^----------------------^
<stdin>:23:9: Warning: Variable is declared as a storage pointer. Use an explicit "storage" keyword to silence this warning.
        NameRecord newRecord;
        ^------------------^
<stdin>:23:9: Warning: Uninitialized storage pointer. Did you mean '<type> memory newRecord'?
        NameRecord newRecord;
        ^------------------^
- `SMARTBUGS_reentrancy_etherbank` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_reentrancy_etherstore` (solc 0.4.10): compile error with solc 0.4.10: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_reentrancy_reentrancy_simple` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:7:2: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
 pragma solidity ^0.4.15;
 ^----------------------^
<stdin>:25:14: Warning: "throw" is deprecated in favour of "revert()", "require()" and "assert()".
             throw;
             ^---^
- `SMARTBUGS_reentrancy_simple_dao` (solc 0.4.2): compile error with solc 0.4.2: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_time_manipulation_ether_lotto` (solc 0.4.15): compile error with solc 0.4.15: An error occurred during execution
> command: `C:\Users\adeen\.solcx\solc-v0.4.15\solc.exe --combined-json bin,bin-runtime -`
> return code: `1`
> stdout:

> stderr:
Warning: This is a pre-release compiler version, please do not use it in production.
<stdin>:8:2: Error: Source file requires different compiler version (current compiler is 0.4.15-nightly.2017.8.10+commit.8b45bddb.Windows.msvc - note that nightly builds are considered to be strictly less than the released version
 pragma solidity ^0.4.15;
 ^----------------------^
- `SMARTBUGS_time_manipulation_governmental_survey` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_time_manipulation_lottopollo` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_unchecked_low_level_calls_0x0cbe050f75bc8f8c2d6c0d249fea125fd6e1acc9` (solc 0.4.10): compile error with solc 0.4.10: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_unchecked_low_level_calls_0x89c1b3807d4c67df034fffb62f3509561218d30b` (solc 0.4.9): compile error with solc 0.4.9: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_unchecked_low_level_calls_etherpot_lotto` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_unchecked_low_level_calls_king_of_the_ether_throne` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11
- `SMARTBUGS_unchecked_low_level_calls_mishandled` (solc 0.4.0): compile error with solc 0.4.0: py-solc-x does not support solc versions <0.4.11

## Notes

- Scope tonight: `raw/solidifi/buggy_contracts/` + `raw/smartbugs/` only.
- DAppSCAN, DeFiHackLabs, DIVE, raw/dive/, temp_dive/ were not processed.
- `llm_fields.explanation` / snippets left null (no LLM generation).
- `duplicate_of` left null (no cross-dataset dedup tonight).
- tx_origin kept as its own vocabulary class (not folded into access_control).

