# Agent 安全文件工具模块 实施计划

> **给代理执行者：** 推荐配合 `subagent-driven-development（子代理驱动开发）`（每任务独立子代理 + 两阶段审查）或在本会话内按勾选逐步执行并在批次节点与用户确认。任务使用 `- [ ]` 勾选跟踪。

**目标：** 创建统一的 Agent 安全文件工具模块，解决当前 Agent 工具调用无法正常读写本地文件系统的问题，实现安全的文件操作、权限验证、错误处理和审计日志功能。

**架构要点：**
1. 采用分层安全架构：新工具层 (`agent_file_tools.py`) + 现有安全层 (`safe_file_ops.py`) + 新增审计层 (`audit_logger.py`) + 参数验证层 (`tool_validator.py`)
2. 所有文件操作必须通过 `safe_file_ops.py`，禁止直接使用 `open()`
3. 工具注册表统一管理，支持 LangChain 工具调用协议

**技术栈：** Python 3.10+、LangChain/LangGraph、pytest（测试命令：`python -m pytest tests/ -v`）

**关联设计文档：** `docs/specs/2026-04-21-agent-file-tools-设计.md`

**分支策略：** 建议在独立分支 `feature/agent-file-tools` 上实施，完成后再合并到 main。

---

## 文件结构

### 新建文件

| 文件路径 | 职责 |
|---------|------|
| `src/utils/audit_logger.py` | 审计日志记录器，记录所有文件操作 |
| `src/utils/tool_validator.py` | 工具参数验证器，验证路径合法性 |
| `src/tools/agent_file_tools.py` | Agent 安全文件工具模块（工具基类、具体工具、注册表） |
| `tests/test_audit_logger.py` | 审计日志模块测试 |
| `tests/test_tool_validator.py` | 参数验证模块测试 |
| `tests/test_agent_file_tools.py` | Agent 文件工具模块测试 |

### 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `src/agents/agent.py` | 修改工具导入，使用新的 `agent_file_tools.py` |
| `chainlit_ui.py` | 如有需要，同步更新工具导入路径 |

### 保留文件（不修改）

| 文件路径 | 状态 |
|---------|------|
| `src/utils/safe_file_ops.py` | 保留，不修改，作为安全底层 |
| `src/tools/pulse_tools.py` | 保留，业务逻辑工具继续使用 |
| `src/tools/file_manager.py` | 保留但标记为废弃，向后兼容 |

---

## 任务 1：审计日志模块

**涉及文件：**
- 新建：`src/utils/audit_logger.py`
- 测试：`tests/test_audit_logger.py`

- [ ] **步骤 1.1：编写失败测试 - 审计日志记录**

```python
# tests/test_audit_logger.py

import os
import json
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.audit_logger import AuditLogger


class TestAuditLogger(unittest.TestCase):
    """审计日志模块测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="audit_test_")
        self.log_file = os.path.join(self.test_dir, "audit_log.json")
        self.logger = AuditLogger(log_file=self.log_file)

    def tearDown(self):
        """清理临时目录"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_operation_success(self):
        """测试成功操作记录"""
        self.logger.log(
            operation="read_file",
            filepath="/test/file.txt",
            success=True,
            details={"size": 1024}
        )
        
        # 读取日志文件
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            entry = json.loads(line)
        
        self.assertEqual(entry["operation"], "read_file")
        self.assertEqual(entry["filepath"], "/test/file.txt")
        self.assertTrue(entry["success"])
        self.assertEqual(entry["details"]["size"], 1024)
        self.assertIn("timestamp", entry)
```

- [ ] **步骤 1.2：运行测试确认失败**

运行：`python -m pytest tests/test_audit_logger.py::TestAuditLogger::test_log_operation_success -v`  
预期：`ModuleNotFoundError: No module named 'utils.audit_logger'`（模块不存在）

- [ ] **步骤 1.3：最小实现 - 审计日志模块**

```python
# src/utils/audit_logger.py
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
from typing import Dict, Optional

logger = logging.getLogger("pulse_learning.audit")


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_file: Optional[str] = None):
        """初始化审计日志"""
        if log_file:
            self.log_file = log_file
        else:
            self.log_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "audit_log.json"
            )
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
    def log(self, operation: str, filepath: str, success: bool, 
            error: str = "", details: Optional[Dict] = None) -> None:
        """记录操作"""
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
        """追加到日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
```

