"""
Pulse Learning System - 纯 Python 工具函数
不依赖 LangChain，直接操作文件系统
"""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# 导入安全文件操作模块
try:
    from utils.safe_file_ops import safe_read_file, safe_write_file, ReadResult, WriteResult
    from utils.data_paths import get_path_manager, get_projects_dir
except ImportError:
    from ..utils.safe_file_ops import safe_read_file, safe_write_file, ReadResult, WriteResult
    from ..utils.data_paths import get_path_manager, get_projects_dir

PULSE_VAULT_DIR = r"D:\四季如歌\新建文件夹\脉冲学习"
WORKSPACE_PATH = os.path.abspath(os.getenv("COZE_WORKSPACE_PATH", PULSE_VAULT_DIR))
_path_manager = get_path_manager(WORKSPACE_PATH)
PROJECTS_DIR = get_projects_dir()


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
    """安全读取文件内容"""
    result = safe_read_file(
        filepath=file_path,
        workspace_root=PROJECTS_DIR,
        max_chars=100_000,
    )
    if result.success:
        return result.content
    # 如果文件不存在，返回空字符串（兼容旧行为）
    if "不存在" in result.error or "not found" in result.error.lower():
        return ""
    # 其他错误记录日志但返回空（避免崩溃）
    print(f"[WARN] _read_file: {result.error}")
    return ""


def _write_file(file_path: str, content: str) -> bool:
    """安全写入文件内容，返回是否成功"""
    result = safe_write_file(
        filepath=file_path,
        content=content,
        workspace_root=PROJECTS_DIR,
        max_bytes=10*1024*1024,  # 10 MB
        mkdir=True,
    )
    if not result.success:
        print(f"[WARN] _write_file: {result.error}")
    return result.success


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

                    frontmatter.update(updates)

                    new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
                    if not new_frontmatter.endswith('\n'):
                        new_frontmatter += '\n'
                    body = '\n'.join(lines[end_idx + 1:])
                    if body and not body.startswith('\n'):
                        body = '\n' + body
                    new_content = "---\n" + new_frontmatter + "---" + body
                    return new_content
                except Exception as e:
                    pass
    return content


# ==================== 项目管理工具 ====================

def create_project(project_name: str, goal_short: str, goal_long: str, discipline: str = "综合") -> str:
    """
    创建一个新的学习项目
    """
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
current_module_id: 0
current_challenge_id: 0
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
1. 创建第一个学习模块
2. 自动生成微挑战列表
3. 开始第一次脉冲学习

准备好开始了吗？"""


def list_projects() -> str:
    """列出所有学习项目"""
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


def get_project_status(project_name: str) -> str:
    """获取指定项目的详细状态"""
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

    # 获取当前模块信息
    current_module_id = frontmatter.get("current_module_id", 0)
    current_challenge_id = frontmatter.get("current_challenge_id", 0)

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

## 🎮 当前进度

- **当前模块**：{current_module_id if current_module_id > 0 else '无'}
- **当前挑战**：{current_challenge_id if current_challenge_id > 0 else '无'}

---

输入 'continue {project_name}' 继续学习！
"""

    return result


# ==================== 模块管理工具 ====================

def create_module(project_name: str, module_name: str, module_goal: str, estimated_time: int = 30) -> str:
    """在项目中创建一个新的学习模块"""
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

---

## 📚 学习记录

### 学习来源

### 学习内容

### 代码片段

### 截图/附件

### 疑问记录

---

## 🤖 检验任务

*Boss 挑战将在这里生成*

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
        "last_module": date_today,
        "current_module_id": module_id,
        "current_challenge_id": 0
    }
    new_index_content = _update_yaml_frontmatter(index_content, updates)
    _write_file(index_file, new_index_content)

    return f"""✅ 模块创建成功！

📚 项目：{project_name}
🎯 模块 {module_id}：{module_name}
⏱️ 预计时间：{estimated_time} 分钟

现在可以使用 AI 生成微挑战列表了！"""


