import argparse
import csv
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def run_experiment(task):
    seed, threshold, output_dir, force = task

    output = output_dir / f"cvar_t{threshold}_seed{seed}"
    log_path = Path(str(output) + ".log")

    # 정상 완료된 실험은 건너뛰기
    if not force and output.exists():
        try:
            with output.open() as f:
                rows = list(csv.DictReader(f))

            if len(rows) == 1 and all(
                key in rows[0] for key in ("seed", "pdr", "delay_ms")
            ):
                return seed, threshold, "SKIP", 0
        except (OSError, csv.Error):
            pass

    command = [
        "./ns3",
        "run",
        (
            "scratch/olsr_baseline "
            "--mprMode=2 "
            "--nodes=35 "
            "--mobility=random "
            "--speed=20 "
            "--range=200 "
            f"--seed={seed} "
            f"--riskThreshold={threshold} "
            f"--out={output}"
        ),
    ]

    start = time.monotonic()

    with log_path.open("w") as log:
        result = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )

    elapsed = time.monotonic() - start

    if result.returncode != 0:
        return seed, threshold, "FAILED", elapsed

    return seed, threshold, "DONE", elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int,
                        default=list(range(1, 11)))
    parser.add_argument("--thresholds", nargs="+",
                        default=["0.5", "1", "1.5", "2", "2.5", "3"])
    parser.add_argument("--output", default="results/threshold_sweep")
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        (seed, threshold, output_dir, args.force)
        for seed in args.seeds
        for threshold in args.thresholds
    ]

    print(f"Total experiments: {len(tasks)}", flush=True)
    print(f"Parallel workers: {args.workers}", flush=True)

    start = time.monotonic()
    failed = []

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(run_experiment, task)
            for task in tasks
        ]

        for i, future in enumerate(as_completed(futures), 1):
            seed, threshold, status, elapsed = future.result()

            print(
                f"[{i}/{len(tasks)}] "
                f"seed={seed} threshold={threshold} "
                f"{status} ({elapsed:.1f}s)",
                flush=True,
            )

            if status == "FAILED":
                failed.append((seed, threshold))

    print(f"\nTotal time: {time.monotonic() - start:.1f}s")

    if failed:
        print("Failed experiments:", failed)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
