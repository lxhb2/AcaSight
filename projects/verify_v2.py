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

# Check create_module fm structure
with open(mf, encoding='utf-8') as f: raw = f.read()
lines = raw.split('\n')
for i, ln in enumerate(lines[1:], 1):
    if ln.strip() == '---':
        print(f"create_module fm_end: line {i}, line[{i+1}]={repr(lines[i+1][:50])}")
        break

# Monkey-patch to show table_end
_orig = pt.add_challenge
def _patched(proj, mid, desc, *a, **kw):
    mf2 = os.path.join(td, 'modules', f'module_{mid:02d}.md')
    content = pt._read_file(mf2)
    ts = content.find('| 序号 |')
    found_end = None
    skip_first = False
    for ii in range(ts, min(ts+500, len(content))):
        if content[ii:ii+2] == '\n\n':
            after = content[ii+2:ii+5]
            if skip_first:
                if after in ('---', '## ', '###'):
                    found_end = ii + 1
                    print(f"  table_end={found_end}, after={repr(after)}")
                    break
            else:
                skip_first = True
    result = _orig(proj, mid, desc, *a, **kw)
    with open(mf2, encoding='utf-8') as f2: c2 = f2.read()
    m = re.search(r'challenges_total: (\d+)', c2)
    rows = [l for l in c2.split('\n') if l.strip().startswith('|') and '---' not in l and l.strip().count('|') >= 5 and '序号' not in l]
    print(f"  chal={m.group(1) if m else 'X'}, rows={len(rows)}")
    return result
pt.add_challenge = _patched

for desc in ['vars', 'if/else', 'loops', 'functions']:
    print(f"\n[{desc}]:")
    pt.add_challenge('TestE2E', 1, desc)