def get_modules(project_name: str) -> str:
    """获取项目的所有模块列表"""
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


# ==================== 微挑战工具 ====================

def add_challenge(project_name: str, module_id: int, challenge_desc: str, 
                  estimated_time: int = 10, success_criteria: str = "", points: int = 10) -> str:
    """在模块中添加一个微挑战"""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。请先创建模块。"

    content = _read_file(module_file)

    challenges = []
    table_start = content.find("| 序号 | 挑战内容 |")
    if table_start > 0:
        table_end = len(content)
        sep_pos = content.find("|------|----------|", table_start)
        if sep_pos > 0:
            after_sep = sep_pos
            for i in range(sep_pos, min(sep_pos + 3000, len(content))):
                if content[i:i+2] == '\n\n':
                    table_end = i + 1
                    break

        table_content = content[table_start:table_end]
        lines = table_content.split('\n')

        for line in lines[2:]:
            if line.strip() and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6 and parts[1].isdigit():
                    challenges.append({
                        "id": int(parts[1]),
                        "desc": parts[2],
                        "time": parts[3],
                        "criteria": parts[4],
                        "status": parts[5],
                        "points": parts[6]
                    })

    # 添加新挑战
    new_id = len(challenges) + 1
    new_challenge = {
        "id": new_id,
        "desc": challenge_desc,
        "time": f"{estimated_time}分钟",
        "criteria": success_criteria if success_criteria else "手动标记完成",
        "status": "⏳ 待完成",
        "points": f"{points}分"
    }

    # 重新生成表格
    table_lines = [
        "| 序号 | 挑战内容 | 预计时间 | 成功标志 | 状态 | 分数 |",
        "|------|----------|----------|----------|------|------|"
    ]

    for challenge in challenges + [new_challenge]:
        table_lines.append(
            f"| {challenge['id']} | {challenge['desc']} | {challenge['time']} | {challenge['criteria']} | {challenge['status']} | {challenge['points']} |"
        )

    # 替换表格内容（使用上面已计算好的 table_end）
    if table_start > 0:
        new_content = content[:table_start] + "\n".join(table_lines) + "\n" + content[table_end:]
    else:
        list_section = "## 🎮 微挑战列表"
        if list_section in content:
            insert_pos = content.find(list_section) + len(list_section)
            new_content = content[:insert_pos] + "\n\n" + "\n".join(table_lines) + "\n" + content[insert_pos:]
        else:
            return "错误：无法找到微挑战列表位置"

    # 更新 frontmatter 中的 challenges_total
    frontmatter = _parse_yaml_frontmatter(new_content)
    updates = {"challenges_total": new_id}
    new_content = _update_yaml_frontmatter(new_content, updates)
    _write_file(module_file, new_content)

    return f"""✅ 微挑战添加成功！

📚 项目：{project_name}
🎯 模块 {module_id}
🎮 微挑战 {new_id}：{challenge_desc}
⏱️ 预计时间：{estimated_time} 分钟
💰 分数：{points} 分

当前模块共有 {new_id} 个微挑战。"""


