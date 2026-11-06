#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Optional
ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / 'data' / 'processed'
MASTER_JSON = ROOT / 'processed' / 'master_dataset_phase2.json'
FIG_DIR = ROOT / 'reports' / 'figures'
FIG_PATH = FIG_DIR / 'vulnerability_class_distribution.png'
CSV_DEFAULT = ROOT / 'reports' / 'class_counts.csv'
CANONICAL_MAP: dict[str, str] = {'reentrancy': 'Reentrancy', 'integer_overflow': 'Arithmetic', 'access_control': 'AccessControl', 'unchecked_call': 'UncheckedReturn', 'time_manipulation': 'TimeManipulation', 'front_running': 'FrontRunning', 'bad_randomness': 'BadRandomness', 'denial_of_service': 'DenialOfService', 'short_address': 'ShortAddress', 'tx_origin': 'TxOrigin', 'other': 'OtherVulnerability', 'none': 'None', 'Reentrancy': 'Reentrancy', 'AccessControl': 'AccessControl', 'Arithmetic': 'Arithmetic', 'UncheckedReturn': 'UncheckedReturn', 'TimeManipulation': 'TimeManipulation', 'FrontRunning': 'FrontRunning', 'TxOrigin': 'TxOrigin', 'OtherVulnerability': 'OtherVulnerability', 'Flashloan': 'Flashloan', 'Oracle Manipulation': 'OracleManipulation', 'OracleManipulation': 'OracleManipulation', 'BadRandomness': 'BadRandomness', 'DenialOfService': 'DenialOfService', 'ShortAddress': 'ShortAddress'}
PREFERRED_ORDER = ['AccessControl', 'OtherVulnerability', 'Reentrancy', 'Arithmetic', 'UncheckedReturn', 'TimeManipulation', 'FrontRunning', 'TxOrigin', 'Flashloan', 'BadRandomness', 'DenialOfService', 'OracleManipulation', 'ShortAddress']

def canonicalize(raw: str) -> str:
    s = (raw or '').strip()
    if not s:
        return 'OtherVulnerability'
    if s in CANONICAL_MAP:
        return CANONICAL_MAP[s]
    key = s.lower().replace(' ', '_').replace('-', '_')
    return CANONICAL_MAP.get(key, s)

def extract_categories(row: dict[str, Any]) -> list[str]:
    labels = row.get('labels')
    cats: list[str] = []
    if isinstance(labels, dict):
        raw = labels.get('categories') or []
        if isinstance(raw, list):
            cats = [canonicalize(str(c)) for c in raw if str(c).strip()]
    elif row.get('vulnerability_types'):
        cats = [canonicalize(str(c)) for c in row['vulnerability_types'] if str(c).strip()]
    elif row.get('primary_vulnerability_type'):
        cats = [canonicalize(str(row['primary_vulnerability_type']))]
    cats = [c for c in cats if c and c != 'None']
    seen: set[str] = set()
    out: list[str] = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

def is_vulnerable_record(row: dict[str, Any]) -> bool:
    labels = row.get('labels')
    if isinstance(labels, dict) and 'is_vulnerable' in labels:
        return bool(labels['is_vulnerable'])
    if row.get('label') == 'vulnerable':
        return True
    if row.get('intent_label') == 'actual_exploit':
        return True
    return False

def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding='utf-8', errors='replace') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f'[warn] bad JSON in {path.name}:{line_no}: {e}', file=sys.stderr)
                continue
            if isinstance(obj, dict):
                yield obj

