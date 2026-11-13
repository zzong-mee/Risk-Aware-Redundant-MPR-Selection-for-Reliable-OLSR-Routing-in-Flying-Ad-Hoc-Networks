#!/usr/bin/env python3
"""Side-by-side ns-3 OLSR / Mode4 MPR CSV visualizer (Tkinter, stdlib only)."""
import argparse
import csv
import math
import tkinter as tk
from collections import defaultdict
from tkinter import ttk

def read_csv(path):
    frames = defaultdict(lambda: {"nodes": {}, "edges": [], "mpr": defaultdict(set), "routes": {}})
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = round(float(r["time"]), 3)
            typ, src = r["type"], int(r["id"])
            fr = frames[t]
            if typ == "NODE":
                fr["nodes"][src] = (float(r["x_or_to"]), float(r["y_or_weight"]))
            elif typ == "EDGE":
                fr["edges"].append((src, int(float(r["x_or_to"]))))
            elif typ == "MPR":
                fr["mpr"][src].add(int(float(r["x_or_to"])))
            elif typ == "ROUTE":
                fr["routes"][(src, int(float(r["x_or_to"])))] = int(float(r["y_or_weight"]))
    return dict(frames)

def trace_route(frame, start, target):
    """Reconstruct a route using each intermediate node's own next-hop table."""
    if start == target:
        return [start]
    path = [start]
    seen = {start}
    current = start
    for _ in range(len(frame["nodes"])):
        hop = frame["routes"].get((current, target))
        if hop is None or hop not in frame["nodes"] or hop in seen:
            return None
        path.append(hop)
        if hop == target:
            return path
        seen.add(hop)
        current = hop
    return None


