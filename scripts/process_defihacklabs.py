#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Optional
ROOT = Path(__file__).resolve().parent.parent
ADDR_RE = re.compile('0x[a-fA-F0-9]{40}')
PRAGMA_RE = re.compile('pragma\\s+solidity\\s+([^;]+);', re.IGNORECASE)
VULN_ADDR_COMMENT_RE = re.compile('Vulnerable\\s+Contract[^0-9a-fx]*?(0x[a-fA-F0-9]{40})', re.IGNORECASE)
TOTAL_LOST_RE = re.compile('Total\\s+Lost\\s*:\\s*(.+)', re.IGNORECASE)
SKIP_NAME_EXACT = {'basetest.sol', 'interface.sol', 'tokenhelper.sol', 'stablemath.sol', 'poc-template.sol', 'rpcs_alive_test.sol'}
SKIP_NAME_CONTAINS = ('basetest', 'tokenhelper', 'poc-template', 'rpcs_alive')
KNOWN_INFRA = {'0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', '0x0000000000000000000000000000000000000000', '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c', '0x7a250d5630b4cf539739df2c5dacb4c659f2488d', '0xe592427a0aece92de3edee1f18e0157c05861564'}
ATTACK_RULES: list[tuple[str, tuple[str, ...]]] = [('Flashloan', ('flashloan', 'flash loan', 'flash_loan', 'iflashloan', 'flashborrow', 'aave.*flash', 'dydx.*flash', 'balancer.*flash', 'uniswapv2.*swap.*callback', 'uniswapv3.*flash', 'pancake.*flash')), ('Oracle Manipulation', ('oracle', 'price.?feed', 'price.?manipulat', 'spot.?price', 'twap', 'chainlink', 'getprice', 'manipulate.?price')), ('Reentrancy', ('reentranc', 'onerc721received', 'tokensreceived', 'call.?before.?state')), ('AccessControl', ('access.?control', 'onlyowner', 'missing.?auth', 'unauthorized', 'setmarketingwallet', 'privileged', 'ownership', 'init(?!ializ)', 'initialize\\(')), ('Arithmetic', ('overflow', 'underflow', 'integer.?bug', 'precision.?loss', 'rounding', 'donation.?attack', 'share.?inflation', 'first.?depositor'))]
PROTOCOL_SUFFIXES = re.compile('(_exp|_poc|_hack|_attack|_test|_forge)?$', re.IGNORECASE)
DATE_SUFFIX = re.compile('_\\d{8}$')

def setup_logging(verbose: bool) -> logging.Logger:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    return logging.getLogger('process_defihacklabs')

def resolve_repo(explicit: Optional[str], log: logging.Logger) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend([ROOT / 'data' / 'DeFiHackLabs', ROOT / 'data' / 'defihacklabs', ROOT / 'Raw' / 'defihacklabs', ROOT / 'raw' / 'defihacklabs'])
    for c in candidates:
        if c.is_dir():
            log.info('DeFiHackLabs root: %s', c)
            return c.resolve()
    raise FileNotFoundError('DeFiHackLabs directory not found. Expected data/DeFiHackLabs or Raw/defihacklabs.')

def is_helper(path: Path) -> bool:
    name = path.name.lower()
    if name in SKIP_NAME_EXACT:
        return True
    if any((s in name for s in SKIP_NAME_CONTAINS)):
        return True
    parts = {p.lower() for p in path.parts}
    if 'forge-std' in parts or ('lib' in parts and 'forge-std' in str(path).lower()):
        if 'src' in parts and 'test' not in parts:
            return True
    return False

def looks_like_exploit(path: Path) -> bool:
    name = path.name
    lower = name.lower()
    if lower.endswith('_exp.sol') or lower.endswith('_exp.t.sol'):
        return True
    if '_exp.' in lower:
        return True
    if lower.endswith('_poc.sol') or lower.endswith('_hack.sol'):
        return True
    parent = path.parent.name
    if re.fullmatch('\\d{4}-\\d{2}', parent) and lower.endswith('.sol'):
        return True
    return False

def iter_solidity_files(repo: Path) -> Iterable[Path]:
    search_roots = []
    for rel in ('src/test', 'test', 'src', '.'):
        p = (repo / rel).resolve()
        if p.is_dir() and p not in search_roots:
            search_roots.append(p)
    seen: set[Path] = set()
    for root in search_roots:
        for pattern in ('**/*.sol', '**/*.t.sol'):
            for f in root.glob(pattern):
                if not f.is_file():
                    continue
                rp = f.resolve()
                if rp in seen:
                    continue
                seen.add(rp)
                if 'forge-std' in rp.parts or '.git' in rp.parts:
                    continue
                yield rp

