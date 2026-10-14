#!/usr/bin/env python3
from __future__ import annotations
import csv
import json
import re
import shutil
import traceback
from collections import Counter
from pathlib import Path
from solcx import compile_source, install_solc, set_solc_version
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'raw'
PROCESSED = ROOT / 'processed'
SOURCE_OUT = PROCESSED / 'source'
BYTECODE_OUT = PROCESSED / 'bytecode'
LOG_DIR = PROCESSED / 'logs'
CLASS_ID = {'reentrancy': 0, 'integer_overflow': 1, 'access_control': 2, 'unchecked_call': 3, 'time_manipulation': 4, 'front_running': 5, 'bad_randomness': 6, 'denial_of_service': 7, 'short_address': 8, 'tx_origin': 9, 'other': 10, 'none': 11}
SOLIDIFI_FOLDER_MAP = {'Re-entrancy': 'reentrancy', 'Overflow-Underflow': 'integer_overflow', 'tx.origin': 'tx_origin', 'Unchecked-Send': 'unchecked_call', 'Unhandled-Exceptions': 'unchecked_call', 'Timestamp-Dependency': 'time_manipulation', 'TOD': 'front_running'}
SMARTBUGS_CAT_MAP = {'reentrancy': 'reentrancy', 'arithmetic': 'integer_overflow', 'access_control': 'access_control', 'unchecked_low_level_calls': 'unchecked_call', 'time_manipulation': 'time_manipulation', 'front_running': 'front_running', 'bad_randomness': 'bad_randomness', 'denial_of_service': 'denial_of_service', 'short_addresses': 'short_address', 'other': 'other'}
SOLIDIFI_PIN = '0.4.26'
SOLIDIFI_FALLBACK = '0.5.17'
PRAGMA_RE = re.compile('pragma\\s+solidity\\s+([^;]+);', re.IGNORECASE)

