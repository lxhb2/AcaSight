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

# Inline debug: monkey-patch _update_yaml_frontmatter
orig_upd = pt._update_yaml_frontmatter
def debug_upd(content, updates):
    m_in = re.search(r'challenges_total: (\d+)', content)
    result = orig_upd(content, updates)
    m_out = re.search(r'challenges_total: (\d+)', result)
    fm_end = content.find('---', content.find('---') + 1)
    fm_text = content[content.find('---')+3:fm_end]
    # Check if frontmatter close is on same line as content
    close_line = content[content.find('---', content.find('---') + 1):]
    print(f'  upd: in_chal={m_in.group(1) if m_in else "X"}, updates={updates}, out_chal={m_out.group(1) if m_out else "X"}')
    print(f'  fm_text[0:60]: {repr(fm_text[:60])}')
    # check for corruption: is --- on same line as table content?
    ts = content.find('| 序号 |')
    first_n2 = content.find('\n\n', ts)
    print(f'  first n2 at {first_n2}: {repr(content[first_n2:first_n2+10])}')
    second_n2 = content.find('\n\n', first_n2 + 1)
    print(f'  second n2 at {second_n2}: {repr(content[second_n2:second_n2+10])}')
    return result
pt._update_yaml_frontmatter = debug_upd

# Patch _write_file too
orig_wf = pt._write_file
def debug_wf(fp, c):
    m = re.search(r'challenges_total: (\d+)', c)
    print(f'  _write_file: chal={m.group(1) if m else "X"}, len={len(c)}')
    return orig_wf(fp, c)
pt._write_file = debug_wf

for desc in ['vars', 'if/else', 'loops', 'functions']:
    mf = os.path.join(td, 'modules', 'module_01.md')
    # check file BEFORE add
    with open(mf, encoding='utf-8') as f: before = f.read()
    bm = re.search(r'challenges_total: (\d+)', before)
    print(f'\nAdding [{desc}]: file BEFORE has chal={bm.group(1) if bm else "X"}')
    r = pt.add_challenge('TestE2E', 1, desc)
    with open(mf, encoding='utf-8') as f: after = f.read()
    am = re.search(r'challenges_total: (\d+)', after)
    print(f'  file AFTER has chal={am.group(1) if am else "X"}')
