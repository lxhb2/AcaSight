# -*- coding: utf-8 -*-
"""Simple table_end finder - find blank line BEFORE markdown content (--- or ##)"""
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
# Strategy: find the blank line BEFORE the first markdown content
# that follows the table. Markdown content starts with ## or --- or #.
# Find first \n\n, then check what follows
print("All \n\n positions from table_start:")
pos = ts
for i in range(20):
    idx = raw.find('\n\n', pos)
    if idx == -1 or idx > ts + 600: break
    following = repr(raw[idx+2:idx+20])
    print(f"  [{i+1}] at {idx}: follows={following}")
    pos = idx + 1
