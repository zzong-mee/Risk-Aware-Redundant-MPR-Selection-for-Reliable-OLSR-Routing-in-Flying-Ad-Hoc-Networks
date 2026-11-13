#!/usr/bin/env python3
"""Offline CVaR diagnostic for ns-3 LET CSV. Does not change ns-3 RNG or MPR."""
import argparse
import csv
import hashlib
import math
import random
from pathlib import Path


def let_seconds(r, v, radius):
    c = sum(x*x for x in r) - radius*radius
    if c >= 0:
        return 0.0
    a = sum(x*x for x in v)
    if a < 1e-12:
        return math.inf
    b = 2 * sum(x*y for x, y in zip(r, v))
    d = b*b - 4*a*c
    if d < 0:
        return math.inf
    return max(0.0, (-b + math.sqrt(d)) / (2*a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', type=Path)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--horizon', type=float, default=5.0)
    ap.add_argument('--alpha', type=float, default=0.9)
    ap.add_argument('--scenarios', type=int, default=20)
    ap.add_argument('--sigma', type=float, default=2.0)
    ap.add_argument('--range', dest='radius', type=float, default=200.0)
    ap.add_argument('--interval', type=float, default=5.0,
                    help='Sample each directed node-neighbor pair once per time bucket (seconds).')
    ap.add_argument('--seed', type=int, default=12345)
    args = ap.parse_args()
    if not (0 <= args.alpha < 1 and args.scenarios > 0 and args.horizon > 0 and
            args.sigma >= 0 and args.radius > 0 and args.interval > 0):
        ap.error('Invalid parameters')
    out = args.output or args.input.with_suffix('.cvar.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    processed = skipped = 0
    with args.input.open(newline='') as fin, out.open('w', newline='') as fout:
        reader = csv.DictReader(fin)
        required = {'time','node','neighbor','selected','rx','ry','rz','vx','vy','vz'}
        if not required.issubset(reader.fieldnames or []):
            ap.error('Input lacks vector columns; use the updated OLSR source and rerun mode 2.')
        writer = csv.writer(fout)
        writer.writerow(['time','node','neighbor','selected','nominal_let','mean_loss',
                         'cvar_loss','tail_count','horizon','alpha','scenarios','sigma'])
        for row in reader:
            bucket = math.floor(float(row['time']) / args.interval)
            key = (row['node'], row['neighbor'], bucket)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            r = tuple(float(row[k]) for k in ('rx','ry','rz'))
            v = tuple(float(row[k]) for k in ('vx','vy','vz'))
            nominal = let_seconds(r, v, args.radius)
            # Independent per record, reproducible without consuming ns-3 RNG streams.
            token = f'{args.seed}|{bucket}|{row["node"]}|{row["neighbor"]}'.encode()
            rng = random.Random(int.from_bytes(hashlib.blake2b(token, digest_size=8).digest(), 'big'))
            losses = []
            for _ in range(args.scenarios):
                perturbed = tuple(x + rng.gauss(0, args.sigma) for x in v)
                let = let_seconds(r, perturbed, args.radius)
                losses.append(max(0.0, args.horizon - let))
            losses.sort(reverse=True)
            # For equal-weight scenarios, empirical CVaR uses fractional tail mass.
            tail_mass = args.scenarios * (1 - args.alpha)
            full = int(math.floor(tail_mass))
            fraction = tail_mass - full
            tail_sum = sum(losses[:full])
            if fraction > 1e-12:
                tail_sum += fraction * losses[full]
            cvar = tail_sum / tail_mass
            writer.writerow([row['time'], row['node'], row['neighbor'], row['selected'],
                             nominal, sum(losses)/len(losses), cvar, tail_mass,
                             args.horizon, args.alpha, args.scenarios, args.sigma])
            processed += 1
    print(f'Wrote {processed:,} CVaR records to {out} (skipped {skipped:,} repeated time-bucket records)')
    print('CVaR is an assumed Gaussian velocity-error scenario estimate, not validated link-failure probability.')

if __name__ == '__main__':
    main()
