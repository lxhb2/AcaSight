# -*- coding: utf-8 -*-
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
pos = ts
while True:
    idx = raw.find('\n\n', pos)
    if idx == -1 or idx > ts + 500: break
    before = repr(raw[max(0,idx-15):idx])
    after = repr(raw[idx+2:idx+15])
    print('  n2 at', idx, '-> before:', before, 'after:', after)
    pos = idx + 1
