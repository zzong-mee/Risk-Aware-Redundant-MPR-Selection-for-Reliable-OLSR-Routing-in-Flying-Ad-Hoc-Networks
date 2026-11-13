#!/usr/bin/env python3
"""Paired OLSR MPR experiment runner for ns-3; run from ns-3 root."""
import argparse
import csv
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

MODES = {0: None, 1: None, 2: '1.5', 3: '1.0'}

def valid(path, seed, mode):
    if not path.is_file():
        return False
    try:
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        return (len(rows) == 1 and int(rows[0]['seed']) == seed
                and int(rows[0]['mpr_mode']) == mode
                and 0 <= float(rows[0]['pdr']) <= 1
                and int(rows[0]['tx']) > 0)
    except (OSError, ValueError, KeyError, TypeError, csv.Error):
        return False

def execute(task):
    seed, mode, out, force = task
    if not force and valid(out, seed, mode):
        return seed, mode, 'SKIP', 0.0
    args = [f'--mprMode={mode}', '--nodes=35', '--mobility=random',
            '--speed=20', '--range=200', f'--seed={seed}',
            f'--out={out}']
    if MODES[mode]:
        args.append(f'--riskThreshold={MODES[mode]}')
    command = ['./ns3', 'run', 'scratch/olsr_baseline ' + ' '.join(args)]
    start = time.monotonic()
    with Path(str(out) + '.run.log').open('w') as f:
        result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
    status = 'DONE' if result.returncode == 0 and valid(out, seed, mode) else 'FAILED'
    return seed, mode, status, time.monotonic() - start

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--seeds', nargs='+', type=int, default=list(range(1, 11)))
    p.add_argument('--output', default='results/experiment7')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()
    if a.workers < 1 or any(s < 1 for s in a.seeds):
        p.error('workers and seeds must be positive')
    output = Path(a.output)
    output.mkdir(parents=True, exist_ok=True)
    tasks = [(seed, mode, output / f'mode{mode}_seed{seed}', a.force)
             for seed in a.seeds for mode in MODES]
    start = time.monotonic()
    failures = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(execute, task) for task in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            seed, mode, status, elapsed = future.result()
            print(f'[{i}/{len(tasks)}] seed={seed} mode={mode}: {status} ({elapsed:.1f}s)', flush=True)
            if status == 'FAILED':
                failures.append((seed, mode))
    print(f'Elapsed: {time.monotonic()-start:.1f}s; failed: {failures}')
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
