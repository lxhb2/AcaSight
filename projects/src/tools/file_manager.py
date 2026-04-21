import os
import json
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

# 项目根目录
WORKSPACE_PATH = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
PROJECTS_DIR = os.path.join(WORKSPACE_PATH, "assets", "PulseLearning")


def _ensure_project_dir(project_name: str) -> str:
    """确保项目目录存在"""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    attachments_dir = os.path.join(project_dir, "attachments")

    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(modules_dir, exist_ok=True)
    os.makedirs(attachments_dir, exist_ok=True)

    return project_dir


def _read_file(file_path: str) -> str:
    """读取文件内容"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def _write_file(file_path: str, content: str) -> None:
    """写入文件内容"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


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
                except:
                    return {}
    return {}


def _update_yaml_frontmatter(content: str, updates: dict) -> str:
    """更新 YAML frontmatter"""
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
                    frontmatter = frontmatter if frontmatter else {}

                    # 更新字段
                    frontmatter.update(updates)

                    # 重新生成 frontmatter
                    new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
                    new_content = "---\n" + new_frontmatter + "---" + '\n'.join(lines[end_idx+1:])
                    return new_content
                except Exception as e:
                    pass
    return content


@tool
def create_project(project_name: str, goal_short: str, goal_long: str, discipline: str = "综合") -> str:
    """
    创建一个新的学习项目

    Args:
        project_name: 项目名称
        goal_short: 短期目标（本次学习周期目标）
        goal_long: 长期目标（最终要达到的目标）
        discipline: 学习领域（如：编程、数学、语言等）

    Returns:
        创建结果信息
    """
    ctx = request_context.get() or new_context(method="create_project")

    # 创建项目目录结构
    project_dir = _ensure_project_dir(project_name)

    # 检查项目是否已存在
    index_file = os.path.join(project_dir, "_index.md")
    if os.path.exists(index_file):
        return f"项目 '{project_name}' 已存在！请使用其他名称或继续现有项目。"

    # 创建当前时间
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_today = datetime.now().strftime("%Y-%m-%d")

    # 创建 _index.md 文件
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

    _write_file(index_file, index_content)

    # 创建 resources.md 文件
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
    _write_file(resources_file, resources_content)

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


@tool
def list_projects() -> str:
    """
    列出所有学习项目

    Returns:
        项目列表信息
    """
    ctx = request_context.get() or new_context(method="list_projects")

    if not os.path.exists(PROJECTS_DIR):
        return "还没有创建任何学习项目。使用 create_project 创建你的第一个项目吧！"

    projects = []
    for project_name in os.listdir(PROJECTS_DIR):
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        index_file = os.path.join(project_dir, "_index.md")

        if os.path.isfile(index_file):
            content = _read_file(index_file)
            frontmatter = _parse_yaml_frontmatter(content)

            project_info = {
                "name": project_name,
                "status": frontmatter.get("status", "unknown"),
                "total_modules": frontmatter.get("total_modules", 0),
                "total_score": frontmatter.get("total_score", 0),
                "max_combo": frontmatter.get("max_combo", 0),
                "goal_short": frontmatter.get("goal_short", ""),
                "last_module": frontmatter.get("last_module", "")
            }
            projects.append(project_info)

    if not projects:
        return "还没有创建任何学习项目。使用 create_project 创建你的第一个项目吧！"

    # 生成项目列表
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

    return result


@tool
def get_project_status(project_name: str) -> str:
    """
    获取指定项目的详细状态

    Args:
        project_name: 项目名称

    Returns:
        项目状态详情
    """
    ctx = request_context.get() or new_context(method="get_project_status")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。请检查项目名称或使用 list_projects 查看所有项目。"

    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)

    status_emoji = {
        "active": "🟢 进行中",
        "completed": "✅ 已完成",
        "paused": "⏸️ 已暂停",
        "unknown": "❓ 未知"
    }.get(frontmatter.get("status", "unknown"), "❓ 未知")

    result = f"""# 📊 {project_name} - 项目状态

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

{content}
"""

    return result


