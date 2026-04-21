#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Learning System - 快速测试
测试 CLI 核心功能
"""
import os
import sys

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 设置工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECTS_DIR)
os.chdir(PROJECTS_DIR)


def test_ollama():
    """测试 Ollama 连接"""
    print("=" * 50)
    print("测试 1: Ollama 连接")
    print("=" * 50)
    
    from src.utils.ollama_client import OllamaClient
    client = OllamaClient(model="qwen3.5:4b", base_url="http://localhost:11434")
    
    response = client.chat([
        {"role": "user", "content": "用一句话介绍自己"}
    ])
    
    print(f"响应: {response['message']['content'][:100]}...")
    print("[OK] Ollama 连接成功!")
    return True


def test_create_project():
    """测试创建项目"""
    print("\n" + "=" * 50)
    print("测试 2: 创建项目")
    print("=" * 50)
    
    from src.tools.pulse_tools import create_project, list_projects
    
    # 创建项目
    result = create_project(
        project_name="测试项目",
        goal_short="学会 Python 基础",
        goal_long="精通 Python 编程",
        discipline="编程"
    )
    print(result[:200])
    
    # 列出项目
    print("\n--- 项目列表 ---")
    print(list_projects())
    print("[OK] 项目创建成功!")
    return True


def test_create_module():
    """测试创建模块"""
    print("\n" + "=" * 50)
    print("测试 3: 创建模块")
    print("=" * 50)
    
    from src.tools.pulse_tools import create_module, get_modules
    
    # 创建模块
    result = create_module(
        project_name="测试项目",
        module_name="Python 基础语法",
        module_goal="掌握 Python 基本语法和数据类型",
        estimated_time=30
    )
    print(result[:300])
    
    # 获取模块
    print("\n--- 模块列表 ---")
    print(get_modules("测试项目"))
    print("[OK] 模块创建成功!")
    return True


def test_generate_challenges():
    """测试自动生成挑战"""
    print("\n" + "=" * 50)
    print("测试 4: AI 生成微挑战")
    print("=" * 50)
    
    from src.utils.ollama_client import OllamaClient
    from src.tools.pulse_tools import add_challenge
    import json
    import re
    
    client = OllamaClient(model="qwen3.5:4b", base_url="http://localhost:11434")
    
    prompt = """请根据以下信息生成 3 个微挑战。
模块名称：Python 基础语法
模块目标：掌握 Python 基本语法

请以 JSON 数组格式输出：
[{"description": "挑战描述", "estimated_time": 5, "success_criteria": "成功标志", "points": 10}]"""
    
    response = client.chat([{"role": "user", "content": prompt}])
    content = response["message"]["content"]
    
    # 提取 JSON
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        challenges = json.loads(json_match.group())
        print(f"生成了 {len(challenges)} 个挑战:")
        for c in challenges:
            print(f"  - {c.get('description')} (+{c.get('points')}分)")
            
            # 添加挑战
            add_challenge(
                project_name="测试项目",
                module_id=1,
                challenge_desc=c.get("description", ""),
                estimated_time=c.get("estimated_time", 5),
                success_criteria=c.get("success_criteria", ""),
                points=c.get("points", 10)
            )
        
        print("[OK] 挑战生成成功!")
    else:
        print("JSON 解析失败")
        print(content[:200])
    
    return True


def test_complete_challenge():
    """测试完成挑战"""
    print("\n" + "=" * 50)
    print("测试 5: 完成挑战")
    print("=" * 50)
    
    from src.tools.pulse_tools import complete_challenge
    
    result = complete_challenge(
        project_name="测试项目",
        module_id=1,
        challenge_id=1,
        notes="完成了第一个挑战！"
    )
    print(result)
    print("[OK] 挑战完成!")
    return True


def main():
    print("🎯 Pulse Learning System - 快速测试")
    print("=" * 50)
    
    tests = [
        ("Ollama 连接", test_ollama),
        ("创建项目", test_create_project),
        ("创建模块", test_create_module),
        ("AI生成挑战", test_generate_challenges),
        ("完成挑战", test_complete_challenge),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {name} 失败: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)


if __name__ == "__main__":
    main()
