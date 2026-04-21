#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECTS_DIR, 'src'))
os.chdir(PROJECTS_DIR)

from utils.llm_client import create_client, is_online, get_active_provider
from utils.prompt_builder import build_pulse_learning_system_prompt_light, build_pulse_learning_system_prompt

print("=== 网络检测 ===")
print("online:", is_online())

print("\n=== 当前 Provider ===")
p = get_active_provider()
print(f"provider: {p.get('provider')}, model: {p.get('model')}")

print("\n=== 客户端 ===")
client = create_client()
print(f"client: {client}")

print("\n=== 提示词长度对比 ===")
prompt_light = build_pulse_learning_system_prompt_light()
prompt_full = build_pulse_learning_system_prompt()
print(f"精简版: {len(prompt_light)} chars (~{len(prompt_light)//4} tokens)")
print(f"完整版: {len(prompt_full)} chars (~{len(prompt_full)//4} tokens)")
print(f"精简后减少: {(1 - len(prompt_light)/len(prompt_full))*100:.0f}%")

print("\n=== Ollama API 测试 ===")
try:
    resp = client.chat([{"role": "user", "content": "OK"}])
    print("响应:", resp["message"]["content"][:100])
    print("\n✅ 全部测试通过!")
except Exception as e:
    print(f"错误: {e}")
