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

# Patch add_challenge to show table_end calculation
orig_add = pt.add_challenge
def debug_add(project, module_id, desc, *a, **kw):
    mf = os.path.join(td, 'modules', f'module_{module_id:02d}.md')
    content = pt._read_file(mf)
    ts = content.find('| 序号 |')
    print(f'\n=== add_challenge {desc} ===')
    print(f'  ts={ts}')
    print(f'  content[{ts}:{ts+80}] = {repr(content[ts:ts+80])}')
    # Show ALL \n\n after ts
    pos = ts
    for i in range(8):
        idx = content.find('\n\n', pos)
        if idx == -1 or idx > ts+600: break
        after = repr(content[idx+2:idx+15])
        print(f'  n2[{i+1}] at {idx}: after={after}')
        pos = idx + 1
    return orig_add(project, module_id, desc, *a, **kw)
pt.add_challenge = debug_add

for desc in ['vars', 'if/else', 'loops']:
    r = pt.add_challenge('TestE2E', 1, desc)
    mf = os.path.join(td, 'modules', 'module_01.md')
    with open(mf, encoding='utf-8') as f: c = f.read()
    m = re.search(r'challenges_total: (\d+)', c)
    print(f'  RESULT chal={m.group(1) if m else "X"}\n')