def complete_challenge(project_name: str, module_id: int, challenge_id: int, notes: str = "", actual_time: int = 0) -> str:
    """完成一个微挑战
    
    Args:
        project_name: 项目名称
        module_id: 模块ID
        challenge_id: 挑战ID
        notes: 完成笔记
        actual_time: 实际耗时（分钟），可选
    """
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 解析表格
    challenges = []
    table_start = content.find("| 序号 | 挑战内容 |")
    if table_start > 0:
        table_end = len(content)
        sep_pos = content.find("|------|----------|", table_start)
        if sep_pos > 0:
            for i in range(sep_pos, min(sep_pos + 3000, len(content))):
                if content[i:i+2] == '\n\n':
                    table_end = i + 1
                    break

        table_content = content[table_start:table_end]
        lines = table_content.split('\n')

        for line in lines[2:]:
            if line.strip() and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7:
                    challenges.append({
                        "id": int(parts[1]) if parts[1].isdigit() else 0,
                        "desc": parts[2],
                        "time": parts[3],
                        "criteria": parts[4],
                        "status": parts[5],
                        "points": int(''.join(filter(str.isdigit, parts[6]))) if parts[6] else 10
                    })

    # 查找目标挑战
    target_challenge = None
    for challenge in challenges:
        if challenge["id"] == challenge_id:
            target_challenge = challenge
            break

    if not target_challenge:
        return f"微挑战 {challenge_id} 不存在。"

    if "✅" in target_challenge["status"]:
        return f"微挑战 {challenge_id} 已经完成了！"

    # 更新挑战状态
    earned_points = target_challenge["points"]

    # 重新生成表格
    table_lines = [
        "| 序号 | 挑战内容 | 预计时间 | 成功标志 | 状态 | 分数 |",
        "|------|----------|----------|----------|------|------|"
    ]

    for challenge in challenges:
        if challenge["id"] == challenge_id:
            challenge["status"] = "✅ 已完成"
        table_lines.append(
            f"| {challenge['id']} | {challenge['desc']} | {challenge['time']} | {challenge['criteria']} | {challenge['status']} | {challenge['points']}分 |"
        )

    # 替换表格内容（使用上面已计算好的 table_end）
    if table_start > 0:
        new_content = content[:table_start] + "\n".join(table_lines) + "\n" + content[table_end:]

    # 更新 frontmatter
    completed_count = frontmatter.get("challenges_completed", 0) + 1
    total_count = frontmatter.get("challenges_total", 0)
    current_score = frontmatter.get("score", 0) + earned_points

    # 连击计算
    current_combo = frontmatter.get("current_combo", 0) + 1
    max_combo = max(frontmatter.get("max_combo", 0), current_combo)
    combo_bonus = current_combo * 2
    total_earned = earned_points + combo_bonus

    # 时间统计
    total_time_spent = frontmatter.get("total_time_spent", 0) + actual_time

    updates = {
        "challenges_completed": completed_count,
        "score": current_score + total_earned,
        "current_combo": current_combo,
        "max_combo": max_combo,
        "status": "in_progress",
        "total_time_spent": total_time_spent
    }

    new_content = _update_yaml_frontmatter(new_content, updates)
    _write_file(module_file, new_content)

    # 更新项目文件
    index_file = os.path.join(project_dir, "_index.md")
    if os.path.exists(index_file):
        index_content = _read_file(index_file)
        index_frontmatter = _parse_yaml_frontmatter(index_content)
        
        total_score = index_frontmatter.get("total_score", 0) + total_earned
        index_updates = {
            "total_score": total_score,
            "current_combo": current_combo,
            "current_challenge_id": challenge_id + 1 if challenge_id < total_count else 0
        }
        new_index_content = _update_yaml_frontmatter(index_content, index_updates)
        _write_file(index_file, new_index_content)

    # 计算进度
    progress = int((completed_count / total_count * 100)) if total_count > 0 else 0

    # 生成进度条
    progress_bar_length = 20
    filled = int(progress_bar_length * progress / 100)
    progress_bar = "█" * filled + "░" * (progress_bar_length - filled)

    result = f"""✅ 恭喜！微挑战完成！

📚 项目：{project_name}
🎯 模块 {module_id}
🎮 微挑战 {challenge_id}：{target_challenge['desc']}

---

## 📊 本次得分

- **基础分数**：+{earned_points} 分
- **连击奖励**：+{combo_bonus} 分 🔥
- **总计获得**：+{total_earned} 分

## 📈 当前进度

```
{progress_bar} {progress}%
```

- **完成微挑战**：{completed_count} / {total_count}
- **模块总分**：{current_score + total_earned} 分
- **当前连击**：{current_combo} 🔥
- **最大连击**：{max_combo} 💪

"""

    # 时间统计显示
    if actual_time > 0:
        hours = actual_time // 60
        mins = actual_time % 60
        time_str = f"{hours}小时{mins}分钟" if hours > 0 else f"{mins}分钟"
        total_hours = total_time_spent // 60
        total_mins = total_time_spent % 60
        total_time_str = f"{total_hours}小时{total_mins}分钟" if total_hours > 0 else f"{total_mins}分钟"
        result += f"""## ⏱️ 时间统计

- **本次耗时**：{time_str}
- **累计耗时**：{total_time_str}

"""

    # 检查是否所有挑战都完成了
    if completed_count >= total_count and total_count > 0:
        result += (
            f"\n🎉 太棒了！所有微挑战已完成！\n"
            f"现在可以输入 'finish {project_name}' 完成脉冲，进入检验阶段！\n"
        )

    # 更新徽章系统
    try:
        from .badge_manager import get_badge_manager
        bm = get_badge_manager()
        stats = bm.user_badges["stats"]
        bm.update_stats(
            total_score=stats["total_score"] + total_earned,
            max_combo=max(stats["max_combo"], current_combo),
            total_challenges=stats["total_challenges"] + 1
        )
        new_badges = bm.check_unlocks()
        if new_badges:
            result += "\n🏅 **新解锁徽章：**\n"
            for badge in new_badges:
                result += f"  ✅ {badge['icon']} {badge['name']} - {badge['description']}\n"
    except Exception as e:
        print(f"[Badge] 更新失败: {e}")

    return result


