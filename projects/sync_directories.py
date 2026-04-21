#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脉冲学习系统 - 目录同步脚本
将 PulseLearning 目录与 Obsidian Vault 同步
"""
import os
import shutil
from pathlib import Path

# 路径配置
PULSE_LEARNING_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "PulseLearning"
)
OBSIDIAN_VAULT_DIR = r"D:\四季如歌\新建文件夹\脉冲学习\Vault"


def ensure_junction():
    """确保 Junction 链接存在"""
    junction_path = os.path.join(OBSIDIAN_VAULT_DIR, "Projects", "PulseLearning")
    
    # 检查是否已存在 junction
    if os.path.exists(junction_path):
        try:
            # 检查是否是 junction
            import subprocess
            result = subprocess.run(
                ["fsutil", "reparsepoint", "query", junction_path],
                capture_output=True,
                text=True
            )
            if "Reparse Tag" in result.stdout:
                print(f"✅ Junction 已存在: {junction_path}")
                return True
        except:
            pass
    
    # 创建 junction（需要管理员权限）
    try:
        import subprocess
        # 确保父目录存在
        os.makedirs(os.path.dirname(junction_path), exist_ok=True)
        
        # 删除已存在的普通目录
        if os.path.exists(junction_path) and not os.path.islink(junction_path):
            shutil.rmtree(junction_path)
        
        # 创建 junction
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", junction_path, PULSE_LEARNING_DIR],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Junction 创建成功: {junction_path} -> {PULSE_LEARNING_DIR}")
            return True
        else:
            print(f"❌ Junction 创建失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def sync_daily_notes():
    """同步每日笔记到 PulseLearning"""
    daily_source = os.path.join(OBSIDIAN_VAULT_DIR, "Daily")
    daily_target = os.path.join(PULSE_LEARNING_DIR, "Daily")
    
    if not os.path.exists(daily_source):
        print(f"⚠️ 源目录不存在: {daily_source}")
        return
    
    os.makedirs(daily_target, exist_ok=True)
    
    # 复制新的每日笔记
    for filename in os.listdir(daily_source):
        if filename.endswith('.md'):
            src = os.path.join(daily_source, filename)
            dst = os.path.join(daily_target, filename)
            
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"📄 复制: {filename}")


def sync_knowledge():
    """同步知识笔记到 PulseLearning"""
    knowledge_source = os.path.join(OBSIDIAN_VAULT_DIR, "Knowledge")
    knowledge_target = os.path.join(PULSE_LEARNING_DIR, "Knowledge")
    
    if not os.path.exists(knowledge_source):
        print(f"⚠️ 源目录不存在: {knowledge_source}")
        return
    
    os.makedirs(knowledge_target, exist_ok=True)
    
    # 复制新的知识笔记
    for filename in os.listdir(knowledge_source):
        if filename.endswith('.md'):
            src = os.path.join(knowledge_source, filename)
            dst = os.path.join(knowledge_target, filename)
            
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"📚 复制: {filename}")


def get_unified_path(subpath: str = "") -> str:
    """
    获取统一路径
    优先返回 PulseLearning 目录下的路径
    
    Args:
        subpath: 子路径
    
    Returns:
        统一后的完整路径
    """
    return os.path.join(PULSE_LEARNING_DIR, subpath)


def main():
    """主函数"""
    print("=" * 50)
    print("脉冲学习系统 - 目录同步")
    print("=" * 50)
    print()
    
    print(f"PulseLearning 目录: {PULSE_LEARNING_DIR}")
    print(f"Obsidian Vault 目录: {OBSIDIAN_VAULT_DIR}")
    print()
    
    # 检查目录是否存在
    if not os.path.exists(PULSE_LEARNING_DIR):
        print(f"❌ PulseLearning 目录不存在: {PULSE_LEARNING_DIR}")
        return
    
    if not os.path.exists(OBSIDIAN_VAULT_DIR):
        print(f"❌ Obsidian Vault 目录不存在: {OBSIDIAN_VAULT_DIR}")
        return
    
    # 确保 junction 存在
    print("1. 检查 Junction 链接...")
    ensure_junction()
    print()
    
    # 同步每日笔记
    print("2. 同步每日笔记...")
    sync_daily_notes()
    print()
    
    # 同步知识笔记
    print("3. 同步知识笔记...")
    sync_knowledge()
    print()
    
    print("=" * 50)
    print("同步完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
