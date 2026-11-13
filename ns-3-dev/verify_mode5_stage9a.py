#!/usr/bin/env python3
"""Check Gauss-Markov 3D position trace: bounds and nonzero Z movement."""
import csv, sys, collections
if len(sys.argv)!=4:
    sys.exit('Usage: python3 verify_mode5_stage9a.py POSITIONS_CSV XY_BOUND Z_BOUND')
path,xy,zmax=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
by_node=collections.defaultdict(list)
with open(path,newline='') as f:
    for row in csv.DictReader(f):
        t,node,x,y,z=(float(row['time']),int(row['node']),float(row['x']),float(row['y']),float(row['z']))
        if not (0<=x<=xy and 0<=y<=xy and 0<=z<=zmax):
            sys.exit(f'FAIL: out of bounds node={node} t={t} xyz={(x,y,z)}')
        by_node[node].append((t,x,y,z))
if not by_node: sys.exit('FAIL: empty trace')
moving_z=sum(any(abs(v[3]-values[0][3])>1e-5 for v in values[1:]) for values in by_node.values())
print(f'nodes={len(by_node)} samples={sum(map(len,by_node.values()))} z_moving_nodes={moving_z} bounds=PASS')
if moving_z==0: sys.exit('FAIL: no node changed altitude')
print('PASS: 3D movement and coordinate bounds observed')
