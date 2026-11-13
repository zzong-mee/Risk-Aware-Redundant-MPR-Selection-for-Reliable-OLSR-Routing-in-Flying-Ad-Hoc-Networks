import re
from pathlib import Path
from collections import defaultdict

ROOT = Path("results/main")
SPEED = 15
SEED = 6

NODE_RE = re.compile(
    r"^\s*Node:\s*(\d+),\s*Time:\s*\+?([\d.]+)s"
)
ROUTE_RE = re.compile(
    r"^\s*(\d+\.\d+\.\d+\.\d+)\s+"
    r"(\d+\.\d+\.\d+\.\d+)\s+"
    r"(\d+)\s+(\d+)\s*$"
)


def load_routes(mode):
    path = ROOT / f"speed{SPEED}_seed{SEED}_mode{mode}.csv.routes.txt"

    routes = defaultdict(dict)
    current_node = None
    in_olsr_table = False
    node_headers = 0
    olsr_headers = 0
    route_rows = 0
    unmatched = []

    for line in path.read_text().splitlines():
        m = NODE_RE.match(line)

        if m:
            node_headers += 1

            in_olsr_table = "OLSR Routing table" in line
            current_node = None

            if in_olsr_table:
                current_node = (float(m.group(2)), int(m.group(1)))
                routes[current_node]
                olsr_headers += 1

            continue

        if not in_olsr_table or current_node is None:
            continue

        if line.strip().startswith("Destination"):
            continue

        if not line.strip():
            continue

        m = ROUTE_RE.match(line)

        if m:
            dest, nexthop, interface, hops = m.groups()
            routes[current_node][dest] = (
                nexthop,
                int(hops)
            )
            route_rows += 1
        elif len(unmatched) < 5:
            unmatched.append(line)

    print(
        f"Mode {mode}: "
        f"전체 헤더 {node_headers}, "
        f"OLSR 헤더 {olsr_headers}, "
        f"스냅샷 {len(routes)}, "
        f"경로 {route_rows}"
    )

    if unmatched:
        print("파싱되지 않은 행 예시:")
        for line in unmatched:
            print(repr(line))

    return routes

r3 = load_routes(3)
r4 = load_routes(4)

common = set(r3) & set(r4)

same = 0
next_hop_diff = 0
hop_diff = 0
missing_in_4 = 0
extra_in_4 = 0
examples = []

for key in sorted(common):
    a = r3[key]
    b = r4[key]

    for dest in set(a) | set(b):
        if dest not in b:
            missing_in_4 += 1
            continue

        if dest not in a:
            extra_in_4 += 1
            continue

        if a[dest] == b[dest]:
            same += 1
        else:
            if a[dest][0] != b[dest][0]:
                next_hop_diff += 1
            if a[dest][1] != b[dest][1]:
                hop_diff += 1

            if len(examples) < 15:
                examples.append((key, dest, a[dest], b[dest]))

print("\n===== 라우팅 테이블 비교 =====")
print("공통 스냅샷:", len(common))
print("동일 경로:", same)
print("다음 홉 차이:", next_hop_diff)
print("홉 수 차이:", hop_diff)
print("Mode 4에서 누락된 경로:", missing_in_4)
print("Mode 4에만 존재하는 경로:", extra_in_4)

print("\n===== 경로 차이 예시 =====")
for key, dest, a, b in examples:
    print(
        f"time={key[0]:.1f}s node={key[1]} "
        f"dest={dest} Mode3={a} Mode4={b}"
    )

print("\n===== 홉 수 변화 방향 분석 =====")

hop_increase = 0
hop_decrease = 0
hop_same = 0

by_time = defaultdict(lambda: {
    "increase": 0,
    "decrease": 0,
    "same": 0,
    "next_hop_diff": 0
})

for key in sorted(common):
    time, node = key

    for dest in set(r3[key]) & set(r4[key]):
        nh3, h3 = r3[key][dest]
        nh4, h4 = r4[key][dest]

        if h4 > h3:
            hop_increase += 1
            by_time[time]["increase"] += 1
        elif h4 < h3:
            hop_decrease += 1
            by_time[time]["decrease"] += 1
        else:
            hop_same += 1
            by_time[time]["same"] += 1

        if nh3 != nh4:
            by_time[time]["next_hop_diff"] += 1

print("Mode 4 홉 수 증가:", hop_increase)
print("Mode 4 홉 수 감소:", hop_decrease)
print("홉 수 동일:", hop_same)

print("\n===== 시각별 비교 =====")
for time, counts in sorted(by_time.items()):
    print(
        f"{time:.1f}s: "
        f"증가={counts['increase']}, "
        f"감소={counts['decrease']}, "
        f"동일={counts['same']}, "
        f"다음 홉 차이={counts['next_hop_diff']}"
    )

print("\n===== 실제 데이터 플로우 경로 분석 =====")

SOURCE_NODE = 0
DESTINATION = "10.1.1.30"

for key in sorted(common):
    time, node = key

    if node != SOURCE_NODE:
        continue

    route3 = r3[key].get(DESTINATION)
    route4 = r4[key].get(DESTINATION)

    print(f"\n시간: {time:.1f}s")
    print(f"Mode 3: {route3}")
    print(f"Mode 4: {route4}")

    if route3 and route4:
        if route3[0] != route4[0]:
            print("→ 다음 홉이 다름")

        if route3[1] != route4[1]:
            print("→ 홉 수가 다름")
