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
def generate_boss_task(project_name: str, module_id: int, task_description: str, success_criteria: str, difficulty: str = "中等") -> str:
    """
    为模块生成 Boss 挑战任务（检验任务），双倍评分

    Args:
        project_name: 项目名称
        module_id: 模块编号
        task_description: Boss 任务描述
        success_criteria: 成功标准（如何判断任务完成）
        difficulty: 难度等级（简单/中等/困难），默认为中等

    Returns:
        Boss 任务创建结果
    """
    ctx = request_context.get() or new_context(method="generate_boss_task")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 检查是否已经有 Boss 任务
    boss_section = "## 🤖 检验任务以及任务汇报"
    if "### 🎯 Boss 挑战" in content:
        return f"模块 {module_id} 已经有 Boss 挑战了！请先完成现有挑战。"

    # 根据 difficulty 设置分数（双倍基础分）
    difficulty_scores = {
        "简单": 20,
        "中等": 40,
        "困难": 60
    }
    base_points = difficulty_scores.get(difficulty, 40)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 生成 Boss 任务内容
    boss_task_content = f"""
### 🎯 Boss 挑战

**难度**：{difficulty}
**分数**：{base_points} 分（双倍奖励！💎）
**发布时间**：{now}

#### 📋 任务描述
{task_description}

#### ✅ 成功标准
{success_criteria}

#### 📤 任务汇报
*完成后在此处填写任务汇报内容*

- **完成时间**：
- **实现方案**：
- **遇到的问题**：
- **解决方案**：
- **代码/链接**：

#### 📊 评分状态
- **状态**：⏳ 待完成
- **评分**：未评分
- **得分**：{base_points} 分（双倍奖励）
"""

    # 更新 frontmatter
    updates = {
        "boss_task_status": "pending",
        "boss_task_points": base_points
    }
    new_content = _update_yaml_frontmatter(content, updates)

    # 替换检验任务部分
    if boss_section in new_content:
        boss_start = new_content.find(boss_section)
        insert_pos = boss_start + len(boss_section)
        new_content = new_content[:insert_pos] + "\n\n" + boss_task_content + "\n" + new_content[insert_pos:]

    _write_file(module_file, new_content)

    return f"""🎯 Boss 挑战已生成！

📚 项目：{project_name}
🎯 模块 {module_id}

## 🤖 Boss 挑战详情

**难度**：{difficulty}
**💎 双倍奖励**：{base_points} 分
**任务描述**：{task_description}

### 成功标准
{success_criteria}

---

这是一次综合性的检验任务，需要你运用本模块学到的所有知识！

完成后使用 `complete_boss_task` 提交任务汇报，获得双倍分数奖励！🚀
"""


