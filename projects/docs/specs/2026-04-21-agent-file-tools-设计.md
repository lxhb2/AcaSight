# Agent 安全文件工具模块设计文档

## 1. 概述

### 1.1 背景

当前 Pulse Learning Agent 系统中存在两套并行的文件操作实现：

| 模块 | 文件操作方式 | 安全机制 |
|------|-------------|---------|
| `file_manager.py` | 直接使用 `open()` | ❌ 无 |
| `pulse_tools.py` | 通过 `safe_file_ops.py` | ✅ 完整 |

这导致 Agent 在不同路径调用工具时安全性不一致。用户报告"Agent 工具调用功能存在异常，无法直接在本地文件系统执行文件写入和读取操作"。

### 1.2 目标

创建统一的 **Agent 安全文件工具模块** (`agent_file_tools.py`)，实现：

1. ✅ **统一工具入口** - 所有文件操作通过同一模块
2. ✅ **安全执行** - 复用 `safe_file_ops.py` 的安全机制
3. ✅ **权限验证** - 操作前验证路径合法性
4. ✅ **错误处理** - 完善的异常处理和结果格式化
5. ✅ **日志记录** - 审计日志记录所有文件操作
6. ✅ **Agent 友好** - 支持 LangChain 工具调用协议

### 1.3 架构选择

采用**方案 A：分层安全架构**

```
Agent (agent.py / chainlit_ui.py)
    ↓ calls tools
新模块: agent_file_tools.py (工具注册表 + 执行器 + 日志)
    ↓ uses
现有模块: safe_file_ops.py (已验证的安全机制)
    ↓ operates on
文件系统: PROJECTS_DIR / Obsidian Vault
```

---

## 2. 架构设计

### 2.1 模块结构

```
src/tools/
├── agent_file_tools.py      ← 新建：统一工具模块
│   ├── AgentFileTool        ← 工具基类
│   ├── CreateProjectTool    ← 工具实现
│   ├── ReadFileTool         ← 通用文件读取
│   ├── WriteFileTool        ← 通用文件写入
│   ├── ToolRegistry         ← 工具注册表
│   └── ToolExecutor         ← 工具执行器
├── pulse_tools.py           ← 保留：业务逻辑工具
├── file_manager.py          ← 逐步废弃（仅向后兼容）
└── ...

src/utils/
├── safe_file_ops.py         ← 保留：安全文件操作
├── audit_logger.py          ← 新建：审计日志
└── tool_validator.py        ← 新建：参数验证
```

### 2.2 核心组件

#### 2.2.1 审计日志模块 (`audit_logger.py`)

```python
class AuditLogger:
    """记录所有文件操作"""
    
    def log_operation(
        operation: str,        # read / write / delete
        filepath: str,         # 操作路径
        success: bool,         # 是否成功
        error: str = "",       # 错误信息
        details: dict = None,  # 附加详情
    ) -> None
```

#### 2.2.2 参数验证模块 (`tool_validator.py`)

```python
class ToolValidator:
    """验证工具参数"""
    
    def validate_path(
        filepath: str,
        workspace_root: str,
        allowed_extensions: list = None,
        max_depth: int = 10,
    ) -> ValidationResult
```

#### 2.2.3 工具基类 (`agent_file_tools.py`)

```python
class AgentFileTool(ABC):
    """所有文件工具的基类"""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def description(self) -> str: ...
    
    @property
    @abstractmethod
    def args_schema(self) -> Dict: ...
    
    @abstractmethod
    def execute(self, **kwargs) -> str: ...
    
    def validate(self, **kwargs) -> ValidationResult: ...
```

### 2.3 数据流

```
用户请求
    ↓
Agent (LangGraph) 调用工具
    ↓
ToolExecutor.execute(tool_name, args)
    ↓
1. ToolValidator 验证参数
2. AuditLogger 记录操作开始
3. 调用 safe_file_ops.py 执行操作
4. AuditLogger 记录操作结果
5. 格式化返回结果
    ↓
Agent 返回结果给用户
```

