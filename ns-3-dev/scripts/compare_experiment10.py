#!/usr/bin/env python3
"""Paired comparison: Experiment 9 Mode 2 vs Experiment 10 Mode 4."""

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

OLD = Path("results/experiment9_metrics.csv")
NEW = Path("results/experiment10")

# t critical value for 95% two-sided CI, df=9.
T_CRITICAL = 2.262157

old = {}
with OLD.open(newline="") as f:
    for row in csv.DictReader(f):
        if int(row["mode"]) == 2:
            key = (int(row["range_m"]), int(row["seed"]))
            old[key] = row


def analyze_mode4(radius, seed):
    prefix = NEW / f"mode4_range{radius}_seed{seed}"

    with prefix.open(newline="") as f:
        result = next(csv.DictReader(f))

    from collections import defaultdict
    by_node = defaultdict(list)

    with Path(str(prefix) + ".mpr.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            if float(r["time"]) < 20:
                continue

            selected = frozenset(
                x.strip()
                for x in r["mpr_addresses"].split(";")
                if x.strip()
            )

            by_node[r["node_address"]].append(
                (float(r["time"]), selected)
            )

    changes = transitions = 0
    mpr_total = mpr_events = 0

    for rows in by_node.values():
        rows.sort(key=lambda x: x[0])

        mpr_events += len(rows)
        mpr_total += sum(len(s) for _, s in rows)

        for (_, before), (_, after) in zip(rows, rows[1:]):
            transitions += 1
            changes += before != after

    tc_tx = tc_rx = tx_bytes = 0

    with Path(str(prefix) + ".control.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            if float(r["time"]) < 20:
                continue

            if r["event"] == "TX":
                tc_tx += int(r["tc_count"])
                tx_bytes += int(r["packet_bytes"])
            elif r["event"] == "RX":
                tc_rx += int(r["tc_count"])

    return {
        "pdr_pct": float(result["pdr"]) * 100,
        "mean_mpr": mpr_total / mpr_events,
        "change_rate_pct": 100 * changes / transitions,
        "tc_tx": tc_tx,
        "tc_rx": tc_rx,
        "tx_bytes": tx_bytes,
    }


def paired_stats(differences):
    n = len(differences)
    mean = statistics.mean(differences)
    sd = statistics.stdev(differences)
    se = sd / math.sqrt(n)

    return (
        mean,
        mean - T_CRITICAL * se,
        mean + T_CRITICAL * se,
    )


METRICS = [
    ("pdr_pct", "PDR (percentage points)"),
    ("mean_mpr", "Mean MPR"),
    ("change_rate_pct", "MPR change rate (pp)"),
    ("tc_tx", "TC TX"),
    ("tc_rx", "TC RX"),
    ("tx_bytes", "Control TX bytes"),
]

print("Paired analysis: Mode 4 - Mode 2")
print("95% confidence intervals, n=10 paired seeds")
print()

for radius in (150, 200, 250):
    print(f"========== Range {radius}m ==========")

    pairs = []

    for seed in range(11, 21):
        key = (radius, seed)

        if key not in old:
            raise RuntimeError(f"Missing Mode 2 result: {key}")

        pairs.append((old[key], analyze_mode4(radius, seed)))

    for key, label in METRICS:
        values2 = [float(a[key]) for a, b in pairs]
        values4 = [float(b[key]) for a, b in pairs]

        differences = [
            b - a for a, b in zip(values2, values4)
        ]

        mean, lo, hi = paired_stats(differences)

        significant = lo > 0 or hi < 0

        print(
            f"{label:27s} "
            f"M2={statistics.mean(values2):10.3f} "
            f"M4={statistics.mean(values4):10.3f} "
            f"Diff={mean:+10.3f} "
            f"95%CI=[{lo:+.3f}, {hi:+.3f}] "
            f"{'SIGNIFICANT' if significant else 'NOT SIGNIFICANT'}"
        )

    print()
