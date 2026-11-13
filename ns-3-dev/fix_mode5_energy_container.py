#!/usr/bin/env python3
"""Fix ns-3 Mode 5 EnergySourceContainer assignment without replacing other code."""
from pathlib import Path
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else 'scratch/olsr_baseline.cc')
source = path.read_text(encoding='utf-8')
old = 'mode5Sources = battery.Install(n);'
new = 'mode5Sources.Add(battery.Install(n));'
if old not in source:
    if new in source:
        print(f'Already patched: {path}')
        sys.exit(0)
    sys.exit(f'Expected assignment not found in {path}; no changes made.')
if source.count(old) != 1:
    sys.exit(f'Expected exactly one assignment, found {source.count(old)}; no changes made.')
backup = path.with_suffix(path.suffix + '.before_energy_fix.bak')
if backup.exists():
    sys.exit(f'Backup already exists: {backup}; no changes made.')
backup.write_text(source, encoding='utf-8')
path.write_text(source.replace(old, new, 1), encoding='utf-8')
print(f'Patched: {path}')
print(f'Backup:  {backup}')
print(f'Change:  {old} -> {new}')
