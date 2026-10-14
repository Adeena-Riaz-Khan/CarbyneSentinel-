#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Optional
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPLOITS = ROOT / 'data' / 'processed' / 'defihacklabs_exploits.jsonl'
DEFAULT_OUT = ROOT / 'data' / 'processed' / 'defi_intent_bench.jsonl'
PER_CLASS = 50
TARGET_MODULES = ['DEFI_INTENT_BENCH', 'LLM_EVAL']
DATASET_SOURCE = 'DeFi-Intent-Bench'
INTENT_EXPLOIT = 'actual_exploit'
INTENT_TRANSFER = 'benign_transfer'
INTENT_ARBITRAGE = 'benign_arbitrage'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7'
UNI_V2_ROUTER = '0x7a250d5630b4cf539739df2c5dacb4c659f2488d'
UNI_V3_ROUTER = '0xe592427a0aece92de3edee1f18e0157c05861564'
AAVE_V3_POOL = '0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2'

def _keccak_selector(sig: str) -> str:
    try:
        from Crypto.Hash import keccak
        h = keccak.new(digest_bits=256)
        h.update(sig.encode('ascii'))
        return '0x' + h.hexdigest()[:8]
    except Exception:
        return '0x' + hashlib.sha3_256(sig.encode('ascii')).hexdigest()[:8]

def _pad_addr(addr: str) -> str:
    a = addr.lower().removeprefix('0x')
    return a.zfill(64)

def _pad_uint(n: int) -> str:
    return f'{n:064x}'

def _encode_call(sig: str, *words: str) -> str:
    sel = _keccak_selector(sig).removeprefix('0x')
    return '0x' + sel + ''.join((w.removeprefix('0x') for w in words))

def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

def _http_get_json(url: str, headers: Optional[dict[str, str]]=None, timeout: int=30) -> Any:
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'DeFi-Intent-Bench/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def make_record(*, category: str, idx: int, source_code: str, bytecode: Optional[str], is_vulnerable: bool, categories: list[str], extra: Optional[dict[str, Any]]=None) -> dict[str, Any]:
    rec: dict[str, Any] = {'id': f'INTENT_{category}_{idx:04d}', 'source_code': source_code, 'bytecode': bytecode, 'labels': {'is_vulnerable': is_vulnerable, 'categories': categories}, 'intent_label': category, 'dataset_source': DATASET_SOURCE, 'target_modules': list(TARGET_MODULES)}
    if extra:
        rec.update(extra)
    return rec

def exploit_to_intent(row: dict[str, Any], idx: int) -> dict[str, Any]:
    cats = row.get('labels', {}).get('categories') or []
    return make_record(category=INTENT_EXPLOIT, idx=idx, source_code=row.get('source_code') or '', bytecode=row.get('bytecode'), is_vulnerable=True, categories=list(cats), extra={'provenance': {'upstream_id': row.get('id'), 'upstream_dataset': row.get('dataset_source', 'DeFiHackLabs'), 'exploit_name': row.get('exploit_name'), 'protocol': row.get('protocol'), 'primary_address': row.get('primary_address')}})

def _synthetic_transfer(idx: int, rng: random.Random) -> dict[str, Any]:
    sender = f'0x{rng.getrandbits(160):040x}'
    recipient = f'0x{rng.getrandbits(160):040x}'
    token = rng.choice([USDC, USDT, WETH])
    amount = rng.choice([10 ** 6, 10 ** 8, 5 * 10 ** 17, 10 ** 18, 25 * 10 ** 18])
    value_wei = 0 if token != WETH else amount if rng.random() < 0.3 else 0
    if value_wei:
        calldata = '0x'
        kind = 'native_eth_transfer'
        payload = {'type': kind, 'from': sender, 'to': recipient, 'value_wei': str(value_wei), 'token': None, 'note': 'Plain ETH transfer between EOAs; no DEX routing, no flash loan.'}
        bytecode = calldata
    else:
        calldata = _encode_call('transfer(address,uint256)', _pad_addr(recipient), _pad_uint(amount))
        kind = 'erc20_transfer'
        payload = {'type': kind, 'from': sender, 'to': token, 'value_wei': '0', 'token': token, 'recipient': recipient, 'amount': str(amount), 'note': 'Standard ERC-20 transfer; net owner balance decreases by amount.'}
        bytecode = calldata
    source = f'// DeFi-Intent-Bench synthetic benign_transfer #{idx:04d}\n// kind={kind}\n' + json.dumps(payload, indent=2)
    return make_record(category=INTENT_TRANSFER, idx=idx, source_code=source, bytecode=bytecode, is_vulnerable=False, categories=[], extra={'provenance': {'generation': 'synthetic_template', 'kind': kind, 'from': sender, 'to': payload.get('to')}})

