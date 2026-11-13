#!/usr/bin/env python3
"""Extract and test the actual LET function from ns-3 OLSR source (no source edits)."""
from pathlib import Path
import re
import subprocess
import tempfile

source = Path('src/olsr/model/olsr-routing-protocol.cc')
if not source.is_file():
    raise SystemExit('Run from ns-3-dev root: python3 test_mode5_let.py')
s = source.read_text()
match = re.search(r'static\s+double\s+CalculateLinkExpirationTime\s*\(', s)
if not match:
    raise SystemExit('Cannot find static CalculateLinkExpirationTime in source')
start = match.start()
brace = s.find('{', match.end())
if brace < 0:
    raise SystemExit('Function opening brace not found')
depth = 0
end = None
for i in range(brace, len(s)):
    if s[i] == '{': depth += 1
    elif s[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end is None:
    raise SystemExit('Function closing brace not found')
func = s[start:end]
cpp = r'''#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <string>
struct Vector { double x,y,z; };
Vector operator-(const Vector& a,const Vector& b) {return {a.x-b.x,a.y-b.y,a.z-b.z};}
''' + func + r'''
int main() {
    struct Test { const char* name; Vector pi,pj,vi,vj; double range,expected; bool infinite; };
    Test cases[] = {
      {"moving_apart", {0,0,0},{100,0,0},{0,0,0},{10,0,0},150,5,false},
      {"approaching_then_departing", {0,0,0},{100,0,0},{0,0,0},{-10,0,0},150,25,false},
      {"equal_velocity", {0,0,0},{100,0,0},{10,0,0},{10,0,0},150,0,true},
      {"3d_moving_apart", {0,0,0},{0,0,100},{0,0,0},{0,0,10},150,5,false},
      {"out_of_range", {0,0,0},{200,0,0},{0,0,0},{0,0,0},150,0,false},
    };
    int failures=0;
    for(const auto& t : cases) {
        double actual=CalculateLinkExpirationTime(t.pi,t.pj,t.vi,t.vj,t.range);
        bool ok=t.infinite ? std::isinf(actual) && actual>0 : std::isfinite(actual) && std::abs(actual-t.expected)<1e-9;
        std::cout << (ok ? "PASS " : "FAIL ") << t.name << " actual=" << actual;
        if(t.infinite) std::cout << " expected=inf";
        else std::cout << " expected=" << t.expected;
        std::cout << '\n';
        failures+=!ok;
    }
    return failures ? 1 : 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mode5_let_') as tmp:
    p = Path(tmp)
    (p/'let_test.cc').write_text(cpp)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-O2',str(p/'let_test.cc'),'-o',str(p/'let_test')],check=True)
    result = subprocess.run([str(p/'let_test')],check=False)
    raise SystemExit(result.returncode)