- [ ] **步骤 1.4：运行测试确认通过**

运行：`python -m pytest tests/test_audit_logger.py::TestAuditLogger::test_log_operation_success -v`  
预期：`PASSED`

- [ ] **步骤 1.5：提交**

```bash
git add src/utils/audit_logger.py tests/test_audit_logger.py
git commit -m "feat: 添加审计日志模块 - 记录所有文件操作"
```

---

## 任务 2：参数验证模块

**涉及文件：**
- 新建：`src/utils/tool_validator.py`
- 测试：`tests/test_tool_validator.py`

- [ ] **步骤 2.1：编写失败测试 - 路径验证**

```python
# tests/test_tool_validator.py

import os
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.tool_validator import ToolValidator, PathValidationResult, ValidationResult


class TestToolValidator(unittest.TestCase):
    """参数验证模块测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="validator_test_")
        self.validator = ToolValidator()

    def test_validate_path_inside(self):
        """测试路径在 workspace 内"""
        test_file = os.path.join(self.test_dir, "test.txt")
        result = self.validator.validate_path(test_file, self.test_dir)
        
        self.assertTrue(result.success)
        self.assertEqual(result.resolved_path, os.path.normpath(test_file))

    def test_validate_path_outside(self):
        """测试路径在 workspace 外（逃逸）"""
        outside_file = os.path.join(tempfile.gettempdir(), "outside.txt")
        result = self.validator.validate_path(outside_file, self.test_dir)
        
        self.assertFalse(result.success)
        self.assertIn("逃逸", result.error)

    def test_validate_content_size_ok(self):
        """测试内容大小验证 - 正常"""
        content = "small content"
        result = self.validator.validate_content_size(content, max_bytes=1024)
        
        self.assertTrue(result.success)

    def test_validate_content_size_exceeded(self):
        """测试内容大小验证 - 超限"""
        content = "x" * 2048
        result = self.validator.validate_content_size(content, max_bytes=1024)
        
        self.assertFalse(result.success)
        self.assertIn("超过", result.error)
```

- [ ] **步骤 2.2：运行测试确认失败**

运行：`python -m pytest tests/test_tool_validator.py -v`  
预期：`ModuleNotFoundError: No module named 'utils.tool_validator'`

- [ ] **步骤 2.3：最小实现 - 参数验证模块**

```python
# src/utils/tool_validator.py
"""
工具参数验证模块

功能：
1. 路径合法性验证
2. 文件类型白名单
3. 深度限制
4. 大小限制
"""

import os
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    error: str = ""


@dataclass  
class PathValidationResult(ValidationResult):
    """路径验证结果"""
    resolved_path: str = ""
    is_symlink: bool = False


class ToolValidator:
    """工具参数验证器"""
    
    def validate_path(self, filepath: str, workspace_root: str,
                     allowed_extensions: Optional[List[str]] = None,
                     max_depth: int = 10) -> PathValidationResult:
        """验证路径合法性"""
        # 1. 展开路径
        resolved = os.path.normpath(os.path.abspath(
            os.path.expanduser(os.path.expandvars(filepath))
        ))
        workspace_resolved = os.path.normpath(os.path.abspath(workspace_root))
        
        # 2. 路径边界检查
        if not (resolved == workspace_resolved or resolved.startswith(workspace_resolved + os.sep)):
            return PathValidationResult(
                success=False,
                error=f"路径逃逸 workspace: {filepath}",
                resolved_path=resolved,
            )
            
        # 3. 检查深度
        depth = resolved.count(os.sep) - workspace_root.count(os.sep)
        if depth > max_depth:
            return PathValidationResult(
                success=False,
                error=f"路径深度 {depth} 超过限制 {max_depth}",
                resolved_path=resolved,
            )
            
        # 4. 检查扩展名
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
        """验证内容大小"""
        if len(content.encode('utf-8')) > max_bytes:
            return ValidationResult(
                success=False,
                error=f"内容超过最大允许大小 ({max_bytes} bytes)"
            )
        return ValidationResult(success=True)
```

- [ ] **步骤 2.4：运行测试确认通过**

运行：`python -m pytest tests/test_tool_validator.py -v`  
预期：全部 PASSED

- [ ] **步骤 2.5：提交**

```bash
git add src/utils/tool_validator.py tests/test_tool_validator.py
git commit -m "feat: 添加参数验证模块 - 路径和大小验证"
```

