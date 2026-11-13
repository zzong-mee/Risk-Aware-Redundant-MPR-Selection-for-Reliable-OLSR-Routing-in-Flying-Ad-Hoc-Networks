#!/usr/bin/env python3
"""Validate sampled first link range-exceedance in [prediction_time, prediction_time+H].
Interpolates positions ONLY at the prediction time, using adjacent recorded snapshots.
All future link-break checks use actual recorded positions, not interpolated positions.
Requires fine-grained position samples (recommended <= 0.5 seconds).
"""
import argparse
import bisect
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


def auc(scores, labels):
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return float('nan')
    ranked = sorted(zip(scores, labels))
    rank_sum = 0.0
    i = 0
    while i < len(ranked):
        j = i + 1
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        rank_sum += (i + 1 + j) / 2 * sum(y for _, y in ranked[i:j])
        i = j
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def interpolate(a, b, fraction):
    return tuple(x + fraction * (y-x) for x,y in zip(a,b))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--positions', type=Path, required=True)
    parser.add_argument('--cvar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--range', dest='radius', type=float, default=200)
    parser.add_argument('--horizon', type=float, default=5)
    parser.add_argument('--threshold', type=float, default=1)
    parser.add_argument('--max-snapshot-gap', type=float, default=0.51)
    args = parser.parse_args()
    if args.radius <= 0 or args.horizon <= 0 or args.max_snapshot_gap <= 0:
        parser.error('range, horizon and max-snapshot-gap must be positive')

    positions = defaultdict(dict)
    with args.positions.open(newline='') as f:
        for row in csv.DictReader(f):
            positions[round(float(row['time']), 6)][int(row['node'])] = tuple(float(row[k]) for k in ('x','y','z'))
    times = sorted(positions)
    if len(times) < 2:
        parser.error('At least two position snapshots are required')
    gaps = [b-a for a,b in zip(times, times[1:])]
    print(f'Snapshots={len(times)}, interval min/max={min(gaps):.3f}/{max(gaps):.3f}s')
    if max(gaps) > args.max_snapshot_gap + 1e-7:
        parser.error('Snapshot gaps too large; rerun ns-3 with position logging at 0.5s')

    skipped = Counter()
    records = []
    with args.cvar.open(newline='') as f:
        for row in csv.DictReader(f):
            t = float(row['time'])
            stop = t + args.horizon
            if t < times[0] or stop > times[-1] + 1e-7:
                skipped['outside_observed_time'] += 1
                continue
            i = bisect.bisect_right(times, t) - 1
            if i < 0 or i + 1 >= len(times):
                skipped['no_bracketing_snapshots'] += 1
                continue
            t0,t1 = times[i],times[i+1]
            try:
                # Valid only if address assignment is 10.1.1.(node_id+1).
                a = int(row['node'].split('.')[-1]) - 1
                b = int(row['neighbor'].split('.')[-1]) - 1
                if a < 0 or b < 0:
                    raise ValueError('invalid node id')
                frac = (t-t0)/(t1-t0)
                pa = interpolate(positions[t0][a],positions[t1][a],frac)
                pb = interpolate(positions[t0][b],positions[t1][b],frac)
            except (KeyError, ValueError, IndexError):
                skipped['address_mapping_or_missing_positions'] += 1
                continue
            d0 = math.dist(pa,pb)
            if d0 >= args.radius:
                skipped['out_of_range_at_prediction'] += 1
                continue
            first_break = None
            max_dist = d0
            j = bisect.bisect_right(times,t)
            missing_future = False
            while j < len(times) and times[j] <= stop + 1e-7:
                ts = times[j]
                try:
                    dist = math.dist(positions[ts][a], positions[ts][b])
                except KeyError:
                    skipped['missing_future_position'] += 1
                    missing_future = True
                    break
                max_dist = max(max_dist,dist)
                if dist >= args.radius:
                    first_break = ts
                    break
                j += 1
            else:
                # All future snapshots checked, including last <= stop.
                pass
            if missing_future:
                continue
            label = int(first_break is not None)
            records.append((row,t,d0,first_break,max_dist,label))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['time','node','neighbor','distance_at_prediction_interpolated','first_observed_out_of_range_time','max_observed_distance','break_within_horizon','cvar_loss','nominal_let','selected'])
        for row,t,d0,break_time,max_dist,label in records:
            writer.writerow([row['time'],row['node'],row['neighbor'],d0,'' if break_time is None else break_time,max_dist,label,row['cvar_loss'],row['nominal_let'],row['selected']])
    print('Matched:',len(records),'Skipped:',dict(skipped))
    if not records:
        return
    labels=[r[5] for r in records]
    cvar=[float(r[0]['cvar_loss']) for r in records]
    let=[float(r[0]['nominal_let']) for r in records]
    print(f'Observed range exceedance within H: {sum(labels)}/{len(labels)} ({100*sum(labels)/len(labels):.2f}%)')
    print(f'ROC-AUC CVaR: {auc(cvar,labels):.4f}')
    print(f'ROC-AUC LET (-LET): {auc([-v for v in let],labels):.4f}')
    pred=[v > args.threshold for v in cvar]
    tp=sum(p and y for p,y in zip(pred,labels))
    fp=sum(p and not y for p,y in zip(pred,labels))
    fn=sum(not p and y for p,y in zip(pred,labels))
    print(f'CVaR > {args.threshold:g}s: precision={tp/(tp+fp) if tp+fp else float("nan"):.4f}, recall={tp/(tp+fn) if tp+fn else float("nan"):.4f}')
    print('LIMITATIONS: start positions interpolated; breaks between snapshots may be missed; same-link samples are correlated.')
    print('The CVaR CSV has no scenario failure probability; this script compares CVaR and LET only.')

if __name__=='__main__':
    main()
