#!/usr/bin/env python3
"""Add failure-only MPR coverage diagnostics to the existing complete ns-3 source.

Keeps the user's local olsr-routing-protocol.cc intact except for one insertion.
"""
from pathlib import Path
import sys

path = Path('src/olsr/model/olsr-routing-protocol.cc')
if not path.is_file():
    sys.exit(f'ERROR: {path} not found. Run from ~/jm/ns-3-dev')
s = path.read_text()
if 'MODE5_FAILURE_DETAIL' in s:
    sys.exit('Already installed; no changes made.')
anchor = '''        NS_LOG_UNCOND("MODE5_COVERAGE"
              << " node=" << m_mainAddress
              << " audit=" << mode5AuditId
              << " targets=" << targets.size()
              << " uncovered=" << uncovered.size()
              << " mprs=" << mprSet.size());'''
# Locate existing log statement flexibly, retaining exact local formatting.
import re
pattern = re.compile(r'(?P<stmt>^[ \t]*NS_LOG_UNCOND\("MODE5_COVERAGE"[\s\S]*?<<\s*" mprs="\s*<<\s*mprSet\.size\(\)\s*\);)', re.M)
matches = list(pattern.finditer(s))
if len(matches) != 1:
    sys.exit(f'ERROR: expected exactly one MODE5_COVERAGE statement, found {len(matches)}; no changes made.')
insert = '''
        // Failure-only diagnostic: does not alter MPR selection.
        if (!uncovered.empty())
        {
            for (const auto& target : uncovered)
            {
                NS_LOG_UNCOND("MODE5_FAILURE_DETAIL"
                              << " node=" << m_mainAddress
                              << " audit=" << mode5AuditId
                              << " target=" << target);
                for (const auto& twoHop : mode5OriginalN2)
                {
                    if (twoHop.twoHopNeighborAddr == target)
                    {
                        NS_LOG_UNCOND("MODE5_FAILURE_RELAY"
                                      << " node=" << m_mainAddress
                                      << " audit=" << mode5AuditId
                                      << " target=" << target
                                      << " relay=" << twoHop.neighborMainAddr
                                      << " selected=" << (mprSet.count(twoHop.neighborMainAddr) ? 1 : 0));
                    }
                }
            }
        }'''
backup = path.with_name(path.name + '.before-failure-detail.bak')
if backup.exists():
    sys.exit(f'ERROR: backup {backup} already exists; no changes made.')
backup.write_text(s)
m = matches[0]
path.write_text(s[:m.end()] + insert + s[m.end():])
print(f'Updated complete source: {path}')
print(f'Original backup: {backup}')
print('Added failure-only diagnostics without changing MPR selection logic.')