def _synthetic_arbitrage(idx: int, rng: random.Random) -> dict[str, Any]:
    variants = ['uni_v2_multihop', 'uni_v3_exact_input', 'aave_flash_arb']
    kind = variants[idx % len(variants)]
    trader = f'0x{rng.getrandbits(160):040x}'
    amount_in = rng.choice([10 ** 17, 5 * 10 ** 17, 10 ** 18, 2 * 10 ** 18])
    min_out = int(amount_in * rng.uniform(1.001, 1.04))
    if kind == 'uni_v2_multihop':
        path = [WETH, USDC, WETH]
        calldata = _encode_call('swapExactTokensForTokens(uint256,uint256,address[],address,uint256)', _pad_uint(amount_in), _pad_uint(min_out), _pad_uint(160), _pad_addr(trader), _pad_uint(2000000000 + idx))
        target = UNI_V2_ROUTER
        note = 'Uniswap V2 multi-hop WETH→USDC→WETH; expected net WETH increase from price discrepancy. No privilege escalation / storage overwrite.'
    elif kind == 'uni_v3_exact_input':
        calldata = _encode_call('exactInput((bytes,address,uint256,uint256,uint256))', _pad_uint(32), _pad_addr(trader), _pad_uint(2000000000 + idx), _pad_uint(amount_in), _pad_uint(min_out))
        target = UNI_V3_ROUTER
        path = [WETH, USDT, WETH]
        note = 'Uniswap V3 exactInput arb route; profit from fee-tier / pool imbalance. Legitimate MEV, not an exploit of broken auth.'
    else:
        calldata = _encode_call('flashLoanSimple(address,address,uint256,bytes,uint16)', _pad_addr(trader), _pad_addr(WETH), _pad_uint(amount_in), _pad_uint(160), _pad_uint(0))
        target = AAVE_V3_POOL
        path = [WETH, USDC, WETH]
        note = 'Aave V3 flashLoanSimple → DEX cycle → repay principal+premium; keeper keeps residual. Flash liquidity is repaid in the same tx.'
    payload = {'type': kind, 'from': trader, 'to': target, 'path': path, 'amount_in': str(amount_in), 'min_amount_out': str(min_out), 'expected_net_profit_wei': str(max(0, min_out - amount_in)), 'note': note}
    source = f'// DeFi-Intent-Bench synthetic benign_arbitrage #{idx:04d}\n// kind={kind}\n' + json.dumps(payload, indent=2)
    return make_record(category=INTENT_ARBITRAGE, idx=idx, source_code=source, bytecode=calldata, is_vulnerable=False, categories=[], extra={'provenance': {'generation': 'synthetic_template', 'kind': kind, 'router_or_pool': target, 'path': path}})

def fetch_etherscan_transfers(api_key: str, n: int, rng: random.Random) -> list[dict[str, Any]]:
    url = 'https://api.etherscan.io/api?' + urllib.parse.urlencode({'module': 'account', 'action': 'tokentx', 'contractaddress': USDC, 'page': 1, 'offset': min(n * 3, 100), 'sort': 'desc', 'apikey': api_key})
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f'[warn] Etherscan transfer fetch failed: {e}', file=sys.stderr)
        return []
    results = data.get('result') if isinstance(data, dict) else None
    if not isinstance(results, list) or data.get('status') != '1':
        print(f'[warn] Etherscan unexpected response: {str(data)[:200]}', file=sys.stderr)
        return []
    out: list[dict[str, Any]] = []
    for i, tx in enumerate(results):
        if len(out) >= n:
            break
        try:
            value = int(tx.get('value') or '0')
        except ValueError:
            continue
        if value <= 0:
            continue
        to_addr = (tx.get('to') or '').lower()
        frm = (tx.get('from') or '').lower()
        calldata = _encode_call('transfer(address,uint256)', _pad_addr(to_addr), _pad_uint(value))
        payload = {'type': 'etherscan_tokentx', 'hash': tx.get('hash'), 'from': frm, 'to': (tx.get('contractAddress') or USDC).lower(), 'token': USDC, 'recipient': to_addr, 'amount': str(value), 'blockNumber': tx.get('blockNumber'), 'note': 'Live ERC-20 transfer pulled from Etherscan tokentx API.'}
        source = f'// DeFi-Intent-Bench live benign_transfer #{len(out):04d}\n' + json.dumps(payload, indent=2)
        out.append(make_record(category=INTENT_TRANSFER, idx=len(out), source_code=source, bytecode=calldata, is_vulnerable=False, categories=[], extra={'provenance': {'generation': 'etherscan', 'tx_hash': tx.get('hash'), 'block': tx.get('blockNumber')}}))
        time.sleep(0.2)
    _ = rng
    return out

