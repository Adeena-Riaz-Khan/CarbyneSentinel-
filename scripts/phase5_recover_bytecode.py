from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "features"))

from process_solidifi_smartbugs import detect_pragma
from solcx import (
    compile_source,
    get_installable_solc_versions,
    get_installed_solc_versions,
    install_solc,
    set_solc_version,
)

from disasm import check_offsets, disassemble, parse_hex

MASTER_PATH = ROOT / "processed" / "master_dataset_phase2.json"
MASTER_BACKUP_PATH = (
    ROOT / "processed" / "master_dataset_phase2.pre_phase5_bytecode_recovery.json"
)
SPLITS_PATH = ROOT / "data" / "processed" / "phase4_splits.json"
LOG_PATH = ROOT / "processed" / "logs" / "bytecode_recovery_log.json"
APPROVED_RUN_NAME = "approved_stage_a_fallback_and_stage_d"
NOVEMBER_RUN_NAME = "november_exact_batch_a"
NOVEMBER_BATCH_B_WAVE1_RUN = "november_batch_b_wave1"

SAMPLE_IDS = [
    "SMARTBUGS_denial_of_service_auction",
    "SMARTBUGS_access_control_parity_wallet_bug_1",
    "DIVE_0x1016ab41df0f9eb18dcb5bb9322368139564c30b",
    "DIVE_0x10a2f61ad6b9c9a0360f227ea8965d8f1313fb84",
    "DIVE_0x015ccd5ad83e95b5cb91b920f689ea329d096190",
    "DIVE_0x00ea6f91b00e080e816f1bb2fad71b0fe1528983",
]

NOVEMBER_EXACT_BATCH_A = [
    "DIVE_0x11571485d2b56e5d25f47e4883389dd0cde8bf36",
    "DIVE_0x77f104bbdecb179e4cc756e81636ecc18303d91d",
    "DIVE_0x411139af515804562ddca220220728c9791cc714",
    "SMARTBUGS_reentrancy_spank_chain_payment",
]

NOVEMBER_BATCH_B_WAVE1 = [
    "SMARTBUGS_arithmetic_insecure_transfer",
    "SMARTBUGS_arithmetic_timelock",
    "SMARTBUGS_reentrancy_etherstore",
    "SMARTBUGS_bad_randomness_blackjack",
    "SMARTBUGS_access_control_parity_wallet_bug_2",
    "DIVE_0xdadcdbf39bb4dfc33b40489025a1db7d1268b1db",
    "DIVE_0x0d547f8b8d7201523a834addbb27e40140ee6f18",
    "DIVE_0x99e36751a954b1c653f5faeee844179d21fa306d",
    "DIVE_0xf02904cbf8e5134aeaf45626e96b782ed233fe04",
    "DIVE_0xb444cb2bcb19180602328fa774738cb8dbd6677b",
    "DIVE_0x0860ba896cf7c9f198d1bed18de2b81510c1cdc9",
]

APPROVED_FALLBACKS: dict[str, str] = {
    "SMARTBUGS_arithmetic_insecure_transfer": "0.4.11",
    "SMARTBUGS_arithmetic_timelock": "0.4.11",
    "SMARTBUGS_reentrancy_etherstore": "0.4.11",
    "SMARTBUGS_bad_randomness_blackjack": "0.4.11",
    "SMARTBUGS_access_control_parity_wallet_bug_2": "0.4.11",
    "DIVE_0xdadcdbf39bb4dfc33b40489025a1db7d1268b1db": "0.4.11",
    "DIVE_0x0d547f8b8d7201523a834addbb27e40140ee6f18": "0.4.11",
    "DIVE_0x99e36751a954b1c653f5faeee844179d21fa306d": "0.4.11",
    "DIVE_0xf02904cbf8e5134aeaf45626e96b782ed233fe04": "0.4.18",
    "DIVE_0xb444cb2bcb19180602328fa774738cb8dbd6677b": "0.4.20",
    "DIVE_0x0860ba896cf7c9f198d1bed18de2b81510c1cdc9": "0.4.20",
}


def load_master() -> dict[str, dict]:
    rows = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    return {row["contract_id"]: row for row in rows}


def load_splits() -> dict:
    return json.loads(SPLITS_PATH.read_text(encoding="utf-8"))


