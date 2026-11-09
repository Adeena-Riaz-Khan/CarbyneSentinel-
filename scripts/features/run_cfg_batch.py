from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts" / "augment"))

from cfg import (
    build_cfg,
    cfg_to_record,
    render_cfg_png,
    validate_cfg,
    write_cfg_dot,
    write_cfg_json,
)
from disasm import check_offsets, disassemble, parse_hex
from run_batch import BATCH_IDS, load_batch_rows, read_bytecode

OUT_DIR = ROOT / "processed" / "features" / "cfg"


def run_cfg_self_checks() -> list[str]:
    errors = []

    jump_hex = "60055600005b00"
    ins = disassemble(jump_hex)
    cfg = build_cfg(ins)
    errs = validate_cfg(ins, cfg)
    if errs:
        errors.extend(["jump toy: " + e for e in errs])
    jump_edges = [e for e in cfg["edges"] if e["type"] == "jump"]
    if len(jump_edges) != 1 or jump_edges[0]["target_offset"] != 5:
        errors.append("jump toy: expected one resolved jump to offset 5")
    jump_block = next(b for b in cfg["blocks"] if b["terminal"] == "JUMP")
    if any(
        e["source"] == jump_block["id"] and e["type"] == "sequential"
        for e in cfg["edges"]
    ):
        errors.append("jump toy: JUMP block should not have sequential edge")

    jumpi_hex = "6001600657005b00"
    ins2 = disassemble(jumpi_hex)
    cfg2 = build_cfg(ins2)
    errs2 = validate_cfg(ins2, cfg2)
    if errs2:
        errors.extend(["jumpi toy: " + e for e in errs2])
    true_edges = [e for e in cfg2["edges"] if e["type"] == "jumpi_true"]
    false_edges = [e for e in cfg2["edges"] if e["type"] == "jumpi_false"]
    if len(true_edges) != 1 or true_edges[0]["target_offset"] != 6:
        errors.append("jumpi toy: expected jumpi_true to offset 6")
    if len(false_edges) != 1:
        errors.append("jumpi toy: expected jumpi_false fall-through")

    stop_hex = "00"
    ins3 = disassemble(stop_hex)
    cfg3 = build_cfg(ins3)
    if cfg3["edges"]:
        errors.append("stop toy: terminal block should have no edges")
    if validate_cfg(ins3, cfg3):
        errors.extend(["stop toy: " + e for e in validate_cfg(ins3, cfg3)])

    dyn_hex = "6001600056"
    ins4 = disassemble(dyn_hex)
    cfg4 = build_cfg(ins4)
    unresolved = [e for e in cfg4["edges"] if e["type"] == "unresolved_jump"]
    if len(unresolved) != 1:
        errors.append("dynamic toy: expected one unresolved_jump")
    if any(e["type"] == "jump" for e in cfg4["edges"]):
        errors.append("dynamic toy: should not invent a resolved jump")

    true_dyn_hex = "355600"
    ins5 = disassemble(true_dyn_hex)
    cfg5 = build_cfg(ins5)
    errs5 = validate_cfg(ins5, cfg5)
    if errs5:
        errors.extend(["true dynamic toy: " + e for e in errs5])
    if cfg5["stats"]["unresolved_jumps"] != 1 or cfg5["stats"]["resolved_jumps"] != 0:
        errors.append("true dynamic toy: CALLDATALOAD + JUMP must be counted as 1 unresolved jump")

    return errors


def main() -> int:
    print("=== cfg self checks ===")
    self_errors = run_cfg_self_checks()
    if self_errors:
        for err in self_errors:
            print("FAIL:", err)
        return 1
    print("cfg self checks passed")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_batch_rows()
    print(f"\n=== cfg batch size {len(rows)} ===")
    print(f"output_dir={OUT_DIR}")

    ok_count = 0
    all_errors = []
    summary_rows = []
    png_count = 0

    for row in rows:
        cid = row["contract_id"]
        try:
            raw = read_bytecode(row)
            data = parse_hex(raw)
            instructions = disassemble(raw)
        except ValueError as exc:
            all_errors.append(f"{cid}: {exc}")
            print(f"\n[{cid}] ERROR {exc}")
            continue

        offset_errors = check_offsets(instructions, len(data))
        cfg = build_cfg(instructions)
        cfg_errors = validate_cfg(instructions, cfg)
        record = cfg_to_record(cid, instructions, cfg)

        json_path = OUT_DIR / f"{cid}.json"
        dot_path = OUT_DIR / f"{cid}.dot"
        png_path = OUT_DIR / f"{cid}.png"
        write_cfg_json(record, json_path)
        write_cfg_dot(record, dot_path)
        png_ok = render_cfg_png(dot_path, png_path)
        if png_ok:
            png_count += 1

        print(f"\n[{cid}]")
        print(
            f"  class={row.get('primary_vulnerability_type')} "
            f"instructions={len(instructions)} "
            f"blocks={cfg['stats']['block_count']} "
            f"edges={cfg['stats']['edge_count']} "
            f"resolved_jumps={cfg['stats']['resolved_jumps']} "
            f"unresolved_jumps={cfg['stats']['unresolved_jumps']}"
        )
        print(f"  wrote {json_path.name} {dot_path.name}" + (f" {png_path.name}" if png_ok else " (png skipped: no graphviz dot)"))

        summary_rows.append(
            {
                "contract_id": cid,
                "primary_vulnerability_type": row.get("primary_vulnerability_type"),
                "instruction_count": len(instructions),
                "block_count": cfg["stats"]["block_count"],
                "edge_count": cfg["stats"]["edge_count"],
                "resolved_jumps": cfg["stats"]["resolved_jumps"],
                "unresolved_jumps": cfg["stats"]["unresolved_jumps"],
                "json_path": str(json_path.relative_to(ROOT)).replace("\\", "/"),
                "dot_path": str(dot_path.relative_to(ROOT)).replace("\\", "/"),
                "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/") if png_ok else None,
                "validation_ok": not (offset_errors or cfg_errors),
            }
        )

        if offset_errors or cfg_errors:
            for err in offset_errors + cfg_errors:
                print("  FAIL:", err)
                all_errors.append(f"{cid}: {err}")
        else:
            ok_count += 1
            print("  validation: ok")

    summary = {
        "batch_size": len(rows),
        "processed_ok": ok_count,
        "error_count": len(all_errors),
        "png_rendered": png_count,
        "totals": {
            "blocks": sum(r["block_count"] for r in summary_rows),
            "edges": sum(r["edge_count"] for r in summary_rows),
            "resolved_jumps": sum(r["resolved_jumps"] for r in summary_rows),
            "unresolved_jumps": sum(r["unresolved_jumps"] for r in summary_rows),
        },
        "contracts": summary_rows,
    }
    summary_path = OUT_DIR / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("\n=== summary ===")
    print(f"processed_ok={ok_count}/{len(rows)}")
    print(f"error_count={len(all_errors)}")
    print(f"png_rendered={png_count}/{len(rows)}")
    print(f"total_blocks={summary['totals']['blocks']}")
    print(f"total_edges={summary['totals']['edges']}")
    print(f"total_resolved_jumps={summary['totals']['resolved_jumps']}")
    print(f"total_unresolved_jumps={summary['totals']['unresolved_jumps']}")
    print(f"summary_path={summary_path}")
    if all_errors:
        return 1
    print("cfg batch validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
