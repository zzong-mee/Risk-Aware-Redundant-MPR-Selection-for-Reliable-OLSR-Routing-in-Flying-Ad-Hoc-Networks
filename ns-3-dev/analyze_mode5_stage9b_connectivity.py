#!/usr/bin/env python3
"""Analyze ideal-range 3D graph from ns-3 positions.csv; no external packages."""
import argparse,csv,math,collections
p=argparse.ArgumentParser()
p.add_argument('positions_csv')
p.add_argument('--range',type=float,required=True,help='Ideal communication radius (m)')
p.add_argument('--src',type=int,default=0)
p.add_argument('--dst',type=int,default=None)
p.add_argument('--output',default=None)
a=p.parse_args()
if a.range<=0:p.error('--range must be >0')
bytime=collections.defaultdict(dict)
with open(a.positions_csv,newline='') as f:
    for r in csv.DictReader(f):
        t=float(r['time']); i=int(r['node'])
        bytime[t][i]=(float(r['x']),float(r['y']),float(r['z']))
if not bytime:p.error('no position samples')
all_nodes=set().union(*(set(v) for v in bytime.values()))
dst=a.dst if a.dst is not None else max(all_nodes)
rows=[]
for t,pos in sorted(bytime.items()):
    graph={i:set() for i in pos}
    ids=sorted(pos)
    for ix,i in enumerate(ids):
        for j in ids[ix+1:]:
            if math.dist(pos[i],pos[j])<=a.range:
                graph[i].add(j);graph[j].add(i)
    seen=set(); sizes=[]
    for i in ids:
        if i in seen:continue
        queue=[i];seen.add(i)
        for v in queue:
            for w in graph[v]-seen:
                seen.add(w);queue.append(w)
        sizes.append(len(queue))
    reachable=False; hops=-1
    if a.src in graph and dst in graph:
        q=collections.deque([(a.src,0)]); visited={a.src}
        while q:
            v,d=q.popleft()
            if v==dst:reachable=True;hops=d;break
            for w in graph[v]-visited:
                visited.add(w);q.append((w,d+1))
    rows.append(dict(time=t,nodes=len(ids),edges=sum(map(len,graph.values()))//2,
                     components=len(sizes),largest_component=max(sizes),
                     src_dst_connected=int(reachable),shortest_hops=hops))
if a.output:
    with open(a.output,'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
n=len(rows)
print(f'samples={n} nodes={len(all_nodes)} radius={a.range:g}m src={a.src} dst={dst}')
print(f'connected_samples={sum(r["src_dst_connected"] for r in rows)}/{n} ({100*sum(r["src_dst_connected"] for r in rows)/n:.2f}%)')
print(f'avg_edges={sum(r["edges"] for r in rows)/n:.2f} avg_components={sum(r["components"] for r in rows)/n:.2f} avg_largest_component={sum(r["largest_component"] for r in rows)/n:.2f}')
print('NOTE: geometric potential connectivity, not measured wireless delivery or OLSR route availability')
if a.output:print('CSV:',a.output)