def load_master(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []

def classify_imbalance(pct: float, majority_pct: float=15.0, minority_pct: float=5.0) -> str:
    if pct >= majority_pct:
        return 'Majority Class'
    if pct < minority_pct:
        return 'Minority Class (Needs Augmentation)'
    return 'Moderate Class'

def collect(include_master: bool=True, skip_intent_bench: bool=True) -> tuple[Counter[str], int, int, Counter[str]]:
    class_counts: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    seen_ids: set[str] = set()
    unique = 0
    multilabel = 0
    jsonl_files = sorted(PROCESSED_DIR.glob('*.jsonl')) if PROCESSED_DIR.is_dir() else []
    for path in jsonl_files:
        if skip_intent_bench and path.name == 'defi_intent_bench.jsonl':
            continue
        for row in iter_jsonl(path):
            if not is_vulnerable_record(row):
                continue
            rid = str(row.get('id') or row.get('contract_id') or '')
            if rid and rid in seen_ids:
                continue
            if rid:
                seen_ids.add(rid)
            cats = extract_categories(row)
            if not cats:
                cats = ['OtherVulnerability']
            if len(cats) > 1:
                multilabel += 1
            unique += 1
            src = row.get('dataset_source') or row.get('source_dataset') or path.stem
            by_source[str(src)] += 1
            for c in cats:
                class_counts[c] += 1
    if include_master:
        for row in load_master(MASTER_JSON):
            if not is_vulnerable_record(row):
                continue
            rid = str(row.get('contract_id') or row.get('id') or '')
            if rid and rid in seen_ids:
                continue
            if rid:
                seen_ids.add(rid)
            cats = extract_categories(row)
            if not cats:
                cats = ['OtherVulnerability']
            if len(cats) > 1:
                multilabel += 1
            unique += 1
            by_source[str(row.get('source_dataset') or 'master')] += 1
            for c in cats:
                class_counts[c] += 1
    return (class_counts, unique, multilabel, by_source)

def build_rows(class_counts: Counter[str]) -> list[dict[str, Any]]:
    total_labels = sum(class_counts.values()) or 1
    ordered = sorted(class_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    rows = []
    for name, count in ordered:
        pct = 100.0 * count / total_labels
        rows.append({'vulnerability_class': name, 'record_count': count, 'percentage': round(pct, 2), 'imbalance': classify_imbalance(pct)})
    return rows

def print_markdown(rows: list[dict[str, Any]], unique_contracts: int, multilabel: int, by_source: Counter[str], total_labels: int) -> None:
    n_classes = len(rows)
    print('# Vulnerability class distribution\n')
    print(f'- **Unique vulnerable contracts counted:** {unique_contracts:,}')
    print(f'- **Multi-label contracts (>1 class):** {multilabel:,}')
    print(f'- **Total class-tag occurrences:** {total_labels:,}')
    print(f'- **Number of vulnerability classes/types:** **{n_classes}**')
    print(f'- **Sources:** {dict(by_source)}\n')
    print('| Vulnerability Class | Total Record Count | % of Labeled Tags | Imbalance Classification |')
    print('|---|---:|---:|---|')
    for r in rows:
        print(f"| {r['vulnerability_class']} | {r['record_count']:,} | {r['percentage']:.2f}% | {r['imbalance']} |")
    minority = [r for r in rows if 'Minority' in r['imbalance']]
    majority = [r for r in rows if r['imbalance'] == 'Majority Class']
    print('\n## Advisor takeaway\n')
    print(f'The labeled vulnerable set spans **{n_classes} vulnerability classes**. Tag mass is dominated by ' + (', '.join((f"**{r['vulnerability_class']}** ({r['percentage']:.1f}%)" for r in majority)) or 'no single majority class') + '. ')
    if minority:
        names = ', '.join((r['vulnerability_class'] for r in minority))
        print(f'\n**Minority classes that need synthetic augmentation / rebalancing before training:** {names}. A model trained on this mix can become lazy and over-predict majority tags (AccessControl / Other / Reentrancy / Arithmetic). Use obfuscation and controlled transforms preferentially on these scarce classes to generate more varied positive examples - both to balance training and to probe detector robustness under disguise.')
    else:
        print('\nNo class fell below the minority threshold (<5% of tag mass); still monitor rare tails before final training splits.')
    print('\n*Note:* percentages are over **class-tag occurrences** (multi-label contracts contribute to each of their categories once). Unique contract count is reported separately so contracts are not double-counted as units of analysis.')

def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['vulnerability_class', 'record_count', 'percentage', 'imbalance'])
        w.writeheader()
        w.writerows(rows)

def plot_bars(rows: list[dict[str, Any]], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        raise SystemExit('matplotlib is required. Install with: pip install matplotlib\n' + str(e)) from e
    names = [r['vulnerability_class'] for r in rows][::-1]
    counts = [r['record_count'] for r in rows][::-1]
    pcts = [r['percentage'] for r in rows][::-1]
    n = len(names)
    fig_h = max(4.5, 0.45 * n + 1.5)
    fig, ax = plt.subplots(figsize=(11, fig_h), dpi=150)
    try:
        cmap = plt.colormaps['Blues']
    except (AttributeError, KeyError):
        cmap = plt.get_cmap('Blues')
    norms = np.linspace(0.35, 0.95, n)
    colors = [cmap(v) for v in norms]
    y = np.arange(n)
    bars = ax.barh(y, counts, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel('Number of vulnerable contracts tagged with class', fontsize=10)
    ax.set_title('Vulnerability Class Distribution (Processed Datasets)', fontsize=13, fontweight='bold', pad=12)
    ax.grid(axis='x', linestyle='--', alpha=0.35)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    xmax = max(counts) if counts else 1
    for bar, count, pct in zip(bars, counts, pcts):
        ax.text(bar.get_width() + xmax * 0.01, bar.get_y() + bar.get_height() / 2, f'{count:,}  ({pct:.1f}%)', va='center', ha='left', fontsize=8.5, color='#1a202c')
    ax.set_xlim(0, xmax * 1.22)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\n[ok] figure saved -> {path}')

def parse_args(argv: Optional[list[str]]=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Plot vulnerability class distribution')
    p.add_argument('--output-csv', nargs='?', const=str(CSV_DEFAULT), default=None, help=f'Write CSV breakdown (default path: {CSV_DEFAULT})')
    p.add_argument('--no-master', action='store_true', help='Skip processed/master_dataset_phase2.json')
    p.add_argument('--include-intent-bench', action='store_true', help='Include defi_intent_bench.jsonl exploits (may overlap DeFiHackLabs)')
    p.add_argument('--figure', type=Path, default=FIG_PATH, help='Output PNG path')
    return p.parse_args(argv)

def main(argv: Optional[list[str]]=None) -> int:
    args = parse_args(argv)
    class_counts, unique, multilabel, by_source = collect(include_master=not args.no_master, skip_intent_bench=not args.include_intent_bench)
    if not class_counts:
        print('[error] No vulnerable records found.', file=sys.stderr)
        return 1
    rows = build_rows(class_counts)
    total_labels = sum(class_counts.values())
    print_markdown(rows, unique, multilabel, by_source, total_labels)
    plot_bars(rows, args.figure if args.figure.is_absolute() else ROOT / args.figure)
    if args.output_csv is not None:
        csv_path = Path(args.output_csv)
        if not csv_path.is_absolute():
            csv_path = ROOT / csv_path
        write_csv(rows, csv_path)
        print(f'[ok] csv saved -> {csv_path}')
    print(f'\n**Classes / types counted: {len(rows)}**')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
