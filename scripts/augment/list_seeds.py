#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_QUOTA, SEED_MANIFEST, pick_minority_seeds, pick_reentrancy_seeds, write_seed_manifest

def main() -> int:
    p = argparse.ArgumentParser(description='Pick augmentation seeds for Waves A/B')
    p.add_argument('--with-reentrancy', type=int, default=0, help='Extra reentrancy seeds for B1')
    p.add_argument('--out', type=str, default=str(SEED_MANIFEST))
    args = p.parse_args()
    seeds = pick_minority_seeds(DEFAULT_QUOTA)
    if args.with_reentrancy > 0:
        extra = pick_reentrancy_seeds(args.with_reentrancy)
        seen = {s['contract_id'] for s in seeds}
        for r in extra:
            if r['contract_id'] not in seen:
                seeds.append(r)
    out = write_seed_manifest(seeds, path=__import__('pathlib').Path(args.out))
    counts = Counter((s['primary_vulnerability_type'] for s in seeds))
    print(f'[ok] wrote {len(seeds)} seeds -> {out}')
    for k, v in counts.most_common():
        print(f'  {k}: {v}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
