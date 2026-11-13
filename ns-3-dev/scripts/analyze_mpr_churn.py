#!/usr/bin/env python3
"""Compute MPR selection churn from ns-3 olsr_baseline .mpr.csv logs.

Event count: for each node, compare consecutive MPR sets and count one event
when the set differs. Also report number of relay additions/removals (symmetric
set differences). First observed set per node is a baseline, not a change.
"""
import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

PATTERN = re.compile(r"speed(?P<speed>\d+(?:\.\d+)?)_seed(?P<seed>\d+)_mode(?P<mode>\d+)")

def analyze(path):
    events = defaultdict(list)
    with path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            t = float(row['time'])
            node = row['node_address'].strip()
            members = frozenset(x.strip() for x in row['mpr_addresses'].split(';') if x.strip())
            events[node].append((t, members))
    n_events = n_add = n_remove = n_observations = 0
    for node, entries in events.items():
        # Preserve file order for equal timestamps; sort by time otherwise.
        entries.sort(key=lambda x: x[0])
        previous = None
        for t, members in entries:
            n_observations += 1
            if previous is not None:
                added, removed = members - previous, previous - members
                n_events += bool(added or removed)
                n_add += len(added)
                n_remove += len(removed)
            previous = members
    return dict(churn_events=n_events, relay_additions=n_add,
                relay_removals=n_remove, relay_changes=n_add+n_remove,
                observed_nodes=len(events), recomputations=n_observations)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path, help='Directory containing speed*_seed*_mode*.mpr.csv logs')
    p.add_argument('--out', type=Path, default=Path('results/mpr_churn_runs.csv'))
    a = p.parse_args()
    files = sorted(a.root.rglob('*.mpr.csv'))
    rows = []
    for file in files:
        match = PATTERN.search(str(file))
        if not match:
            print(f'SKIP unrecognized name: {file}')
            continue
        row = {'speed': float(match['speed']), 'seed': int(match['seed']), 'mode': int(match['mode'])}
        row.update(analyze(file))
        rows.append(row)
    if not rows:
        raise SystemExit('No matching .mpr.csv logs. Locate logs with: find . -name "*.mpr.csv"')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary = a.out.with_name('mpr_churn_summary.csv')
    groups = defaultdict(list)
    for row in rows: groups[(row['speed'], row['mode'])].append(row)
    with summary.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['speed','mode','runs','churn_events_mean','churn_events_sd','relay_changes_mean','relay_changes_sd'])
        for (speed, mode), group in sorted(groups.items()):
            churn = [x['churn_events'] for x in group]
            changes = [x['relay_changes'] for x in group]
            writer.writerow([speed,mode,len(group),mean(churn),stdev(churn) if len(churn)>1 else '',
                             mean(changes),stdev(changes) if len(changes)>1 else ''])
    print(f'Processed {len(rows)} runs from {len(files)} logs')
    print(f'Per-run: {a.out}')
    print(f'Summary: {summary}')
    for key, group in sorted(groups.items()):
        print(f'speed={key[0]:g}, mode={key[1]}, n={len(group)}, churn_mean={mean(x["churn_events"] for x in group):.2f}')
    if len(rows) != 200:
        print('WARNING: Expected 200 runs for the existing experiment; inspect missing logs.')

if __name__ == '__main__': main()
