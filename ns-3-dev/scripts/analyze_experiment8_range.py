#!/usr/bin/env python3
"""Experiment 8-2 paired PDR analysis by radio range."""
import argparse
import csv
import math
from pathlib import Path
from statistics import mean, stdev

T95 = {1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,
       8:2.306,9:2.262,10:2.228,11:2.201,12:2.179,13:2.160,14:2.145,
       15:2.131,16:2.120,17:2.110,18:2.101,19:2.093,20:2.086}

def ci(values):
    n = len(values)
    if n < 2:
        return None
    try:
        from scipy.stats import t
        critical = t.ppf(0.975, n-1)
    except ImportError:
        critical = T95.get(n-1, 1.96)
    half = critical * stdev(values) / math.sqrt(n)
    return mean(values)-half, mean(values)+half

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dir', default='results/experiment8_range')
    p.add_argument('--seeds', type=int, nargs='+', default=list(range(11,21)))
    p.add_argument('--ranges', type=float, nargs='+', default=[150,200,250])
    a = p.parse_args()
    base = Path(a.dir)
    incomplete = False
    for radius in a.ranges:
        data = {}
        for seed in a.seeds:
            for mode in (0,2,3):
                path = base / f'mode{mode}_range{radius:g}_seed{seed}'
                try:
                    with path.open(newline='') as f:
                        rows = list(csv.DictReader(f))
                    if len(rows) != 1:
                        continue
                    r = rows[0]
                    if (int(r['seed']) != seed or int(r['mpr_mode']) != mode
                        or abs(float(r['speed'])-20)>1e-6
                        or abs(float(r['range'])-radius)>1e-6
                        or int(r['tx'])<=0 or not 0<=float(r['pdr'])<=1):
                        continue
                    data[seed,mode] = (float(r['pdr'])*100, float(r['delay_ms']))
                except (OSError, ValueError, KeyError, csv.Error):
                    pass
        complete = [s for s in a.seeds if all((s,m) in data for m in (0,2,3))]
        print(f'\n=== Range {radius:g} m: paired seeds {len(complete)}/{len(a.seeds)} ===')
        if len(complete) != len(a.seeds):
            incomplete = True
            print('Missing/incomplete seeds:', [s for s in a.seeds if s not in complete])
        if not complete:
            continue
        print('mode   mean_PDR(%)   SD_PDR   mean_delay(ms)')
        for m in (0,2,3):
            pdr = [data[s,m][0] for s in complete]
            delays = [data[s,m][1] for s in complete]
            sd = stdev(pdr) if len(pdr)>1 else float('nan')
            print(f'{m:4d}   {mean(pdr):11.3f}   {sd:6.3f}   {mean(delays):14.3f}')
        print('Paired PDR difference vs Standard (percentage points):')
        for m in (2,3):
            diffs = [data[s,m][0]-data[s,0][0] for s in complete]
            bounds = ci(diffs)
            interval = f'[{bounds[0]:+.3f}, {bounds[1]:+.3f}]' if bounds else 'N/A'
            print(f' mode {m}: mean={mean(diffs):+.3f} pp, 95% CI={interval}, improved={sum(d>0 for d in diffs)}/{len(diffs)}')
    print('\nNote: paired CIs assume independent seeds; verify matching mobility and traffic settings.')
    if incomplete:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