---

## 任务 3：工具基类

**涉及文件：**
- 新建：`src/tools/agent_file_tools.py`（仅基类部分）
- 测试：`tests/test_agent_file_tools.py`

- [ ] **步骤 3.1：编写失败测试 - 工具基类抽象方法**

```python
# tests/test_agent_file_tools.py

import os
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.agent_file_tools import AgentFileTool


class ConcreteTool(AgentFileTool):
    """用于测试的具体工具实现"""
    
    @property
    def name(self) -> str:
        return "test_tool"
    
    @property
    def description(self) -> str:
        return "测试工具"
    
    @property
    def args_schema(self) -> dict:
        return {"type": "object", "properties": {}}
    
    def execute(self, **kwargs) -> str:
        return "test result"


class TestAgentFileTool(unittest.TestCase):
    """Agent 文件工具基类测试"""

    def test_tool_name(self):
        """测试工具名称"""
        tool = ConcreteTool()
        self.assertEqual(tool.name, "test_tool")

    def test_tool_description(self):
        """测试工具描述"""
        tool = ConcreteTool()
        self.assertIn("测试", tool.description)

    def test_tool_execute(self):
        """测试工具执行"""
        tool = ConcreteTool()
        result = tool.execute()
        self.assertEqual(result, "test result")
```

- [ ] **步骤 3.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py -v`  
预期：`ModuleNotFoundError: No module named 'tools.agent_file_tools'`

- [ ] **步骤 3.3：最小实现 - 工具基类部分**

```python
# src/tools/agent_file_tools.py
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
try:
    from utils.safe_file_ops import (
        safe_read_file, safe_write_file, safe_delete_file,
        ReadResult, WriteResult,
    )
    from utils.data_paths import get_projects_dir
    from utils.audit_logger import AuditLogger
    from utils.tool_validator import ToolValidator
except ImportError:
    from ..utils.safe_file_ops import (
        safe_read_file, safe_write_file, safe_delete_file,
        ReadResult, WriteResult,
    )
    from ..utils.data_paths import get_projects_dir
    from ..utils.audit_logger import AuditLogger
    from ..utils.tool_validator import ToolValidator

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
        filepath = kwargs.get('filepath', '')
        if not filepath:
            return True  # 某些工具没有 filepath 参数
            
        result = _validator.validate_path(filepath, PROJECTS_DIR)
        if not result.success:
            logger.warning(f"Validation failed for {self.name}: {result.error}")
            return False
        return True
        
    def log_operation(self, success: bool, error: str = "", details: Optional[Dict] = None):
        """记录操作日志"""
        _audit_logger.log(
            operation=self.name,
            filepath=details.get('filepath', '') if details else '',
            success=success,
            error=error,
            details=details,
        )
```

- [ ] **步骤 3.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestAgentFileTool -v`  
预期：全部 PASSED

- [ ] **步骤 3.5：提交**

```bash
git add src/tools/agent_file_tools.py tests/test_agent_file_tools.py
git commit -m "feat: 添加工具基类 - AgentFileTool 抽象类"
```

---

## 任务 4：创建项目工具

**涉及文件：**
- 修改：`src/tools/agent_file_tools.py`（添加 CreateProjectTool）
- 测试：`tests/test_agent_file_tools.py`（添加 CreateProjectTool 测试）

- [ ] **步骤 4.1：编写失败测试 - 创建项目**

