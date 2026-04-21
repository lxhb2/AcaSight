"""
记忆系统工具
提供学习日志和记忆管理功能
"""
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.integrated_system import get_integrated_system


@tool
def view_learning_logs(days: int = 1) -> str:
    """
    查看学习日志

    Args:
        days: 查看最近几天的日志，默认1天

    Returns:
        学习日志内容
    """
    ctx = request_context.get() or new_context(method="view_learning_logs")

    try:
        system = get_integrated_system()
        memory = system.memory

        result = f"""# 📝 最近 {days} 天的学习日志

"""

        today = memory.get_today_logs()
        if today:
            result += "## 今日学习记录\n\n"
            for log in today[-10:]:  # 显示最后10条
                result += f"- {log}\n"
        else:
            result += "今天还没有学习记录。开始学习吧！\n"

        return result

    except Exception as e:
        return f"查看学习日志失败: {str(e)}"


@tool
def distill_learning_memory(days: int = 7) -> str:
    """
    蒸馏学习日志到记忆索引

    Args:
        days: 蒸馏最近几天的日志，默认7天

    Returns:
        蒸馏结果
    """
    ctx = request_context.get() or new_context(method="distill_learning_memory")

    try:
        system = get_integrated_system()
        result = system.distill_memory(days)

        return f"""✅ {result}

学习日志已整理并保存到 MEMORY.md，方便后续查阅！
"""
    except Exception as e:
        return f"蒸馏学习记忆失败: {str(e)}"


@tool
def search_learning_history(keyword: str, days: int = 7) -> str:
    """
    搜索学习历史

    Args:
        keyword: 搜索关键词
        days: 搜索最近几天的记录，默认7天

    Returns:
        搜索结果
    """
    ctx = request_context.get() or new_context(method="search_learning_history")

    try:
        system = get_integrated_system()
        results = system.search_logs(keyword, days)

        if not results:
            return f"在最近 {days} 天的学习日志中没有找到包含 '{keyword}' 的记录。"

        result = f"""# 🔍 搜索结果: "{keyword}"

在最近 {days} 天的日志中找到 {len(results)} 条记录：

---

"""

        for item in results:
            result += f"""## {item['date']}
- 日志文件: `{item['path']}`
- 匹配次数: {item['matches']} 次

---

"""

        return result

    except Exception as e:
        return f"搜索学习历史失败: {str(e)}"


@tool
def view_memory_index() -> str:
    """
    查看记忆索引（MEMORY.md）

    Returns:
        记忆索引内容
    """
    ctx = request_context.get() or new_context(method="view_memory_index")

    try:
        system = get_integrated_system()
        summary = system.get_memory_summary()

        return f"""# 🧠 学习记忆索引

{summary}

---

*这是自动维护的学习记忆索引，包含了学习过程中的重要信息。*
"""
    except Exception as e:
        return f"查看记忆索引失败: {str(e)}"


@tool
def log_custom_note(note_content: str, note_type: str = "普通", project: str = "") -> str:
    """
    记录自定义学习笔记

    Args:
        note_content: 笔记内容
        note_type: 笔记类型（普通、重要、疑问、灵感）
        project: 项目名称（可选）

    Returns:
        记录结果
    """
    ctx = request_context.get() or new_context(method="log_custom_note")

    try:
        system = get_integrated_system()
        project_name = project if project else "未指定项目"

        system.logger.log_note(note_content, note_type, project_name)

        type_emoji = {
            "普通": "📝",
            "重要": "⭐",
            "疑问": "❓",
            "灵感": "💡"
        }.get(note_type, "📝")

        return f"""✅ 学习笔记已记录！

📚 项目: {project_name}
📝 类型: {note_type} {type_emoji}
📄 内容: {note_content}

---

笔记已保存到今日学习日志中！
"""
    except Exception as e:
        return f"记录笔记失败: {str(e)}"