def main():
    ap = argparse.ArgumentParser(description="Compare 8-node OLSR MPR sets")
    ap.add_argument("baseline", nargs="?", default="olsr-route-trace-8nodes-mode0.csv")
    ap.add_argument("proposed", nargs="?", default="olsr-route-trace-8nodes-mode4.csv")
    args = ap.parse_args()
    base = read_csv(args.baseline)
    prop = read_csv(args.proposed)
    times = sorted(t for t in base.keys() & prop.keys()
                   if base[t]["nodes"] and prop[t]["nodes"])
    if not times:
        raise SystemExit("No common NODE timestamps in the two CSV files.")
    node_ids = sorted(set(base[times[0]]["nodes"]) & set(prop[times[0]]["nodes"]))
    if not node_ids:
        raise SystemExit("No common node IDs.")

    # Only treat set differences as "backup" when mobility matches.
    max_error = 0.0
    mismatches = 0
    for t in times:
        for n in base[t]["nodes"].keys() & prop[t]["nodes"].keys():
            a, b = base[t]["nodes"][n], prop[t]["nodes"][n]
            d = math.dist(a, b)
            max_error = max(max_error, d)
            if d > 0.05:
                mismatches += 1
    comparable = mismatches == 0

    root = tk.Tk()
    root.title("OLSR vs Hysteresis-CVaR-RAMPR | MPR comparison")
    root.geometry("1380x850")
    root.configure(bg="#f1f5f9")
    idx = tk.IntVar(value=0)
    focus = tk.IntVar(value=0 if 0 in node_ids else node_ids[0])
    destination = tk.IntVar(value=7 if 7 in node_ids else node_ids[-1])
    speed = tk.DoubleVar(value=1.0)
    playing = tk.BooleanVar(value=False)
    show_all = tk.BooleanVar(value=False)
    status = tk.StringVar()
    warning = tk.StringVar()
    if comparable:
        warning.set("동일한 노드 위치 확인됨 (오차 ≤ 0.05m) | 주황색 = Mode 4에서 추가 선택된 MPR")
    else:
        warning.set(f"주의: 두 실험의 이동 경로가 다릅니다! 위치 불일치 {mismatches}건, 최대 {max_error:.2f}m. "
                    "주황색은 '집합 차이'일 뿐 백업 MPR로 확정할 수 없습니다.")

    title = tk.Label(root, text="OLSR MPR 선택 비교 | 8-node FANET",
                     font=("Arial", 20, "bold"), bg="#f1f5f9", fg="#0f172a")
    title.pack(pady=(12, 4))
    tk.Label(root, textvariable=warning, font=("Arial", 11, "bold"),
             fg=("#166534" if comparable else "#b91c1c"), bg="#f1f5f9",
             wraplength=1300).pack(pady=(0, 8))

    control = tk.Frame(root, bg="#f1f5f9")
    control.pack(fill="x", padx=18, pady=5)
    play_btn = ttk.Button(control, text="▶ 재생", command=lambda: toggle())
    play_btn.pack(side="left", padx=4)
    ttk.Button(control, text="⟲ 처음", command=lambda: (playing.set(False), idx.set(0), slider.set(0), render())).pack(side="left", padx=4)
    tk.Label(control, text="기준 노드:", bg="#f1f5f9").pack(side="left", padx=(16, 4))
    node_combo = ttk.Combobox(control, textvariable=focus, values=node_ids, state="readonly", width=5)
    node_combo.pack(side="left")
    node_combo.bind("<<ComboboxSelected>>", lambda _e: render())
    tk.Label(control, text="도착 노드:", bg="#f1f5f9").pack(side="left", padx=(12, 4))
    dest_combo = ttk.Combobox(control, textvariable=destination, values=node_ids, state="readonly", width=5)
    dest_combo.pack(side="left")
    dest_combo.bind("<<ComboboxSelected>>", lambda _e: render())
    tk.Label(control, text="재생 속도:", bg="#f1f5f9").pack(side="left", padx=(16, 4))
    speed_combo = ttk.Combobox(control, textvariable=speed, values=[0.5, 1.0, 2.0, 4.0],
                               state="readonly", width=5)
    speed_combo.pack(side="left")
    ttk.Checkbutton(control, text="모든 노드의 MPR 표시", variable=show_all,
                    command=lambda: render()).pack(side="left", padx=18)
    tk.Label(control, textvariable=status, bg="#f1f5f9",
             font=("Arial", 11, "bold")).pack(side="right", padx=10)

    slider = ttk.Scale(root, from_=0, to=len(times)-1, orient="horizontal",
                       command=lambda v: (idx.set(round(float(v))), render()))
    slider.pack(fill="x", padx=22, pady=7)
    panes = tk.Frame(root, bg="#f1f5f9")
    panes.pack(fill="both", expand=True, padx=15, pady=5)
    canvases = []
    count_labels = []
    for col, heading in enumerate(("기존 OLSR (Mode 0)", "Hysteresis-CVaR-RAMPR (Mode 4)")):
        frame = tk.Frame(panes, bg="white", highlightthickness=1, highlightbackground="#cbd5e1")
        frame.grid(row=0, column=col, padx=6, sticky="nsew")
        tk.Label(frame, text=heading, font=("Arial", 15, "bold"),
                 bg="white", fg="#0f172a").pack(pady=(10, 2))
        counter = tk.Label(frame, bg="#f8fafc", fg="#0f172a",
                           font=("Arial", 12, "bold"), pady=7)
        counter.pack(fill="x", padx=8, pady=(4, 2))
        count_labels.append(counter)
        c = tk.Canvas(frame, bg="white", highlightthickness=0, height=450)
        c.pack(fill="both", expand=True, padx=8, pady=8)
        canvases.append(c)
    panes.columnconfigure(0, weight=1)
    panes.columnconfigure(1, weight=1)
    panes.rowconfigure(0, weight=1)

    info = tk.Label(root, bg="#e2e8f0", fg="#0f172a",
                    font=("Arial", 12), justify="left", anchor="w",
                    wraplength=1300, padx=15, pady=10)
    info.pack(fill="x", padx=21, pady=(4, 12))

    def render():
        t = times[min(max(idx.get(), 0), len(times)-1)]
        n = focus.get()
        target = destination.get()
        b, p = base[t], prop[t]
        bm = b["mpr"].get(n, set())
        pm = p["mpr"].get(n, set())
        extra = pm - bm
        lost = bm - pm
        status.set(f"t = {t:.1f}s  |  {idx.get()+1}/{len(times)}")
        path0 = trace_route(b, n, target)
        path4 = trace_route(p, n, target)
        route_info = (f"\n데이터 경로 {n} → {target} | Mode 0: "
                      + (" → ".join(map(str, path0)) if path0 else "경로 없음")
                      + "    | Mode 4: "
                      + (" → ".join(map(str, path4)) if path4 else "경로 없음"))
        info.config(text=(f"노드 {n} | 기존 MPR: {sorted(bm)} ({len(bm)}개)     "
                          f"Mode 4 MPR: {sorted(pm)} ({len(pm)}개)     "
                          f"Mode 4에만 있는 MPR: {sorted(extra)}     "
                          f"기존에만 있는 MPR: {sorted(lost)}" + route_info
                          + ("\n※ 이동 경로가 달라 백업 MPR로 해석할 수 없습니다." if not comparable else
                             "\n※ 주황색은 Mode 0 대비 추가된 MPR이며, 동일한 2홉 노드 중복 커버 여부는 별도 검증이 필요합니다.")))
        count_labels[0].config(text=f"기준 노드 {n} | 선택 MPR {len(bm)}개 | {sorted(bm)}")
        count_labels[1].config(text=f"기준 노드 {n} | 선택 MPR {len(pm)}개 | 추가 {len(extra)}개 | {sorted(pm)}")
        for side, (canvas, frame) in enumerate(zip(canvases, (b, p))):
            canvas.delete("all")
            w, h = max(canvas.winfo_width(), 550), max(canvas.winfo_height(), 400)
            pts = frame["nodes"]
            if not pts:
                continue
            # Shared coordinate transform for both sides, including all timestamps.
            x0, y0, x1, y1 = bounds
            scale = min((w-80)/(x1-x0), (h-80)/(y1-y0))
            def xy(i):
                x, y = pts[i]
                return (40+(x-x0)*scale, 40+(y-y0)*scale)
            # Avoid visually merging close nodes: displace only their DRAWN positions.
            # Underlying simulation coordinates and CSV values remain unchanged.
            node_positions = {node: xy(node) for node in sorted(pts)}
            drawn = {}
            for node in sorted(pts, key=lambda i: (i != target, i != n, i)):
                x, y = node_positions[node]
                if any(math.hypot(x-ox, y-oy) < 34 for ox, oy in drawn.values()):
                    for radius in (38, 50, 65, 80):
                        candidates = [(x + radius*math.cos(k*math.pi/4),
                                       y + radius*math.sin(k*math.pi/4)) for k in range(8)]
                        valid = [(cx, cy) for cx, cy in candidates
                                 if 20 <= cx <= w-20 and 36 <= cy <= h-34
                                 and all(math.hypot(cx-ox, cy-oy) >= 34 for ox, oy in drawn.values())]
                        if valid:
                            x, y = min(valid, key=lambda v: math.hypot(v[0]-x, v[1]-y))
                            break
                drawn[node] = (x, y)
            def draw_xy(node):
                return drawn[node]
            # Tiny dotted tether indicates that a close node was displaced for clarity.
            for node, (x, y) in drawn.items():
                ox, oy = node_positions[node]
                if math.hypot(x-ox, y-oy) > 1:
                    canvas.create_line(ox, oy, x, y, fill="#94a3b8", dash=(2, 3))
            for a, z in frame["edges"]:
                if a in pts and z in pts:
                    ax, ay = draw_xy(a); bx, by = draw_xy(z)
                    canvas.create_line(ax, ay, bx, by, fill="#cbd5e1", width=1.3)
            for a, chosen in frame["mpr"].items():
                if not show_all.get() and a != n:
                    continue
                if a not in pts:
                    continue
                for z in chosen:
                    if z not in pts:
                        continue
                    ax, ay = draw_xy(a); bx, by = draw_xy(z)
                    color = "#16a34a" if side == 0 or z in base[t]["mpr"].get(a, set()) else "#f97316"
                    canvas.create_line(ax, ay, bx, by, fill=color, width=3.2, dash=(7, 4),
                                       arrow=tk.LAST, arrowshape=(9, 10, 4))
            # Draw the routing-table path on top of MPR relations.
            route = path0 if side == 0 else path4
            if route:
                for a, z in zip(route, route[1:]):
                    ax, ay = draw_xy(a); bx, by = draw_xy(z)
                    dx, dy = bx-ax, by-ay
                    length = math.hypot(dx, dy)
                    if length > 1:
                        ux, uy = dx/length, dy/length
                        ax += ux*16; ay += uy*16
                        bx -= ux*16; by -= uy*16
                    canvas.create_line(ax, ay, bx, by, fill="#a855f7", width=4.5,
                                       arrow=tk.LAST, arrowshape=(12, 13, 5))
            else:
                canvas.create_text(w/2, 22, text=f"{n} → {target}: 라우팅 경로 없음",
                                   fill="#dc2626", font=("Arial", 12, "bold"))
            for node in sorted(pts):
                x, y = draw_xy(node)
                fill = "#64748b"
                if side == 1 and node in extra and not show_all.get():
                    fill = "#f97316"
                elif node in frame["mpr"].get(n, set()) and not show_all.get():
                    fill = "#16a34a"
                if node == n:
                    fill = "#2563eb"
                if node == target:
                    fill = "#dc2626"
                radius = 17 if node in (n, target) else 14
                if node == target:
                    canvas.create_oval(x-23, y-23, x+23, y+23, outline="#dc2626", width=3)
                canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                   fill=fill, outline="white", width=2)
                canvas.create_text(x, y, text=str(node), fill="white", font=("Arial", 10, "bold"))
                if node == n and node != target:
                    canvas.create_text(x, y-30, text=f"SRC {n}", fill="#2563eb", font=("Arial", 10, "bold"))
                if node == target:
                    canvas.create_text(x, y-34, text=f"DEST {target}", fill="#dc2626", font=("Arial", 11, "bold"))
            canvas.create_rectangle(8, h-33, w-8, h-3, fill="white", outline="")
            canvas.create_text(10, h-14, anchor="w", fill="#64748b",
                               text="회색: 근접 연결   초록: 기본 MPR   주황: 추가 MPR   보라: OLSR 경로",
                               font=("Arial", 9))
    def toggle():
        playing.set(not playing.get())
        play_btn.config(text="⏸ 일시정지" if playing.get() else "▶ 재생")
        if playing.get():
            tick()
    def tick():
        if not playing.get():
            return
        if idx.get() >= len(times)-1:
            playing.set(False)
            play_btn.config(text="▶ 재생")
            return
        idx.set(idx.get()+1)
        render()
        slider.set(idx.get())
        dt = max(20, int((times[idx.get()] - times[idx.get()-1])*1000/speed.get()))
        root.after(dt, tick)

    all_positions = [pt for t in times for data in (base[t], prop[t])
                     for pt in data["nodes"].values()]
    xs = [p[0] for p in all_positions]
    ys = [p[1] for p in all_positions]
    bounds = (min(xs)-10, min(ys)-10, max(xs)+10, max(ys)+10)
    for c in canvases:
        c.bind("<Configure>", lambda _e: render())
    render()
    root.mainloop()

if __name__ == "__main__":
    main()
