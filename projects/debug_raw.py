# -*- coding: utf-8 -*-
import sys, os, shutil, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
os.environ['COZE_WORKSPACE_PATH'] = os.getcwd()
import importlib, src.tools.pulse_tools as pt
importlib.reload(pt)

td = os.path.join(pt.PROJECTS_DIR, 'TestE2E')
if os.path.exists(td): shutil.rmtree(td)
pt.create_project('TestE2E', 'e2e', 'full', 'coding')
pt.create_module('TestE2E', 'Basics', 'learn', 30)
pt.add_challenge('TestE2E', 1, 'vars')

mf = os.path.join(td, 'modules', 'module_01.md')
with open(mf, encoding='utf-8') as f: raw = f.read()

# Find the first ---close position
pos0 = raw.find('---')
pos1 = raw.find('---', pos0+1)
print(f"First --- at {pos0}, second at {pos1}")
print(f"Chars {pos0-5}:{pos1+10}:")
segment = raw[pos0-5:pos1+10]
for i, ch in enumerate(segment):
    if ch == '\n':
        print(f"  [{i}] '\\n'")
    else:
        print(f"  [{i}] {repr(ch)}", end='')
        if (i+1) % 8 == 0: print()
print()

# Also check what _update_yaml_frontmatter does step by step
lines = raw.split('\n')
print(f"lines[9:14]:")
for li in range(9, 14):
    print(f"  [{li}] {repr(lines[li])}")
print(f"end_idx = 11 (--- at line 11)")
print(f"lines[12] = {repr(lines[12])}")
print(f"'\\n'.join(lines[11:14]) = {repr(chr(10).join(lines[11:14]))}")