def protocol_from_filename(stem: str) -> str:
    name = stem
    name = re.sub('_exp$', '', name, flags=re.IGNORECASE)
    name = re.sub('_poc$', '', name, flags=re.IGNORECASE)
    name = re.sub('_hack$', '', name, flags=re.IGNORECASE)
    name = DATE_SUFFIX.sub('', name)
    parts = [p for p in re.split('[_\\-]+', name) if p]
    if not parts:
        return stem
    drop = {'first', 'second', 'kill', 'old', 'new', 'v1', 'v2', 'v3', 'bsc', 'eth', 'arb'}
    core = [p for p in parts if p.lower() not in drop] or parts
    proto = core[0]
    proto_spaced = re.sub('(?<=[a-z])(?=[A-Z])', ' ', proto)
    proto_spaced = re.sub('(?<=[A-Z])(?=[A-Z][a-z])', ' ', proto_spaced)
    label = proto_spaced.strip()
    if ' ' not in label and label.isalpha() and (len(label) <= 12):
        if not label.isupper() and label.lower() not in {'parity', 'bean', 'fei', 'sushi'}:
            pass
    return label

def extract_pragma(source: str) -> str:
    m = PRAGMA_RE.search(source)
    return m.group(1).strip() if m else 'unknown'

def extract_addresses(source: str) -> tuple[Optional[str], list[str]]:
    all_addrs = []
    seen = set()
    for m in ADDR_RE.finditer(source):
        a = m.group(0).lower()
        if a not in seen:
            seen.add(a)
            all_addrs.append(a)
    primary = None
    vm = VULN_ADDR_COMMENT_RE.search(source)
    if vm:
        primary = vm.group(1).lower()
    else:
        named = re.findall('(?i)(vulnerable|target|vault|pool|pair|token|victim)[^\\n=]{0,40}=\\s*(0x[a-fA-F0-9]{40})', source)
        if named:
            primary = named[0][1].lower()
        else:
            for a in all_addrs:
                if a not in KNOWN_INFRA:
                    primary = a
                    break
            if primary is None and all_addrs:
                primary = all_addrs[0]
    return (primary, all_addrs)

def classify_attack_vectors(source: str, filename: str) -> list[str]:
    text = f'{filename}\n{source}'.lower()
    found: list[str] = []
    for label, patterns in ATTACK_RULES:
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                found.append(label)
                break
    if not found:
        found = ['OtherVulnerability']
    order = [r[0] for r in ATTACK_RULES] + ['OtherVulnerability']
    return [c for c in order if c in found]

def extract_total_lost(source: str) -> Optional[str]:
    m = TOTAL_LOST_RE.search(source)
    if not m:
        return None
    val = m.group(1).strip()
    val = val.split('//')[0].strip()
    if val.upper() in {'N/A', 'NA', ''}:
        return None
    return val[:120]

def make_id(stem: str) -> str:
    safe = re.sub('[^A-Za-z0-9_.-]+', '_', stem)
    return f'DEFIACT_{safe}'

def placeholder_fetch_etherscan(address: Optional[str], log: logging.Logger, enabled: bool) -> None:
    if not enabled:
        return
    if not address:
        log.info('[fetch-etherscan] skipped — no primary address on this PoC')
        return
    log.info('[fetch-etherscan] PLACEHOLDER: would GET https://api.etherscan.io/api?module=contract&action=getsourcecode&address=%s when ETHERSCAN_API_KEY is configured (not fetching now).', address)

def build_record(path: Path, source: str, repo: Path) -> dict[str, Any]:
    stem = path.stem
    protocol = protocol_from_filename(stem)
    primary, all_addrs = extract_addresses(source)
    categories = classify_attack_vectors(source, path.name)
    pragma = extract_pragma(source)
    try:
        rel = str(path.relative_to(repo)).replace('\\', '/')
    except ValueError:
        rel = str(path)
    return {'id': make_id(stem), 'source_code': source, 'bytecode': None, 'compiler_version': pragma, 'labels': {'is_vulnerable': True, 'categories': categories, 'swc_ids': [], 'line_numbers': []}, 'intent_label': 'actual_exploit', 'dataset_source': 'DeFiHackLabs', 'target_modules': ['LLM_EVAL', 'OBFUSCATION_BENCH', 'DEFI_INTENT_BENCH'], 'exploit_name': stem, 'protocol': protocol, 'primary_address': primary, 'addresses': all_addrs[:50], 'total_lost': extract_total_lost(source), 'poc_path': rel, 'victim_source_code': None}

