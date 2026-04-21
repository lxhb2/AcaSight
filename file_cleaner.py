#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件清理工具
删除重复、临时和多余文件
"""

import os
import shutil
from pathlib import Path
import json
from typing import List, Dict, Set
import hashlib

class FileCleaner:
    """文件清理工具"""
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir or r"C:\Users\Administrator\.qclaw\workspace")
        self.backup_dir = self.workspace_dir / "backups"
        self.log_file = self.workspace_dir / "cleanup_log.json"
        
        # 创建备份目录
        self.backup_dir.mkdir(exist_ok=True)
        
        # 清理规则
        self.cleanup_rules = {
            'temp_files': [
                '*.tmp', '*.temp', '*.bak', '*.backup',
                '~*', '*~', '._*', '.DS_Store',
                'Thumbs.db', 'desktop.ini'
            ],
            'log_files': [
                '*.log', '*.log.*', 'debug.log', 'error.log'
            ],
            'cache_files': [
                '__pycache__', '*.pyc', '*.pyo', '*.pyd',
                '.cache', '.pytest_cache', '.mypy_cache'
            ],
            'duplicate_patterns': [
                '*_copy*', '*_old*', '*_backup*',
                '*_v[0-9]*', '*_version*'
            ]
        }
    
    def scan_workspace(self) -> Dict[str, List[str]]:
        """扫描工作区文件"""
        print("扫描工作区文件...")
        
        files_by_type = {
            'python_files': [],
            'data_files': [],
            'documentation': [],
            'temporary': [],
            'duplicates': [],
            'large_files': []
        }
        
        total_size = 0
        file_count = 0
        
        for file_path in self.workspace_dir.rglob('*'):
            if file_path.is_file():
                file_count += 1
                file_size = file_path.stat().st_size
                total_size += file_size
                
                # 分类文件
                if self._is_temp_file(file_path):
                    files_by_type['temporary'].append(str(file_path))
                elif file_path.suffix in ['.py', '.pyw']:
                    files_by_type['python_files'].append(str(file_path))
                elif file_path.suffix in ['.db', '.sqlite', '.csv', '.json', '.txt']:
                    files_by_type['data_files'].append(str(file_path))
                elif file_path.suffix in ['.md', '.rst', '.txt', '.pdf']:
                    files_by_type['documentation'].append(str(file_path))
                
                # 检查大文件
                if file_size > 10 * 1024 * 1024:  # 10MB
                    files_by_type['large_files'].append(f"{file_path} ({file_size/1024/1024:.1f} MB)")
        
        print(f"扫描完成: {file_count} 个文件, {total_size/1024/1024:.1f} MB")
        
        # 查找重复文件
        files_by_type['duplicates'] = self._find_duplicate_files()
        
        return files_by_type
    
    def _is_temp_file(self, file_path: Path) -> bool:
        """判断是否为临时文件"""
        filename = file_path.name
        
        # 检查临时文件模式
        for pattern in self.cleanup_rules['temp_files']:
            if pattern.startswith('*'):
                if filename.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if filename.startswith(pattern[:-1]):
                    return True
        
        # 检查缓存目录
        for cache_pattern in self.cleanup_rules['cache_files']:
            if cache_pattern in str(file_path):
                return True
        
        return False
    
    def _find_duplicate_files(self) -> List[str]:
        """查找重复文件"""
        print("查找重复文件...")
        
        file_hashes = {}
        duplicates = []
        
        for file_path in self.workspace_dir.rglob('*'):
            if file_path.is_file() and file_path.stat().st_size > 0:
                try:
                    # 计算文件哈希
                    file_hash = self._calculate_file_hash(file_path)
                    
                    if file_hash in file_hashes:
                        # 找到重复文件
                        original = file_hashes[file_hash]
                        duplicates.append(f"{file_path} (重复于: {original})")
                    else:
                        file_hashes[file_hash] = str(file_path)
                except Exception as e:
                    print(f"计算文件哈希失败 {file_path}: {e}")
        
        return duplicates
    
    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """计算文件哈希值"""
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def backup_before_cleanup(self, files_to_backup: List[str]):
        """清理前备份文件"""
        print("创建备份...")
        
        backup_info = {
            'timestamp': self._get_timestamp(),
            'backup_files': []
        }
        
        for file_path_str in files_to_backup:
            file_path = Path(file_path_str)
            if file_path.exists():
                # 创建备份路径
                relative_path = file_path.relative_to(self.workspace_dir)
                backup_path = self.backup_dir / relative_path
                
                # 确保目录存在
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                try:
                    shutil.copy2(file_path, backup_path)
                    backup_info['backup_files'].append(str(file_path))
                    print(f"  已备份: {file_path}")
                except Exception as e:
                    print(f"  备份失败 {file_path}: {e}")
        
        # 保存备份信息
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        print(f"备份完成，信息保存在: {self.log_file}")
    
    def cleanup_temporary_files(self, dry_run: bool = True) -> List[str]:
        """清理临时文件"""
        print("清理临时文件..." + ("(模拟运行)" if dry_run else ""))
        
        cleaned_files = []
        
        for file_path in self.workspace_dir.rglob('*'):
            if file_path.is_file() and self._is_temp_file(file_path):
                try:
                    if dry_run:
                        print(f"  [模拟] 将删除: {file_path}")
                    else:
                        file_path.unlink()
                        print(f"  已删除: {file_path}")
                    cleaned_files.append(str(file_path))
                except Exception as e:
                    print(f"  删除失败 {file_path}: {e}")
        
        # 清理空目录
        self._cleanup_empty_directories(dry_run)
        
        return cleaned_files
    
    def _cleanup_empty_directories(self, dry_run: bool = True):
        """清理空目录"""
        for dir_path in sorted(self.workspace_dir.rglob('*'), key=lambda x: len(str(x)), reverse=True):
            if dir_path.is_dir() and dir_path != self.workspace_dir:
                try:
                    # 检查目录是否为空
                    if not any(dir_path.iterdir()):
                        if dry_run:
                            print(f"  [模拟] 将删除空目录: {dir_path}")
                        else:
                            dir_path.rmdir()
                            print(f"  已删除空目录: {dir_path}")
                except Exception as e:
                    print(f"  删除目录失败 {dir_path}: {e}")
    
    def cleanup_duplicate_files(self, files_to_check: List[str], dry_run: bool = True) -> List[str]:
        """清理重复文件"""
        print("清理重复文件..." + ("(模拟运行)" if dry_run else ""))
        
        cleaned_files = []
        file_contents = {}
        
        for file_path_str in files_to_check:
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # 只读取前1000字符进行比较
                    
                    # 检查是否有相同内容
                    if content in file_contents:
                        # 找到重复文件
                        original = file_contents[content]
                        if dry_run:
                            print(f"  [模拟] 将删除重复文件: {file_path}")
                            print(f"        重复于: {original}")
                        else:
                            # 保留修改时间较新的文件
                            original_mtime = Path(original).stat().st_mtime
                            current_mtime = file_path.stat().st_mtime
                            
                            if current_mtime > original_mtime:
                                # 当前文件较新，删除原始文件
                                Path(original).unlink()
                                file_contents[content] = str(file_path)
                                print(f"  已删除较旧文件: {original}")
                                cleaned_files.append(original)
                            else:
                                # 原始文件较新，删除当前文件
                                file_path.unlink()
                                print(f"  已删除较新文件: {file_path}")
                                cleaned_files.append(str(file_path))
                    else:
                        file_contents[content] = str(file_path)
                        
                except Exception as e:
                    print(f"  处理文件失败 {file_path}: {e}")
        
        return cleaned_files
    
    def optimize_database_files(self):
        """优化数据库文件"""
        print("优化数据库文件...")
        
        db_files = list(self.workspace_dir.rglob('*.db')) + list(self.workspace_dir.rglob('*.sqlite'))
        
        for db_file in db_files:
            try:
                self._optimize_sqlite_db(db_file)
            except Exception as e:
                print(f"  优化数据库失败 {db_file}: {e}")
    
    def _optimize_sqlite_db(self, db_path: Path):
        """优化SQLite数据库"""
        import sqlite3
        
        original_size = db_path.stat().st_size
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 执行优化命令
        cursor.execute("VACUUM")
        cursor.execute("PRAGMA optimize")
        
        conn.commit()
        conn.close()
        
        new_size = db_path.stat().st_size
        reduction = original_size - new_size
        
        if reduction > 0:
            print(f"  优化数据库: {db_path.name}")
            print(f"    原始大小: {original_size/1024/1024:.2f} MB")
            print(f"    优化后: {new_size/1024/1024:.2f} MB")
            print(f"    减少: {reduction/1024/1024:.2f} MB ({reduction/original_size*100:.1f}%)")
    
    def generate_cleanup_report(self, scan_results: Dict[str, List[str]]) -> str:
        """生成清理报告"""
        report_lines = [
            "=" * 60,
            "工作区文件清理报告",
            "=" * 60,
            f"生成时间: {self._get_timestamp()}",
            f"工作区目录: {self.workspace_dir}",
            ""
        ]
        
        # 统计信息
        total_files = sum(len(files) for files in scan_results.values())
        report_lines.append(f"文件统计:")
        for file_type, files in scan_results.items():
            report_lines.append(f"  {file_type}: {len(files)} 个文件")
        report_lines.append("")
        
        # 详细列表
        for file_type, files in scan_results.items():
            if files:
                report_lines.append(f"{file_type.upper()}:")
                for file in files[:10]:  # 只显示前10个
                    report_lines.append(f"  • {file}")
                if len(files) > 10:
                    report_lines.append(f"  ... 还有 {len(files) - 10} 个文件")
                report_lines.append("")
        
        # 建议
        report_lines.append("清理建议:")
        if scan_results['temporary']:
            report_lines.append("  1. 清理临时文件 (可安全删除)")
        if scan_results['duplicates']:
            report_lines.append("  2. 清理重复文件")
        if scan_results['large_files']:
            report_lines.append("  3. 检查大文件")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run_full_cleanup(self, dry_run: bool = True):
        """运行完整清理流程"""
        print("开始完整文件清理流程")
        print("=" * 60)
        
        # 1. 扫描工作区
        scan_results = self.scan_workspace()
        
        # 2. 生成报告
        report = self.generate_cleanup_report(scan_results)
        print(report)
        
        # 3. 备份重要文件
        important_files = scan_results['python_files'] + scan_results['data_files']
        self.backup_before_cleanup(important_files)
        
        # 4. 清理临时文件
        if scan_results['temporary']:
            print("\n清理临时文件:")
            cleaned = self.cleanup_temporary_files(dry_run)
            print(f"  已标记 {len(cleaned)} 个临时文件待清理")
        
        # 5. 清理重复文件
        if scan_results['duplicates']:
            print("\n清理重复文件:")
            cleaned = self.cleanup_duplicate_files(scan_results['duplicates'], dry_run)
            print(f"  已标记 {len(cleaned)} 个重复文件待清理")
        
        # 6. 优化数据库
        print("\n优化数据库文件:")
        self.optimize_database_files()
        
        print("\n" + "=" * 60)
        if dry_run:
            print("模拟运行完成！请检查报告，确认无误后设置 dry_run=False 执行实际清理。")
        else:
            print("实际清理完成！")
        print("=" * 60)

# 使用示例
if __name__ == "__main__":
    # 创建清理工具
    cleaner = FileCleaner()
    
    # 运行完整清理（模拟运行）
    cleaner.run_full_cleanup(dry_run=True)
    
    # 如果要实际执行清理，取消注释下面这行：
    # cleaner.run_full_cleanup(dry_run=False)