@tool
def complete_boss_task(project_name: str, module_id: int, report_content: str, code_snippet: str = "") -> str:
    """
    完成 Boss 挑战任务，提交任务汇报

    Args:
        project_name: 项目名称
        module_id: 模块编号
        report_content: 任务汇报内容（包括实现方案、遇到的问题、解决方案等）
        code_snippet: 代码片段（可选）

    Returns:
        完成结果和分数
    """
    ctx = request_context.get() or new_context(method="complete_boss_task")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    # 检查 Boss 任务状态
    boss_status = frontmatter.get("boss_task_status", "pending")
    if boss_status == "completed":
        return "Boss 挑战已经完成了！"

    if boss_status == "pending":
        # 获取 Boss 任务分数
        boss_points = frontmatter.get("boss_task_points", 40)

        # 更新 frontmatter
        current_score = frontmatter.get("score", 0)
        new_score = current_score + boss_points

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        updates = {
            "boss_task_status": "completed",
            "boss_task_completed_time": now,
            "score": new_score
        }
        new_content = _update_yaml_frontmatter(content, updates)

        # 更新任务汇报部分
        report_section = "#### 📤 任务汇报"
        if report_section in new_content:
            report_start = new_content.find(report_section)
            report_end = new_content.find("#### 📊 评分状态", report_start)

            if report_end > report_start:
                new_report_content = f"""#### 📤 任务汇报
- **完成时间**：{now}
- **实现方案**：
{report_content}
"""

                if code_snippet:
                    new_report_content += f"""
- **代码/链接**：
```python
{code_snippet}
```
"""

                new_report_content += """
- **遇到的问题**：（如果有）
- **解决方案**：（如果有）
"""

                new_content = new_content[:report_start] + new_report_content + new_content[report_end:]

        # 更新评分状态
        score_section = "#### 📊 评分状态"
        if score_section in new_content:
            score_start = new_content.find(score_section)
            score_end = new_content.find("\n\n", score_start)
            if score_end == -1:
                score_end = new_content.find("\n---", score_start)

            new_score_section = f"""#### 📊 评分状态
- **状态**：✅ 已完成
- **评分**：满分
- **得分**：+{boss_points} 分 💎
- **完成时间**：{now}
"""

            if score_end > score_start:
                new_content = new_content[:score_start] + new_score_section + new_content[score_end:]

        _write_file(module_file, new_content)

        # 更新项目总分
        index_file = os.path.join(project_dir, "_index.md")
        if os.path.exists(index_file):
            index_content = _read_file(index_file)
            index_frontmatter = _parse_yaml_frontmatter(index_content)
            project_total = index_frontmatter.get("total_score", 0)
            new_project_total = project_total + boss_points

            index_updates = {"total_score": new_project_total}
            new_index_content = _update_yaml_frontmatter(index_content, index_updates)
            _write_file(index_file, new_index_content)

        result = f"""🎉 Boss 挑战完成！恭喜通关！

📚 项目：{project_name}
🎯 模块 {module_id}
💎 获得分数：+{boss_points} 分（双倍奖励！）

---

## 📊 本次 Boss 挑战

**难度**：挑战成功！
**实现方案**：
{report_content}
"""

        if code_snippet:
            result += f"""

**代码片段**：
```python
{code_snippet}
```
"""

        result += f"""

## 🏆 模块最终数据

- **模块总分**：{new_score} 分
- **项目总分**：{new_project_total} 分
- **Boss 挑战**：✅ 已完成

---

太棒了！你已经成功完成了这个模块的所有挑战，包括 Boss 挑战！

这就是脉冲学习闭环的完整流程！🎊

准备好开始下一个模块了吗？
"""

        return result

    return "Boss 挑战状态异常，请检查模块状态。"


@tool
def get_boss_task(project_name: str, module_id: int) -> str:
    """
    获取模块的 Boss 挑战详情

    Args:
        project_name: 项目名称
        module_id: 模块编号

    Returns:
        Boss 挑战详情
    """
    ctx = request_context.get() or new_context(method="get_boss_task")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    modules_dir = os.path.join(project_dir, "modules")
    module_file = os.path.join(modules_dir, f"module_{module_id:02d}.md")

    if not os.path.exists(module_file):
        return f"模块 {module_id} 不存在。"

    content = _read_file(module_file)
    frontmatter = _parse_yaml_frontmatter(content)

    boss_status = frontmatter.get("boss_task_status", "pending")
    boss_points = frontmatter.get("boss_task_points", 40)

    if boss_status == "pending":
        # 查找 Boss 任务内容
        boss_section_start = content.find("### 🎯 Boss 挑战")
        if boss_section_start > 0:
            boss_section_end = content.find("#### 📤 任务汇报", boss_section_start)
            if boss_section_end == -1:
                boss_section_end = content.find("\n####", boss_section_start + 1)

            if boss_section_end > boss_section_start:
                boss_content = content[boss_section_start:boss_section_end].strip()

                result = f"""# 🤖 Boss 挑战（模块 {module_id}）

💎 双倍奖励：{boss_points} 分

{boss_content}

---

准备好接受挑战了吗？使用 `complete_boss_task` 提交任务汇报！
"""
                return result

        return f"模块 {module_id} 还没有生成 Boss 挑战。"

    elif boss_status == "completed":
        boss_completed_time = frontmatter.get("boss_task_completed_time", "未知")
        return f"""# 🤖 Boss 挑战（模块 {module_id}）

✅ **已完成**

- **完成时间**：{boss_completed_time}
- **获得分数**：+{boss_points} 分 💎

---

Boss 挑战已成功完成！🎉
"""

    else:
        return f"Boss 挑战状态：{boss_status}"