def finish_module(project_name: str, module_id: int = None, task_description: str = "",
                  success_criteria: str = "", actual_time: int = 0) -> str:
    """完成一个模块（完成脉冲）
    
    流程：检查完成度 -> 生成检验任务 -> 更新文件 -> 输出游戏化反馈
    
    Args:
        project_name: 项目名称
        module_id: 模块ID（可选，默认当前模块）
        task_description: 检验任务描述（可选，自动生成）
        success_criteria: 成功标准（可选，自动生成）
        actual_time: 模块实际耗时（分钟）
    """
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")
    modules_dir = os.path.join(project_dir, "modules")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    index_content = _read_file(index_file)
    index_frontmatter = _parse_yaml_frontmatter(index_content)

    # 确定要完成的模块
    if module_id is None:
        module_id = index_frontmatter.get("current_module_id", 0)
    
    if module_id == 0:
        return "没有当前模块。请先创建模块或指定 module_id。"

    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")
    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 检查微挑战完成度
    completed = frontmatter.get("challenges_completed", 0)
    total = frontmatter.get("challenges_total", 0)

    if completed < total:
        return (f"模块 {module_id} 还有 {total - completed} 个微挑战未完成！\n"
                f"请先完成所有微挑战再 finish。当前进度：{completed}/{total}")

    # 如果 Boss 挑战已完成，直接返回
    if frontmatter.get("boss_task_status") == "completed":
        return f"模块 {module_id} 已经完成了！"

    # 检查是否已有 active 的 Boss 任务
    if frontmatter.get("boss_task_status") == "active":
        return (f"模块 {module_id} 已有进行中的检验任务！\n\n"
                f"检验任务：{frontmatter.get('boss_task_description', '综合检验')}\n"
                f"成功标准：{frontmatter.get('boss_task_criteria', '完成任务')}\n\n"
                f"完成检验任务：complete_boss_task('{project_name}', {module_id}, '你的完成总结')")

    # 计算模块总分
    module_score = frontmatter.get("score", 0)
    module_name = frontmatter.get("module_name", f"模块 {module_id}")
    discipline = index_frontmatter.get("discipline", "综合")
    
    # 时间统计
    total_time_spent = frontmatter.get("total_time_spent", 0) + actual_time
    hours = total_time_spent // 60
    mins = total_time_spent % 60
    time_str = f"{hours}小时{mins}分钟" if hours > 0 else f"{mins}分钟"

    # 自动生成检验任务（基于模块内容）
    if not task_description:
        task_description = _generate_exam_task(content, module_name, discipline)
    if not success_criteria:
        success_criteria = _generate_exam_criteria(content, discipline)

    # 生成检验任务（Boss 挑战）
    exam_points = 40  # 固定 40 分作为检验任务基础分
    
    updates = {
        "boss_task_status": "active",
        "boss_task_description": task_description,
        "boss_task_criteria": success_criteria,
        "boss_task_points": exam_points,
        "total_time_spent": total_time_spent,
        "status": "in_review"  # 正在检验状态
    }
    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(module_file, new_content)

    # 更新项目 index 文件
    index_updates = {
        "last_module": module_name,
        "last_finish": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_time_spent": index_frontmatter.get("total_time_spent", 0) + actual_time
    }
    new_index_content = _update_yaml_frontmatter(index_content, index_updates)
    _write_file(index_file, new_index_content)

    # 连击统计
    current_combo = index_frontmatter.get("current_combo", 0)
    max_combo = index_frontmatter.get("max_combo", 0)

    # 生成进度条
    progress_bar_length = 20
    full_bar = "=" * progress_bar_length

    result = f"""# 🎉 脉冲完成！

## 📚 {project_name} / {module_name}

所有微挑战已完成！正在进入检验阶段...

---

## 📊 模块完成报告

```
{'='*50}
  PULSE COMPLETE
{'='*50}
```

| 指标 | 数值 |
|------|------|
| 完成微挑战 | {completed}/{total} |
| 微挑战得分 | {module_score} 分 |
| 实际耗时 | {time_str} |
| 当前连击 | {current_combo} 🔥 |
| 最大连击 | {max_combo} 💪 |

---

## 🎯 检验任务（Boss 挑战）

**任务描述**：
> {task_description}

**成功标准**：
> {success_criteria}

**奖励分数**：{exam_points} 分（Boss 双倍加成！）

---

## 📋 下一步

请完成任务后，使用以下命令完成检验：

```
complete_boss_task("{project_name}", {module_id}, "你的完成总结")
```

或者直接在 Web UI / CLI 中输入：

`完成Boss {project_name} {module_id} 我的总结`
"""

    # 更新徽章系统
    try:
        from .badge_manager import get_badge_manager
        bm = get_badge_manager()
        stats = bm.user_badges["stats"]
        bm.update_stats(
            total_score=stats["total_score"],
            max_combo=max(stats["max_combo"], current_combo),
            modules_completed=stats["modules_completed"] + 1
        )
        new_badges = bm.check_unlocks()
        if new_badges:
            result += "\n## 🏅 新解锁徽章\n\n"
            for badge in new_badges:
                result += f"- {badge['icon']} **{badge['name']}** - {badge['description']}\n"
    except Exception as e:
        print(f"[Badge] 更新失败: {e}")

    return result


