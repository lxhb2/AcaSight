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
with open(mf, encoding='utf-8') as f: c = f.read()

# Show raw bytes around first 500 chars of body (after frontmatter)
fm1 = c.find('---')
fm2 = c.find('---', fm1+1)
print(f"Frontmatter: first --- at {fm1}, second at {fm2}")
print(f"Content[{fm1}:{fm2+3}]:")
print(repr(c[fm1:fm2+3]))
print()
print("After second ---:")
print(repr(c[fm2+3:fm2+30]))
print()

# Now trace what _update_yaml_frontmatter does
lines = c.split('\n')
print(f"Total lines: {len(lines)}")
end_idx = -1
for i, line in enumerate(lines[1:], 1):
    if line.strip() == "---":
        end_idx = i
        print(f"  line[{i}] = '---' (end_idx)")
        break
    print(f"  line[{i}] = {repr(line[:40])}")

print(f"\nlines[1:{end_idx}] (frontmatter text):")
print(repr('\n'.join(lines[1:end_idx])))
print(f"\nlines[{end_idx}:{end_idx+4}]:")
for j in range(end_idx, min(end_idx+5, len(lines))):
    print(f"  [{j}] {repr(lines[j])}")
print(f"\nlines[{end_idx+1}:{end_idx+5}] joined:")
print(repr('\n'.join(lines[end_idx+1:end_idx+5])))
print(f"\nlines[{end_idx+1}:] joined (what gets appended):")
print(repr('\n'.join(lines[end_idx+1:])))
