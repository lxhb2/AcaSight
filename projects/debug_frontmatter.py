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

# Add vars then check the frontmatter structure
pt.add_challenge('TestE2E', 1, 'vars')
mf = os.path.join(td, 'modules', 'module_01.md')
with open(mf, encoding='utf-8') as f: c = f.read()

# Find all --- positions
pos = 0
print("All '---' positions:")
while True:
    idx = c.find('---', pos)
    if idx == -1: break
    print(f"  at {idx}: {repr(c[idx:idx+15])}")
    pos = idx + 3

print()
# Show content around first --- close
fm1 = c.find('---')
fm2 = c.find('---', fm1 + 1)
print(f"First --- at {fm1}, second --- at {fm2}")
print(f"Content[{fm1}:{fm2+3}]:")
print(repr(c[fm1:fm2+3]))
print()
print("Content after second ---:")
print(repr(c[fm2+3:fm2+30]))