```python
# 在 tests/test_agent_file_tools.py 中添加

import tempfile
import shutil


class TestCreateProjectTool(unittest.TestCase):
    """创建项目工具测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="project_test_")
        # 修改全局 PROJECTS_DIR 为临时目录
        import tools.agent_file_tools as aft
        self.original_projects_dir = aft.PROJECTS_DIR
        aft.PROJECTS_DIR = self.test_dir

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        import tools.agent_file_tools as aft
        aft.PROJECTS_DIR = self.original_projects_dir

    def test_create_project_success(self):
        """测试成功创建项目"""
        from tools.agent_file_tools import CreateProjectTool
        
        tool = CreateProjectTool()
        result = tool.execute(
            project_name="测试项目",
            goal_short="学习 Python",
            goal_long="成为 Python 专家",
            discipline="编程"
        )
        
        self.assertIn("创建成功", result)
        
        # 验证文件已创建
        project_dir = os.path.join(self.test_dir, "测试项目")
        index_file = os.path.join(project_dir, "_index.md")
        self.assertTrue(os.path.exists(index_file))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "modules")))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "attachments")))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "resources.md")))

    def test_create_project_duplicate(self):
        """测试重复创建项目"""
        from tools.agent_file_tools import CreateProjectTool
        
        tool = CreateProjectTool()
        
        # 第一次创建
        tool.execute(
            project_name="重复项目",
            goal_short="目标1",
            goal_long="目标2"
        )
        
        # 第二次创建应该失败
        result = tool.execute(
            project_name="重复项目",
            goal_short="目标1",
            goal_long="目标2"
        )
        
        self.assertIn("已存在", result)

    def test_create_project_empty_name(self):
        """测试空项目名称"""
        from tools.agent_file_tools import CreateProjectTool
        
        tool = CreateProjectTool()
        result = tool.execute(
            project_name="",
            goal_short="目标1",
            goal_long="目标2"
        )
        
        self.assertIn("不能为空", result)
```

- [ ] **步骤 4.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py::TestCreateProjectTool -v`  
预期：`ImportError: cannot import name 'CreateProjectTool'`（类不存在）

- [ ] **步骤 4.3：最小实现 - CreateProjectTool**

```python
# 在 src/tools/agent_file_tools.py 中添加

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
```

- [ ] **步骤 4.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestCreateProjectTool -v`  
预期：全部 PASSED

- [ ] **步骤 4.5：提交**

```bash
git add src/tools/agent_file_tools.py tests/test_agent_file_tools.py
git commit -m "feat: 添加创建项目工具 - CreateProjectTool"
```

---

## 任务 5：列出项目和获取状态工具

**涉及文件：**
- 修改：`src/tools/agent_file_tools.py`（添加 ListProjectsTool 和 GetProjectStatusTool）
- 测试：`tests/test_agent_file_tools.py`

- [ ] **步骤 5.1：编写失败测试**

```python
# 在 tests/test_agent_file_tools.py 中添加

class TestListProjectsTool(unittest.TestCase):
    """列出项目工具测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="list_test_")
        import tools.agent_file_tools as aft
        self.original_projects_dir = aft.PROJECTS_DIR
        aft.PROJECTS_DIR = self.test_dir
        
        # 创建一个测试项目
        from tools.agent_file_tools import CreateProjectTool
        tool = CreateProjectTool()
        tool.execute(
            project_name="项目A",
            goal_short="学习A",
            goal_long="精通A",
            discipline="编程"
        )

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        import tools.agent_file_tools as aft
        aft.PROJECTS_DIR = self.original_projects_dir

    def test_list_projects(self):
        """测试列出项目"""
        from tools.agent_file_tools import ListProjectsTool
        
        tool = ListProjectsTool()
        result = tool.execute()
        
        self.assertIn("项目A", result)
        self.assertIn("学习A", result)
        self.assertIn("1 个学习项目", result)


class TestGetProjectStatusTool(unittest.TestCase):
    """获取项目状态工具测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="status_test_")
        import tools.agent_file_tools as aft
        self.original_projects_dir = aft.PROJECTS_DIR
        aft.PROJECTS_DIR = self.test_dir
        
        # 创建一个测试项目
        from tools.agent_file_tools import CreateProjectTool
        tool = CreateProjectTool()
        tool.execute(
            project_name="状态测试项目",
            goal_short="短期目标",
            goal_long="长期目标",
            discipline="测试"
        )

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        import tools.agent_file_tools as aft
        aft.PROJECTS_DIR = self.original_projects_dir

    def test_get_project_status_success(self):
        """测试成功获取项目状态"""
        from tools.agent_file_tools import GetProjectStatusTool
        
        tool = GetProjectStatusTool()
        result = tool.execute(project_name="状态测试项目")
        
        self.assertIn("状态测试项目", result)
        self.assertIn("短期目标", result)
        self.assertIn("长期目标", result)

    def test_get_project_status_not_found(self):
        """测试项目不存在"""
        from tools.agent_file_tools import GetProjectStatusTool
        
        tool = GetProjectStatusTool()
        result = tool.execute(project_name="不存在的项目")
        
        self.assertIn("不存在", result)
```

