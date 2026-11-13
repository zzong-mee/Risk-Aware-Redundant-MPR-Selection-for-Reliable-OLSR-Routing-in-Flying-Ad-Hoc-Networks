#!/usr/bin/env python3
"""Verify Mode 5 candidate ranking and 2-hop coverage from AUDIT logs."""
import argparse
import math
import re
from collections import defaultdict

P = re.compile(r'\[node (\d+)\].*?Mode5 AUDIT (BEGIN|ROUND|CANDIDATE|CHOICE|COVERAGE|UNCOVERED|END)\s+(.*)')
KV = re.compile(r'([a-zA-Z_]+)=([^\s]+)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log', nargs='?', default='mode5_stage7.log')
    args = ap.parse_args()
    groups = defaultdict(lambda: {'rounds': defaultdict(lambda: {'candidates': [], 'choice': None}), 'coverage': None, 'end': False})
    with open(args.log, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = P.search(line)
            if not m:
                continue
            node, kind, rest = m.groups()
            d = dict(KV.findall(rest))
            if 'audit' not in d:
                continue
            key = (node, d['audit'])
            g = groups[key]
            if kind == 'CANDIDATE':
                g['rounds'][int(d['round'])]['candidates'].append(d)
            elif kind == 'CHOICE':
                g['rounds'][int(d['round'])]['choice'] = d
            elif kind == 'ROUND':
                _ = g['rounds'][int(d['round'])]
            elif kind == 'COVERAGE':
                g['coverage'] = d
            elif kind == 'END':
                g['end'] = True
    checks = failures = fallback = incomplete = rounds = 0
    for key, g in groups.items():
        if not g['end'] or g['coverage'] is None:
            incomplete += 1
            continue
        coverage = g['coverage']
        checks += 1
        if int(coverage['uncovered']) != 0:
            failures += 1
            print('FAIL coverage', key, coverage)
        for n, r in g['rounds'].items():
            rounds += 1
            c = r['choice']
            if c is None:
                failures += 1
                print('FAIL missing choice', key, n)
                continue
            eligible = [x for x in r['candidates'] if x.get('eligible') == '1']
            if c['type'] == 'SELECT':
                checks += 1
                if not eligible:
                    failures += 1
                    print('FAIL SELECT without eligible candidates', key, n)
                    continue
                expected = min(eligible, key=lambda x: (float(x['weight']), float(x['etx']), tuple(int(v) for v in x['neighbor'].split('.'))))
                if c.get('neighbor') != expected['neighbor']:
                    failures += 1
                    print('FAIL not minimum', key, n, 'actual', c.get('neighbor'), 'expected', expected['neighbor'])
            elif c['type'] == 'FALLBACK':
                fallback += 1
                if eligible:
                    failures += 1
                    print('FAIL FALLBACK despite eligible candidate', key, n)
            elif c['type'] == 'NONE':
                if eligible:
                    failures += 1
                    print('FAIL NONE despite eligible candidate', key, n)
    print(f'audits={len(groups)} complete={len(groups)-incomplete} rounds={rounds} checks={checks} fallback={fallback} incomplete={incomplete} failures={failures}')
    if not groups or checks == 0:
        print('NO AUDIT DATA: ensure NS_LOG is enabled and Mode 5 executed')
        return 2
    if failures:
        return 1
    if incomplete:
        print('WARNING: incomplete audits were skipped')
    print('PASS: recorded candidate ranking and 2-hop coverage checks')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