def fetch_etherscan_swaps(api_key: str, n: int, rng: random.Random) -> list[dict[str, Any]]:
    url = 'https://api.etherscan.io/api?' + urllib.parse.urlencode({'module': 'account', 'action': 'txlist', 'address': UNI_V2_ROUTER, 'page': 1, 'offset': min(n * 4, 100), 'sort': 'desc', 'apikey': api_key})
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f'[warn] Etherscan swap fetch failed: {e}', file=sys.stderr)
        return []
    results = data.get('result') if isinstance(data, dict) else None
    if not isinstance(results, list) or data.get('status') != '1':
        print(f'[warn] Etherscan unexpected response: {str(data)[:200]}', file=sys.stderr)
        return []
    out: list[dict[str, Any]] = []
    for tx in results:
        if len(out) >= n:
            break
        if str(tx.get('isError', '0')) != '0':
            continue
        inp = (tx.get('input') or '').lower()
        if not (inp.startswith('0x38ed1739') or inp.startswith('0x7ff36ab5') or inp.startswith('0x18cbafe5')):
            continue
        if len(inp) < 10:
            continue
        payload = {'type': 'etherscan_uni_v2_swap', 'hash': tx.get('hash'), 'from': (tx.get('from') or '').lower(), 'to': UNI_V2_ROUTER, 'value_wei': tx.get('value'), 'blockNumber': tx.get('blockNumber'), 'note': 'Live Uniswap V2 router swap from Etherscan. Treated as benign arbitrage/liquidation-class routing (no exploit PoC).'}
        source = f'// DeFi-Intent-Bench live benign_arbitrage #{len(out):04d}\n' + json.dumps(payload, indent=2)
        out.append(make_record(category=INTENT_ARBITRAGE, idx=len(out), source_code=source, bytecode=inp if inp.startswith('0x') else '0x' + inp, is_vulnerable=False, categories=[], extra={'provenance': {'generation': 'etherscan', 'tx_hash': tx.get('hash'), 'block': tx.get('blockNumber'), 'router': UNI_V2_ROUTER}}))
        time.sleep(0.2)
    _ = rng
    return out

def fetch_dune_placeholder(api_key: str, n: int, label: str) -> list[dict[str, Any]]:
    import os
    env_key = 'DUNE_QUERY_ID_TRANSFERS' if label == INTENT_TRANSFER else 'DUNE_QUERY_ID_ARBITRAGE'
    query_id = os.environ.get(env_key)
    if not query_id:
        print(f'[info] Dune key present but {env_key} unset — skipping live Dune for {label}.', file=sys.stderr)
        return []
    url = f'https://api.dune.com/api/v1/query/{query_id}/results'
    try:
        data = _http_get_json(url, headers={'X-Dune-API-Key': api_key})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f'[warn] Dune fetch failed: {e}', file=sys.stderr)
        return []
    rows = (data.get('result') or {}).get('rows') or []
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows[:n]):
        payload = {'type': 'dune_row', 'query_id': query_id, 'row': row}
        source = f'// DeFi-Intent-Bench Dune {label} #{i:04d}\n' + json.dumps(payload, indent=2)
        calldata = row.get('data') or row.get('input') or row.get('calldata') or '0x'
        out.append(make_record(category=label, idx=i, source_code=source, bytecode=calldata if str(calldata).startswith('0x') else '0x', is_vulnerable=False, categories=[], extra={'provenance': {'generation': 'dune', 'query_id': query_id}}))
    return out

