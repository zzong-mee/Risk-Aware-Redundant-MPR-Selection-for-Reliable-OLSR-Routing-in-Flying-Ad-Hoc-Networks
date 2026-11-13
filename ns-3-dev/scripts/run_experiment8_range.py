#!/usr/bin/env python3
"""Experiment 8-2: range sweep with parallel ns-3 runs and optional reuse of 200m data."""
import argparse
import csv
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REQUIRED = {'seed', 'mpr_mode', 'speed', 'range', 'tx', 'rx', 'pdr', 'delay_ms'}

def valid_result(path, seed, mode, speed, radius):
    try:
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 1 or not REQUIRED.issubset(rows[0]):
            return False
        r = rows[0]
        return (int(r['seed']) == seed and int(r['mpr_mode']) == mode
                and abs(float(r['speed']) - speed) < 1e-6
                and abs(float(r['range']) - radius) < 1e-6
                and int(r['tx']) > 0 and int(r['rx']) >= 0
                and 0 <= float(r['pdr']) <= 1)
    except (OSError, ValueError, KeyError, csv.Error):
        return False

def work(task):
    root, outdir, source, seed, mode, radius, force, reuse = task
    name = f'mode{mode}_range{radius:g}_seed{seed}'
    path = outdir / name
    if not force and valid_result(path, seed, mode, 20, radius):
        return name, 'SKIP', 0.0, ''
    if not force and reuse and radius == 200:
        old = source / f'mode{mode}_speed20_seed{seed}'
        if valid_result(old, seed, mode, 20, 200):
            shutil.copy2(old, path)
            return name, 'REUSE', 0.0, str(old)
    path.unlink(missing_ok=True)
    risk = 1.5 if mode == 2 else 1.0
    cmd = ['./ns3', 'run',
           ('scratch/olsr_baseline '
            f'--mprMode={mode} --nodes=35 --mobility=random '
            f'--speed=20 --range={radius:g} --seed={seed} '
            f'--riskThreshold={risk} --out={path}')]
    started = time.monotonic()
    log = Path(str(path) + '.log')
    with log.open('w') as f:
        proc = subprocess.run(cmd, cwd=root, stdout=f, stderr=subprocess.STDOUT, check=False)
    elapsed = time.monotonic() - started
    ok = proc.returncode == 0 and valid_result(path, seed, mode, 20, radius)
    if not ok:
        path.unlink(missing_ok=True)
    return name, 'DONE' if ok else 'FAIL', elapsed, str(log)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=16)
    p.add_argument('--seeds', type=int, nargs='+', default=list(range(11, 21)))
    p.add_argument('--ranges', type=float, nargs='+', default=[150, 200, 250])
    p.add_argument('--modes', type=int, nargs='+', default=[0, 2, 3])
    p.add_argument('--output', default='results/experiment8_range')
    p.add_argument('--reuse-from', default='results/experiment8_speed')
    p.add_argument('--no-reuse', action='store_true')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()
    if a.workers < 1 or any(m not in (0, 2, 3) for m in a.modes) or any(r <= 0 for r in a.ranges):
        p.error('invalid workers, modes, or ranges')
    root = Path.cwd().resolve()
    if not (root / 'ns3').exists():
        p.error('run from ns-3 root directory')
    outdir = (root / a.output).resolve()
    source = (root / a.reuse_from).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tasks = [(root, outdir, source, s, m, r, a.force, not a.no_reuse)
             for r in a.ranges for s in a.seeds for m in a.modes]
    print(f'Experiments={len(tasks)}, workers={a.workers}, output={outdir}', flush=True)
    started = time.monotonic()
    failures = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(work, task) for task in tasks]
        try:
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    name, status, elapsed, detail = future.result()
                except Exception as exc:
                    name, status, elapsed, detail = 'unknown', 'ERROR', 0.0, repr(exc)
                print(f'[{i}/{len(tasks)}] {status:5} {name} {elapsed:.1f}s {detail}', flush=True)
                if status in ('FAIL', 'ERROR'):
                    failures.append((name, detail))
        except KeyboardInterrupt:
            print('\nInterrupted. Existing child processes may continue; check with pgrep before restarting.', flush=True)
            raise SystemExit(130)
    print(f'Total wall time: {time.monotonic()-started:.1f}s')
    if failures:
        print('Failed tasks:')
        for name, detail in failures:
            print(f'  {name}: {detail}')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