@tool
def create_module(project_name: str, module_name: str, module_goal: str, estimated_time: int = 30) -> str:
    """
    在项目中创建一个新的学习模块

    Args:
        project_name: 项目名称
        module_name: 模块名称
        module_goal: 模块学习目标
        estimated_time: 预计学习时间（分钟），默认 30 分钟

    Returns:
        创建结果信息
    """
    ctx = request_context.get() or new_context(method="create_module")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。请先创建项目。"

    # 读取项目信息
    index_content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(index_content)

    # 获取当前模块数量
    current_modules = frontmatter.get("total_modules", 0)
    module_id = current_modules + 1

    # 创建模块文件
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_today = datetime.now().strftime("%Y-%m-%d")

    module_content = f"""---
module_id: {module_id}
module_name: "{module_name}"
status: "planned"
estimated_time: {estimated_time}
start_time: ""
end_time: ""
challenges_completed: 0
challenges_total: 0
score: 0
boss_task_status: "pending"
---

# 🎯 模块 {module_id}：{module_name}

## 📝 本次最小学习目标

{module_goal}

**预计时间**：{estimated_time} 分钟
**创建时间**：{now}

---

## 🎮 微挑战列表

| 序号 | 挑战内容 | 预计时间 | 成功标志 | 状态 | 分数 |
|------|----------|----------|----------|------|------|

*使用 add_challenge 添加微挑战*

---

## 📚 学习记录

### 学习来源

### 学习内容

### 代码片段

### 截图/附件

### 疑问记录

---

## 🤖 检验任务以及任务汇报

*模块学习完成后，AI 将生成一个检验任务（Boss 挑战）*

---

## 📈 本次学习报告

- **完成度**：0%
- **反馈**：
- **下次建议**：

---

*通过完成微挑战积累分数，最终完成检验任务获得双倍奖励！*
"""

    _write_file(module_file, module_content)

    # 更新项目索引
    updates = {
        "total_modules": module_id,
        "last_module": date_today
    }
    new_index_content = _update_yaml_frontmatter(index_content, updates)
    _write_file(index_file, new_index_content)

    return f"""✅ 模块创建成功！

📚 项目：{project_name}
🎯 模块 {module_id}：{module_name}
⏱️ 预计时间：{estimated_time} 分钟

## 下一步操作

1. 添加微挑战列表（4-8 个微挑战）
2. 开始学习并完成微挑战
3. 完成检验任务（Boss 挑战）

准备好添加微挑战了吗？告诉我你想完成哪些小任务！"""


@tool
def get_modules(project_name: str) -> str:
    """
    获取项目的所有模块列表

    Args:
        project_name: 项目名称

    Returns:
        模块列表
    """
    ctx = request_context.get() or new_context(method="get_modules")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")

    if not os.path.exists(project_dir):
        return f"项目 '{project_name}' 不存在。"

    if not os.path.exists(modules_dir):
        return f"项目 '{project_name}' 还没有创建任何模块。"

    modules = []
    module_files = sorted([f for f in os.listdir(modules_dir) if f.startswith("module_") and f.endswith(".md")])

    for module_file in module_files:
        file_path = os.path.join(modules_dir, module_file)
        content = _read_file(file_path)
        frontmatter = _parse_yaml_frontmatter(content)

        modules.append({
            "id": frontmatter.get("module_id", 0),
            "name": frontmatter.get("module_name", ""),
            "status": frontmatter.get("status", "unknown"),
            "estimated_time": frontmatter.get("estimated_time", 0),
            "score": frontmatter.get("score", 0),
            "challenges_completed": frontmatter.get("challenges_completed", 0),
            "challenges_total": frontmatter.get("challenges_total", 0)
        })

    if not modules:
        return f"项目 '{project_name}' 还没有创建任何模块。使用 create_module 创建第一个模块吧！"

    result = f"# 🧩 {project_name} - 模块列表\n\n"

    for module in modules:
        status_emoji = {
            "planned": "📋 计划中",
            "in_progress": "🔄 进行中",
            "completed": "✅ 已完成"
        }.get(module["status"], "❓ 未知")

        progress = f"{module['challenges_completed']}/{module['challenges_total']}" if module['challenges_total'] > 0 else "0/0"

        result += f"""## 模块 {module['id']}：{module['name']} {status_emoji}

- **状态**：{module['status']}
- **预计时间**：{module['estimated_time']} 分钟
- **分数**：{module['score']} 分
- **微挑战进度**：{progress}

---

"""

    result += f"\n📊 共有 {len(modules)} 个模块"

    return result
