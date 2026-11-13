#!/usr/bin/env python3
"""ns-3 FANET speed sweep, independent processes, resumable outputs."""
import argparse
import csv
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REQUIRED = {'seed','mpr_mode','speed','range','tx','rx','pdr','delay_ms'}

def valid_result(path, seed, mode, speed):
    try:
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 1 or not REQUIRED.issubset(rows[0]):
            return False
        r = rows[0]
        return (int(r['seed']) == seed and int(r['mpr_mode']) == mode
                and abs(float(r['speed'])-speed)<1e-6
                and int(r['tx'])>0 and 0 <= float(r['pdr']) <= 1)
    except (OSError, ValueError, KeyError, csv.Error):
        return False

def work(task):
    root, outdir, seed, mode, speed, force = task
    name = f'mode{mode}_speed{speed:g}_seed{seed}'
    path = outdir/name
    if not force and valid_result(path, seed, mode, speed):
        return name, 'SKIP', 0.0, ''
    # Clean up incomplete summaries so failures cannot be mistaken for successes.
    path.unlink(missing_ok=True)
    risk = 1.5 if mode == 2 else 1.0
    cmd = ['./ns3', 'run',
           ('scratch/olsr_baseline '
            f'--mprMode={mode} --nodes=35 --mobility=random '
            f'--speed={speed:g} --range=200 --seed={seed} '
            f'--riskThreshold={risk} --out={path}')]
    started = time.monotonic()
    log = Path(str(path)+'.log')
    with log.open('w') as f:
        p = subprocess.run(cmd, cwd=root, stdout=f, stderr=subprocess.STDOUT,
                           check=False)
    elapsed = time.monotonic()-started
    ok = p.returncode == 0 and valid_result(path, seed, mode, speed)
    return name, ('DONE' if ok else 'FAIL'), elapsed, str(log)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--seeds', type=int, nargs='+', default=list(range(11,21)))
    p.add_argument('--speeds', type=float, nargs='+', default=[5,10,20,30])
    p.add_argument('--modes', type=int, nargs='+', default=[0,2,3])
    p.add_argument('--output', default='results/experiment8_speed')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()
    if a.workers < 1 or any(m not in (0,2,3) for m in a.modes):
        p.error('workers must be >= 1 and modes must be among 0, 2, 3')
    root = Path.cwd().resolve()
    if not (root/'ns3').exists():
        p.error('run this script from the ns-3 root directory')
    outdir = (root/a.output).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tasks = [(root,outdir,s,m,v,a.force) for v in a.speeds for s in a.seeds for m in a.modes]
    print(f'Experiments={len(tasks)}, workers={a.workers}, output={outdir}', flush=True)
    started = time.monotonic()
    failures=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(work,t) for t in tasks]
        for i,fut in enumerate(as_completed(futures),1):
            try:
                name,status,elapsed,log=fut.result()
            except Exception as e:
                name,status,elapsed,log='unknown','ERROR',0.0,str(e)
            print(f'[{i}/{len(tasks)}] {status:5} {name} {elapsed:.1f}s {log}', flush=True)
            if status in ('FAIL','ERROR'):
                failures.append((name,log))
    print(f'Total wall time: {time.monotonic()-started:.1f}s')
    if failures:
        print('Failed tasks:')
        for name,log in failures:
            print(f'  {name}: {log}')
        raise SystemExit(1)

if __name__=='__main__':
    main()
