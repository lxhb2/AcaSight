import os
import json
from datetime import datetime
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from .file_manager import (
    PROJECTS_DIR,
    _read_file,
    _parse_yaml_frontmatter
)


@tool
def get_learning_history(project_name: str, days: int = 7) -> str:
    """
    获取指定天数内的学习历史记录

    Args:
        project_name: 项目名称
        days: 查询最近几天的历史（默认7天）

    Returns:
        学习历史记录
    """
    ctx = request_context.get() or new_context(method="get_learning_history")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")

    if not os.path.exists(modules_dir):
        return f"项目 '{project_name}' 还没有创建任何模块。"

    now = datetime.now()
    history_entries = []

    # 获取所有模块文件
    module_files = sorted([f for f in os.listdir(modules_dir) if f.startswith("module_") and f.endswith(".md")])

    for module_file in module_files:
        file_path = os.path.join(modules_dir, module_file)
        content = _read_file(file_path)
        frontmatter = _parse_yaml_frontmatter(content)

        module_id = frontmatter.get("module_id", 0)
        module_name = frontmatter.get("module_name", "未命名")
        status = frontmatter.get("status", "unknown")
        score = frontmatter.get("score", 0)
        start_time = frontmatter.get("start_time", "")
        end_time = frontmatter.get("end_time", "")

        # 提取学习记录（微挑战完成记录）
        learning_records = []
        record_section = "### 微挑战"
        while record_section in content:
            record_start = content.find(record_section)
            record_end = content.find("\n###", record_start + len(record_section))
            if record_end == -1:
                record_end = content.find("\n##", record_start + len(record_section))
            if record_end == -1:
                record_end = len(content)

            record_content = content[record_start:record_end]
            learning_records.append(record_content)

            # 查找下一个记录
            next_start = content.find("### 微挑战", record_end)
            if next_start > record_end:
                record_section = content[next_start:next_start + len(record_section)]
                content = content[next_start:]
            else:
                break

        # 如果模块在查询时间范围内，添加到历史
        if start_time:
            try:
                start_date = datetime.strptime(start_time.split()[0], "%Y-%m-%d")
                days_diff = (now - start_date).days
                if days_diff <= days:
                    history_entries.append({
                        "module_id": module_id,
                        "module_name": module_name,
                        "status": status,
                        "score": score,
                        "start_time": start_time,
                        "end_time": end_time,
                        "records": learning_records
                    })
            except:
                pass

    if not history_entries:
        return f"最近 {days} 天内没有学习记录。"

    # 生成历史报告
    result = f"""# 📚 {project_name} - 学习历史

📅 查询范围：最近 {days} 天
📊 记录数：{len(history_entries)} 条

---

"""

    for entry in history_entries:
        status_emoji = {
            "planned": "📋",
            "in_progress": "🔄",
            "completed": "✅"
        }.get(entry["status"], "❓")

        result += f"""## {entry['module_id']}. {entry['module_name']} {status_emoji}

- **状态**：{entry['status']}
- **开始时间**：{entry['start_time']}
- **完成时间**：{entry['end_time'] or '进行中'}
- **获得分数**：{entry['score']} 分

"""

        if entry['records']:
            result += "### 📝 学习记录\n\n"
            for record in entry['records'][:2]:  # 只显示前2条记录
                result += f"{record}\n\n"

        result += "---\n\n"

    return result


@tool
def get_learning_statistics(project_name: str) -> str:
    """
    获取学习统计数据

    Args:
        project_name: 项目名称

    Returns:
        学习统计数据
    """
    ctx = request_context.get() or new_context(method="get_learning_statistics")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")

    if not os.path.exists(project_dir):
        return f"项目 '{project_name}' 不存在。"

    # 读取项目信息
    index_file = os.path.join(project_dir, "_index.md")
    if os.path.exists(index_file):
        index_content = _read_file(index_file)
        index_frontmatter = _parse_yaml_frontmatter(index_content)
    else:
        index_frontmatter = {}

    # 统计模块数据
    total_modules = 0
    completed_modules = 0
    in_progress_modules = 0
    total_challenges = 0
    completed_challenges = 0
    total_study_time = 0
    total_score = 0
    max_combo = 0

    if os.path.exists(modules_dir):
        module_files = [f for f in os.listdir(modules_dir) if f.startswith("module_") and f.endswith(".md")]

        for module_file in module_files:
            file_path = os.path.join(modules_dir, module_file)
            content = _read_file(file_path)
            frontmatter = _parse_yaml_frontmatter(content)

            total_modules += 1
            total_study_time += frontmatter.get("estimated_time", 0)
            total_score += frontmatter.get("score", 0)

            if frontmatter.get("status") == "completed":
                completed_modules += 1
            elif frontmatter.get("status") == "in_progress":
                in_progress_modules += 1

            completed_challenges += frontmatter.get("challenges_completed", 0)
            total_challenges += frontmatter.get("challenges_total", 0)

    # 从项目信息中获取最大连击
    max_combo = index_frontmatter.get("max_combo", 0)

    # 计算统计数据
    completion_rate = int((completed_modules / total_modules * 100)) if total_modules > 0 else 0
    challenge_completion_rate = int((completed_challenges / total_challenges * 100)) if total_challenges > 0 else 0

    result = f"""# 📊 {project_name} - 学习统计

## 📈 总体数据

| 指标 | 数据 |
|------|------|
| **总模块数** | {total_modules} 个 |
| **已完成模块** | {completed_modules} 个 |
| **进行中模块** | {in_progress_modules} 个 |
| **模块完成率** | {completion_rate}% |
| **总学习时长** | {total_study_time} 分钟 |
| **总获得分数** | {total_score} 分 |
| **最大连击** | {max_combo} 🔥 |

## 🎮 微挑战统计

| 指标 | 数据 |
|------|------|
| **总微挑战数** | {total_challenges} 个 |
| **已完成挑战** | {completed_challenges} 个 |
| **挑战完成率** | {challenge_completion_rate}% |

## 🏆 成就

"""

    # 添加成就
    achievements = []

    if total_modules >= 1:
        achievements.append("🥉 **初学者**：完成第一个学习模块")
    if total_modules >= 3:
        achievements.append("🥈 **进阶者**：完成3个学习模块")
    if total_modules >= 5:
        achievements.append("🥇 **专家**：完成5个学习模块")
    if max_combo >= 5:
        achievements.append("🔥 **连击大师**：达成5连击")
    if max_combo >= 10:
        achievements.append("💎 **连击王者**：达成10连击")
    if total_score >= 100:
        achievements.append("⭐ **百分达人**：累计获得100分")
    if total_score >= 500:
        achievements.append("🌟 **千分王者**：累计获得500分")

    if achievements:
        for achievement in achievements:
            result += f"- {achievement}\n"
    else:
        result += "暂无成就，继续努力！💪\n"

    result += f"""

---

💡 提示：保持连击，完成更多挑战，解锁更多成就！
"""

    return result


@tool
def get_daily_summary(project_name: str) -> str:
    """
    获取今日学习摘要

    Args:
        project_name: 项目名称

    Returns:
        今日学习摘要
    """
    ctx = request_context.get() or new_context(method="get_daily_summary")

    return get_learning_history(project_name, days=1)