def _generate_exam_task(module_content: str, module_name: str, discipline: str) -> str:
    """根据模块内容自动生成检验任务描述"""
    # 提取模块目标的关键词
    goal = ""
    for line in module_content.split('\n'):
        if 'goal' in line.lower() and ':' in line:
            goal = line.split(':', 1)[1].strip().strip('"').strip("'")
            break
    
    if not goal:
        goal = module_name
    
    exam_templates = {
        "编程": f"综合运用本次学习的编程技能，独立完成一个实战项目。可以是：自动化脚本、数据处理工具、或任意与目标相关的程序。",
        "数学": f"独立解答3-5道综合应用题，涵盖本次学习的核心知识点。请写出完整解题过程。",
        "语言": f"完成一篇{goal}相关的写作任务，或进行一次模拟对话练习，展示综合运用能力。",
        "综合": f"完成一个综合性任务：总结本次学习的所有要点，并能够向他人清晰讲解核心概念。"
    }
    
    return exam_templates.get(discipline, exam_templates["综合"])


def _generate_exam_criteria(module_content: str, discipline: str) -> str:
    """根据模块内容自动生成成功标准"""
    criteria_templates = {
        "编程": "代码能正常运行，实现了预期功能，有适当的注释和错误处理。",
        "数学": "解题过程完整，答案正确，对核心概念有正确理解。",
        "语言": "表达清晰流畅，用词准确，语法正确，能够有效传达信息。",
        "综合": "能用自己的话准确描述核心概念，完成度80%以上，有个人思考和总结。"
    }
    
    return criteria_templates.get(discipline, criteria_templates["综合"])


