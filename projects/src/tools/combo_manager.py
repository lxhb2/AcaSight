import os
import json
from datetime import datetime
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
def reset_combo(project_name: str, reason: str = "") -> str:
    """
    重置项目的连击数

    Args:
        project_name: 项目名称
        reason: 重置原因（可选）

    Returns:
        重置结果
    """
    ctx = request_context.get() or new_context(method="reset_combo")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)

    current_combo = frontmatter.get("current_combo", 0)
    max_combo = frontmatter.get("max_combo", 0)

    if current_combo == 0:
        return f"项目 '{project_name}' 的连击数已经是0了，无需重置。"

    # 更新 frontmatter
    updates = {"current_combo": 0}
    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(index_file, new_content)

    result = f"""⏸️ 连击已重置！

📚 项目：{project_name}
🔥 之前连击：{current_combo}
📊 最大连击：{max_combo}（保持不变）

"""

    if reason:
        result += f"重置原因：{reason}\n"

    result += """

---

别灰心！连击重置是一个新的开始。💪

继续努力，再次创造新的连击记录！🚀
"""

    return result


@tool
def pause_combo(project_name: str, hours: int = 24) -> str:
    """
    暂停连击（防止因休息而中断）

    Args:
        project_name: 项目名称
        hours: 暂停时长（小时），默认24小时

    Returns:
        暂停结果
    """
    ctx = request_context.get() or new_context(method="pause_combo")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)

    current_combo = frontmatter.get("current_combo", 0)

    if current_combo == 0:
        return f"当前没有连击，无需暂停。"

    # 设置暂停时间
    now = datetime.now()
    pause_until = now.timestamp() + (hours * 3600)

    # 更新 frontmatter
    updates = {
        "combo_paused": True,
        "combo_pause_until": pause_until
    }
    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(index_file, new_content)

    return f"""⏸️ 连击已暂停保护！

📚 项目：{project_name}
🔥 当前连击：{current_combo}
⏰ 保护时长：{hours} 小时
🛡️ 连击状态：已冻结

---

在接下来 {hours} 小时内，你的连击数将被保护，不会因为休息而中断。

休息是为了走更远的路！😊
"""


@tool
def resume_combo(project_name: str) -> str:
    """
    恢复连击（结束暂停保护）

    Args:
        project_name: 项目名称

    Returns:
        恢复结果
    """
    ctx = request_context.get() or new_context(method="resume_combo")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)

    is_paused = frontmatter.get("combo_paused", False)

    if not is_paused:
        return "连击没有被暂停保护，无需恢复。"

    # 更新 frontmatter
    updates = {
        "combo_paused": False,
        "combo_pause_until": 0
    }
    new_content = _update_yaml_frontmatter(content, updates)
    _write_file(index_file, new_content)

    return f"""▶️ 连击保护已解除！

📚 项目：{project_name}
🔥 当前连击：{frontmatter.get('current_combo', 0)}
✅ 保护状态：已解除

---

连击保护已结束，继续完成挑战来增加连击数吧！🚀
"""


@tool
def get_combo_status(project_name: str) -> str:
    """
    获取项目的连击状态

    Args:
        project_name: 项目名称

    Returns:
        连击状态信息
    """
    ctx = request_context.get() or new_context(method="get_combo_status")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    content = _read_file(index_file)
    frontmatter = _parse_yaml_frontmatter(content)

    current_combo = frontmatter.get("current_combo", 0)
    max_combo = frontmatter.get("max_combo", 0)
    is_paused = frontmatter.get("combo_paused", False)

    result = f"""# 🔥 {project_name} - 连击状态

## 📊 当前数据

- **当前连击**：{current_combo} 🔥
- **最大连击**：{max_combo} 💪
- **保护状态**：{'🛡️ 已暂停保护' if is_paused else '✅ 正常'}

---

"""

    if is_paused:
        pause_until = frontmatter.get("combo_pause_until", 0)
        if pause_until > 0:
            from datetime import datetime
            resume_time = datetime.fromtimestamp(pause_until)
            result += f"### 🛡️ 保护详情\n\n连击保护将持续到：{resume_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n在保护期间，连击数不会因为休息而中断。\n\n"

    if current_combo > 0:
        result += f"### 🎯 保持连击\n\n你已经达成 **{current_combo} 连击**！继续保持，创造新的记录！\n\n"
        if current_combo < max_combo:
            result += f"距离最大连击还差 {max_combo - current_combo} 个挑战！💪\n"
    else:
        result += "### 🚀 开始挑战\n\n当前没有连击，完成一个挑战开始新的连击记录！\n"

    # 连击奖励提示
    if current_combo > 0:
        bonus = current_combo * 2
        result += f"\n### 💰 连击奖励\n\n当前每个额外挑战可获得 **+{bonus} 分** 连击奖励！\n"

    result += "\n---\n\n💡 提示：使用 `reset_combo` 可以重置连击，使用 `pause_combo` 可以暂停保护。"

    return result