- [ ] **步骤 5.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py::TestListProjectsTool -v`  
预期：`ImportError: cannot import name 'ListProjectsTool'`

- [ ] **步骤 5.3：最小实现**

```python
# 在 src/tools/agent_file_tools.py 中添加

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
```

- [ ] **步骤 5.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestListProjectsTool tests/test_agent_file_tools.py::TestGetProjectStatusTool -v`  
预期：全部 PASSED

- [ ] **步骤 5.5：提交**

```bash
git add src/tools/agent_file_tools.py tests/test_agent_file_tools.py
git commit -m "feat: 添加列出项目和获取状态工具"
```

---

## 任务 6：通用读写文件工具

**涉及文件：**
- 修改：`src/tools/agent_file_tools.py`（添加 ReadFileTool 和 WriteFileTool）
- 测试：`tests/test_agent_file_tools.py`

- [ ] **步骤 6.1：编写失败测试**

```python
# 在 tests/test_agent_file_tools.py 中添加

class TestReadWriteFileTools(unittest.TestCase):
    """通用读写文件工具测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="rw_test_")
        import tools.agent_file_tools as aft
        self.original_projects_dir = aft.PROJECTS_DIR
        aft.PROJECTS_DIR = self.test_dir

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        import tools.agent_file_tools as aft
        aft.PROJECTS_DIR = self.original_projects_dir

    def test_write_file_success(self):
        """测试成功写入文件"""
        from tools.agent_file_tools import WriteFileTool
        
        tool = WriteFileTool()
        result = tool.execute(
            filepath="test_dir/test.txt",
            content="Hello World"
        )
        
        self.assertIn("写入成功", result)
        
        # 验证文件内容
        file_path = os.path.join(self.test_dir, "test_dir", "test.txt")
        with open(file_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), "Hello World")

    def test_read_file_success(self):
        """测试成功读取文件"""
        from tools.agent_file_tools import WriteFileTool, ReadFileTool
        
        # 先写入
        write_tool = WriteFileTool()
        write_tool.execute(
            filepath="read_test.txt",
            content="Test Content"
        )
        
        # 再读取
        read_tool = ReadFileTool()
        result = read_tool.execute(filepath="read_test.txt")
        
        self.assertIn("Test Content", result)

    def test_read_nonexistent_file(self):
        """测试读取不存在的文件"""
        from tools.agent_file_tools import ReadFileTool
        
        tool = ReadFileTool()
        result = tool.execute(filepath="nonexistent.txt")
        
        self.assertIn("读取失败", result)
```

- [ ] **步骤 6.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py::TestReadWriteFileTools -v`  
预期：`ImportError: cannot import name 'ReadFileTool'`

- [ ] **步骤 6.3：最小实现**

```python
# 在 src/tools/agent_file_tools.py 中添加

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
```

- [ ] **步骤 6.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestReadWriteFileTools -v`  
预期：全部 PASSED

- [ ] **步骤 6.5：提交**

```bash
git add src/tools/agent_file_tools.py tests/test_agent_file_tools.py
git commit -m "feat: 添加通用读写文件工具"
```

---

## 任务 7：工具注册表

**涉及文件：**
- 修改：`src/tools/agent_file_tools.py`（添加 ToolRegistry 和全局实例）
- 测试：`tests/test_agent_file_tools.py`

- [ ] **步骤 7.1：编写失败测试**

```python
# 在 tests/test_agent_file_tools.py 中添加

class TestToolRegistry(unittest.TestCase):
    """工具注册表测试"""

    def test_registry_register_and_execute(self):
        """测试注册表注册和执行"""
        from tools.agent_file_tools import ToolRegistry, CreateProjectTool
        
        registry = ToolRegistry()
        registry.register(CreateProjectTool())
        
        # 获取工具
        tool = registry.get("create_project")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "create_project")
        
    def test_registry_list_tools(self):
        """测试列出所有工具"""
        from tools.agent_file_tools import ToolRegistry, CreateProjectTool
        
        registry = ToolRegistry()
        registry.register(CreateProjectTool())
        
        tools = registry.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "create_project")
        
    def test_registry_execute_nonexistent(self):
        """测试执行不存在的工具"""
        from tools.agent_file_tools import ToolRegistry
        
        registry = ToolRegistry()
        result = registry.execute("nonexistent_tool")
        
        self.assertIn("不存在", result)
```

- [ ] **步骤 7.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py::TestToolRegistry -v`  
预期：`ImportError: cannot import name 'ToolRegistry'`

- [ ] **步骤 7.3：最小实现**

```python
# 在 src/tools/agent_file_tools.py 末尾添加

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


