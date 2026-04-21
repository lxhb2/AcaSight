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
mf = os.path.join(td, 'modules', 'module_01.md')
with open(mf, encoding='utf-8') as f: content = f.read()

ts = content.find('| 序号 |')
print(f"table_start = {ts}")
print(f"content[ts:ts+3] = {repr(content[ts:ts+3])}")
print()

# Show lines 1-8 from table_start
lines_from_ts = content[ts:].split('\n')
for i, ln in enumerate(lines_from_ts[:10]):
    print(f"  line[{i}] (from ts): {repr(ln[:80])}")
    if i > 8: break

print()
# Find separator line: starts with | and contains only - and | and space
sep_line_idx = -1
for i, ln in enumerate(lines_from_ts[1:], 1):
    stripped = ln.strip()
    if stripped and all(c in '-|: ' for c in stripped) and '-' in stripped:
        sep_line_idx = i
        print(f"Separator found at line[{i}]: {repr(stripped)}")
        break

# Table content = lines[0] + line[1] (sep) + challenge rows
# We want to include the separator line (line[1]) and all challenge rows
# The end of table is: separator line + its newline + blank line + first ## heading
# Find first ## after ts
idx_h2 = content.find('##', ts + 1)
print(f"First ## after ts: at {idx_h2}")

# CORRECT table_end: position of \n\n that separates separator from ## heading
# This is the blank line AFTER the separator line
for i in range(ts, min(idx_h2 + 20, len(content))):
    if content[i:i+2] == '\n\n':
        after3 = content[i+2:i+5]
        print(f"  n2 at {i}: follows={repr(content[i+2:i+20])}")
        if after3 in ('## ', '###'):
            print(f"  ==> CORRECT table_end = {i}")
            seg = content[ts:i]
            lines_seg = seg.split('\n')
            print(f"  Segment has {len(lines_seg)} lines:")
            for li, ln in enumerate(lines_seg):
                print(f"    [{li}] {repr(ln[:70])}")
            break

# What does current second_n2 algorithm give?
print()
print("Current algorithm (second_n2):")
count = 0
for i in range(ts, ts + 600):
    if content[i:i+2] == '\n\n':
        count += 1
        if count == 2:
            print(f"  second_n2 = {i+2}")
            print(f"  Content[ts:{i+2}] last 50: {repr(content[i:i+15])}")
            lines2 = content[ts:i+2].split('\n')
            print(f"  {len(lines2)} lines: last={repr(lines2[-1][:50])}")
            break
