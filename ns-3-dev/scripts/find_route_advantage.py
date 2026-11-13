#!/usr/bin/env python3
"""Find observed 0->7 routing-table advantage windows in ns-3 CSV traces."""
import argparse, csv, math
from collections import defaultdict

def load(path):
    frames=defaultdict(lambda:{'nodes':{},'edges':set(),'routes':{}})
    with open(path,encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            t=round(float(r['time']),3); k=r['type']; i=int(r['id']); fr=frames[t]
            if k=='NODE':fr['nodes'][i]=(float(r['x_or_to']),float(r['y_or_weight']))
            elif k=='EDGE':fr['edges'].add((i,int(float(r['x_or_to']))))
            elif k=='ROUTE':fr['routes'][(i,int(float(r['x_or_to'])))]=int(float(r['y_or_weight']))
    return frames

def path(fr,s,d):
    if s==d:return [s]
    visited={s}; p=[s]
    for _ in range(len(fr['nodes'])):
        hop=fr['routes'].get((p[-1],d))
        if hop is None or hop in visited or hop not in fr['nodes']:return None
        p.append(hop)
        if hop==d:return p
        visited.add(hop)
    return None

def physical(fr,p):
    return p is not None and all((a,b) in fr['edges'] or (b,a) in fr['edges'] for a,b in zip(p,p[1:]))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('mode0');ap.add_argument('mode4')
    ap.add_argument('--source',type=int,default=0);ap.add_argument('--dest',type=int,default=7)
    a=ap.parse_args(); b=load(a.mode0);m=load(a.mode4)
    ts=sorted(set(b)&set(m)); results=[]; mismatch=0;maxdiff=0
    for t in ts:
        x,y=b[t],m[t]
        if not x['nodes'] or not y['nodes']:continue
        for i in x['nodes'].keys()&y['nodes'].keys():
            d=math.dist(x['nodes'][i],y['nodes'][i]);maxdiff=max(maxdiff,d)
            mismatch+=d>0.05
        p0=path(x,a.source,a.dest);p4=path(y,a.source,a.dest)
        if p0 is None and p4 is not None:
            results.append((t,p4,physical(y,p4)))
    print(f'공통 시각: {len(ts)}개 | 좌표 불일치: {mismatch}건 | 최대 위치차: {maxdiff:.3f}m')
    if mismatch:print('주의: 두 모드의 노드 이동이 동일하지 않아 공정한 성능 비교로 해석할 수 없습니다.')
    print(f'Mode 0 경로 없음 / Mode 4 경로 있음: {len(results)}개 시점')
    if not results:
        print('해당 장면이 현재 CSV에는 없습니다. 선을 임의로 지우지 말고 조건/시드를 바꿔 재실험하세요.')
        return
    runs=[];cur=[]
    for rec in results:
        if cur and rec[0]-cur[-1][0]>0.501:
            runs.append(cur);cur=[]
        cur.append(rec)
    if cur:runs.append(cur)
    runs.sort(key=len,reverse=True)
    print('\n길게 지속된 구간 상위 10개:')
    for run in runs[:10]:
        t,p,ok=run[0]
        print(f'{t:.1f}~{run[-1][0]:.1f}초 ({len(run)} 프레임), Mode 4 경로: {" -> ".join(map(str,p))}, 물리 EDGE 확인: {"예" if ok else "아니오"}')
    print('\n주의: 라우팅 테이블상의 경로이며 실제 패킷 수신 성공 증거는 아닙니다.')
if __name__=='__main__':main()