# 创建全局工具注册表并注册所有工具
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
```

- [ ] **步骤 7.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestToolRegistry -v`  
预期：全部 PASSED

- [ ] **步骤 7.5：提交**

```bash
git add src/tools/agent_file_tools.py tests/test_agent_file_tools.py
git commit -m "feat: 添加工具注册表 - ToolRegistry"
```

---

## 任务 8：更新 Agent 工具导入

**涉及文件：**
- 修改：`src/agents/agent.py`

- [ ] **步骤 8.1：编写失败测试（集成测试）**

```python
# 在 tests/test_agent_file_tools.py 中添加

class TestAgentIntegration(unittest.TestCase):
    """Agent 集成测试"""

    def test_agent_imports_new_tools(self):
        """测试 Agent 能成功导入新工具"""
        import importlib
        import agents.agent as agent_module
        
        # 重新加载模块以获取最新导入
        importlib.reload(agent_module)
        
        # 检查新工具是否可用
        from tools.agent_file_tools import (
            CreateProjectTool,
            ListProjectsTool,
            GetProjectStatusTool,
            ReadFileTool,
            WriteFileTool,
        )
        
        # 验证工具属性
        self.assertEqual(CreateProjectTool().name, "create_project")
        self.assertEqual(ListProjectsTool().name, "list_projects")
        self.assertEqual(GetProjectStatusTool().name, "get_project_status")
        self.assertEqual(ReadFileTool().name, "read_file")
        self.assertEqual(WriteFileTool().name, "write_file")
```

- [ ] **步骤 8.2：运行测试确认失败**

运行：`python -m pytest tests/test_agent_file_tools.py::TestAgentIntegration -v`  
预期：测试通过但 Agent 尚未使用新工具

- [ ] **步骤 8.3：修改 agent.py**

```python
# 在 src/agents/agent.py 中，将工具导入部分修改为：

# 工具（使用新的 Agent 安全文件工具模块）
try:
    from tools.agent_file_tools import (
        CreateProjectTool, ListProjectsTool, GetProjectStatusTool,
        ReadFileTool, WriteFileTool,
    )
    
    # 实例化工具
    create_project = CreateProjectTool().execute
    list_projects = ListProjectsTool().execute
    get_project_status = GetProjectStatusTool().execute
    read_file = ReadFileTool().execute
    write_file = WriteFileTool().execute
    
    # 尝试从独立模块导入其他工具
    try:
        from tools.boss_task_manager import generate_boss_task, complete_boss_task, get_boss_task
    except ImportError:
        generate_boss_task = complete_boss_task = get_boss_task = None

    try:
        from tools.challenge_manager import complete_module
    except ImportError:
        complete_module = None

    try:
        from tools.history_manager import get_learning_history, get_learning_statistics, get_daily_summary
    except ImportError:
        get_learning_history = get_learning_statistics = get_daily_summary = None

    try:
        from tools.resource_manager import add_learning_resource, add_code_snippet, get_resources, add_note
    except ImportError:
        add_learning_resource = add_code_snippet = get_resources = add_note = None

    try:
        from tools.combo_manager import reset_combo, pause_combo, resume_combo, get_combo_status
    except ImportError:
        reset_combo = pause_combo = resume_combo = get_combo_status = None

    PULSE_TOOLS_AVAILABLE = True
except ImportError:
    PULSE_TOOLS_AVAILABLE = False
```

- [ ] **步骤 8.4：运行测试确认通过**

运行：`python -m pytest tests/test_agent_file_tools.py::TestAgentIntegration -v`  
预期：PASSED

- [ ] **步骤 8.5：运行完整测试套件**

运行：`python -m pytest tests/ -v`  
预期：全部 PASSED

- [ ] **步骤 8.6：提交**

```bash
git add src/agents/agent.py
git commit -m "refactor: 更新 Agent 工具导入，使用新的安全文件工具模块"
```

---

## 任务 9：端到端集成测试

**涉及文件：**
- 新建：`tests/test_e2e_file_tools.py`

- [ ] **步骤 9.1：编写端到端测试**

