#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Optional
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / 'processed'
MASTER_JSON = PROCESSED / 'master_dataset.json'
OUT_JSONL = ROOT / 'data' / 'processed' / 'obfuscation_benchmark.jsonl'
FAIL_JSONL = ROOT / 'data' / 'processed' / 'obfuscation_failed.jsonl'
SEED_MANIFEST = ROOT / 'data' / 'processed' / 'augment_seeds_wave_ab.json'
AUG_SOURCE_ROOT = PROCESSED / 'source' / 'augmented'
AUG_BYTECODE_ROOT = PROCESSED / 'bytecode' / 'augmented'
MINORITY_CLASSES = ['tx_origin', 'time_manipulation', 'front_running', 'bad_randomness', 'denial_of_service', 'short_address']
DEFAULT_QUOTA: dict[str, int] = {'tx_origin': 5, 'time_manipulation': 5, 'front_running': 5, 'bad_randomness': 3, 'denial_of_service': 1, 'short_address': 1}
SOLIDITY_KEYWORDS = {'pragma', 'solidity', 'contract', 'library', 'interface', 'function', 'modifier', 'event', 'struct', 'enum', 'mapping', 'address', 'bool', 'string', 'bytes', 'byte', 'int', 'uint', 'int8', 'int16', 'int32', 'int64', 'int128', 'int256', 'uint8', 'uint16', 'uint32', 'uint64', 'uint128', 'uint256', 'bytes1', 'bytes2', 'bytes4', 'bytes8', 'bytes16', 'bytes32', 'public', 'private', 'internal', 'external', 'view', 'pure', 'payable', 'constant', 'immutable', 'memory', 'storage', 'calldata', 'returns', 'return', 'if', 'else', 'for', 'while', 'do', 'break', 'continue', 'throw', 'revert', 'require', 'assert', 'new', 'delete', 'this', 'super', 'msg', 'block', 'tx', 'now', 'wei', 'ether', 'szabo', 'finney', 'seconds', 'minutes', 'hours', 'days', 'weeks', 'years', 'true', 'false', 'null', 'import', 'from', 'as', 'is', 'using', 'for', 'indexed', 'anonymous', 'constructor', 'fallback', 'receive', 'emit', 'assembly', 'let', 'hex', 'unicode', 'type', 'var', 'fixed', 'ufixed', 'override', 'virtual', 'abstract', 'try', 'catch', 'unchecked', 'error', 'call', 'delegatecall', 'staticcall', 'send', 'transfer', 'balance', 'value', 'gas', 'sender', 'data', 'sig', 'origin', 'timestamp', 'number', 'coinbase', 'difficulty', 'gaslimit', 'blockhash', 'keccak256', 'sha256', 'ripemd160', 'ecrecover', 'addmod', 'mulmod', 'selfdestruct', 'suicide', 'log0', 'log1', 'log2', 'log3', 'log4', 'pragma', 'experimental', 'ABIEncoderV2', 'SMTChecker'}