def ensure_dirs() -> None:
    for p in [SOURCE_OUT / 'solidifi', SOURCE_OUT / 'smartbugs', BYTECODE_OUT / 'solidifi', BYTECODE_OUT / 'smartbugs', LOG_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def sanitize_id_part(s: str) -> str:
    return re.sub('[^A-Za-z0-9_.-]+', '_', s)

def parse_buglog_lines(buglog: Path) -> list[int]:
    if not buglog.exists():
        return []
    lines: list[int] = []
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            text = buglog.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        loc = row.get('loc') or row.get('Loc') or row.get('LOC')
        if loc is None:
            continue
        try:
            lines.append(int(str(loc).strip()))
        except ValueError:
            continue
    return sorted(set(lines))

def detect_pragma(source: str) -> str | None:
    m = PRAGMA_RE.search(source)
    return m.group(1).strip() if m else None

def install_versions(versions: set[str]) -> dict[str, str]:
    status: dict[str, str] = {}
    for v in sorted(versions):
        try:
            print(f'  installing solc {v} ...')
            install_solc(v)
            status[v] = 'installed'
        except Exception as e:
            status[v] = f'FAILED: {e}'
            print(f'  FAILED solc {v}: {e}')
    return status

def compile_contract(source: str, version: str, contract_id: str) -> tuple[bool, str | None, str]:
    try:
        set_solc_version(version)
        compiled = compile_source(source, output_values=['bin', 'bin-runtime'], solc_version=version, optimize=False)
    except Exception as e:
        return (False, None, f'compile error with solc {version}: {e}')
    if not compiled:
        return (False, None, f'solc {version} returned empty output')
    best_name = None
    best_runtime = ''
    all_bins: dict[str, str] = {}
    for full_name, data in compiled.items():
        name = full_name.split(':')[-1]
        runtime = (data.get('bin-runtime') or '').strip()
        creation = (data.get('bin') or '').strip()
        all_bins[name] = creation or runtime
        if len(runtime) > len(best_runtime):
            best_runtime = runtime
            best_name = name
    chosen = best_runtime or (all_bins.get(best_name or '', '') if best_name else '')
    if not chosen:
        for b in all_bins.values():
            if b:
                chosen = b
                break
    if not chosen:
        return (False, None, f'solc {version}: no bytecode emitted (abstract/interface only?)')
    note = f'compiled with solc {version}; primary_contract={best_name}; n_contracts={len(all_bins)}'
    return (True, chosen, note)

def write_bytecode(dataset: str, contract_id: str, bytecode: str) -> str:
    rel = f'bytecode/{dataset}/{contract_id}.bin'
    path = PROCESSED / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    hex_body = bytecode[2:] if bytecode.startswith('0x') else bytecode
    path.write_text(hex_body + '\n', encoding='utf-8')
    return rel.replace('\\', '/')

def process_solidifi(entries: list[dict], compile_log: list[dict]) -> None:
    base = RAW / 'solidifi' / 'buggy_contracts'
    if not base.exists():
        raise FileNotFoundError(f'Missing {base}')
    for folder, vtype in SOLIDIFI_FOLDER_MAP.items():
        folder_path = base / folder
        if not folder_path.exists():
            print(f'WARNING: missing SolidiFI folder {folder}')
            continue
        sols = sorted(folder_path.glob('buggy_*.sol'), key=lambda p: int(re.search('(\\d+)', p.stem).group(1)))
        for sol in sols:
            m = re.search('(\\d+)', sol.stem)
            num = m.group(1) if m else sol.stem
            cid = f'SOLIDIFI_{sanitize_id_part(folder)}_{sol.stem}'
            dest_rel = f'source/solidifi/{cid}.sol'
            dest = PROCESSED / dest_rel
            shutil.copy2(sol, dest)
            buglog = folder_path / f'BugLog_{num}.csv'
            line_nums = parse_buglog_lines(buglog)
            source_text = sol.read_text(encoding='utf-8', errors='replace')
            pragma = detect_pragma(source_text)
            notes_parts = [f"SolidiFI folder label '{folder}' -> {vtype}", 'BugLog bug-type text ignored (charset corruption); folder used as ground truth']
            if not line_nums:
                notes_parts.append(f'no usable lines from {buglog.name}')
            ok, bytecode, cnote = compile_contract(source_text, SOLIDIFI_PIN, cid)
            used_version = SOLIDIFI_PIN
            used_fallback = False
            if not ok:
                ok2, bytecode2, cnote2 = compile_contract(source_text, SOLIDIFI_FALLBACK, cid)
                if ok2:
                    ok, bytecode, cnote = (ok2, bytecode2, cnote2)
                    used_version = SOLIDIFI_FALLBACK
                    used_fallback = True
                    notes_parts.append(f'0.4.26 failed; fell back to {SOLIDIFI_FALLBACK}')
                else:
                    notes_parts.append(f'0.4.26 failed: {cnote}')
                    notes_parts.append(f'0.5.17 also failed: {cnote2}')
                    cnote = f'{cnote} | fallback: {cnote2}'
            bytecode_path = None
            if ok and bytecode:
                bytecode_path = write_bytecode('solidifi', cid, bytecode)
            compile_log.append({'contract_id': cid, 'source_dataset': 'solidifi', 'requested_version': SOLIDIFI_PIN, 'used_version': used_version if ok else None, 'used_fallback': used_fallback, 'success': ok, 'detail': cnote})
            entries.append({'contract_id': cid, 'source_dataset': 'solidifi', 'source_code_path': dest_rel.replace('\\', '/'), 'bytecode_path': bytecode_path, 'label': 'vulnerable', 'vulnerability_types': [vtype], 'primary_vulnerability_type': vtype, 'compiler_version': used_version if ok else SOLIDIFI_PIN if pragma else 'unknown', 'compiled_successfully': ok, 'duplicate_of': None, 'notes': '; '.join(notes_parts), 'gnn_fields': {'vulnerable_function_name': None, 'vulnerable_line_numbers': line_nums or None, 'vulnerability_class_id': CLASS_ID[vtype]}, 'llm_fields': {'vulnerable_function_snippet': None, 'explanation': None, 'severity': None}, '_pragma_raw': pragma})
            print(f"  [{('OK' if ok else 'FAIL')}] {cid} solc={(used_version if ok else 'n/a')}")

def process_smartbugs(entries: list[dict], compile_log: list[dict]) -> None:
    base = RAW / 'smartbugs'
    vuln_path = base / 'vulnerabilities.json'
    versions_path = base / 'versions.csv'
    if not vuln_path.exists():
        raise FileNotFoundError(vuln_path)
    vulns = json.loads(vuln_path.read_text(encoding='utf-8'))
    version_map: dict[str, str] = {}
    with versions_path.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            file_key = row.get('file') or row.get('File')
            compiled = row.get('compiled version') or row.get('compiled_version')
            if file_key and compiled:
                version_map[file_key.replace('\\', '/')] = compiled.strip()
    for item in vulns:
        rel_path = item['path'].replace('\\', '/')
        src = base / Path(*rel_path.split('/'))
        if not src.exists():
            print(f'WARNING: missing SmartBugs file {src}')
            continue
        folder_cat = Path(rel_path).parts[1] if len(Path(rel_path).parts) > 1 else 'other'
        primary = SMARTBUGS_CAT_MAP.get(folder_cat, 'other')
        types = []
        all_lines: list[int] = []
        for v in item.get('vulnerabilities') or []:
            cat = SMARTBUGS_CAT_MAP.get(v.get('category', ''), 'other')
            if cat not in types:
                types.append(cat)
            for ln in v.get('lines') or []:
                try:
                    all_lines.append(int(ln))
                except (TypeError, ValueError):
                    pass
        if primary not in types:
            types.insert(0, primary)
        all_lines = sorted(set(all_lines))
        name = item.get('name') or src.name
        cid = f'SMARTBUGS_{sanitize_id_part(folder_cat)}_{sanitize_id_part(Path(name).stem)}'
        dest_rel = f'source/smartbugs/{cid}.sol'
        dest = PROCESSED / dest_rel
        shutil.copy2(src, dest)
        source_text = src.read_text(encoding='utf-8', errors='replace')
        pragma = detect_pragma(source_text)
        compiled_ver = version_map.get(rel_path) or item.get('pragma')
        if compiled_ver and compiled_ver.startswith('^'):
            compiled_ver = compiled_ver.lstrip('^')
        notes_parts = [f"SmartBugs folder '{folder_cat}' -> primary {primary}", f'JSON categories -> {types}']
        if item.get('source'):
            notes_parts.append(f"upstream_source={item['source']}")
        ok = False
        bytecode = None
        cnote = 'no compiler version'
        used_version = compiled_ver
        if compiled_ver:
            ok, bytecode, cnote = compile_contract(source_text, compiled_ver, cid)
            if not ok:
                notes_parts.append(cnote)
        bytecode_path = None
        if ok and bytecode:
            bytecode_path = write_bytecode('smartbugs', cid, bytecode)
        compile_log.append({'contract_id': cid, 'source_dataset': 'smartbugs', 'requested_version': compiled_ver, 'used_version': used_version if ok else None, 'used_fallback': False, 'success': ok, 'detail': cnote})
        entries.append({'contract_id': cid, 'source_dataset': 'smartbugs', 'source_code_path': dest_rel.replace('\\', '/'), 'bytecode_path': bytecode_path, 'label': 'vulnerable', 'vulnerability_types': types, 'primary_vulnerability_type': primary, 'compiler_version': used_version if used_version else 'unknown', 'compiled_successfully': ok, 'duplicate_of': None, 'notes': '; '.join(notes_parts), 'gnn_fields': {'vulnerable_function_name': None, 'vulnerable_line_numbers': all_lines or None, 'vulnerability_class_id': CLASS_ID[primary]}, 'llm_fields': {'vulnerable_function_snippet': None, 'explanation': None, 'severity': None}, '_pragma_raw': pragma})
        print(f"  [{('OK' if ok else 'FAIL')}] {cid} solc={(used_version if ok else 'n/a')}")

def flatten_for_csv(entry: dict) -> dict:
    g = entry['gnn_fields']
    l = entry['llm_fields']
    return {'contract_id': entry['contract_id'], 'source_dataset': entry['source_dataset'], 'source_code_path': entry['source_code_path'], 'bytecode_path': entry['bytecode_path'], 'label': entry['label'], 'vulnerability_types': json.dumps(entry['vulnerability_types']), 'primary_vulnerability_type': entry['primary_vulnerability_type'], 'compiler_version': entry['compiler_version'], 'compiled_successfully': entry['compiled_successfully'], 'duplicate_of': entry['duplicate_of'], 'notes': entry['notes'], 'vulnerable_function_name': g['vulnerable_function_name'], 'vulnerable_line_numbers': json.dumps(g['vulnerable_line_numbers']), 'vulnerability_class_id': g['vulnerability_class_id'], 'vulnerable_function_snippet': l['vulnerable_function_snippet'], 'explanation': l['explanation'], 'severity': l['severity']}

def write_outputs(entries: list[dict], compile_log: list[dict]) -> None:
    clean = []
    for e in entries:
        c = {k: v for k, v in e.items() if not k.startswith('_')}
        clean.append(c)
    master_json = PROCESSED / 'master_dataset.json'
    master_json.write_text(json.dumps(clean, indent=2), encoding='utf-8')
    master_csv = PROCESSED / 'master_dataset.csv'
    rows = [flatten_for_csv(e) for e in clean]
    with master_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (LOG_DIR / 'compile_log.json').write_text(json.dumps(compile_log, indent=2), encoding='utf-8')
    by_source = Counter((e['source_dataset'] for e in clean))
    by_label = Counter((e['label'] for e in clean))
    by_primary = Counter((e['primary_vulnerability_type'] for e in clean))
    compiled_ok = sum((1 for e in clean if e['compiled_successfully']))
    compiled_fail = len(clean) - compiled_ok
    solidifi = [e for e in clean if e['source_dataset'] == 'solidifi']
    smartbugs = [e for e in clean if e['source_dataset'] == 'smartbugs']
    sf_ok = sum((1 for e in solidifi if e['compiled_successfully']))
    sb_ok = sum((1 for e in smartbugs if e['compiled_successfully']))
    fallback_ids = [c['contract_id'] for c in compile_log if c.get('used_fallback')]
    fail_details = [c for c in compile_log if not c['success']]
    lines = ['# Processing summary — SolidiFI + SmartBugs (tonight scope)', '', f'**Total contracts:** {len(clean)}', '', '## By source dataset', '', f"- solidifi: {by_source.get('solidifi', 0)}", f"- smartbugs: {by_source.get('smartbugs', 0)}", '', '## By label', '']
    for k, v in sorted(by_label.items()):
        lines.append(f'- {k}: {v}')
    lines += ['', '## By primary_vulnerability_type', '']
    for k, v in sorted(by_primary.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f'- {k}: {v}')
    lines += ['', '## Compilation', '', f'- compiled successfully: **{compiled_ok}** / {len(clean)}', f'- failed: **{compiled_fail}** / {len(clean)}', f'- solidifi success: {sf_ok} / {len(solidifi)}', f'- smartbugs success: {sb_ok} / {len(smartbugs)}', f'- SolidiFI pin: {SOLIDIFI_PIN}; fallback: {SOLIDIFI_FALLBACK}', f'- SolidiFI contracts that needed fallback to {SOLIDIFI_FALLBACK}: **{len(fallback_ids)}**', '']
    if fallback_ids:
        lines.append('Fallback contract_ids (first 30):')
        for cid in fallback_ids[:30]:
            lines.append(f'- {cid}')
        if len(fallback_ids) > 30:
            lines.append(f'- ... and {len(fallback_ids) - 30} more')
        lines.append('')
    if fail_details:
        lines.append('## Compile failures (all)')
        lines.append('')
        for c in fail_details:
            lines.append(f"- `{c['contract_id']}` (solc {c.get('requested_version')}): {c.get('detail')}")
        lines.append('')
    lines += ['## Notes', '', '- Scope tonight: `raw/solidifi/buggy_contracts/` + `raw/smartbugs/` only.', '- DAppSCAN, DeFiHackLabs, DIVE, raw/dive/, temp_dive/ were not processed.', '- `llm_fields.explanation` / snippets left null (no LLM generation).', '- `duplicate_of` left null (no cross-dataset dedup tonight).', '- tx_origin kept as its own vocabulary class (not folded into access_control).', '']
    (PROCESSED / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))

