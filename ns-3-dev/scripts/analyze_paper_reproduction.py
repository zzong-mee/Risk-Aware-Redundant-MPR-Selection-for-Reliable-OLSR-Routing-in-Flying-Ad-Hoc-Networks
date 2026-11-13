import csv
import os
import math
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev

BASE = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get(
    "RESULTS", BASE / "results/paper_reproduction"
))
OUT = Path(os.environ.get(
    "ANALYSIS_OUT", BASE / "results/paper_reproduction_analysis"
))
OUT.mkdir(parents=True, exist_ok=True)

MODES = [0, 1, 3, 4]
SPEEDS = [5, 10, 15, 20, 25]
SEEDS = range(1, 11)

records = []
for speed in SPEEDS:
    for seed in SEEDS:
        for mode in MODES:
            p = ROOT / f"speed{speed}_seed{seed}_mode{mode}.csv"

            with p.open(newline="") as f:
                flows = list(csv.DictReader(f))

            tx = sum(int(r["tx"]) for r in flows)
            rx = sum(int(r["rx"]) for r in flows)

            delay = (
                sum(float(r["delay_ms"]) * int(r["rx"])
                    for r in flows) / rx
                if rx else float("nan")
            )

            with Path(str(p) + ".control.csv").open(newline="") as f:
                overhead = sum(
                    int(r["packet_bytes"])
                    for r in csv.DictReader(f)
                    if r["event"] == "TX"
                )

            records.append({
                "speed": speed,
                "seed": seed,
                "mode": mode,
                "tx": tx,
                "rx": rx,
                "pdr": 100 * rx / tx if tx else float("nan"),
                "delay_ms": delay,
                "overhead_bytes": overhead,
            })

def save_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

save_csv(OUT / "all_runs.csv", records)

# 95% CI: t distribution, df=9, two-sided
T95 = 2.262157

summary = []
for speed in SPEEDS:
    for mode in MODES:
        group = [
            r for r in records
            if r["speed"] == speed and r["mode"] == mode
        ]

        row = {"speed": speed, "mode": mode}

        for metric in ["pdr", "delay_ms", "overhead_bytes"]:
            values = [r[metric] for r in group if math.isfinite(r[metric])]
            n = len(values)

            avg = mean(values) if values else float("nan")
            ci = T95 * stdev(values) / math.sqrt(n) if n > 1 else float("nan")

            row[f"{metric}_mean"] = avg
            row[f"{metric}_ci95"] = ci

        summary.append(row)

save_csv(OUT / "summary.csv", summary)

# 동일 speed, seed에서 Mode 4 - 비교 Mode
lookup = {(r["speed"], r["seed"], r["mode"]): r for r in records}
paired = []

for speed in SPEEDS:
    for other in [0, 1, 3]:
        row = {"speed": speed, "comparison": f"4_minus_{other}"}

        for metric in ["pdr", "delay_ms", "overhead_bytes"]:
            diffs = [
                lookup[(speed, seed, 4)][metric]
                - lookup[(speed, seed, other)][metric]
                for seed in SEEDS
            ]
            diffs = [x for x in diffs if math.isfinite(x)]
            n = len(diffs)

            row[f"{metric}_mean_diff"] = mean(diffs) if n else float("nan")
            row[f"{metric}_ci95"] = (
                T95 * stdev(diffs) / math.sqrt(n)
                if n > 1 else float("nan")
            )

        paired.append(row)

save_csv(OUT / "paired_comparison.csv", paired)

print("\n===== 속도별 PDR 평균 (%) =====")
print(f"{'Speed':>6} {'Mode 0':>10} {'Mode 1':>10} {'Mode 3':>10} {'Mode 4':>10}")

for speed in SPEEDS:
    vals = {
        r["mode"]: r["pdr_mean"]
        for r in summary if r["speed"] == speed
    }
    print(f"{speed:>6} " + " ".join(f"{vals[m]:>10.2f}" for m in MODES))

print("\n===== Mode 4 - Mode 0 (동일 시드 비교) =====")
print(f"{'Speed':>6} {'PDR 차이(pp)':>15} {'95% CI(pp)':>22}")

for r in paired:
    if r["comparison"] == "4_minus_0":
        d = r["pdr_mean_diff"]
        ci = r["pdr_ci95"]
        print(f"{r['speed']:>6} {d:>15.2f} [{d-ci:>8.2f}, {d+ci:>8.2f}]")

print("\n분석 결과 저장:", OUT)