def load_master() -> list[dict[str, Any]]:
    with MASTER_JSON.open(encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit(f'Unexpected master format: {MASTER_JSON}')
    return data

def resolve_source_path(row: dict[str, Any]) -> Path:
    rel = row.get('source_code_path') or ''
    path = PROCESSED / rel
    return path

def pick_minority_seeds(quota: Optional[dict[str, int]]=None, require_compiled: bool=True) -> list[dict[str, Any]]:
    quota = quota or DEFAULT_QUOTA
    master = load_master()
    seeds: list[dict[str, Any]] = []
    for cls, n in quota.items():
        rows = [r for r in master if r.get('primary_vulnerability_type') == cls and (r.get('compiled_successfully') if require_compiled else True) and resolve_source_path(r).is_file()]
        seeds.extend(rows[:n])
    return seeds

def pick_reentrancy_seeds(n: int=5) -> list[dict[str, Any]]:
    master = load_master()
    rows = [r for r in master if r.get('primary_vulnerability_type') == 'reentrancy' and r.get('compiled_successfully') and resolve_source_path(r).is_file()]
    return rows[:n]

def write_seed_manifest(seeds: list[dict[str, Any]], path: Path=SEED_MANIFEST) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = []
    for r in seeds:
        slim.append({'contract_id': r['contract_id'], 'source_dataset': r.get('source_dataset'), 'source_code_path': r.get('source_code_path'), 'bytecode_path': r.get('bytecode_path'), 'primary_vulnerability_type': r.get('primary_vulnerability_type'), 'vulnerability_types': r.get('vulnerability_types'), 'compiler_version': r.get('compiler_version'), 'compiled_successfully': r.get('compiled_successfully'), 'gnn_fields': r.get('gnn_fields'), 'llm_fields': r.get('llm_fields')})
    path.write_text(json.dumps(slim, indent=2), encoding='utf-8')
    return path

def load_seed_manifest(path: Path=SEED_MANIFEST) -> list[dict[str, Any]]:
    with path.open(encoding='utf-8') as f:
        return json.load(f)

def compile_source(source: str, version: str) -> tuple[bool, Optional[str], str]:
    from solcx import compile_source as _compile_source
    from solcx import install_solc, set_solc_version
    versions_to_try = [version]
    if version.startswith('0.4'):
        versions_to_try.append('0.5.17')
    last_err = ''
    for ver in versions_to_try:
        try:
            install_solc(ver)
            set_solc_version(ver)
            compiled = _compile_source(source, output_values=['bin', 'bin-runtime'], solc_version=ver, optimize=False)
        except Exception as e:
            last_err = str(e)
            continue
        if not compiled:
            last_err = f'solc {ver} empty output'
            continue
        best_runtime = ''
        best_name = None
        for full_name, data in compiled.items():
            name = full_name.split(':')[-1]
            runtime = (data.get('bin-runtime') or '').strip()
            if len(runtime) > len(best_runtime):
                best_runtime = runtime
                best_name = name
        if not best_runtime:
            for data in compiled.values():
                creation = (data.get('bin') or '').strip()
                if creation:
                    best_runtime = creation
                    break
        if best_runtime:
            return (True, best_runtime, f'compiled with solc {ver}; primary={best_name}')
        last_err = f'solc {ver}: no bytecode'
    return (False, None, last_err)

def read_parent_bytecode(row: dict[str, Any]) -> Optional[str]:
    rel = row.get('bytecode_path')
    if not rel:
        return None
    path = PROCESSED / rel
    if not path.is_file():
        return None
    return path.read_text(encoding='utf-8').strip().replace('0x', '').lower()

def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

def make_variant_id(parent_id: str, technique: str, idx: int=1) -> str:
    return f'{parent_id}__{technique}_v{idx}'

def build_record(*, parent: dict[str, Any], technique: str, level: str, severity: str, variant_id: str, source_rel: str, bytecode_rel: Optional[str], compiler_version: str, compiled_ok: bool, exploit_verified: Optional[bool], notes: str) -> dict[str, Any]:
    return {'contract_id': variant_id, 'source_dataset': parent.get('source_dataset'), 'source_code_path': source_rel, 'bytecode_path': bytecode_rel, 'label': 'vulnerable', 'vulnerability_types': list(parent.get('vulnerability_types') or []), 'primary_vulnerability_type': parent.get('primary_vulnerability_type'), 'compiler_version': compiler_version, 'compiled_successfully': compiled_ok, 'duplicate_of': None, 'notes': notes, 'parent_contract_id': parent.get('contract_id'), 'transformation_level': level, 'transformation_techniques': [technique], 'obfuscation_severity': severity, 'exploit_verified_after_transform': exploit_verified, 'gnn_fields': parent.get('gnn_fields'), 'llm_fields': parent.get('llm_fields')}

def save_variant_artifacts(*, technique: str, variant_id: str, source_text: str, bytecode_hex: Optional[str]) -> tuple[str, Optional[str]]:
    src_dir = AUG_SOURCE_ROOT / technique
    src_dir.mkdir(parents=True, exist_ok=True)
    src_path = src_dir / f'{variant_id}.sol'
    src_path.write_text(source_text, encoding='utf-8')
    source_rel = str(src_path.relative_to(PROCESSED)).replace('\\', '/')
    bytecode_rel = None
    if bytecode_hex:
        bc_dir = AUG_BYTECODE_ROOT / technique
        bc_dir.mkdir(parents=True, exist_ok=True)
        bc_path = bc_dir / f'{variant_id}.bin'
        hex_body = bytecode_hex[2:] if bytecode_hex.startswith('0x') else bytecode_hex
        bc_path.write_text(hex_body.strip().lower() + '\n', encoding='utf-8')
        bytecode_rel = str(bc_path.relative_to(PROCESSED)).replace('\\', '/')
    return (source_rel, bytecode_rel)
IDENT_RE = re.compile('\\b([A-Za-z_][A-Za-z0-9_]*)\\b')

def strip_comments_and_strings(source: str) -> str:
    out = list(source)
    i = 0
    n = len(source)
    while i < n:
        if i + 1 < n and source[i:i + 2] == '//':
            while i < n and source[i] != '\n':
                out[i] = ' '
                i += 1
            continue
        if i + 1 < n and source[i:i + 2] == '/*':
            out[i] = out[i + 1] = ' '
            i += 2
            while i + 1 < n and source[i:i + 2] != '*/':
                out[i] = ' ' if source[i] != '\n' else '\n'
                i += 1
            if i + 1 < n:
                out[i] = out[i + 1] = ' '
                i += 2
            continue
        if source[i] in '"\'':
            quote = source[i]
            out[i] = ' '
            i += 1
            while i < n:
                if source[i] == '\\':
                    out[i] = ' '
                    if i + 1 < n:
                        out[i + 1] = ' '
                        i += 2
                        continue
                if source[i] == quote:
                    out[i] = ' '
                    i += 1
                    break
                out[i] = ' ' if source[i] != '\n' else '\n'
                i += 1
            continue
        i += 1
    return ''.join(out)
