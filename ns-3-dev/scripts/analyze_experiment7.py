#!/usr/bin/env python3
"""Summarize paired ns-3 MPR experiment results and paired 95% CIs."""
import argparse
import csv
import math
import statistics as stats
from pathlib import Path

# Two-sided 95% t critical values for df=1..30; normal approximation thereafter.
T95 = [None, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365,
       2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
       2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069,
       2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]

def read(path, seed, mode):
    try:
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 1 or int(rows[0]['seed']) != seed or int(rows[0]['mpr_mode']) != mode:
            return None
        return {'pdr': float(rows[0]['pdr']) * 100,
                'delay': float(rows[0]['delay_ms'])}
    except (OSError, ValueError, KeyError, csv.Error):
        return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dir', default='results/experiment7')
    p.add_argument('--seeds', nargs='+', type=int, default=list(range(1, 11)))
    a = p.parse_args()
    data = {}
    for seed in a.seeds:
        data[seed] = {}
        for mode in range(4):
            data[seed][mode] = read(Path(a.dir) / f'mode{mode}_seed{seed}', seed, mode)
    paired = [s for s in a.seeds if all(data[s][m] is not None for m in range(4))]
    print(f'Complete paired seeds: {len(paired)}/{len(a.seeds)} -> {paired}')
    for seed in a.seeds:
        missing = [m for m in range(4) if data[seed][m] is None]
        if missing:
            print(f'  Missing seed={seed}, modes={missing}')
    if not paired:
        raise SystemExit('No complete paired seeds')
    print('\nMODE  MEAN_PDR(%)  SD_PDR  MEAN_DELAY(ms)')
    for mode in range(4):
        pdrs = [data[s][mode]['pdr'] for s in paired]
        delays = [data[s][mode]['delay'] for s in paired]
        print(f'{mode:4d}  {stats.mean(pdrs):11.3f}  {stats.stdev(pdrs) if len(pdrs)>1 else float("nan"):6.3f}  {stats.mean(delays):14.3f}')
    print('\nPAIRED PDR DIFFERENCES vs MODE 0 (percentage points)')
    for mode in (1, 2, 3):
        diff = [data[s][mode]['pdr'] - data[s][0]['pdr'] for s in paired]
        n = len(diff)
        avg = stats.mean(diff)
        if n > 1:
            se = stats.stdev(diff) / math.sqrt(n)
            t = T95[n - 1] if n - 1 <= 30 else 1.96
            ci = (avg - t * se, avg + t * se)
            print(f'mode={mode}: mean={avg:+.3f} pp, 95% CI=[{ci[0]:+.3f}, {ci[1]:+.3f}] pp, improved={sum(d>0 for d in diff)}/{n}')
        else:
            print(f'mode={mode}: mean={avg:+.3f} pp (CI requires >=2 seeds)')
    print('\nNote: CIs assume independent seed-level differences; exploratory if threshold tuned on these seeds.')

if __name__ == '__main__':
    main()
