#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path("results/experiment10")

def analyze(prefix):
    with prefix.open(newline="") as f:
        result = next(csv.DictReader(f))

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

    total = sum(len(rows) for rows in by_node.values())
    mean_mpr = (
        sum(len(s) for rows in by_node.values() for _, s in rows)
        / total if total else 0
    )

    changes = comparisons = 0
    for rows in by_node.values():
        rows.sort(key=lambda x: x[0])
        for (_, before), (_, after) in zip(rows, rows[1:]):
            comparisons += 1
            changes += before != after

    tc_tx = tc_rx = control_bytes = 0

    with Path(str(prefix) + ".control.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            if float(r["time"]) < 20:
                continue
            if r["event"] == "TX":
                tc_tx += int(r["tc_count"])
                control_bytes += int(r["packet_bytes"])
            elif r["event"] == "RX":
                tc_rx += int(r["tc_count"])

    return {
        "pdr": float(result["pdr"]) * 100,
        "delay": float(result["delay_ms"]),
        "mean_mpr": mean_mpr,
        "change_rate": (
            changes / comparisons * 100 if comparisons else 0
        ),
        "tc_tx": tc_tx,
        "tc_rx": tc_rx,
        "control_bytes": control_bytes
    }

print("Experiment 10: Mode 4 summary")
print()

for radius in (150, 200, 250):
    rows = []

    for seed in range(11, 21):
        prefix = ROOT / f"mode4_range{radius}_seed{seed}"
        rows.append(analyze(prefix))

    print(f"Range = {radius}m, Seeds = {len(rows)}")

    for key, label in [
        ("pdr", "PDR (%)"),
        ("delay", "Delay (ms)"),
        ("mean_mpr", "Mean MPR"),
        ("change_rate", "MPR change rate (%)"),
        ("tc_tx", "TC TX"),
        ("tc_rx", "TC RX"),
        ("control_bytes", "Control TX bytes")
    ]:
        mean = sum(r[key] for r in rows) / len(rows)
        print(f"  {label:23s}: {mean:.3f}")

    print()
