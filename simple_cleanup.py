#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单文件清理
"""

import os
import shutil
from pathlib import Path
import json

def simple_cleanup():
    """简单清理"""
    workspace = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("开始简单文件清理...")
    print("=" * 60)
    
    # 1. 清理临时文件
    print("1. 清理临时文件:")
    temp_patterns = ['*.tmp', '*.temp', '*.bak', '*.backup', '~*', '*~']
    
    cleaned = []
    for pattern in temp_patterns:
        for file in workspace.rglob(pattern):
            try:
                print(f"  删除: {file.name}")
                file.unlink()
                cleaned.append(str(file))
            except Exception as e:
                print(f"  删除失败 {file}: {e}")
    
    print(f"  清理了 {len(cleaned)} 个临时文件")
    
    # 2. 清理重复的数据库文件
    print("\n2. 清理重复数据库文件:")
    db_files = list(workspace.rglob('*.db')) + list(workspace.rglob('*.sqlite'))
    
    # 只保留最新的
    if len(db_files) > 1:
        db_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest = db_files[0]
        
        for db_file in db_files[1:]:
            try:
                print(f"  删除旧数据库: {db_file.name}")
                db_file.unlink()
            except Exception as e:
                print(f"  删除失败 {db_file}: {e}")
    
    # 3. 清理旧的备份文件
    print("\n3. 清理旧的备份文件:")
    backup_files = list(workspace.rglob('*backup*')) + list(workspace.rglob('*_old*'))
    
    for backup in backup_files:
        try:
            print(f"  删除备份: {backup.name}")
            backup.unlink()
        except Exception as e:
            print(f"  删除失败 {backup}: {e}")
    
    # 4. 清理Python缓存
    print("\n4. 清理Python缓存:")
    cache_dirs = list(workspace.rglob('__pycache__'))
    
    for cache_dir in cache_dirs:
        try:
            print(f"  删除缓存目录: {cache_dir}")
            shutil.rmtree(cache_dir)
        except Exception as e:
            print(f"  删除失败 {cache_dir}: {e}")
    
    # 5. 统计清理结果
    print("\n" + "=" * 60)
    print("清理完成!")
    print(f"清理了: {len(cleaned)} 个临时文件")
    print(f"清理了: {len(db_files)-1 if len(db_files)>1 else 0} 个旧数据库")
    print(f"清理了: {len(backup_files)} 个备份文件")
    print(f"清理了: {len(cache_dirs)} 个缓存目录")
    print("=" * 60)

if __name__ == "__main__":
    simple_cleanup()