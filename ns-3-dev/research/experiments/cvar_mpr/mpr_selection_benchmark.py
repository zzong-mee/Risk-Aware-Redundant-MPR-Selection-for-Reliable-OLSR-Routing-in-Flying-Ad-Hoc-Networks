#!/usr/bin/env python3
"""Reproducible topology-level MPR benchmark; not an ns-3 routing implementation."""
import argparse, csv, math, random

def cvar(samples, alpha=.9):
    s=sorted(samples)
    k=max(1,math.ceil((1-alpha)*len(s)))
    return sum(s[-k:])/k

def trial(rng, n, radius, speed, horizon, alpha, threshold):
    pos=[(rng.uniform(0,1000),rng.uniform(0,1000)) for _ in range(n)]
    vel=[(speed*math.cos(t),speed*math.sin(t)) for t in [rng.uniform(0,2*math.pi) for _ in range(n)]]
    def links(p):
        return [{j for j in range(n) if i!=j and math.dist(p[i],p[j])<=radius} for i in range(n)]
    adj=links(pos)
    one=adj[0]
    two=set().union(*(adj[j] for j in one)) - one - {0} if one else set()
    candidates={j:adj[j]&two for j in one}
    if not two: return []
    # Monte Carlo uncertainty in positions/velocities; link failure probability per candidate->2hop edge.
    failure={}
    for j in one:
        for k in candidates[j]:
            samples=[]
            for _ in range(48):
                t=horizon
                a=(pos[j][0]+(vel[j][0]+rng.gauss(0,speed*.2))*t,
                   pos[j][1]+(vel[j][1]+rng.gauss(0,speed*.2))*t)
                b=(pos[k][0]+(vel[k][0]+rng.gauss(0,speed*.2))*t,
                   pos[k][1]+(vel[k][1]+rng.gauss(0,speed*.2))*t)
                # Loss severity: normalized exceedance beyond communication radius.
                samples.append(min(1.,max(0.,(math.dist(a,b)-radius)/max(1.,radius*.25))))
            failure[j,k]=(sum(x>0 for x in samples)/len(samples),cvar(samples,alpha))
    def select(mode):
        selected=set()
        target={k:(2 if mode=='fixed' or (mode=='cvar' and min((failure[j,k][1] for j in one if k in candidates[j]),default=0)>=threshold) else 1) for k in two}
        # Coverage feasibility: cannot request two relays when only one candidate exists.
        target={k:min(v,sum(k in candidates[j] for j in one)) for k,v in target.items()}
        while True:
            deficit={k:max(0,target[k]-sum(k in candidates[j] for j in selected)) for k in two}
            if not any(deficit.values()):break
            options=[]
            for j in one-selected:
                benefit=sum(deficit[k]>0 for k in candidates[j])
                if benefit==0:continue
                risk=sum(failure[j,k][0] for k in candidates[j] if deficit[k]>0)/benefit
                score=benefit if mode in ('greedy','fixed') else benefit/(.1+risk)
                if mode=='cvar':score=benefit/(.1+sum(failure[j,k][1] for k in candidates[j] if deficit[k]>0)/benefit)
                options.append((score,benefit,-j,j))
            if not options:break
            selected.add(max(options)[-1])
        return selected
    out=[]
    for mode in ('greedy','fixed','let','cvar'):
        chosen=select(mode)
        covered=sum(any(k in candidates[j] for j in chosen) for k in two)
        redundant=sum(sum(k in candidates[j] for j in chosen)>=2 for k in two)
        # Independent Bernoulli failure approximation from predicted edge risk.
        expected=sum(1-math.prod(failure[j,k][0] for j in chosen if k in candidates[j]) for k in two)/len(two)
        out.append(dict(mode=mode,onehop=len(one),twohop=len(two),mpr=len(chosen),coverage=covered/len(two),redundant=redundant/len(two),predicted_survival=expected))
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--runs',type=int,default=100);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--nodes',type=int,default=70);p.add_argument('--radius',type=float,default=280)
    p.add_argument('--speed',type=float,default=12);p.add_argument('--horizon',type=float,default=3)
    p.add_argument('--alpha',type=float,default=.9);p.add_argument('--threshold',type=float,default=.25)
    p.add_argument('--output',default='mpr_results.csv');a=p.parse_args()
    rng=random.Random(a.seed); rows=[]
    for run in range(a.runs):
        for r in trial(rng,a.nodes,a.radius,a.speed,a.horizon,a.alpha,a.threshold):
            r['run']=run;r['seed']=a.seed;rows.append(r)
    if not rows:raise SystemExit('No 2-hop neighborhoods sampled; adjust density/radius')
    with open(a.output,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for mode in ('greedy','fixed','let','cvar'):
        sub=[r for r in rows if r['mode']==mode]
        print(mode, 'samples', len(sub), {k:round(sum(r[k] for r in sub)/len(sub),4) for k in ('mpr','coverage','redundant','predicted_survival')})
    print('Wrote',a.output)
if __name__=='__main__':main()
