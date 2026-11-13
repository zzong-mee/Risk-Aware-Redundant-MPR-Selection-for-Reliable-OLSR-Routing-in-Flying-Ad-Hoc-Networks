#!/usr/bin/env python3
"""Experiment 10: Hysteresis-CVaR (Mode 4) range sweep."""

import argparse
import csv
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REQUIRED = {
    "seed", "mpr_mode", "speed", "range",
    "tx", "rx", "pdr", "delay_ms"
}

def valid_result(path, seed, radius):
    try:
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))

        if len(rows) != 1 or not REQUIRED.issubset(rows[0]):
            return False

        r = rows[0]
        return (
            int(r["seed"]) == seed
            and int(r["mpr_mode"]) == 4
            and abs(float(r["speed"]) - 20.0) < 1e-6
            and abs(float(r["range"]) - radius) < 1e-6
            and int(r["tx"]) > 0
            and int(r["rx"]) >= 0
            and 0 <= float(r["pdr"]) <= 1
        )
    except (OSError, ValueError, KeyError, csv.Error):
        return False

def work(task):
    root, outdir, seed, radius, force = task

    name = f"mode4_range{radius:g}_seed{seed}"
    path = outdir / name

    if not force and valid_result(path, seed, radius):
        return name, "SKIP", 0.0, ""

    cmd = [
        "./ns3",
        "run",
        (
            "scratch/olsr_baseline "
            f"--mprMode=4 "
            f"--nodes=35 "
            f"--mobility=random "
            f"--speed=20 "
            f"--range={radius:g} "
            f"--seed={seed} "
            f"--simTime=120 "
            f"--area=350 "
            f"--riskAddThreshold=1.5 "
            f"--riskRemoveThreshold=0.5 "
            f"--riskHorizon=5 "
            f"--riskSigma=2 "
            f"--riskAlpha=0.9 "
            f"--riskScenarios=100 "
            f"--out={path}"
        )
    ]

    started = time.monotonic()
    log = Path(str(path) + ".log")

    with log.open("w") as f:
        proc = subprocess.run(
            cmd,
            cwd=root,
            stdout=f,
            stderr=subprocess.STDOUT,
            check=False
        )

    elapsed = time.monotonic() - started
    ok = proc.returncode == 0 and valid_result(path, seed, radius)

    return name, "DONE" if ok else "FAIL", elapsed, str(log)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--seeds", type=int, nargs="+",
        default=list(range(11, 21))
    )
    parser.add_argument(
        "--ranges", type=float, nargs="+",
        default=[150, 200, 250]
    )
    parser.add_argument(
        "--output", default="results/experiment10"
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.workers < 1 or any(r <= 0 for r in args.ranges):
        parser.error("Invalid workers or ranges")

    root = Path.cwd().resolve()
    outdir = root / args.output
    outdir.mkdir(parents=True, exist_ok=True)

    tasks = [
        (root, outdir, seed, radius, args.force)
        for radius in args.ranges
        for seed in args.seeds
    ]

    print(
        f"Experiment 10: {len(tasks)} runs, "
        f"workers={args.workers}",
        flush=True
    )

    failures = []

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, task) for task in tasks]

        for i, future in enumerate(as_completed(futures), 1):
            try:
                name, status, elapsed, detail = future.result()
            except Exception as exc:
                name, status, elapsed, detail = (
                    "unknown", "ERROR", 0.0, repr(exc)
                )

            print(
                f"[{i}/{len(tasks)}] {status} "
                f"{name} {elapsed:.1f}s",
                flush=True
            )

            if status in ("FAIL", "ERROR"):
                failures.append((name, detail))

    if failures:
        print("\nFailed runs:")
        for name, detail in failures:
            print(name, detail)
        raise SystemExit(1)

    print("\nExperiment 10 completed successfully.")

if __name__ == "__main__":
    main()
