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
def add_learning_resource(project_name: str, resource_type: str, title: str, url: str = "", description: str = "") -> str:
    """
    添加学习资源到资源库

    Args:
        project_name: 项目名称
        resource_type: 资源类型（教程、文档、视频、书籍等）
        title: 资源标题
        url: 资源链接（可选）
        description: 资源描述（可选）

    Returns:
        添加结果
    """
    ctx = request_context.get() or new_context(method="add_learning_resource")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    resources_file = os.path.join(project_dir, "resources.md")

    if not os.path.exists(resources_file):
        return f"项目 '{project_name}' 的资源库不存在。"

    content = _read_file(resources_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 根据资源类型选择插入位置
    resource_sections = {
        "教程": "### 教程与文档",
        "文档": "### 教程与文档",
        "视频": "### 视频课程",
        "书籍": "### 书籍推荐",
        "链接": "### 参考链接"
    }

    section_title = resource_sections.get(resource_type, "### 其他资源")

    # 构造资源条目
    resource_entry = f"""
- [{title}]({url}) - {description} *({now})*
""" if url else f"""
- {title} - {description} *({now})*
"""

    # 在对应章节后插入
    if section_title in content:
        section_start = content.find(section_title)
        section_end = content.find("\n##", section_start + len(section_title))
        if section_end == -1:
            section_end = content.find("\n---", section_start + len(section_title))

        if section_end > section_start:
            new_content = content[:section_end] + resource_entry + content[section_end:]
            _write_file(resources_file, new_content)

            return f"""✅ 学习资源已添加！

📚 项目：{project_name}
📖 类型：{resource_type}
📝 标题：{title}
🔗 链接：{url if url else '无'}
📄 描述：{description}

---

资源已保存到资源库，随时可以查看！📚
"""

    # 如果找不到对应章节，添加到末尾
    new_content = content.rstrip() + f"\n\n## {resource_type}\n\n{resource_entry}"
    _write_file(resources_file, new_content)

    return f"""✅ 学习资源已添加！

📚 项目：{project_name}
📖 类型：{resource_type}
📝 标题：{title}
🔗 链接：{url if url else '无'}
📄 描述：{description}

---

资源已保存到资源库！📚
"""


@tool
def add_code_snippet(project_name: str, title: str, code: str, language: str = "python", description: str = "") -> str:
    """
    添加代码片段到资源库

    Args:
        project_name: 项目名称
        title: 代码片段标题
        code: 代码内容
        language: 编程语言（默认python）
        description: 代码描述（可选）

    Returns:
        添加结果
    """
    ctx = request_context.get() or new_context(method="add_code_snippet")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    resources_file = os.path.join(project_dir, "resources.md")

    if not os.path.exists(resources_file):
        return f"项目 '{project_name}' 的资源库不存在。"

    content = _read_file(resources_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构造代码片段条目
    snippet_entry = f"""
### {title}
*{description}* - 添加于 {now}

```{language}
{code}
```

"""

    # 查找"代码片段"章节
    code_section = "### 代码片段"
    if code_section in content:
        section_start = content.find(code_section)
        section_end = content.find("\n##", section_start + len(code_section))
        if section_end == -1:
            section_end = content.find("\n---", section_start + len(code_section))

        if section_end > section_start:
            new_content = content[:section_end] + snippet_entry + content[section_end:]
            _write_file(resources_file, new_content)

            return f"""✅ 代码片段已添加！

📚 项目：{project_name}
📝 标题：{title}
💻 语言：{language}
📄 描述：{description}

---

代码片段已保存到资源库！👨‍💻
"""

    # 如果找不到章节，添加到末尾
    new_content = content.rstrip() + f"\n\n{code_section}\n\n{snippet_entry}"
    _write_file(resources_file, new_content)

    return f"""✅ 代码片段已添加！

📚 项目：{project_name}
📝 标题：{title}
💻 语言：{language}
📄 描述：{description}

---

代码片段已保存到资源库！👨‍💻
"""


@tool
def get_resources(project_name: str, resource_type: str = "") -> str:
    """
    获取项目资源库内容

    Args:
        project_name: 项目名称
        resource_type: 资源类型过滤（可选）

    Returns:
        资源库内容
    """
    ctx = request_context.get() or new_context(method="get_resources")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    resources_file = os.path.join(project_dir, "resources.md")

    if not os.path.exists(resources_file):
        return f"项目 '{project_name}' 的资源库不存在或为空。"

    content = _read_file(resources_file)

    if resource_type:
        # 过滤特定类型的资源
        section_title = f"### {resource_type}"
        if section_title in content:
            section_start = content.find(section_title)
            section_end = content.find("\n##", section_start + len(section_title))
            if section_end == -1:
                section_end = content.find("\n---", section_start + len(section_title))

            filtered_content = content[section_start:section_end] if section_end > section_start else ""

            return f"""# 📚 {project_name} - {resource_type}

{filtered_content}
"""

        return f"资源库中没有类型为 '{resource_type}' 的资源。"

    return f"""# 📚 {project_name} - 资源库

{content}
"""


@tool
def add_note(project_name: str, note_content: str, note_type: str = "普通") -> str:
    """
    添加学习笔记到项目

    Args:
        project_name: 项目名称
        note_content: 笔记内容
        note_type: 笔记类型（普通、重要、疑问、灵感）

    Returns:
        添加结果
    """
    ctx = request_context.get() or new_context(method="add_note")

    project_dir = os.path.join(PROJECTS_DIR, project_name)
    index_file = os.path.join(project_dir, "_index.md")

    if not os.path.exists(index_file):
        return f"项目 '{project_name}' 不存在。"

    content = _read_file(index_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 根据笔记类型选择图标
    type_icons = {
        "普通": "📝",
        "重要": "⭐",
        "疑问": "❓",
        "灵感": "💡"
    }
    icon = type_icons.get(note_type, "📝")

    # 构造笔记条目
    note_entry = f"""
### {icon} {now} - {note_type}

{note_content}

---

"""

    # 查找"学习笔记"章节
    notes_section = "## 📝 学习笔记"
    if notes_section in content:
        section_start = content.find(notes_section)
        section_end = content.find("\n---", section_start)

        if section_end > section_start:
            new_content = content[:section_end] + note_entry + content[section_end:]
            _write_file(index_file, new_content)

            return f"""✅ 学习笔记已添加！

📚 项目：{project_name}
📝 类型：{note_type} {icon}
⏰ 时间：{now}

---

笔记已保存！📚
"""

    # 如果找不到章节，添加到末尾
    new_content = content.rstrip() + f"\n\n{notes_section}\n\n{note_entry}"
    _write_file(index_file, new_content)

    return f"""✅ 学习笔记已添加！

📚 项目：{project_name}
📝 类型：{note_type} {icon}
⏰ 时间：{now}

---

笔记已保存！📚
"""
