import os
import json
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from .file_manager import (
    PROJECTS_DIR,
    _read_file,
    _write_file,
    _parse_yaml_frontmatter,
    _update_yaml_frontmatter
)


@tool
def add_challenge(project_name: str, module_id: int, challenge_desc: str, estimated_time: int = 10, success_criteria: str = "", points: int = 10) -> str:
    """
    在模块中添加一个微挑战

    Args:
        project_name: 项目名称
        module_id: 模块编号
        challenge_desc: 挑战内容描述
        estimated_time: 预计时间（分钟），默认 10 分钟
        success_criteria: 成功标志（如何判断挑战完成）
        points: 分数，默认 10 分

    Returns:
        添加结果信息
    """
    ctx = request_context.get() or new_context(method="add_challenge")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。请先创建模块。"

    content = _read_file(module_file)

    # 解析表格中的微挑战
    challenges = []
    table_start = content.find("| 序号 | 挑战内容 |")
    if table_start > 0:
        table_end = content.find("\n\n", table_start)
        if table_end == -1:
            table_end = len(content)

        table_content = content[table_start:table_end]
        lines = table_content.split('\n')

        # 跳过表头和分隔符
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

    # 替换表格内容
    if table_start > 0:
        table_end = content.find("\n\n", table_start)
        if table_end == -1:
            table_end = len(content)

        new_content = content[:table_start] + "\n".join(table_lines) + "\n" + content[table_end:]
    else:
        # 如果没有找到表格，在微挑战列表标题后添加
        list_section = "## 🎮 微挑战列表"
        if list_section in content:
            insert_pos = content.find(list_section) + len(list_section)
            new_content = content[:insert_pos] + "\n\n" + "\n".join(table_lines) + "\n" + content[insert_pos:]
        else:
            return "错误：无法找到微挑战列表位置"

    _write_file(module_file, new_content)

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

当前模块共有 {new_id} 个微挑战。

继续添加更多挑战，还是开始学习？"""


@tool
def complete_challenge(project_name: str, module_id: int, challenge_id: int, notes: str = "") -> str:
    """
    完成一个微挑战

    Args:
        project_name: 项目名称
        module_id: 模块编号
        challenge_id: 微挑战编号
        notes: 完成时的笔记或备注（可选）

    Returns:
        完成结果信息和分数
    """
    ctx = request_context.get() or new_context(method="complete_challenge")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 解析表格中的微挑战
    challenges = []
    table_start = content.find("| 序号 | 挑战内容 |")
    if table_start > 0:
        table_end = content.find("\n\n", table_start)
        if table_end == -1:
            table_end = len(content)

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

    # 替换表格内容
    if table_start > 0:
        table_end = content.find("\n\n", table_start)
        if table_end == -1:
            table_end = len(content)

        new_content = content[:table_start] + "\n".join(table_lines) + "\n" + content[table_end:]

    # 更新 frontmatter
    completed_count = frontmatter.get("challenges_completed", 0) + 1
    total_count = frontmatter.get("challenges_total", 0)
    current_score = frontmatter.get("score", 0) + earned_points

    # 更新连击
    current_combo = frontmatter.get("current_combo", 0) + 1
    max_combo = max(frontmatter.get("max_combo", 0), current_combo)
    combo_bonus = current_combo * 2  # 连击奖励：每个连击额外加2分

    total_earned = earned_points + combo_bonus
    final_score = current_score + total_earned - earned_points  # 修正计算

    updates = {
        "challenges_completed": completed_count,
        "score": final_score,
        "current_combo": current_combo,
        "max_combo": max_combo,
        "status": "in_progress"
    }

    new_content = _update_yaml_frontmatter(new_content, updates)
    _write_file(module_file, new_content)

    # 添加学习记录
    if notes:
        learning_record_section = "## 📚 学习记录"
        if learning_record_section in new_content:
            insert_pos = new_content.find(learning_record_section) + len(learning_record_section)
            record_entry = f"""

### 微挑战 {challenge_id} 完成记录 ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

**内容**：{target_challenge['desc']}
**获得分数**：{earned_points} 分
**连击奖励**：+{combo_bonus} 分
**总获得**：{total_earned} 分
**笔记**：{notes}

