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
with open(mf, 'rb') as f: raw_bytes = f.read()
content = raw_bytes.decode('utf-8')
ts = content.find('| 序号 |')

# Raw bytes at positions 370-410
print("Bytes 370-415 (decoded):")
for i in range(370, min(420, len(content))):
    ch = content[i]
    if ch == '\n':
        print(f"  [{i}] LF")
    elif ch == '\r':
        print(f"  [{i}] CR")
    else:
        print(f"  [{i}] {repr(ch)}", end='')
        if (i+1) % 8 == 0: print()
print()

# Find all \n\n
print("All \\n\\n positions and what follows:")
pos = ts
for _ in range(15):
    idx = content.find('\n\n', pos)
    if idx == -1 or idx > ts + 600: break
    following = repr(content[idx+2:idx+22])
    print(f"  at {idx}: follows={following}")
    pos = idx + 1

# Find ## or --- that immediately follows the table
print()
print("First ## after table_start:")
idx = content.find('##', ts+1)
print(f"  at {idx}: {repr(content[idx:idx+30])}")
print("First --- after table_start:")
idx2 = content.find('---', ts+1)
print(f"  at {idx2}: {repr(content[idx2:idx2+10])}")