def _reindex(rows: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    fixed = []
    for i, r in enumerate(rows):
        r = dict(r)
        r['id'] = f'INTENT_{category}_{i:04d}'
        r['intent_label'] = category
        r['dataset_source'] = DATASET_SOURCE
        r['target_modules'] = list(TARGET_MODULES)
        fixed.append(r)
    return fixed

def fill_to_n(live: list[dict[str, Any]], n: int, category: str, rng: random.Random) -> list[dict[str, Any]]:
    rows = list(live[:n])
    while len(rows) < n:
        i = len(rows)
        if category == INTENT_TRANSFER:
            rows.append(_synthetic_transfer(i, rng))
        else:
            rows.append(_synthetic_arbitrage(i, rng))
    return _reindex(rows[:n], category)

def load_exploits(path: Path, n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows = _load_jsonl(path)
    if not rows:
        raise SystemExit(f'No exploit rows found in {path}')
    usable = [r for r in rows if (r.get('source_code') or '').strip()]
    if len(usable) < n:
        usable = rows
    if len(usable) < n:
        raise SystemExit(f'Need {n} exploits but only found {len(usable)} in {path}')
    sample = rng.sample(usable, n)
    return [exploit_to_intent(r, i) for i, r in enumerate(sample)]

def build_benign_transfers(n: int, rng: random.Random, etherscan_key: Optional[str], dune_key: Optional[str]) -> list[dict[str, Any]]:
    live: list[dict[str, Any]] = []
    if dune_key:
        live.extend(fetch_dune_placeholder(dune_key, n, INTENT_TRANSFER))
    if etherscan_key and len(live) < n:
        live.extend(fetch_etherscan_transfers(etherscan_key, n - len(live), rng))
    mode = 'live+synthetic' if live else 'synthetic_template'
    print(f'[info] benign_transfer source mode: {mode} ({len(live)} live)')
    return fill_to_n(live, n, INTENT_TRANSFER, rng)

def build_benign_arbitrage(n: int, rng: random.Random, etherscan_key: Optional[str], dune_key: Optional[str]) -> list[dict[str, Any]]:
    live: list[dict[str, Any]] = []
    if dune_key:
        live.extend(fetch_dune_placeholder(dune_key, n, INTENT_ARBITRAGE))
    if etherscan_key and len(live) < n:
        live.extend(fetch_etherscan_swaps(etherscan_key, n - len(live), rng))
    mode = 'live+synthetic' if live else 'synthetic_template'
    print(f'[info] benign_arbitrage source mode: {mode} ({len(live)} live)')
    return fill_to_n(live, n, INTENT_ARBITRAGE, rng)

def print_stats(rows: list[dict[str, Any]]) -> None:
    counts = Counter((r['intent_label'] for r in rows))
    vuln = Counter((bool(r.get('labels', {}).get('is_vulnerable')) for r in rows))
    print('\n=== DeFi-Intent-Bench distribution ===')
    print(f'total records: {len(rows)}')
    for label in (INTENT_EXPLOIT, INTENT_TRANSFER, INTENT_ARBITRAGE):
        print(f'  {label}: {counts.get(label, 0)}')
    print(f'is_vulnerable true/false: {vuln.get(True, 0)} / {vuln.get(False, 0)}')

def print_verification_samples(rows: list[dict[str, Any]]) -> None:
    print('\n=== Verification samples (1 per intent class) ===')
    by = {r['intent_label']: r for r in rows}
    first: dict[str, dict[str, Any]] = {}
    for r in rows:
        first.setdefault(r['intent_label'], r)
    for label in (INTENT_EXPLOIT, INTENT_TRANSFER, INTENT_ARBITRAGE):
        r = first.get(label) or by.get(label)
        if not r:
            print(f'  MISSING sample for {label}')
            continue
        src_preview = (r.get('source_code') or '').replace('\n', ' ')[:120]
        bc = r.get('bytecode')
        bc_preview = bc[:42] + '...' if isinstance(bc, str) and len(bc) > 42 else bc
        print(f'\n[{label}]')
        print(f"  id:            {r.get('id')}")
        print(f"  is_vulnerable: {r.get('labels', {}).get('is_vulnerable')}")
        print(f"  categories:    {r.get('labels', {}).get('categories')}")
        print(f'  bytecode:      {bc_preview}')
        print(f'  source_code:   {src_preview}...')

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Build DeFi-Intent-Bench (~150 balanced traces)')
    p.add_argument('--exploits', type=Path, default=DEFAULT_EXPLOITS, help='Path to defihacklabs_exploits.jsonl')
    p.add_argument('--out', type=Path, default=DEFAULT_OUT, help='Output JSONL path')
    p.add_argument('--per-class', type=int, default=PER_CLASS, help='Records per intent class')
    p.add_argument('--seed', type=int, default=42, help='RNG seed for sampling/shuffle')
    p.add_argument('--etherscan-api-key', default=None, help='Optional Etherscan API key')
    p.add_argument('--dune-api-key', default=None, help='Optional Dune Analytics API key')
    return p.parse_args(argv)

def main(argv: Optional[list[str]]=None) -> int:
    args = parse_args(argv)
    rng = random.Random(args.seed)
    n = args.per_class
    if not args.exploits.is_file():
        raise SystemExit(f'Exploits file not found: {args.exploits}')
    print(f'[info] loading exploits from {args.exploits}')
    exploits = load_exploits(args.exploits, n, rng)
    transfers = build_benign_transfers(n, rng, args.etherscan_api_key, args.dune_api_key)
    arbs = build_benign_arbitrage(n, rng, args.etherscan_api_key, args.dune_api_key)
    combined = exploits + transfers + arbs
    rng.shuffle(combined)
    _write_jsonl(args.out, combined)
    print(f'\n[ok] wrote {len(combined)} records -> {args.out}')
    print_stats(combined)
    print_verification_samples(combined)
    counts = Counter((r['intent_label'] for r in combined))
    for label in (INTENT_EXPLOIT, INTENT_TRANSFER, INTENT_ARBITRAGE):
        if counts.get(label, 0) != n:
            print(f'[error] expected {n} {label}, got {counts.get(label, 0)}', file=sys.stderr)
            return 1
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
