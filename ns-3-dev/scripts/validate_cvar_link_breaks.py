#!/usr/bin/env python3
"""Compare predicted CVaR/nominal LET with observed sampled position link breaks.
This measures sampled range exceedance, NOT continuous first passage or OLSR link loss.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def auc(scores, labels):
    pos = sum(labels)
    neg = len(labels) - pos
    if not pos or not neg:
        return float('nan')
    ordered = sorted(zip(scores, labels), key=lambda z: z[0])
    rank_sum = 0.0
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        rank = (i + 1 + j) / 2
        rank_sum += rank * sum(label for _, label in ordered[i:j])
        i = j
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--positions', type=Path, required=True)
    ap.add_argument('--cvar', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--range', dest='radius', type=float, default=200.0)
    ap.add_argument('--horizon', type=float, default=5.0)
    ap.add_argument('--threshold', type=float, default=1.0)
    ap.add_argument('--time-tolerance', type=float, default=0.02)
    args = ap.parse_args()
    if args.radius <= 0 or args.horizon <= 0:
        ap.error('range and horizon must be positive')
    positions = defaultdict(dict)
    with args.positions.open(newline='') as f:
        for row in csv.DictReader(f):
            positions[round(float(row['time']), 6)][int(row['node'])] = tuple(float(row[k]) for k in ('x','y','z'))
    times = sorted(positions)
    if len(times) < 2:
        ap.error('Not enough position snapshots')
    gaps = [b-a for a,b in zip(times,times[1:])]
    print(f'Position snapshots: {len(times)}, first times: {times[:5]}, min/max interval: {min(gaps):.3f}/{max(gaps):.3f}s')
    print('IMPORTANT: This uses positions sampled at t and t+H only; intermediate disconnect/reconnect events can be missed.')
    records = []
    skipped = defaultdict(int)
    with args.cvar.open(newline='') as f:
        for row in csv.DictReader(f):
            t = float(row['time'])
            # Pair with the nearest snapshot at or after the prediction time, within tolerance.
            # A 5-second position sampling grid cannot match predictions at t=2.003s.
            start = min(times, key=lambda x: abs(x-t))
            if abs(start-t) > args.time_tolerance:
                skipped['no_start_snapshot'] += 1
                continue
            target = start + args.horizon
            end = min(times, key=lambda x: abs(x-target))
            if abs(end-target) > args.time_tolerance:
                skipped['no_end_snapshot'] += 1
                continue
            try:
                a = int(row['node'].split('.')[-1])-1
                b = int(row['neighbor'].split('.')[-1])-1
                p0, q0 = positions[start][a], positions[start][b]
                p1, q1 = positions[end][a], positions[end][b]
            except (KeyError, ValueError, IndexError):
                skipped['address_mapping_or_position'] += 1
                continue
            dist0 = math.dist(p0,q0)
            dist1 = math.dist(p1,q1)
            if dist0 >= args.radius:
                skipped['not_connected_at_start'] += 1
                continue
            label = int(dist1 >= args.radius)
            records.append((row, start, end, dist0, dist1, label))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time','node','neighbor','snapshot_start','snapshot_end','distance_start','distance_end','out_of_range_at_end','cvar_loss','nominal_let','selected'])
        for row, start, end, d0, d1, label in records:
            writer.writerow([row['time'],row['node'],row['neighbor'],start,end,d0,d1,label,row['cvar_loss'],row['nominal_let'],row['selected']])
    print('Matched:',len(records),'Skipped:',dict(skipped))
    if not records:
        print('NO VALID MATCHES. The current CVaR sample timestamps do not align with position snapshots.')
        print('Do not interpolate 5-second positions to invent continuous link breaks; increase position logging frequency or generate predictions on the same time grid.')
        return
    labels=[r[5] for r in records]
    cvar=[float(r[0]['cvar_loss']) for r in records]
    let=[float(r[0]['nominal_let']) for r in records]
    print(f'Out-of-range at t+H: {sum(labels)}/{len(labels)} ({100*sum(labels)/len(labels):.2f}%)')
    print('ROC-AUC CVaR:',f'{auc(cvar,labels):.4f}')
    print('ROC-AUC nominal LET risk (-LET):',f'{auc([-x for x in let],labels):.4f}')
    predicted=[int(x>args.threshold) for x in cvar]
    tp=sum(p and y for p,y in zip(predicted,labels))
    fp=sum(p and not y for p,y in zip(predicted,labels))
    fn=sum((not p) and y for p,y in zip(predicted,labels))
    print(f'CVaR > {args.threshold:g}s: precision={tp/(tp+fp) if tp+fp else float("nan"):.4f}, recall={tp/(tp+fn) if tp+fn else float("nan"):.4f}')
    print('WARNING: Repeated observations from the same links are correlated; do not treat them as independent trials.')

if __name__=='__main__':
    main()