def main() -> None:
    print('=== ensure dirs ===')
    ensure_dirs()
    versions = {SOLIDIFI_PIN, SOLIDIFI_FALLBACK}
    versions_path = RAW / 'smartbugs' / 'versions.csv'
    with versions_path.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            v = (row.get('compiled version') or '').strip()
            if v:
                versions.add(v)
    print(f'=== installing {len(versions)} solc versions via py-solc-x ===')
    install_status = install_versions(versions)
    (LOG_DIR / 'solc_install_status.json').write_text(json.dumps(install_status, indent=2), encoding='utf-8')
    entries: list[dict] = []
    compile_log: list[dict] = []
    print('=== processing SolidiFI ===')
    process_solidifi(entries, compile_log)
    print('=== processing SmartBugs ===')
    process_smartbugs(entries, compile_log)
    print('=== writing outputs ===')
    write_outputs(entries, compile_log)
    notes_path = ROOT / 'NOTES.md'
    append = ['', '## 2026-09-23 — SolidiFI + SmartBugs overnight pass', '', f'- Processed {len(entries)} contracts into `processed/` (solidifi buggy_contracts + smartbugs only).', '- Schema uses `vulnerability_types` (list) + `primary_vulnerability_type`; `tx_origin` is its own class (id=9).', '- SolidiFI labels taken from folder names; BugLog `bug type` text ignored due to charset corruption; `loc` retained as line numbers.', f'- SolidiFI compiler pin `{SOLIDIFI_PIN}` with fallback `{SOLIDIFI_FALLBACK}`.', f"- SolidiFI fallback count: {sum((1 for c in compile_log if c.get('used_fallback')))}.", f"- Compile success: {sum((1 for e in entries if e['compiled_successfully']))} / {len(entries)}.", '- Did not touch DAppSCAN, DeFiHackLabs, DIVE, raw/dive/, or temp_dive/.', '- LLM explanation/snippet fields left null.', '']
    with notes_path.open('a', encoding='utf-8') as f:
        f.write('\n'.join(append))
    print('NOTES.md updated.')
if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