"""
            new_content = new_content[:insert_pos] + record_entry + new_content[insert_pos:]
            _write_file(module_file, new_content)

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
- **模块总分**：{final_score} 分
- **当前连击**：{current_combo} 🔥
- **最大连击**：{max_combo} 💪

---

继续保持连击！下一个挑战是什么？
"""

    # 检查是否所有挑战都完成了
    if completed_count >= total_count and total_count > 0:
        result += f"""

🎉 太棒了！所有微挑战都已完成！

准备好完成 **Boss 挑战**了吗？完成检验任务将获得双倍分数奖励！
"""

    return result


@tool
def complete_module(project_name: str, module_id: int, summary: str, achievements: str = "", next_steps: str = "") -> str:
    """
    完成一个模块，生成学习报告

    Args:
        project_name: 项目名称
        module_id: 模块编号
        summary: 学习总结
        achievements: 达成的成果（可选）
        next_steps: 下一步建议（可选）

    Returns:
        完成结果和报告
    """
    ctx = request_context.get() or new_context(method="complete_module")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 检查模块状态
    if frontmatter.get("status") == "completed":
        return f"模块 {module_id} 已经完成了！"

    # 更新模块状态
    now = datetime.now()
    date_now = now.strftime("%Y-%m-%d %H:%M:%S")
    date_today = now.strftime("%Y-%m-%d")

    updates = {
        "status": "completed",
        "end_time": date_now
    }

    # 如果没有开始时间，设置为现在
    if not frontmatter.get("start_time"):
        updates["start_time"] = date_now

    new_content = _update_yaml_frontmatter(content, updates)

    # 更新学习报告部分
    report_section = "## 📈 本次学习报告"

    # 计算完成度
    completed = frontmatter.get("challenges_completed", 0)
    total = frontmatter.get("challenges_total", 0)
    completion_rate = int((completed / total * 100)) if total > 0 else 0

    report_content = f"""
## 📈 本次学习报告

- **完成度**：{completion_rate}%
- **完成时间**：{date_now}
- **学习总结**：
{summary}
"""

    if achievements:
        report_content += f"""
- **主要成果**：
{achievements}
"""

    if next_steps:
        report_content += f"""
- **下次建议**：
{next_steps}
"""

    report_content += f"""
---

🎉 恭喜完成模块 {module_id}！
获得分数：{frontmatter.get('score', 0)} 分

"""

    # 替换学习报告部分
    if report_section in new_content:
        report_start = new_content.find(report_section)
        report_end = new_content.find("\n---", report_start)
        if report_end == -1:
            report_end = len(new_content)

        new_content = new_content[:report_start] + report_content + new_content[report_end:]
    else:
        # 在末尾添加
        new_content += "\n" + report_content

    _write_file(module_file, new_content)

    # 更新项目总分
    index_file = os.path.join(project_dir, "_index.md")
    if os.path.exists(index_file):
        index_content = _read_file(index_file)
        index_frontmatter = _parse_yaml_frontmatter(index_content)

        # 重置连击
        module_score = frontmatter.get("score", 0)
        total_score = index_frontmatter.get("total_score", 0) + module_score
        current_combo = 0  # 完成模块后重置连击

        index_updates = {
            "total_score": total_score,
            "current_combo": current_combo,
            "last_module": date_today
        }

        new_index_content = _update_yaml_frontmatter(index_content, index_updates)
        _write_file(index_file, new_index_content)

    result = f"""🎉 模块完成！

📚 项目：{project_name}
🎯 模块 {module_id} 完成

## 📊 学习数据

- **完成度**：{completion_rate}%
- **完成微挑战**：{completed} / {total}
- **模块分数**：{frontmatter.get('score', 0)} 分
- **项目总分**：{total_score} 分

## 📝 学习报告

{summary}
"""

    if achievements:
        result += f"\n### 🏆 主要成果\n{achievements}\n"

    if next_steps:
        result += f"\n### 🚀 下一步建议\n{next_steps}\n"

    result += f"""

---

太棒了！你已经完成了一个完整的学习脉冲！

准备好开始下一个模块了吗？还是先休息一下？
"""

    return result
