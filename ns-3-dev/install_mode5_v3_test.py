#!/usr/bin/env python3
"""Add the Mode 5 V3 round-trip TestCase to an existing ns-3 OLSR header test suite.
Preserves all original tests and makes a .bak backup. Idempotent.
Run from the ns-3 root: python3 install_mode5_v3_test.py
"""
from pathlib import Path
import re
import shutil
import sys

root = Path.cwd()
target = root / 'src/olsr/test/olsr-header-test-suite.cc'
addition = Path(__file__).with_name('mode5-v3-test-case.inc').read_text()
if not target.is_file():
    sys.exit(f'Cannot find {target}; run from ns-3 root')
source = target.read_text()
if 'class OlsrMode5HelloV3TestCase' in source:
    print('Test class already present; no changes made.')
    sys.exit(0)

# Insert before the next test class, preserving existing test cases.
anchor = re.search(r'(?m)^class OlsrTcTestCase\s*:', source)
if not anchor:
    sys.exit('Could not locate OlsrTcTestCase. Original file unchanged.')
source = source[:anchor.start()] + addition + '\n' + source[anchor.start():]

# Find the original Hello registration (even if wrapped across lines).
pattern = re.compile(r'AddTestCase\s*\(\s*new\s+OlsrHelloTestCase\s*\(\s*\)\s*,\s*TestCase::Duration::\w+\s*\)\s*;')
match = pattern.search(source)
if not match:
    sys.exit('Could not locate AddTestCase(new OlsrHelloTestCase(), ...). Original file unchanged.\n'
             'Please share the bottom of olsr-header-test-suite.cc.')
registration = '\n        AddTestCase(new OlsrMode5HelloV3TestCase(), TestCase::Duration::QUICK);'
source = source[:match.end()] + registration + source[match.end():]
backup = target.with_suffix(target.suffix + '.bak')
if backup.exists():
    sys.exit(f'Backup already exists: {backup}. Original file unchanged.')
shutil.copy2(target, backup)
target.write_text(source)
print(f'Updated: {target}')
print(f'Backup:  {backup}')
print('Added Mode 5 V3 tests for 15, 16, and 29 reception ratios.')