def get_current_challenge(project_name: str) -> Dict[str, Any]:
    """获取当前项目和模块的下一个挑战"""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")
    
    if not os.path.exists(index_file):
        return {"error": f"项目 {project_name} 不存在"}
    
    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)
    
    current_module_id = frontmatter.get("current_module_id", 0)
    
    if current_module_id == 0:
        return {"error": "没有当前模块，请先创建模块"}
    
    # 获取模块信息
    module_file = os.path.join(project_dir, "modules", f"module_{current_module_id:02d}.md")
    if not os.path.exists(module_file):
        return {"error": f"模块 {current_module_id} 文件不存在"}
    
    module_content = _read_file(module_file)
    module_frontmatter = _parse_yaml_frontmatter(module_content)
    
    # 查找下一个未完成的挑战
    challenges_completed = module_frontmatter.get("challenges_completed", 0)
    challenges_total = module_frontmatter.get("challenges_total", 0)
    
    next_challenge_id = challenges_completed + 1 if challenges_completed < challenges_total else 0
    
    return {
        "project_name": project_name,
        "module_id": current_module_id,
        "module_name": module_frontmatter.get("module_name", ""),
        "challenge_id": next_challenge_id,
        "challenges_completed": challenges_completed,
        "challenges_total": challenges_total,
        "progress": f"{challenges_completed}/{challenges_total}"
    }


# ==================== Boss 挑战工具 ====================

def generate_boss_task(project_name: str, module_id: int, task_description: str = "", 
                       success_criteria: str = "", points: int = 20) -> str:
    """生成 Boss 挑战"""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    # 检查是否所有微挑战都完成了
    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)
    
    completed = frontmatter.get("challenges_completed", 0)
    total = frontmatter.get("challenges_total", 0)
    
    if completed < total:
        return f"请先完成所有微挑战 ({completed}/{total})，才能生成 Boss 挑战！"

    # 更新 Boss 挑战状态
    updates = {
        "boss_task_status": "active",
        "boss_task_description": task_description or "综合检验任务",
        "boss_task_criteria": success_criteria or "完成检验任务",
        "boss_task_points": points * 2  # 双倍分数
    }
    
    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(module_file, new_content)

    return f"""🎉 Boss 挑战已生成！

📚 项目：{project_name}
🎯 模块 {module_id}

## 🤖 检验任务

**任务内容**：{task_description or "综合检验任务"}
**成功标准**：{success_criteria or "完成检验任务"}
**奖励分数**：{points * 2} 分（双倍！）

完成 Boss 挑战后，使用 complete_boss_task 完成任务！"""