def split_for_contract(splits: dict, contract_id: str) -> str | None:
    for name in ("train", "val", "test"):
        if contract_id in splits["splits"][name]:
            return name
    return None


def recovery_path_for(dataset: str, contract_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", contract_id)[:160]
    return ROOT / "processed" / "bytecode" / "phase2_recovery" / dataset / f"{safe}.bin"


def normalize_recorded_version(raw: str | None) -> tuple[str | None, str]:
    if raw is None:
        return None, "compiler_version is missing"
    text = str(raw).strip()
    if text == "" or text.lower() == "unknown":
        return None, "compiler_version is empty or unknown"
    if "nightly" in text.lower():
        return None, f"deferred: nightly compiler recorded ({text})"
    text = text[1:] if text.startswith("v") or text.startswith("V") else text
    text = text.split("+")[0].strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", text):
        return None, f"deferred: cannot parse stable solc version from '{raw}'"
    return text, "ok"


def parse_semver(text: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def pragma_allows_version(pragma: str | None, version: str) -> tuple[bool, str]:
    if pragma is None:
        return False, "no pragma found"
    expr = pragma.strip()
    target = parse_semver(version)
    if target is None:
        return False, f"invalid target version {version}"

    if expr.startswith("^"):
        base = parse_semver(expr[1:].strip())
        if base is None:
            return False, f"cannot parse caret pragma {expr}"
        upper = (base[0] + 1, 0, 0)
        if base <= target < upper:
            return True, f"pragma {expr} allows {version}"
        return False, f"pragma {expr} does not allow {version}"

    if expr.startswith(">="):
        rest = expr[2:].strip().split()[0]
        base = parse_semver(rest)
        if base is None:
            return False, f"cannot parse >= pragma {expr}"
        if target >= base:
            return True, f"pragma {expr} allows {version}"
        return False, f"pragma {expr} does not allow {version}"

    if expr.startswith(">"):
        rest = expr[1:].strip().split()[0]
        base = parse_semver(rest)
        if base is None:
            return False, f"cannot parse > pragma {expr}"
        if target > base:
            return True, f"pragma {expr} allows {version}"
        return False, f"pragma {expr} does not allow {version}"

    exact = parse_semver(expr)
    if exact is not None:
        if exact == target:
            return True, f"exact pragma {expr} matches {version}"
        return False, f"exact pragma {expr} does not allow {version}"

    return False, f"unsupported pragma form {expr}"


def compile_runtime_only(source: str, version: str) -> tuple[bool, str | None, str]:
    try:
        installed = {str(v) for v in get_installed_solc_versions()}
        if version not in installed:
            installable = {str(v) for v in get_installable_solc_versions()}
            if version not in installable:
                return False, None, f"solc {version} is not installable via py-solc-x"
            install_solc(version)
        set_solc_version(version)
        compiled = compile_source(
            source,
            output_values=["bin", "bin-runtime"],
            solc_version=version,
            optimize=False,
        )
    except Exception as exc:
        return False, None, f"compile error with solc {version}: {exc}"

    if not compiled:
        return False, None, f"solc {version} returned empty output"

    best_name = None
    best_runtime = ""
    for full_name, data in compiled.items():
        name = full_name.split(":")[-1]
        runtime = (data.get("bin-runtime") or "").strip()
        if len(runtime) > len(best_runtime):
            best_runtime = runtime
            best_name = name

    if not best_runtime:
        return (
            False,
            None,
            f"solc {version}: no bin-runtime emitted (creation bytecode not accepted)",
        )

    note = (
        f"compiled with solc {version}; primary_contract={best_name}; "
        f"n_contracts={len(compiled)}; artifact=bin-runtime"
    )
    return True, best_runtime, note


def validate_runtime_hex(bytecode: str) -> list[str]:
    errors = []
    text = bytecode or ""
    if re.search(r"__\$[A-Za-z0-9_]+\$__", text) or re.search(r"__[A-Za-z0-9_:.]{1,64}__", text):
        return ["unlinked library placeholder in runtime bytecode"]
    try:
        data = parse_hex(bytecode)
    except ValueError as exc:
        return [str(exc)]
    if len(data) == 0:
        errors.append("runtime bytecode is empty")
        return errors
    try:
        instructions = disassemble(bytecode)
    except Exception as exc:
        errors.append(f"disassemble failed: {exc}")
        return errors
    if not instructions:
        errors.append("disassemble produced zero instructions")
    errors.extend(check_offsets(instructions, len(data)))
    return errors


def write_recovery_bytecode(dataset: str, contract_id: str, bytecode: str) -> str:
    path = recovery_path_for(dataset, contract_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    hex_body = bytecode[2:] if bytecode.startswith(("0x", "0X")) else bytecode
    path.write_text(hex_body + "\n", encoding="utf-8")
    rel = path.relative_to(ROOT / "processed").as_posix()
    return rel


def classify_target(row: dict) -> tuple[str, str | None, str]:
    cid = row.get("contract_id") or ""
    dataset = row.get("source_dataset")
    recorded = str(row.get("compiler_version") or "").strip()
    version, reason = normalize_recorded_version(recorded)

    if dataset not in {"smartbugs", "dive"}:
        return "deferred", None, f"dataset {dataset} not in approved recovery"

    if cid in APPROVED_FALLBACKS:
        return (
            "approved_fallback",
            APPROVED_FALLBACKS[cid],
            f"approved fallback map; recorded={recorded}; exact_note={reason}",
        )

    if version is None:
        return "deferred", None, reason

    parts = parse_semver(version)
    if (
        dataset == "smartbugs"
        and parts is not None
        and (parts[0], parts[1]) == (0, 4)
        and parts[2] < 11
    ):
        return (
            "deferred",
            version,
            f"deferred: solc {version} below 0.4.11 unsupported by py-solc-x",
        )

    return "exact", version, "ok"


def recover_one(row: dict, splits: dict) -> dict:
    cid = row["contract_id"]
    dataset = row.get("source_dataset")
    source_rel = row.get("source_code_path")
    recorded = row.get("compiler_version")
    entry = {
        "contract_id": cid,
        "source_dataset": dataset,
        "source_path": source_rel,
        "split": split_for_contract(splits, cid),
        "class": row.get("primary_vulnerability_type"),
        "recorded_compiler_version": recorded,
        "pragma": None,
        "requested_compiler_version": None,
        "used_compiler_version": None,
        "used_fallback": False,
        "fallback_reason": None,
        "recovery_mode": None,
        "status": "failed",
        "success": False,
        "deferred": False,
        "skipped_existing": False,
        "output_path": None,
        "bytecode_bytes": None,
        "instruction_count": None,
        "validation_ok": False,
        "detail": "",
        "failure_reason": None,
    }

    mode, recorded_stable, classify_note = classify_target(row)
    entry["recovery_mode"] = mode
    entry["requested_compiler_version"] = recorded_stable

    if mode == "deferred":
        entry["status"] = "deferred"
        entry["deferred"] = True
        entry["failure_reason"] = classify_note
        entry["detail"] = classify_note
        return entry

    if not source_rel:
        entry["failure_reason"] = "missing source_code_path"
        return entry

    source_path = ROOT / "processed" / source_rel
    if not source_path.is_file():
        entry["failure_reason"] = f"source file not found: {source_rel}"
        return entry

    out_path = recovery_path_for(str(dataset), cid)
    if out_path.is_file():
        existing = out_path.read_text(encoding="utf-8").strip()
        val_errors = validate_runtime_hex(existing)
        if not val_errors:
            data = parse_hex(existing)
            instructions = disassemble(existing)
            entry["success"] = True
            entry["status"] = "skipped_existing_valid"
            entry["skipped_existing"] = True
            entry["validation_ok"] = True
            entry["output_path"] = out_path.relative_to(ROOT / "processed").as_posix()
            entry["bytecode_bytes"] = len(data)
            entry["instruction_count"] = len(instructions)
            entry["used_compiler_version"] = recorded_stable
            entry["detail"] = "existing recovery artifact validated; not overwritten"
            return entry
        entry["detail"] = "existing artifact failed validation; recompiling"

    source = source_path.read_text(encoding="utf-8", errors="replace")
    pragma = detect_pragma(source)
    entry["pragma"] = pragma

    use_version = recorded_stable
    used_fallback = False
    fallback_reason = None

    if mode == "approved_fallback":
        fb_version = APPROVED_FALLBACKS.get(cid)
        if not fb_version:
            entry["failure_reason"] = "approved_fallback mode without APPROVED_FALLBACKS entry"
            entry["detail"] = entry["failure_reason"]
            return entry
        allowed, allow_note = pragma_allows_version(pragma, fb_version)
        if not allowed:
            entry["failure_reason"] = f"approved fallback blocked: {allow_note}"
            entry["detail"] = allow_note
            return entry
        use_version = fb_version
        used_fallback = True
        fallback_reason = (
            f"original={recorded}; exact unavailable or unsupported; "
            f"approved fallback to {fb_version}; pragma={allow_note}"
        )

    entry["attempted_compiler_version"] = use_version
    ok, bytecode, detail = compile_runtime_only(source, use_version)
    entry["detail"] = detail
    entry["used_fallback"] = used_fallback
    entry["fallback_reason"] = fallback_reason
    if not ok or not bytecode:
        entry["failure_reason"] = detail
        return entry

    val_errors = validate_runtime_hex(bytecode)
    if val_errors:
        entry["failure_reason"] = "; ".join(val_errors)
        entry["detail"] = detail + " | validation failed"
        return entry

    out_rel = write_recovery_bytecode(str(dataset), cid, bytecode)
    data = parse_hex(bytecode)
    instructions = disassemble(bytecode)
    entry["success"] = True
    entry["validation_ok"] = True
    entry["status"] = "recovered_fallback" if used_fallback else "recovered_exact"
    entry["used_compiler_version"] = use_version
    entry["output_path"] = out_rel
    entry["bytecode_bytes"] = len(data)
    entry["instruction_count"] = len(instructions)
    if used_fallback and fallback_reason:
        entry["detail"] = detail + " | " + fallback_reason
    return entry


def approved_target_ids(master: dict[str, dict], splits: dict) -> list[str]:
    ids = []
    for name in ("train", "val", "test"):
        for cid in splits["splits"][name]:
            row = master[cid]
            if row.get("source_dataset") not in {"smartbugs", "dive"}:
                continue
            bp = row.get("bytecode_path")
            if bp and (ROOT / "processed" / bp).is_file():
                continue
            ids.append(cid)
    return ids


def append_log(run_name: str, entries: list[dict]) -> dict:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.is_file():
        payload = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    else:
        payload = {"runs": []}

    summary = {
        "attempted": len(entries),
        "recovered_exact": sum(1 for e in entries if e.get("status") == "recovered_exact"),
        "recovered_fallback": sum(
            1 for e in entries if e.get("status") == "recovered_fallback"
        ),
        "skipped_existing_valid": sum(
            1 for e in entries if e.get("status") == "skipped_existing_valid"
        ),
        "failed": sum(1 for e in entries if e.get("status") == "failed"),
        "deferred": sum(1 for e in entries if e.get("status") == "deferred"),
        "success_total": sum(1 for e in entries if e.get("success")),
    }
    payload["runs"].append({"name": run_name, "entries": entries, "summary": summary})
    LOG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return summary


def load_approved_success_entries() -> list[dict]:
    payload = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    chosen = None
    for run in payload.get("runs", []):
        if run.get("name") == APPROVED_RUN_NAME:
            chosen = run
    if chosen is None:
        raise SystemExit(f"missing recovery run named {APPROVED_RUN_NAME}")
    return [e for e in chosen["entries"] if e.get("success")]


def validate_success_entries(entries: list[dict], master: dict[str, dict]) -> dict:
    results = []
    path_owners: dict[str, str] = {}
    conflicts = []
    for entry in entries:
        cid = entry["contract_id"]
        row = master.get(cid)
        item = {
            "contract_id": cid,
            "status": entry.get("status"),
            "used_fallback": bool(entry.get("used_fallback")),
            "recorded_compiler_version": entry.get("recorded_compiler_version"),
            "used_compiler_version": entry.get("used_compiler_version"),
            "output_path": entry.get("output_path"),
            "ok": False,
            "errors": [],
        }
        if row is None:
            item["errors"].append("contract missing from master")
            results.append(item)
            continue
        if row.get("source_code_path") != entry.get("source_path"):
            item["errors"].append("source_path mismatch vs master")
        if row.get("source_dataset") != entry.get("source_dataset"):
            item["errors"].append("source_dataset mismatch vs master")
        if not entry.get("output_path"):
            item["errors"].append("missing output_path")
            results.append(item)
            continue
        out_rel = entry["output_path"]
        if out_rel in path_owners and path_owners[out_rel] != cid:
            conflicts.append((out_rel, path_owners[out_rel], cid))
            item["errors"].append(
                f"duplicate artifact mapping with {path_owners[out_rel]}"
            )
        else:
            path_owners[out_rel] = cid
        path = ROOT / "processed" / out_rel
        if not path.is_file():
            item["errors"].append("artifact file missing")
            results.append(item)
            continue
        expected = recovery_path_for(str(row.get("source_dataset")), cid)
        if path.resolve() != expected.resolve():
            item["errors"].append("artifact path does not match contract/dataset mapping")
        raw = path.read_text(encoding="utf-8").strip()
        val_errors = validate_runtime_hex(raw)
        item["errors"].extend(val_errors)
        if "bin-runtime" not in str(entry.get("detail") or "") and entry.get(
            "status"
        ) != "skipped_existing_valid":
            if entry.get("status") == "recovered_exact" or entry.get("status") == "recovered_fallback":
                if "artifact=bin-runtime" not in str(entry.get("detail") or ""):
                    item["errors"].append("recovery detail missing bin-runtime marker")
        if entry.get("status") == "skipped_existing_valid" and not entry.get(
            "skipped_existing"
        ):
            item["errors"].append("skipped status without skipped_existing flag")
        if not item["errors"]:
            data = parse_hex(raw)
            instructions = disassemble(raw)
            item["ok"] = True
            item["bytecode_bytes"] = len(data)
            item["instruction_count"] = len(instructions)
        results.append(item)

    ok_items = [r for r in results if r["ok"]]
    bad_items = [r for r in results if not r["ok"]]
    return {
        "validated_ok": len(ok_items),
        "validated_failed": len(bad_items),
        "conflicts": conflicts,
        "ok_items": ok_items,
        "bad_items": bad_items,
        "exact_ok": sum(1 for r in ok_items if r["status"] in {"recovered_exact", "skipped_existing_valid"} and not r["used_fallback"]),
        "fallback_ok": sum(1 for r in ok_items if r["used_fallback"] or r["status"] == "recovered_fallback"),
        "skipped_existing_ok": sum(1 for r in ok_items if r["status"] == "skipped_existing_valid"),
    }


def unavailable_reasons(master: dict[str, dict], splits: dict, recovery_entries: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for entry in recovery_entries:
        cid = entry.get("contract_id")
        if not cid:
            continue
        prev = by_id.get(cid)
        prev_specific = bool(prev and (prev.get("failure_reason") or prev.get("detail")))
        cur_specific = bool(entry.get("failure_reason") or entry.get("detail"))
        if prev is None or cur_specific or not prev_specific:
            by_id[cid] = entry
    rows = []
    for name in ("train", "val", "test"):
        for cid in splits["splits"][name]:
            row = master[cid]
            bp = row.get("bytecode_path")
            if bp and (ROOT / "processed" / bp).is_file():
                continue
            rec = by_id.get(cid)
            reason = "unknown"
            if row.get("source_dataset") == "dapscan":
                reason = "deferred: DAppSCAN multi-file/import recovery not in this stage"
            elif rec is not None:
                reason = rec.get("failure_reason") or rec.get("detail") or rec.get("status")
            rows.append(
                {
                    "contract_id": cid,
                    "split": name,
                    "class": row.get("primary_vulnerability_type"),
                    "source_dataset": row.get("source_dataset"),
                    "recorded_compiler_version": row.get("compiler_version"),
                    "reason": reason,
                }
            )
    return rows


def integrate_master(ok_items: list[dict], success_entries: list[dict]) -> dict:
    entry_by_id = {e["contract_id"]: e for e in success_entries}
    rows = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    if not MASTER_BACKUP_PATH.is_file():
        MASTER_BACKUP_PATH.write_text(
            json.dumps(rows, indent=2) + "\n", encoding="utf-8"
        )
        backed_up = True
    else:
        backed_up = False

    updated = 0
    for row in rows:
        cid = row["contract_id"]
        item = next((x for x in ok_items if x["contract_id"] == cid), None)
        if item is None:
            continue
        entry = entry_by_id[cid]
        row["bytecode_path"] = item["output_path"]
        row["compiled_successfully"] = True
        row["bytecode_recovery"] = {
            "status": entry.get("status"),
            "used_fallback": bool(entry.get("used_fallback")),
            "fallback_reason": entry.get("fallback_reason"),
            "recorded_compiler_version": entry.get("recorded_compiler_version"),
            "used_compiler_version": entry.get("used_compiler_version"),
            "output_path": item["output_path"],
            "validated": True,
            "artifact": "bin-runtime",
            "skipped_existing": bool(entry.get("skipped_existing")),
        }
        updated += 1

    MASTER_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return {"updated_rows": updated, "backup_path": str(MASTER_BACKUP_PATH), "backup_written": backed_up}


def audit_after_integration(master_rows: list[dict], splits: dict) -> dict:
    by_id = {r["contract_id"]: r for r in master_rows}
    counts = {}
    for name in ("train", "val", "test"):
        ids = splits["splits"][name]
        counts[name] = {
            "locked_ids": len(ids),
            "unique_ids": len(set(ids)),
            "usable_bytecode": 0,
            "classes": {},
        }
        class_counts: dict[str, int] = {}
        for cid in ids:
            row = by_id[cid]
            bp = row.get("bytecode_path")
            usable = bool(bp) and (ROOT / "processed" / bp).is_file()
            if usable:
                counts[name]["usable_bytecode"] += 1
                cls = row.get("primary_vulnerability_type") or "unknown"
                class_counts[cls] = class_counts.get(cls, 0) + 1
        counts[name]["classes"] = dict(sorted(class_counts.items()))

    family_to_split = splits.get("family_to_split") or {}
    leakage_ok = splits.get("leakage_ok")
    return {
        "split_counts": counts,
        "leakage_ok": leakage_ok,
        "n_seed_families": splits.get("n_seed_families"),
        "family_map_size": len(family_to_split),
        "master_size": len(master_rows),
        "master_unique_ids": len(by_id),
    }


def run_validate_integrate(run_name: str | None = None) -> int:
    master = load_master()
    splits = load_splits()
    payload = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    target_run = run_name or APPROVED_RUN_NAME
    approved = None
    for run in payload.get("runs", []):
        if run.get("name") == target_run:
            approved = run
    if approved is None:
        print(f"missing run {target_run}")
        return 1

    success_entries = [e for e in approved["entries"] if e.get("success")]
    print(f"run={target_run} validating success entries={len(success_entries)}")
    validation = validate_success_entries(success_entries, master)
    print(
        f"validation ok={validation['validated_ok']} failed={validation['validated_failed']} "
        f"exact_ok={validation['exact_ok']} fallback_ok={validation['fallback_ok']} "
        f"skipped_existing_ok={validation['skipped_existing_ok']} conflicts={len(validation['conflicts'])}"
    )
    if validation["bad_items"]:
        for item in validation["bad_items"][:20]:
            print(f"[VAL-FAIL] {item['contract_id']}: {item['errors']}")
        print("integration aborted: validation failures present")
        payload.setdefault("audits", []).append(
            {"name": "validate_before_integrate", "validation": {
                "validated_ok": validation["validated_ok"],
                "validated_failed": validation["validated_failed"],
                "bad_items": validation["bad_items"],
                "conflicts": validation["conflicts"],
            }}
        )
        LOG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 1

    integration = integrate_master(validation["ok_items"], success_entries)
    print(f"integration={integration}")

    master_rows = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    audit = audit_after_integration(master_rows, splits)
    all_entries = []
    for run in payload.get("runs", []):
        all_entries.extend(run.get("entries", []))
    unavailable = unavailable_reasons({r["contract_id"]: r for r in master_rows}, splits, all_entries)
    print(f"unavailable_after_integration={len(unavailable)}")

    payload.setdefault("audits", []).append(
        {
            "name": "validate_and_integrate",
            "validation": {
                "validated_ok": validation["validated_ok"],
                "validated_failed": validation["validated_failed"],
                "exact_ok": validation["exact_ok"],
                "fallback_ok": validation["fallback_ok"],
                "skipped_existing_ok": validation["skipped_existing_ok"],
                "conflicts": validation["conflicts"],
            },
            "integration": integration,
            "audit": audit,
            "unavailable": unavailable,
        }
    )
    LOG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for name in ("train", "val", "test"):
        info = audit["split_counts"][name]
        print(
            f"{name}: locked={info['locked_ids']} unique={info['unique_ids']} "
            f"usable={info['usable_bytecode']} classes={info['classes']}"
        )
    test_classes = audit["split_counts"]["test"]["classes"]
    missing_test = [c for c in sorted(set().union(*[set(audit["split_counts"][s]["classes"]) for s in ("train", "val", "test")])) if test_classes.get(c, 0) == 0]
    expected = [
        "access_control",
        "bad_randomness",
        "denial_of_service",
        "front_running",
        "integer_overflow",
        "reentrancy",
        "time_manipulation",
        "tx_origin",
        "unchecked_call",
    ]
    missing_test = [c for c in expected if test_classes.get(c, 0) == 0]
    print(f"test_classes_missing={missing_test}")
    print(f"tx_origin_test={test_classes.get('tx_origin', 0)}")
    print(f"leakage_ok={audit['leakage_ok']}")
    print(f"log={LOG_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--approved-recovery", action="store_true")
    parser.add_argument("--november-exact-batch-a", action="store_true")
    parser.add_argument("--november-batch-b-wave1", action="store_true")
    parser.add_argument("--validate-integrate", action="store_true")
    parser.add_argument("--integrate-run", type=str, default="")
    parser.add_argument("--ids", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.validate_integrate:
        return run_validate_integrate(args.integrate_run.strip() or None)

    chosen = sum(
        bool(x)
        for x in [
            args.sample,
            args.approved_recovery,
            args.november_exact_batch_a,
            args.november_batch_b_wave1,
            bool(args.ids.strip()),
        ]
    )
    if chosen != 1:
        print(
            "Choose exactly one of: --sample | --approved-recovery | "
            "--november-exact-batch-a | --november-batch-b-wave1 | "
            "--ids a,b,c | --validate-integrate"
        )
        return 2

    master = load_master()
    splits = load_splits()
    if args.sample:
        target_ids = list(SAMPLE_IDS)
        run_name = "sample"
    elif args.november_exact_batch_a:
        target_ids = list(NOVEMBER_EXACT_BATCH_A)
        run_name = NOVEMBER_RUN_NAME
    elif args.november_batch_b_wave1:
        target_ids = list(NOVEMBER_BATCH_B_WAVE1)
        run_name = NOVEMBER_BATCH_B_WAVE1_RUN
    elif args.ids.strip():
        target_ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        run_name = "ids"
    else:
        target_ids = approved_target_ids(master, splits)
        run_name = APPROVED_RUN_NAME

    print(f"run={run_name} targets={len(target_ids)} dry_run={args.dry_run}")
    entries = []
    for cid in target_ids:
        row = master.get(cid)
        if row is None:
            entries.append(
                {
                    "contract_id": cid,
                    "success": False,
                    "status": "failed",
                    "deferred": False,
                    "failure_reason": "contract_id not in master_dataset_phase2.json",
                }
            )
            print(f"[MISS] {cid}")
            continue

        if args.dry_run:
            mode, version, note = classify_target(row)
            print(
                f"[DRY] {cid} mode={mode} requested={version} dataset={row.get('source_dataset')} note={note}"
            )
            entries.append(
                {
                    "contract_id": cid,
                    "source_dataset": row.get("source_dataset"),
                    "recovery_mode": mode,
                    "requested_compiler_version": version,
                    "detail": note,
                    "success": False,
                    "status": "dry_run",
                }
            )
            continue

        entry = recover_one(row, splits)
        entries.append(entry)
        status = entry.get("status")
        if entry.get("success"):
            print(
                f"[OK:{status}] {cid} solc={entry.get('used_compiler_version')} "
                f"fallback={entry.get('used_fallback')} bytes={entry.get('bytecode_bytes')} "
                f"out={entry.get('output_path')}"
            )
        elif entry.get("deferred"):
            print(f"[DEFER] {cid}: {entry.get('failure_reason')}")
        else:
            print(f"[FAIL] {cid}: {entry.get('failure_reason')}")

    if not args.dry_run:
        summary = append_log(run_name, entries)
        print(f"summary={summary}")
        print(f"log={LOG_PATH}")
    else:
        print("dry-run complete; no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