```python
# tests/test_e2e_file_tools.py

import os
import tempfile
import shutil
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestE2EFileTools(unittest.TestCase):
    """端到端文件工具测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="e2e_test_")
        import tools.agent_file_tools as aft
        self.original_projects_dir = aft.PROJECTS_DIR
        aft.PROJECTS_DIR = self.test_dir

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        import tools.agent_file_tools as aft
        aft.PROJECTS_DIR = self.original_projects_dir

    def test_full_project_workflow(self):
        """测试完整项目工作流"""
        from tools.agent_file_tools import (
            CreateProjectTool, ListProjectsTool, GetProjectStatusTool,
            WriteFileTool, ReadFileTool
        )
        
        # 1. 创建项目
        create_tool = CreateProjectTool()
        create_result = create_tool.execute(
            project_name="端到端测试项目",
            goal_short="测试工具集成",
            goal_long="验证所有工具协同工作",
            discipline="测试"
        )
        self.assertIn("创建成功", create_result)
        
        # 2. 列出项目
        list_tool = ListProjectsTool()
        list_result = list_tool.execute()
        self.assertIn("端到端测试项目", list_result)
        
        # 3. 获取项目状态
        status_tool = GetProjectStatusTool()
        status_result = status_tool.execute(project_name="端到端测试项目")
        self.assertIn("端到端测试项目", status_result)
        self.assertIn("测试工具集成", status_result)
        
        # 4. 写入文件到项目
        write_tool = WriteFileTool()
        write_result = write_tool.execute(
            filepath="端到端测试项目/notes.md",
            content="# 学习笔记\n\n这是一个测试笔记。"
        )
        self.assertIn("写入成功", write_result)
        
        # 5. 读取文件
        read_tool = ReadFileTool()
        read_result = read_tool.execute(
            filepath="端到端测试项目/notes.md"
        )
        self.assertIn("学习笔记", read_result)
        self.assertIn("测试笔记", read_result)
```

- [ ] **步骤 9.2：运行测试确认通过**

运行：`python -m pytest tests/test_e2e_file_tools.py -v`  
预期：全部 PASSED

- [ ] **步骤 9.3：提交**

```bash
git add tests/test_e2e_file_tools.py
git commit -m "test: 添加端到端集成测试"
```

---

## 风险管理

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| `safe_file_ops.py` 兼容性问题 | 低 | 中 | 保持现有接口不变，仅通过工具层调用 |
| Windows 路径问题 | 中 | 中 | 使用 `os.path.normpath` + `abspath` 统一处理 |
| 测试环境配置差异 | 低 | 低 | 使用 `tempfile.mkdtemp()` 创建隔离测试环境 |
| LangChain 工具协议变更 | 低 | 高 | 工具使用标准 Python 函数，不依赖特定协议 |

---

## 质量控制标准

1. **测试覆盖率**：所有新代码测试覆盖率 ≥ 90%
2. **代码风格**：遵循 PEP 8，使用 `black` 格式化
3. **类型注解**：所有公共函数必须有类型注解
4. **文档字符串**：所有公共函数/类必须有 docstring
5. **无占位符**：计划中禁止 `TODO`/`TBD`/`稍后补充`

---

## 验收标准

- [ ] 所有单元测试通过（`python -m pytest tests/ -v`）
- [ ] 端到端测试通过
- [ ] 审计日志功能正常（可验证 `data/audit_log.json` 存在并记录操作）
- [ ] 参数验证功能正常（路径逃逸被阻止）
- [ ] 安全读写功能正常（通过 `safe_file_ops.py`）
- [ ] Agent 能成功导入和使用新工具
- [ ] 无 regressions（现有测试全部通过）

---

## 关键里程碑

| 里程碑 | 交付物 | 预计时间 |
|--------|--------|---------|
| M1: 基础模块完成 | `audit_logger.py` + `tool_validator.py` + 测试 | 任务 1-2 |
| M2: 工具层完成 | `agent_file_tools.py`（全部工具）+ 测试 | 任务 3-7 |
| M3: 集成完成 | Agent 工具导入更新 + 集成测试 | 任务 8 |
| M4: 验收完成 | 端到端测试 + 全部测试通过 | 任务 9 |

---

## 沟通协调机制

- **进度同步**：每完成一个里程碑（M1-M4）通知用户
- **问题上报**：遇到阻塞问题立即上报，不自行假设
- **代码审查**：每个任务完成后进行自检，关键任务使用 `code-review-expert` 技能

---

**计划编写完成。请审阅以上计划，如需调整请告知，确认后我们开始执行。**