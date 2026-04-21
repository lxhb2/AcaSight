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

# Monkey patch _update_yaml_frontmatter to show what it does
orig = pt._update_yaml_frontmatter
def patched(content, updates):
    lines = content.split('\n')
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    print(f'  _upd_fm: end_idx={end_idx}')
    if end_idx > 0:
        fm_text = '\n'.join(lines[1:end_idx])
        print(f'  fm_text ends: {repr(lines[end_idx-3:end_idx+2])}')
    result = orig(content, updates)
    return result
pt._update_yaml_frontmatter = patched

for desc in ['if/else', 'loops', 'functions']:
    print(f'\n=== Adding {desc} ===')
    with open(mf, encoding='utf-8') as f: c = f.read()
    # Show structure around first ---close
    fm1 = c.find('---')
    fm2 = c.find('---', fm1+1)
    print(f'  first --- at {fm1}: {repr(c[fm1:fm1+5])}')
    print(f'  second --- at {fm2}: {repr(c[fm2:fm2+5])}')
    print(f'  chars between: {repr(c[fm1+3:fm2])}')
    print(f'  after second ---: {repr(c[fm2+3:fm2+10])}')
    pt.add_challenge('TestE2E', 1, desc)
    with open(mf, encoding='utf-8') as f: c2 = f.read()
    m = re.search(r'challenges_total: (\d+)', c2)
    print(f'  file chal={m.group(1) if m else "X"}')