---

## 3. 安全机制

### 3.1 复用现有安全层

直接使用 `safe_file_ops.py` 中已实现的安全机制：

| 安全机制 | 实现位置 | 状态 |
|---------|---------|------|
| 路径边界检查 | `_is_path_inside()` | ✅ 已有 |
| 敏感路径黑名单 | `WRITE_DENIED_PATHS` | ✅ 已有 |
| 符号链接检测 | `_check_symlink()` | ✅ 已有 |
| 设备路径阻止 | `_is_blocked_device()` | ✅ 已有 |
| 写入大小限制 | `max_bytes` 参数 | ✅ 已有 |

### 3.2 新增安全层

在工具执行层增加：

| 安全机制 | 说明 | 实现位置 |
|---------|------|---------|
| 参数类型验证 | 确保参数类型正确 | `ToolValidator` |
| 操作频率限制 | 防止短时间内大量操作 | `ToolExecutor` |
| 权限级别 | 读/写/删除分级权限 | `AgentFileTool` |
| 审计日志 | 完整记录所有操作 | `AuditLogger` |

---

## 4. 实现细节

### 4.1 审计日志 (`src/utils/audit_logger.py`)

```python
"""
审计日志模块 - 记录所有文件操作

功能：
1. 记录每次文件操作的时间、类型、路径、结果
2. 支持日志文件持久化
3. 支持异常操作告警
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("pulse_learning.audit")

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "audit_log.json"
        )
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
    def log(self, operation: str, filepath: str, success: bool, 
            error: str = "", details: Dict = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "filepath": filepath,
            "success": success,
            "error": error,
            "details": details or {},
        }
        logger.info(f"AUDIT: {json.dumps(entry, ensure_ascii=False)}")
        self._append_to_file(entry)
        
    def _append_to_file(self, entry: Dict) -> None:
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
```

### 4.2 参数验证 (`src/utils/tool_validator.py`)

```python
"""
工具参数验证模块

功能：
1. 路径合法性验证
2. 文件类型白名单
3. 深度限制
4. 大小限制
"""

import os
import re
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    success: bool
    error: str = ""
    
@dataclass  
class PathValidationResult(ValidationResult):
    resolved_path: str = ""
    is_symlink: bool = False
    
class ToolValidator:
    """工具参数验证器"""
    
    def validate_path(self, filepath: str, workspace_root: str,
                     allowed_extensions: List[str] = None,
                     max_depth: int = 10) -> PathValidationResult:
        # 1. 展开路径
        resolved = os.path.normpath(os.path.abspath(
            os.path.expanduser(os.path.expandvars(filepath))
        ))
        
        # 2. 检查深度
        depth = resolved.count(os.sep) - workspace_root.count(os.sep)
        if depth > max_depth:
            return PathValidationResult(
                success=False,
                error=f"路径深度 {depth} 超过限制 {max_depth}",
                resolved_path=resolved,
            )
            
        # 3. 检查扩展名
        if allowed_extensions:
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in allowed_extensions:
                return PathValidationResult(
                    success=False,
                    error=f"不支持的文件类型: {ext}",
                    resolved_path=resolved,
                )
                
        return PathValidationResult(
            success=True,
            resolved_path=resolved,
            is_symlink=os.path.islink(filepath),
        )
        
    def validate_content_size(self, content: str, max_bytes: int) -> ValidationResult:
        if len(content.encode('utf-8')) > max_bytes:
            return ValidationResult(
                success=False,
                error=f"内容超过最大允许大小 ({max_bytes} bytes)"
            )
        return ValidationResult(success=True)
```

### 4.3 工具基类 (`src/tools/agent_file_tools.py`)

