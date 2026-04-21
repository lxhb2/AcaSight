# -*- coding: utf-8 -*-
"""端到端测试脚本"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# src 目录有 __init__.py，是包。父目录加入 sys.path，这样 'from src.tools import ...' 可以工作
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)  # projects 根目录
# sys.path.insert(0, os.path.join(SCRIPT_DIR, 'src'))  # 不能加这个，否则 from ..utils 会失败

# Step 1: Create project (跳过已存在的)
print("=" * 60)
print("STEP 1: Create Project")
print("=" * 60)
from src.tools.pulse_tools import create_project, list_projects

# 确保清理旧测试项目
import shutil
test_dir = os.path.join('assets', 'PulseLearning', 'TestE2E')
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
    print(f'[Clean] 已删除旧项目')

result = create_project(
    project_name="TestE2E",
    goal_short="端到端测试项目",
    goal_long="完整测试脉冲学习系统全流程",
    discipline="编程"
)
print(result[:400])

# Step 2: Create module
print("\n" + "=" * 60)
print("STEP 2: Create Module")
print("=" * 60)
from src.tools.pulse_tools import create_module
result = create_module(
    project_name="TestE2E",
    module_name="基础语法",
    module_goal="掌握Python基础语法",
    estimated_time=30
)
print(result[:500])

# Step 3: Add challenges
print("\n" + "=" * 60)
print("STEP 3: Add Challenges")
print("=" * 60)
from src.tools.pulse_tools import add_challenge
for desc in ["变量与数据类型", "条件判断 if/else", "循环 for/while", "函数定义"]:
    r = add_challenge("TestE2E", module_id=1, challenge_desc=desc)
    print(f"  + {desc}: OK")

# Step 4: Complete all challenges
print("\n" + "=" * 60)
print("STEP 4: Complete All Challenges")
print("=" * 60)
from src.tools.pulse_tools import complete_challenge
for cid in [1, 2, 3, 4]:
    r = complete_challenge("TestE2E", module_id=1, challenge_id=cid, notes="测试完成")
    lines = [l for l in r.split('\n') if '完成' in l or '太棒' in l or '得分' in l or 'score' in l.lower()]
    print(f"  Challenge {cid}: {lines[:2]}")

# Step 5: Finish module (指定 module_id=1 因为 TestE2E 旧数据里 current_module_id 可能未更新)
print("\n" + "=" * 60)
print("STEP 5: Finish Module")
print("=" * 60)
from src.tools.pulse_tools import finish_module

# 先检查 index 里的 current_module_id
import src.tools.pulse_tools as pt
idx_file = os.path.join('assets/PulseLearning', 'TestE2E', '_index.md')
idx_content = pt._read_file(idx_file)
idx_fm = pt._parse_yaml_frontmatter(idx_content)
print(f"  [DEBUG] index frontmatter:")
print(f"    total_modules={idx_fm.get('total_modules')}")
print(f"    current_module_id={idx_fm.get('current_module_id')}")

# 也检查 module_01.md 的 frontmatter
mod_file = os.path.join('assets/PulseLearning', 'TestE2E', 'modules', 'module_01.md')
mod_content = pt._read_file(mod_file)
mod_fm = pt._parse_yaml_frontmatter(mod_content)
print(f"  [DEBUG] module_01.md frontmatter:")
print(f"    module_id={mod_fm.get('module_id')}")
print(f"    challenges_completed={mod_fm.get('challenges_completed')}/{mod_fm.get('challenges_total')}")

# 用正确的 module_id
print(f"\n  Calling finish_module('TestE2E', module_id=1)...")
r = finish_module("TestE2E", module_id=1)
print(f"  Result length: {len(r)} chars")
print(f"  First 300 chars: {r[:300]}")

# Step 6: Verify module file updated
print("\n" + "=" * 60)
print("STEP 6: Verify Module File")
print("=" * 60)
module_file = "assets/PulseLearning/TestE2E/modules/module_01.md"
if os.path.exists(module_file):
    with open(module_file, encoding='utf-8') as f:
        content = f.read()
    # Check key fields
    checks = [
        ("boss_task_status: active", "boss_task_status: active" in content),
        ("boss_task_description:", "boss_task_description:" in content),
        ("total_time_spent:", "total_time_spent:" in content),
        ("status: in_review", "status: in_review" in content),
    ]
    for name, ok in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
else:
    print(f"  [FAIL] 模块文件不存在: {module_file}")