def process(args: argparse.Namespace) -> int:
    log = setup_logging(args.verbose)
    repo = resolve_repo(args.repo, log)
    out_path = ROOT / 'data' / 'processed' / 'defihacklabs_exploits.jsonl'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats = Counter()
    category_counts = Counter()
    records: list[dict[str, Any]] = []
    files = sorted(iter_solidity_files(repo), key=lambda p: str(p).lower())
    log.info('Found %d solidity files under scan roots', len(files))
    for path in files:
        stats['files_seen'] += 1
        if is_helper(path):
            stats['skipped_helper'] += 1
            log.debug('Skip helper: %s', path.name)
            continue
        if not looks_like_exploit(path):
            stats['skipped_non_exploit'] += 1
            log.debug('Skip non-exploit: %s', path)
            continue
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            stats['skipped_read_error'] += 1
            log.warning('Failed to read %s: %s', path, e)
            continue
        if len(source.strip()) < 40:
            stats['skipped_empty'] += 1
            continue
        rec = build_record(path, source, repo)
        placeholder_fetch_etherscan(rec.get('primary_address'), log, args.fetch_etherscan)
        records.append(rec)
        stats['exploits'] += 1
        for c in rec['labels']['categories']:
            category_counts[c] += 1
        if args.limit and stats['exploits'] >= args.limit:
            log.info('Reached --limit %d', args.limit)
            break
    unique: dict[str, dict[str, Any]] = {}
    for rec in records:
        if rec['id'] in unique:
            stats['duplicate_id'] += 1
            continue
        unique[rec['id']] = rec
    with out_path.open('w', encoding='utf-8') as f:
        for rec in unique.values():
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    log.info('======== DeFiHackLabs processing complete ========')
    log.info('Solidity files scanned: %d', stats['files_seen'])
    log.info('Exploit records written: %d → %s', len(unique), out_path)
    log.info('Skipped helpers: %d', stats['skipped_helper'])
    log.info('Skipped non-exploit scripts: %d', stats['skipped_non_exploit'])
    log.info('Skipped read errors: %d', stats['skipped_read_error'])
    log.info('Skipped empty: %d', stats['skipped_empty'])
    log.info('Duplicate ids collapsed: %d', stats['duplicate_id'])
    log.info('Attack-vector prevalence: %s', dict(category_counts))
    if args.fetch_etherscan:
        log.info('--fetch-etherscan was set: placeholder log lines emitted (no network calls).')
    verify_output(out_path, log)
    return 0

def verify_output(path: Path, log: logging.Logger) -> None:
    log.info('======== Verification: first 2 JSON lines ========')
    if not path.is_file() or path.stat().st_size == 0:
        log.warning('Output missing or empty: %s', path)
        return
    with path.open('r', encoding='utf-8') as f:
        for i in range(2):
            line = f.readline()
            if not line:
                break
            obj = json.loads(line)
            preview = {'id': obj.get('id'), 'protocol': obj.get('protocol'), 'exploit_name': obj.get('exploit_name'), 'primary_address': obj.get('primary_address'), 'compiler_version': obj.get('compiler_version'), 'intent_label': obj.get('intent_label'), 'labels': obj.get('labels'), 'dataset_source': obj.get('dataset_source'), 'target_modules': obj.get('target_modules'), 'total_lost': obj.get('total_lost'), 'poc_path': obj.get('poc_path'), 'source_code_chars': len(obj.get('source_code') or ''), 'address_count': len(obj.get('addresses') or [])}
            print(json.dumps(preview, indent=2))

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Process DeFiHackLabs exploit PoCs to JSONL')
    p.add_argument('--repo', default=None, help='Path to DeFiHackLabs checkout')
    p.add_argument('--fetch-etherscan', action='store_true', default=False, help='Log placeholder Etherscan source fetches (no network I/O)')
    p.add_argument('--limit', type=int, default=None, help='Max exploit records to write')
    p.add_argument('-v', '--verbose', action='store_true')
    return p.parse_args(argv)
if __name__ == '__main__':
    try:
        raise SystemExit(process(parse_args()))
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.exception('process_defihacklabs failed')
        raise
