#!/usr/bin/env python3
"""Summarize per-mode results of the ns-3 RAMPR experiment."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--dir', default='results/hysteresis_test')
p.add_argument('--seed', type=int, default=8)
p.add_argument('--modes', nargs='+', default=['0', '1', '2', '3', '4', '2t15'])
a = p.parse_args()
print('label,pdr_pct,delay_ms,mean_mpr,changes,change_rate_pct,tc_tx,tc_rx,control_tx_bytes')
for label in a.modes:
    prefix = Path(a.dir) / f'mode{label}_seed{a.seed}'
    if not prefix.exists():
        print(f'# missing: {prefix}')
        continue
    with prefix.open(newline='') as f:
        result = next(csv.DictReader(f))
    by_node = defaultdict(list)
    with Path(str(prefix) + '.mpr.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            if float(r['time']) < 20: continue
            selected = frozenset(x.strip() for x in r['mpr_addresses'].split(';') if x.strip())
            by_node[r['node_address']].append((float(r['time']), selected))
    total = sum(len(x) for x in by_node.values())
    mean_mpr = sum(len(s) for rows in by_node.values() for _, s in rows) / total
    changes = comparisons = 0
    for rows in by_node.values():
        rows.sort(key=lambda x: x[0])
        for (_, before), (_, after) in zip(rows, rows[1:]):
            comparisons += 1
            changes += before != after
    tx = rx = tx_bytes = 0
    with Path(str(prefix) + '.control.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            if float(r['time']) < 20: continue
            if r['event'] == 'TX':
                tx += int(r['tc_count'])
                tx_bytes += int(r['packet_bytes'])
            elif r['event'] == 'RX':
                rx += int(r['tc_count'])
    print(f'{label},{100*float(result["pdr"]):.3f},{float(result["delay_ms"]):.3f},'
          f'{mean_mpr:.3f},{changes},{100*changes/comparisons:.3f},{tx},{rx},{tx_bytes}')
