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
# Print raw bytes from table_start-5 to table_start+300
segment = raw[ts:ts+300]
print("RAW SEGMENT (repr):")
for i, ch in enumerate(segment):
    if ch == '\n':
        print(f"  [{i:3d}] '\\n'")
    elif ch == '\r':
        pass
    else:
        print(f"  [{i:3d}] {repr(ch)}", end='')
        if (i+1) % 5 == 0:
            print()
print()

# Where is '|' 序号 '|' in raw?
print("Chars 200-280:")
for i, ch in enumerate(raw[ts+200:ts+280], ts+200):
    if ch == '\n':
        print(f"  [{i}] '\\n'")
    else:
        print(f"  [{i}] {repr(ch)}", end='')
print()

# What's immediately after the last '|' on the separator row?
print("Chars 350-400:")
for i, ch in enumerate(raw[ts+350:ts+400], ts+350):
    if ch == '\n':
        print(f"  [{i}] '\\n'")
    else:
        print(f"  [{i}] {repr(ch)}", end='')
print()