def complete_boss_task(project_name: str, module_id: int, summary: str) -> str:
    """完成 Boss 挑战"""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    if frontmatter.get("boss_task_status") != "active":
        return "Boss 挑战尚未生成！"

    # 计算奖励
    base_points = frontmatter.get("boss_task_points", 40)
    module_score = frontmatter.get("score", 0) + base_points

    # 更新模块状态
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates = {
        "boss_task_status": "completed",
        "status": "completed",
        "end_time": now,
        "score": module_score
    }

    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(module_file, new_content)

    # 更新徽章系统
    try:
        from .badge_manager import get_badge_manager
        bm = get_badge_manager()
        stats = bm.user_badges["stats"]
        bm.update_stats(
            total_score=stats["total_score"] + base_points,
            boss_completed=stats["boss_completed"] + 1
        )
        new_badges = bm.check_unlocks()
        if new_badges:
            badge_names = ", ".join([b["name"] for b in new_badges])
            return f"🎉 Boss 挑战完成！获得 {base_points} 分！\n🏅 解锁新徽章: {badge_names}"
    except Exception as e:
        print(f"[Badge] 更新失败: {e}")

    # 更新项目总分
    index_file = os.path.join(project_dir, "_index.md")
    if os.path.exists(index_file):
        index_content = _read_file(index_file)
        index_frontmatter = _parse_yaml_frontmatter(index_content)

        total_score = index_frontmatter.get("total_score", 0) + base_points
        
        index_updates = {
            "total_score": total_score,
            "current_combo": 0  # 重置连击
        }
        
        new_index_content = _update_yaml_frontmatter(index_content, index_updates)
        _write_file(index_file, new_index_content)

    return f"""🎊 Boss 挑战完成！

📚 项目：{project_name}
🎯 模块 {module_id}

## 📊 获得奖励

- **Boss 挑战分数**：+{base_points} 分

## 📈 总计

- **模块总分**：{module_score} 分
- **项目总分**：{total_score} 分

---

🎉 恭喜完成整个模块！你已完成一个完整的脉冲学习！
"""


def get_learning_stats(project_name: str = None) -> str:
    """获取学习统计数据
    
    Args:
        project_name: 项目名称，可选。如果不提供则显示所有项目的统计
    """
    from .badge_manager import get_badge_manager
    
    bm = get_badge_manager()
    stats = bm.user_badges["stats"]
    
    result = """# 📊 学习统计

---

## 🏆 总体数据

"""
    
    # 总体统计
    result += f"""- **总分**：{stats.get('total_score', 0)} 分
- **最大连击**：{stats.get('max_combo', 0)} 🔥
- **完成挑战**：{stats.get('total_challenges', 0)} 个
- **完成项目**：{stats.get('completed_projects', 0)} 个
- **Boss 挑战**：{stats.get('boss_completed', 0)} 个

"""
    
    # 已解锁徽章
    unlocked = bm.get_unlocked_badges()
    if unlocked:
        result += "## 🎖️ 已解锁徽章\n\n"
        for badge in unlocked:
            unlock_date = bm.user_badges["unlock_dates"].get(badge["id"], "")
            result += f"- {badge['icon']} **{badge['name']}** - {badge['description']}\n"
            if unlock_date:
                result += f"  - 解锁时间：{unlock_date[:10]}\n"
        result += "\n"
    
    # 下一个徽章进度
    progress = bm.get_progress_to_next()
    if "percent" in progress and progress["percent"] < 100:
        result += f"""## 🎯 下一个徽章

{progress.get('message', '继续加油！')}

"""
        if "badge" in progress:
            badge = progress["badge"]
            result += f"- {badge['icon']} **{badge['name']}** - {badge['description']}\n"
            if "current" in progress and "target" in progress:
                bar_length = 20
                filled = int(bar_length * progress["percent"] / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                result += f"- 进度：`{bar}` {progress['percent']}% ({progress['current']}/{progress['target']})\n"
    
    # 项目时间统计
    if project_name:
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        index_file = os.path.join(project_dir, "_index.md")
        
        if os.path.exists(index_file):
            content = _read_file(index_file)
            frontmatter = _parse_yaml_frontmatter(content)
            
            total_time = frontmatter.get("total_time_spent", 0)
            if total_time > 0:
                hours = total_time // 60
                mins = total_time % 60
                time_str = f"{hours}小时{mins}分钟" if hours > 0 else f"{mins}分钟"
                result += f"""\n---\n\n## ⏱️ 项目时间统计

- **项目**：{project_name}
- **累计耗时**：{time_str}

"""
    
    return result
