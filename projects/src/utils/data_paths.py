"""
数据目录管理模块
统一管理脉冲学习系统的数据存储路径，支持 Obsidian 集成
"""
import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


class DataPathManager:
    """数据目录管理器"""
    
    def __init__(self, workspace_path: str = None, config_path: str = None):
        """
        初始化数据目录管理器
        
        Args:
            workspace_path: 工作空间根目录
            config_path: 配置文件路径
        """
        self.workspace_path = workspace_path or os.getcwd()
        self.config_path = config_path or os.path.join(
            self.workspace_path, "config", "data_paths.json"
        )
        self._config = self._load_config()
        self._paths = self._resolve_paths()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "data_dir": {
                "primary": r"D:\四季如歌\新建文件夹\脉冲学习",
                "obsidian_vault": r"D:\四季如歌\新建文件夹\脉冲学习",
                "use_symlink": False
            },
            "obsidian": {
                "enabled": True,
                "vault_path": r"D:\四季如歌\新建文件夹\脉冲学习"
            }
        }
    
    def _resolve_paths(self) -> Dict[str, str]:
        """解析路径变量"""
        paths = {}
        data_dir = self._config.get("data_dir", {})
        primary = data_dir.get("primary", r"D:\四季如歌\新建文件夹\脉冲学习")

        if os.path.isabs(primary):
            paths["projects"] = primary
        else:
            paths["projects"] = os.path.join(self.workspace_path, primary)

        paths["badges"] = os.path.join(paths["projects"], "badges.json")
        paths["memory"] = os.path.join(paths["projects"], "memory")
        paths["daily_notes"] = os.path.join(paths["projects"], "Vault", "Daily")

        obsidian_config = self._config.get("obsidian", {})
        if obsidian_config.get("enabled") and obsidian_config.get("vault_path"):
            vault_path = obsidian_config["vault_path"]
            paths["obsidian_vault"] = vault_path
            paths["obsidian_projects"] = paths["projects"]
            paths["obsidian_daily"] = os.path.join(
                vault_path,
                obsidian_config.get("daily_notes_folder", "Vault/Daily")
            )

        return paths
    
    @property
    def projects_dir(self) -> str:
        """项目数据目录"""
        return self._paths["projects"]
    
    @property
    def badges_file(self) -> str:
        """徽章数据文件"""
        return self._paths["badges"]
    
    @property
    def memory_dir(self) -> str:
        """记忆目录"""
        return self._paths["memory"]
    
    @property
    def daily_notes_dir(self) -> str:
        """每日笔记目录"""
        return self._paths["daily_notes"]
    
    def is_obsidian_enabled(self) -> bool:
        """检查是否启用 Obsidian 集成"""
        return self._config.get("obsidian", {}).get("enabled", False)
    
    def get_obsidian_vault_path(self) -> Optional[str]:
        """获取 Obsidian Vault 路径"""
        return self._paths.get("obsidian_vault")
    
    def ensure_directories(self) -> None:
        """确保所有必要目录存在"""
        for path in [self.projects_dir, self.memory_dir, self.daily_notes_dir]:
            os.makedirs(path, exist_ok=True)
    
    def setup_obsidian_integration(
        self, 
        vault_path: str,
        use_symlink: bool = True,
        projects_folder: str = "Projects/PulseLearning",
        daily_folder: str = "Daily"
    ) -> Dict[str, Any]:
        """
        设置 Obsidian 集成
        
        Args:
            vault_path: Obsidian Vault 路径
            use_symlink: 是否使用符号链接（Windows 需要管理员权限）
            projects_folder: 项目文件夹名称
            daily_folder: 每日笔记文件夹名称
            
        Returns:
            设置结果
        """
        result = {
            "success": False,
            "method": None,
            "message": "",
            "paths": {}
        }
        
        # 验证 Vault 路径
        if not os.path.exists(vault_path):
            result["message"] = f"Vault 路径不存在: {vault_path}"
            return result
        
        # 检查是否是 Obsidian Vault（存在 .obsidian 目录）
        obsidian_dir = os.path.join(vault_path, ".obsidian")
        if not os.path.exists(obsidian_dir):
            result["message"] = f"不是有效的 Obsidian Vault: {vault_path}"
            return result
        
        target_projects = os.path.join(vault_path, projects_folder)
        target_daily = os.path.join(vault_path, daily_folder)
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(target_projects), exist_ok=True)
        os.makedirs(target_daily, exist_ok=True)
        
        if use_symlink:
            # 尝试创建符号链接
            try:
                # Windows 需要管理员权限创建目录符号链接
                if os.path.exists(target_projects):
                    # 目标已存在，检查是否已经是符号链接
                    if os.path.islink(target_projects):
                        result["method"] = "symlink_exists"
                        result["message"] = "符号链接已存在"
                    else:
                        # 备份现有目录
                        backup_path = f"{target_projects}.backup"
                        if not os.path.exists(backup_path):
                            shutil.move(target_projects, backup_path)
                            result["message"] = f"已备份现有目录到: {backup_path}\n"
                        else:
                            result["message"] = "备份已存在，跳过备份\n"
                        
                        # 创建符号链接
                        os.symlink(self.projects_dir, target_projects, target_is_directory=True)
                        result["method"] = "symlink"
                        result["message"] += f"已创建符号链接: {target_projects} -> {self.projects_dir}"
                else:
                    os.symlink(self.projects_dir, target_projects, target_is_directory=True)
                    result["method"] = "symlink"
                    result["message"] = f"已创建符号链接: {target_projects} -> {self.projects_dir}"
                
                result["success"] = True
                result["paths"]["projects_symlink"] = target_projects
                
            except OSError as e:
                # 符号链接失败（可能是权限问题）
                result["method"] = "symlink_failed"
                result["message"] = f"符号链接失败: {e}\n尝试使用复制模式..."
                use_symlink = False
        
        if not use_symlink:
            # 使用复制模式
            result["method"] = "copy"
            result["message"] = "使用复制模式（需要手动同步）"
            
            # 复制现有数据到 Vault
            if os.path.exists(self.projects_dir) and os.listdir(self.projects_dir):
                try:
                    # 合并而不是覆盖
                    for item in os.listdir(self.projects_dir):
                        src = os.path.join(self.projects_dir, item)
                        dst = os.path.join(target_projects, item)
                        if os.path.isdir(src):
                            if not os.path.exists(dst):
                                shutil.copytree(src, dst)
                        else:
                            if not os.path.exists(dst):
                                shutil.copy2(src, dst)
                    result["message"] = f"已复制数据到: {target_projects}"
                    result["success"] = True
                except Exception as e:
                    result["message"] = f"复制失败: {e}"
            else:
                # 源目录为空，创建目标目录
                os.makedirs(target_projects, exist_ok=True)
                result["success"] = True
                result["message"] = f"已创建目录: {target_projects}"
        
        # 更新配置
        if result["success"]:
            self._config["obsidian"] = {
                "enabled": True,
                "vault_path": vault_path,
                "sync_mode": "symlink" if result["method"] == "symlink" else "copy",
                "daily_notes_folder": daily_folder,
                "projects_folder": projects_folder
            }
            self._config["data_dir"]["use_symlink"] = (result["method"] == "symlink")
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            
            # 重新解析路径
            self._paths = self._resolve_paths()
        
        return result
    
    def migrate_from_legacy(
        self,
        legacy_vault_path: str,
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        从旧的 Vault 结构迁移数据
        
        Args:
            legacy_vault_path: 旧 Vault 路径
            backup: 是否备份
            
        Returns:
            迁移结果
        """
        result = {
            "success": False,
            "migrated_files": [],
            "errors": [],
            "backup_path": None
        }
        
        legacy_projects = os.path.join(legacy_vault_path, "Projects", "PulseLearning")
        
        if not os.path.exists(legacy_projects):
            result["errors"].append(f"旧项目目录不存在: {legacy_projects}")
            return result
        
        # 备份现有数据
        if backup and os.path.exists(self.projects_dir):
            backup_path = f"{self.projects_dir}.backup"
            if not os.path.exists(backup_path):
                shutil.copytree(self.projects_dir, backup_path)
                result["backup_path"] = backup_path
        
        # 迁移项目
        for project_name in os.listdir(legacy_projects):
            src = os.path.join(legacy_projects, project_name)
            dst = os.path.join(self.projects_dir, project_name)
            
            if os.path.isdir(src):
                try:
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    result["migrated_files"].append(project_name)
                except Exception as e:
                    result["errors"].append(f"迁移 {project_name} 失败: {e}")
        
        result["success"] = len(result["migrated_files"]) > 0
        
        # 更新配置
        if result["success"]:
            self._config["migration"] = {
                "legacy_vault_path": legacy_vault_path,
                "migrated": True,
                "backup_created": backup
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据目录状态"""
        status = {
            "workspace": self.workspace_path,
            "projects_dir": self.projects_dir,
            "projects_count": 0,
            "obsidian_enabled": self.is_obsidian_enabled(),
            "obsidian_vault": self.get_obsidian_vault_path(),
            "directories_exist": {
                "projects": os.path.exists(self.projects_dir),
                "memory": os.path.exists(self.memory_dir),
                "daily_notes": os.path.exists(self.daily_notes_dir)
            }
        }
        
        # 统计项目数量
        if os.path.exists(self.projects_dir):
            for item in os.listdir(self.projects_dir):
                item_path = os.path.join(self.projects_dir, item)
                if os.path.isdir(item_path) and os.path.exists(
                    os.path.join(item_path, "_index.md")
                ):
                    status["projects_count"] += 1
        
        # 检查符号链接
        if self.is_obsidian_enabled():
            obsidian_projects = self._paths.get("obsidian_projects")
            if obsidian_projects and os.path.exists(obsidian_projects):
                status["symlink_active"] = os.path.islink(obsidian_projects)
        
        return status


# 全局实例
_path_manager: Optional[DataPathManager] = None


def get_path_manager(workspace_path: str = None) -> DataPathManager:
    """获取全局路径管理器实例"""
    global _path_manager
    if _path_manager is None or workspace_path:
        _path_manager = DataPathManager(workspace_path)
    return _path_manager


def get_projects_dir() -> str:
    """获取项目数据目录"""
    return get_path_manager().projects_dir


def get_badges_file() -> str:
    """获取徽章文件路径"""
    return get_path_manager().badges_file


def get_memory_dir() -> str:
    """获取记忆目录"""
    return get_path_manager().memory_dir
