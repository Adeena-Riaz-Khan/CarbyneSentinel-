# Raw Dataset Reference

## solidifi/
Format: .sol files with injected bugs + a mapping file indicating injected bug line numbers.
Labels: precise, since bugs were injected by SolidiFI's own script.

## smartbugs/ (SmartBugs Curated)
Format: .sol files + vulnerabilities.json mapping file -> DASP-taxonomy vulnerability tags.
Labels: hand-labeled by researchers, treated as reliable ("gold standard").

## dapscan/ (DAppSCAN)
Format: .sol files, labels derived from real professional audit report findings.
Labels: reliable but the repo's internal folder structure is less standardized -
expect inconsistent naming conventions across subfolders.

## defihacklabs/
Format: Foundry exploit reproduction scripts per historical hack, NOT clean labeled
.sol files. The actual vulnerable contract's source usually needs to be pulled
separately (e.g. via Etherscan) using the contract address referenced in each
exploit folder.
Labels: real-world, but need to be manually derived per case.

## slither_hf/ (Slither Audited Smart Contracts, Hugging Face)
Format: a pre-packaged table (parquet/csv), contract source as a text column,
plus Slither tool output as another column. Already has train/val/test splits.
Labels: tool-derived (Slither), not human/audit-verified - treat as slightly
less reliable than smartbugs/dapscan labels, useful mainly as a "benign pool"
after filtering to contracts Slither found clean.