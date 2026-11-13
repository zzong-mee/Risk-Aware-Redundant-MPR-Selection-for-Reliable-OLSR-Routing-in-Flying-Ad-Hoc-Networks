#!/usr/bin/env python3
"""Experiment 9: event-weighted MPR stability and OLSR control overhead.
Run from ns-3 root: python3 scripts/analyze_experiment9.py
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def confidence_interval(xs):
    if len(xs) < 2:
        return None
    try:
        from scipy.stats import t
        critical = float(t.ppf(.975, len(xs) - 1))
    except ImportError:
        critical = {9: 2.262, 19: 2.093}.get(len(xs) - 1, 1.96)
    half = critical * stdev(xs) / math.sqrt(len(xs))
    return (mean(xs) - half, mean(xs) + half)


def mpr_stats(path, expected_mode):
    count_sum = events = transitions = changes = 0
    last_set = {}
    last_time = {}
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        required = {'time', 'node_address', 'mpr_mode', 'mpr_count', 'mpr_addresses'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'{path}: missing MPR columns')
        for row in reader:
            if int(row['mpr_mode']) != expected_mode:
                raise ValueError(f'{path}: wrong mpr_mode')
            node = row['node_address'].strip()
            t = float(row['time'])
            count = int(row['mpr_count'])
            # ns-3 MPR addresses are typically whitespace/semicolon/comma separated.
            raw = row['mpr_addresses'].strip()
            members = frozenset(x for x in raw.replace(';', ' ').replace(',', ' ').split() if x)
            if len(members) != count:
                raise ValueError(f'{path}: MPR count mismatch at node={node}, time={t}: {count} vs {members}')
            if node in last_time and t < last_time[node]:
                raise ValueError(f'{path}: nonmonotonic time for node {node}')
            if node in last_set:
                transitions += 1
                changes += members != last_set[node]
            last_set[node] = members
            last_time[node] = t
            count_sum += count
            events += 1
    if not events or not transitions:
        raise ValueError(f'{path}: insufficient MPR records')
    return dict(mean_mpr=count_sum / events, change_rate_pct=100 * changes / transitions,
                changes=changes, transitions=transitions, mpr_events=events)


def control_stats(path):
    sums = defaultdict(int)
    rows = 0
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        required = {'time', 'node', 'event', 'packet_bytes', 'hello_count', 'tc_count', 'mid_count', 'hna_count'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'{path}: missing control columns')
        for row in reader:
            event = row['event'].strip().upper()
            if event not in ('TX', 'RX'):
                continue
            rows += 1
            sums[f'{event.lower()}_packets'] += 1
            sums[f'{event.lower()}_bytes'] += int(row['packet_bytes'])
            for kind in ('hello', 'tc', 'mid', 'hna'):
                sums[f'{kind}_{event.lower()}'] += int(row[f'{kind}_count'])
    if not rows:
        raise ValueError(f'{path}: no control records')
    return dict(sums)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dir', default='results/experiment8_range')
    p.add_argument('--ranges', type=int, nargs='+', default=[150, 200, 250])
    p.add_argument('--seeds', type=int, nargs='+', default=list(range(11, 21)))
    p.add_argument('--modes', type=int, nargs='+', default=[0, 2, 3])
    p.add_argument('--out', default='results/experiment9_metrics.csv')
    a = p.parse_args()
    base = Path(a.dir)
    data = {}
    errors = []
    for radius in a.ranges:
        for seed in a.seeds:
            for mode in a.modes:
                stem = base / f'mode{mode}_range{radius}_seed{seed}'
                try:
                    # Require the summary file to exist as well; it is normally written at simulation end.
                    with stem.open(newline='') as f:
                        summary = list(csv.DictReader(f))
                    if len(summary) != 1:
                        raise ValueError('summary must have one row')
                    r = summary[0]
                    if (int(r['seed']) != seed or int(r['mpr_mode']) != mode or
                        abs(float(r['range']) - radius) > 1e-6 or
                        abs(float(r['speed']) - 20) > 1e-6):
                        raise ValueError('summary settings mismatch')
                    metrics = mpr_stats(Path(str(stem) + '.mpr.csv'), mode)
                    metrics.update(control_stats(Path(str(stem) + '.control.csv')))
                    metrics.update(range_m=radius, seed=seed, mode=mode, pdr_pct=100*float(r['pdr']))
                    data[radius, seed, mode] = metrics
                except (OSError, ValueError, KeyError, csv.Error) as e:
                    errors.append(f'{stem}: {e}')
    if not data:
        print('No valid runs found. Check --dir and CSV files.')
        raise SystemExit(1)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ['range_m', 'seed', 'mode', 'pdr_pct', 'mean_mpr', 'change_rate_pct',
              'changes', 'transitions', 'mpr_events', 'tc_tx', 'tc_rx', 'hello_tx',
              'tx_bytes', 'rx_bytes', 'tx_packets', 'rx_packets', 'mid_tx', 'hna_tx']
    with out.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for key in sorted(data):
            writer.writerow(data[key])
    print(f'Saved {len(data)} valid runs to {out}')
    metrics = [('mean_mpr', 'Mean MPR'), ('change_rate_pct', 'MPR changes (%)'),
               ('tc_tx', 'TC_TX'), ('tc_rx', 'TC_RX'), ('tx_bytes', 'Control TX bytes')]
    for radius in a.ranges:
        paired = [seed for seed in a.seeds if all((radius, seed, mode) in data for mode in a.modes)]
        print(f'\n=== Range {radius}m: complete paired seeds {len(paired)}/{len(a.seeds)} ===')
        if not paired:
            continue
        print('mode  ' + '  '.join(f'{label:>19}' for _, label in metrics))
        for mode in a.modes:
            vals = [mean([data[radius, s, mode][k] for s in paired]) for k, _ in metrics]
            print(f'{mode:4d}  ' + '  '.join(f'{v:19.3f}' for v in vals))
        if 0 in a.modes:
            for mode in a.modes:
                if mode == 0:
                    continue
                print(f'  Paired differences: mode {mode} minus Standard')
                for k, label in metrics:
                    diffs = [data[radius, s, mode][k] - data[radius, s, 0][k] for s in paired]
                    bounds = confidence_interval(diffs)
                    ci = f'[{bounds[0]:+.3f}, {bounds[1]:+.3f}]' if bounds else 'N/A'
                    print(f'    {label}: {mean(diffs):+.3f}  (95% CI {ci})')
    if errors:
        print(f'\nWARNING: {len(errors)} invalid/missing runs (first 12 shown):')
        for err in errors[:12]:
            print(' ', err)
        raise SystemExit(1)
    print('\nNote: event-weighted MPR means; change rate per consecutive same-node recomputation.')
    print('Control bytes are OLSR logged bytes, not 802.11 MAC airtime. CIs are seed-paired.')

if __name__ == '__main__':
    main()
