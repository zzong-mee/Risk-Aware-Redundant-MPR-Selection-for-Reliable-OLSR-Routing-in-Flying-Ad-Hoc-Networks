import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path("results/main")
SPEED = 15
SEED = 6

def parse_mprs(s):
    if not s.strip():
        return frozenset()
    return frozenset(
        x.strip()
        for x in s.replace(";", " ").replace("|", " ").split()
        if x.strip()
    )

def load(mode):
    p = ROOT / f"speed{SPEED}_seed{SEED}_mode{mode}.csv.mpr.csv"
    by_node = defaultdict(list)

    with p.open(newline="") as f:
        for r in csv.DictReader(f):
            t = float(r["time"])
            node = r["node_address"]
            mprs = parse_mprs(r["mpr_addresses"])

            declared = int(r["mpr_count"])
            if len(mprs) != declared:
                raise ValueError(
                    f"Mode {mode}, node {node}, t={t}: "
                    f"mpr_count={declared}, parsed={len(mprs)}"
                )

            by_node[node].append((t, mprs))

    return by_node

def analyze(by_node):
    total_rows = 0
    total_changes = 0
    total_adds = 0
    total_removes = 0
    sizes = []
    change_counts = []

    for node, entries in by_node.items():
        entries.sort(key=lambda x: x[0])
        prev = None
        changes = 0

        for t, curr in entries:
            total_rows += 1
            sizes.append(len(curr))

            if prev is not None and curr != prev:
                changes += 1
                total_changes += 1
                total_adds += len(curr - prev)
                total_removes += len(prev - curr)

            prev = curr

        change_counts.append((node, changes))

    return {
        "nodes": len(by_node),
        "rows": total_rows,
        "mean_mpr": mean(sizes),
        "changes": total_changes,
        "adds": total_adds,
        "removes": total_removes,
        "top_changes": sorted(
            change_counts,
            key=lambda x: x[1],
            reverse=True
        )[:5],
    }

data = {mode: load(mode) for mode in [3, 4]}

print("===== 15m/s, Seed 6: MPR 비교 =====")

for mode in [3, 4]:
    s = analyze(data[mode])
    print(f"\nMode {mode}")
    print("노드 수:", s["nodes"])
    print("MPR 기록 수:", s["rows"])
    print("평균 MPR 개수:", round(s["mean_mpr"], 3))
    print("MPR 집합 변경:", s["changes"])
    print("MPR 추가:", s["adds"])
    print("MPR 제거:", s["removes"])
    print("변경이 많은 노드:", s["top_changes"])

# 두 Mode의 동일 노드, 동일 시각 기록만 비교
a = {}
b = {}

for mode, dest in [(3, a), (4, b)]:
    for node, entries in data[mode].items():
        for t, mprs in entries:
            key = (node, round(t, 6))
            dest[key] = mprs

common = set(a) & set(b)
only3 = set(a) - set(b)
only4 = set(b) - set(a)

jaccards = []
different = 0

for key in common:
    x, y = a[key], b[key]

    if x != y:
        different += 1

    union = x | y
    jaccards.append(
        len(x & y) / len(union) if union else 1.0
    )

print("\n===== 동일 시각 MPR 집합 비교 =====")
print("공통 기록:", len(common))
print("Mode 3에만 있는 기록:", len(only3))
print("Mode 4에만 있는 기록:", len(only4))

if common:
    print("서로 다른 MPR 집합:", different)
    print("집합 차이 비율(%):", round(100*different/len(common), 2))
    print("평균 Jaccard 유사도:", round(mean(jaccards), 4))
