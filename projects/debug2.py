# -*- coding: utf-8 -*-
"""Debug table_end finding"""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
os.environ['COZE_WORKSPACE_PATH'] = os.getcwd()
import importlib, src.tools.pulse_tools as pt
importlib.reload(pt)

td = os.path.join(pt.PROJECTS_DIR, 'TestE2E')
if os.path.exists(td): shutil.rmtree(td)
pt.create_project('TestE2E', 'e2e', 'full', 'coding')
pt.create_module('TestE2E', 'Basics', 'learn', 30)
mf = os.path.join(td, 'modules', 'module_01.md')

with open(mf, encoding='utf-8') as f: raw = f.read()
ts = raw.find('| 序号 |')
print('table_start:', ts)
print('char at', ts-1, repr(raw[ts-1]))
print('char at', ts, repr(raw[ts]))
print('chars', ts, 'to', ts+60, repr(raw[ts:ts+60]))

# Show first 5 \n\n positions
pos = ts
count = 0
while count < 8:
    idx = raw.find('\n\n', pos)
    if idx == -1: break
    line_start = raw.rfind('\n', 0, idx) + 1
    line = raw[line_start:idx].strip()
    # check if separator
    sep_check = line.endswith('---') or '---' in line
    print(f'  n2 at {idx}, line repr: {repr(line[:50])}, ends---:{line.endswith("---")}, has---:{"---" in line}')
    pos = idx + 1
    count += 1
    if idx > ts + 500: break

print()
print('Separator line check:')
for i in range(ts, ts+200):
    if raw[i] == '\n':
        line_end = i
        line_start = raw.rfind('\n', 0, i) + 1
        line = raw[line_start:i]
        if '---' in line:
            print(f'  Line {line_start}-{i}: ends with ---? {line.strip().endswith("---")}, line: {repr(line.strip()[:60])}')