```python
"""
Agent 安全文件工具模块

提供统一的文件操作工具供 Agent 调用：
- 项目管理工具 (create_project, list_projects, get_project_status)
- 通用文件操作 (read_file, write_file)
- 安全验证和审计日志

设计原则：
1. 所有文件操作必须通过 safe_file_ops.py
2. 每次操作都有审计日志
3. 参数验证在执行前完成
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any

# 安全文件操作
from utils.safe_file_ops import (
    safe_read_file, safe_write_file, safe_delete_file,
    ReadResult, WriteResult,
)
from utils.data_paths import get_projects_dir
from utils.audit_logger import AuditLogger
from utils.tool_validator import ToolValidator

logger = logging.getLogger("pulse_learning.agent_tools")

# 默认工作空间根目录
PROJECTS_DIR = get_projects_dir()

# 全局审计日志实例
_audit_logger = AuditLogger()

# 全局验证器实例  
_validator = ToolValidator()


class AgentFileTool(ABC):
    """Agent 文件工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
        
    @property
    @abstractmethod 
    def description(self) -> str:
        """工具描述"""
        pass
        
    @property
    @abstractmethod
    def args_schema(self) -> Dict:
        """参数模式定义"""
        pass
        
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具"""
        pass
        
    def validate(self, **kwargs) -> bool:
        """验证参数"""
        result = _validator.validate_path(
            kwargs.get('filepath', ''),
            PROJECTS_DIR,
        )
        if not result.success:
            logger.warning(f"Validation failed for {self.name}: {result.error}")
            return False
        return True
        
    def log_operation(self, success: bool, error: str = "", details: Dict = None):
        """记录操作日志"""
        _audit_logger.log(
            operation=self.name,
            filepath=details.get('filepath', '') if details else '',
            success=success,
            error=error,
            details=details,
        )


# ==================== 项目管理工具 ====================

class CreateProjectTool(AgentFileTool):
    """创建学习项目工具"""
    
    @property
    def name(self) -> str:
        return "create_project"
        
    @property
    def description(self) -> str:
        return """创建一个新的学习项目。
        
参数：
- project_name: 项目名称
- goal_short: 短期目标（本次学习周期目标）
- goal_long: 长期目标（最终要达到的目标）
- discipline: 学习领域（如：编程、数学、语言等），默认"综合"

返回：
创建结果信息，包括项目路径和下一步建议
"""
        
    @property
    def args_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "goal_short": {"type": "string", "description": "短期目标"},
                "goal_long": {"type": "string", "description": "长期目标"},
                "discipline": {"type": "string", "description": "学习领域", "default": "综合"},
            },
            "required": ["project_name", "goal_short", "goal_long"],
        }
        
    def execute(self, project_name: str, goal_short: str, goal_long: str, 
                discipline: str = "综合") -> str:
        """创建项目"""
        try:
            # 验证项目名称
            if not project_name or not project_name.strip():
                self.log_operation(False, "项目名称不能为空")
                return "❌ 错误：项目名称不能为空"
                
            # 确保项目目录
            project_dir = os.path.join(PROJECTS_DIR, project_name)
            modules_dir = os.path.join(project_dir, "modules")
            attachments_dir = os.path.join(project_dir, "attachments")
            
            os.makedirs(project_dir, exist_ok=True)
            os.makedirs(modules_dir, exist_ok=True)
            os.makedirs(attachments_dir, exist_ok=True)
            
            # 检查是否已存在
            index_file = os.path.join(project_dir, "_index.md")
            if os.path.exists(index_file):
                self.log_operation(False, f"项目已存在: {project_name}")
                return f"项目 '{project_name}' 已存在！请使用其他名称或继续现有项目。"
            
            # 创建索引文件
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_today = datetime.now().strftime("%Y-%m-%d")
            
            index_content = f"""---
project: "{project_name}"
status: "active"
created: "{date_today}"
last_module: "{date_today}"
total_modules: 0
goal_short: "{goal_short}"
goal_long: "{goal_long}"
discipline: "{discipline}"
total_score: 0
current_combo: 0
max_combo: 0
---

# 📌 {project_name}

## 📊 项目综述

**学习领域**：{discipline}
**创建时间**：{now}
**状态**：进行中 🟢

### 🎯 目标

- **短期目标**：{goal_short}
- **长期目标**：{goal_long}

### 📈 游戏化数据

- **总分数**：0
- **当前连击**：0 🔥
- **最大连击**：0 💪
- **完成模块数**：0 / 0

## 🧩 模块学习索引

| 序号 | 模块名称 | 状态 | 完成日期 | 核心产出 | 分数 |
|------|----------|------|----------|----------|------|

## 📚 资源库

### 学习资源

### 参考链接

## 📝 学习笔记

---

*使用脉冲学习系统，将大目标拆解为小的脉冲，每次学习都有即时反馈！*
"""
            
            result = safe_write_file(
                filepath=index_file,
                content=index_content,
                workspace_root=PROJECTS_DIR,
                mkdir=True,
            )
            
            if not result.success:
                self.log_operation(False, result.error, {"filepath": index_file})
                return f"❌ 创建项目失败：{result.error}"
            
            # 创建资源文件
            resources_file = os.path.join(project_dir, "resources.md")
            resources_content = f"""---
project: "{project_name}"
---

# 📚 {project_name} - 资源库

## 学习资源

### 教程与文档

### 视频课程

### 书籍推荐

## 参考链接

## 代码片段

## 常用命令

---

*在此项目学习中收集的有用资源*
"""
            safe_write_file(
                filepath=resources_file,
                content=resources_content,
                workspace_root=PROJECTS_DIR,
                mkdir=True,
            )
            
            self.log_operation(True, details={
                "filepath": index_file,
                "project_name": project_name,
                "discipline": discipline,
            })
            
            return f"""✅ 项目创建成功！

📁 项目名称：{project_name}
🎯 短期目标：{goal_short}
🚀 长期目标：{goal_long}
📚 学习领域：{discipline}

项目已准备就绪！接下来可以：
1. 拆解第一个学习模块
2. 定义微挑战列表
3. 开始第一次脉冲学习

准备好开始了吗？告诉我你想先学习什么内容！"""
            
        except Exception as e:
            self.log_operation(False, str(e), {"project_name": project_name})
            return f"❌ 创建项目时发生错误：{e}"


class ListProjectsTool(AgentFileTool):
    """列出所有学习项目"""
    
    @property
    def name(self) -> str:
        return "list_projects"
        
    @property
    def description(self) -> str:
        return """列出所有学习项目
        
无参数。返回当前所有项目的状态信息。
"""
        
    @property
    def args_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {},
        }
        
    def execute(self) -> str:
        """列出项目"""
        try:
            if not os.path.exists(PROJECTS_DIR):
                return "还没有创建任何学习项目。使用 create_project 创建你的第一个项目吧！"
                
            projects = []
            for project_name in os.listdir(PROJECTS_DIR):
                project_dir = os.path.join(PROJECTS_DIR, project_name)
                index_file = os.path.join(project_dir, "_index.md")
                
                if os.path.isfile(index_file):
                    result = safe_read_file(
                        filepath=index_file,
                        workspace_root=PROJECTS_DIR,
                    )
                    if result.success:
                        frontmatter = _parse_yaml_frontmatter(result.content)
                        projects.append({
                            "name": project_name,
                            "status": frontmatter.get("status", "unknown"),
                            "total_modules": frontmatter.get("total_modules", 0),
                            "total_score": frontmatter.get("total_score", 0),
                            "max_combo": frontmatter.get("max_combo", 0),
                            "goal_short": frontmatter.get("goal_short", ""),
                            "last_module": frontmatter.get("last_module", ""),
                        })
                        
            if not projects:
                return "还没有创建任何学习项目。使用 create_project 创建你的第一个项目吧！"
                
            result = "# 📚 我的学习项目\n\n"
            for idx, project in enumerate(projects, 1):
                status_emoji = {
                    "active": "🟢",
                    "completed": "✅",
                    "paused": "⏸️",
                    "unknown": "❓"
                }.get(project["status"], "❓")
                
                result += f"""## {idx}. {project['name']} {status_emoji}

- **状态**：{project['status']}
- **短期目标**：{project['goal_short']}
- **完成模块**：{project['total_modules']} 个
- **总分数**：{project['total_score']} 分
- **最大连击**：{project['max_combo']} 🔥
- **最后学习**：{project['last_module']}

---

"""
            
            result += f"\n📊 共有 {len(projects)} 个学习项目"
            
            self.log_operation(True, details={"project_count": len(projects)})
            return result
            
        except Exception as e:
            self.log_operation(False, str(e))
            return f"❌ 列出项目时发生错误：{e}"


class GetProjectStatusTool(AgentFileTool):
    """获取项目状态"""
    
    @property
    def name(self) -> str:
        return "get_project_status"
        
    @property
    def description(self) -> str:
        return """获取指定项目的详细状态
        
参数：
- project_name: 项目名称

返回：
项目的详细状态信息
"""
        
    @property
    def args_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
            },
            "required": ["project_name"],
        }
        
    def execute(self, project_name: str) -> str:
        """获取项目状态"""
        try:
            project_dir = os.path.join(PROJECTS_DIR, project_name)
            index_file = os.path.join(project_dir, "_index.md")
            
            if not os.path.exists(index_file):
                return f"项目 '{project_name}' 不存在。请检查项目名称或使用 list_projects 查看所有项目。"
                
            result = safe_read_file(
                filepath=index_file,
                workspace_root=PROJECTS_DIR,
            )
            
            if not result.success:
                return f"❌ 读取项目状态失败：{result.error}"
                
            frontmatter = _parse_yaml_frontmatter(result.content)
            
            status_emoji = {
                "active": "🟢 进行中",
                "completed": "✅ 已完成",
                "paused": "⏸️ 已暂停",
                "unknown": "❓ 未知"
            }.get(frontmatter.get("status", "unknown"), "❓ 未知")
            
            output = f"""# 📊 {project_name} - 项目状态

## 基本信息

- **状态**：{status_emoji}
- **创建时间**：{frontmatter.get('created', '未知')}
- **最后学习**：{frontmatter.get('last_module', '未知')}
- **学习领域**：{frontmatter.get('discipline', '综合')}

## 🎯 学习目标

- **短期目标**：{frontmatter.get('goal_short', '未设定')}
- **长期目标**：{frontmatter.get('goal_long', '未设定')}

## 📈 游戏化数据

- **总分数**：{frontmatter.get('total_score', 0)} 分
- **当前连击**：{frontmatter.get('current_combo', 0)} 🔥
- **最大连击**：{frontmatter.get('max_combo', 0)} 💪

## 🧩 学习进度

- **完成模块**：{frontmatter.get('total_modules', 0)} 个

---

{result.content}
"""
            
            self.log_operation(True, details={
                "filepath": index_file,
                "project_name": project_name,
            })
            return output
            
        except Exception as e:
            self.log_operation(False, str(e), {"project_name": project_name})
            return f"❌ 获取项目状态时发生错误：{e}"


# ==================== 通用文件操作工具 ====================

class ReadFileTool(AgentFileTool):
    """安全读取任意文件"""
    
    @property
    def name(self) -> str:
        return "read_file"
        
    @property
    def description(self) -> str:
        return """安全读取文件内容

参数：
- filepath: 文件路径（相对于 PROJECTS_DIR）
- max_chars: 最大读取字符数，默认 100000

返回：
文件内容（失败返回错误信息）
"""
        
    @property
    def args_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "max_chars": {"type": "integer", "description": "最大读取字符数", "default": 100000},
            },
            "required": ["filepath"],
        }
        
    def execute(self, filepath: str, max_chars: int = 100000) -> str:
        """读取文件"""
        try:
            full_path = os.path.join(PROJECTS_DIR, filepath)
            result = safe_read_file(
                filepath=full_path,
                workspace_root=PROJECTS_DIR,
                max_chars=max_chars,
            )
            
            if not result.success:
                self.log_operation(False, result.error, {"filepath": full_path})
                return f"❌ 读取失败：{result.error}"
                
            self.log_operation(True, details={
                "filepath": full_path,
                "size": result.size,
            })
            return result.content
            
        except Exception as e:
            self.log_operation(False, str(e), {"filepath": filepath})
            return f"❌ 读取文件时发生错误：{e}"


class WriteFileTool(AgentFileTool):
    """安全写入文件"""
    
    @property
    def name(self) -> str:
        return "write_file"
        
    @property
    def description(self) -> str:
        return """安全写入文件内容

参数：
- filepath: 文件路径（相对于 PROJECTS_DIR）
- content: 写入内容
- max_bytes: 最大写入字节数，默认 10485760 (10MB)

返回：
写入结果（成功/失败信息）
"""
        
    @property
    def args_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "写入内容"},
                "max_bytes": {"type": "integer", "description": "最大写入字节数", "default": 10485760},
            },
            "required": ["filepath", "content"],
        }
        
    def execute(self, filepath: str, content: str, max_bytes: int = 10485760) -> str:
        """写入文件"""
        try:
            full_path = os.path.join(PROJECTS_DIR, filepath)
            result = safe_write_file(
                filepath=full_path,
                content=content,
                workspace_root=PROJECTS_DIR,
                max_bytes=max_bytes,
                mkdir=True,
            )
            
            if not result.success:
                self.log_operation(False, result.error, {"filepath": full_path})
                return f"❌ 写入失败：{result.error}"
                
            self.log_operation(True, details={
                "filepath": full_path,
                "bytes_written": result.bytes_written,
            })
            return f"✅ 写入成功：{filepath} ({result.bytes_written} bytes)"
            
        except Exception as e:
            self.log_operation(False, str(e), {"filepath": filepath})
            return f"❌ 写入文件时发生错误：{e}"


# ==================== 工具注册表 ====================

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, AgentFileTool] = {}
        
    def register(self, tool: AgentFileTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        
    def get(self, name: str) -> Optional[AgentFileTool]:
        """获取工具"""
        return self._tools.get(name)
        
    def list_tools(self) -> List[Dict]:
        """列出所有已注册工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema,
            }
            for tool in self._tools.values()
        ]
        
    def execute(self, name: str, **kwargs) -> str:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            return f"❌ 工具不存在: {name}"
            
        if not tool.validate(**kwargs):
            return f"❌ 参数验证失败: {name}"
            
        return tool.execute(**kwargs)


# ==================== 全局实例 ====================

# 创建工具注册表并注册所有工具
_registry = ToolRegistry()

# 注册所有工具
for tool_class in [
    CreateProjectTool,
    ListProjectsTool,
    GetProjectStatusTool,
    ReadFileTool,
    WriteFileTool,
]:
    _registry.register(tool_class())


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表"""
    return _registry


def execute_tool(name: str, **kwargs) -> str:
    """便捷函数：直接执行工具"""
    return _registry.execute(name, **kwargs)


# ==================== 辅助函数 ====================

def _parse_yaml_frontmatter(content: str) -> dict:
    """解析 YAML frontmatter"""
    if content.startswith("---"):
        lines = content.split('\n')
        if len(lines) > 1:
            end_idx = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    end_idx = i
                    break

            if end_idx > 0:
                try:
                    import yaml
                    frontmatter = yaml.safe_load('\n'.join(lines[1:end_idx]))
                    return frontmatter if frontmatter else {}
                except Exception:
                    return {}
    return {}
