# -*- coding: utf-8 -*-
"""
Pulse Learning System - Chainlit UI v2.0
支持：交互按钮、Markdown 渲染、模型切换、AI 选项自动检测
"""
import os
import sys
import re
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

PROJECTS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECTS_DIR)
sys.path.insert(0, os.path.join(PROJECTS_DIR, "src"))

from tools.pulse_tools import (
    create_project, list_projects, get_project_status,
    create_module, get_modules,
    add_challenge, complete_challenge, finish_module,
)

from tools.qmd_tools import (
    qmd_search, qmd_get, qmd_list_collections, qmd_status as qmd_status_tool,
    qmd_add_collection, qmd_list_files, qmd_get_lines,
)

from utils.llm_client import (
    create_client, is_online, get_active_provider,
    check_ollama_available, check_lmstudio_available, load_model_config,
)
from utils.prompt_builder import build_pulse_learning_system_prompt, build_pulse_learning_system_prompt_light

try:
    import chainlit as cl
except ImportError:
    print("⚠️  Chainlit 未安装，请运行: pip install chainlit")
    sys.exit(1)


PULSE_VAULT_DIR = r"D:\四季如歌\新建文件夹\脉冲学习"

_session_state = {}
_state_lock = threading.Lock()


def get_session_state() -> Dict:
    session_id = getattr(cl.context, "session_id", "default")
    with _state_lock:
        if session_id not in _session_state:
            _session_state[session_id] = {
                "current_project": None,
                "current_module": None,
                "use_light_prompt": True,
                "force_mode": "auto",
                "history": [],
                "last_action": None,
                "pending_options": None,
            }
        return _session_state[session_id]


def save_session_state(state: Dict):
    session_id = getattr(cl.context, "session_id", "default")
    with _state_lock:
        _session_state[session_id] = state


# ==================== 模型状态检测 ====================

def get_model_status() -> Dict[str, Any]:
    """获取当前模型状态"""
    try:
        online = is_online()
    except Exception:
        online = False
    try:
        ollama = check_ollama_available()
    except Exception:
        ollama = False
    try:
        lmstudio = check_lmstudio_available()
    except Exception:
        lmstudio = False

    config = load_model_config()
    providers = config.get("providers", {})

    active = get_active_provider()
    provider_name = active.get("provider", "unknown")
    model_name = active.get("model", "unknown")

    return {
        "online": online,
        "ollama": ollama,
        "lmstudio": lmstudio,
        "provider": provider_name,
        "model": model_name,
        "providers": providers,
    }


def build_status_bar(force_mode: str = "auto") -> str:
    """构建状态栏信息"""
    status = get_model_status()

    if force_mode == "auto":
        mode_name = "自动检测"
        current_model = f"{status['provider']}/{status['model']}"
    elif force_mode == "online":
        mode_name = "☁️ 云端"
        cfg = status["providers"].get("online", {})
        current_model = cfg.get("model", status["model"])
    elif force_mode == "ollama":
        mode_name = "🦙 Ollama"
        cfg = status["providers"].get("offline_ollama", {})
        current_model = cfg.get("model", status["model"])
    elif force_mode == "lmstudio":
        mode_name = "🖥️ LM Studio"
        cfg = status["providers"].get("offline_lmstudio", {})
        current_model = cfg.get("model", status["model"])
    else:
        mode_name = "自动检测"
        current_model = f"{status['provider']}/{status['model']}"

    online_icon = "🟢" if status["online"] else "🔴"
    ollama_icon = "🟢" if status["ollama"] else "⚪"
    lmstudio_icon = "🟢" if status["lmstudio"] else "⚪"

    return (
        f"**模型状态**  |  "
        f"网络: {online_icon}  |  "
        f"Ollama: {ollama_icon}  |  "
        f"LM Studio: {lmstudio_icon}  |  "
        f"当前: {mode_name} `{current_model}`"
    )


# ==================== AI 选项自动检测 ====================

def extract_options_from_response(content: str) -> List[Dict]:
    """
    从 AI 响应中自动检测选项并提取
    支持格式：
    1. 数字列表: 1. xxx  2. xxx  3. xxx
    2. 字母列表: A. xxx  B. xxx  C. xxx
    3. 方括号: [1] xxx  [2] xxx
    4. 中文数字: 一、xxx  二、xxx
    """
    options = []

    # 模式1: 数字列表 "1. xxx" 或 "1、xxx"
    pattern_num = re.compile(r'(?:^|\n)\s*(\d+)[\.、．]\s*(.+?)(?=\n\s*\d+[\.、．]|\n\n|\n$|$)', re.DOTALL)
    matches = pattern_num.findall(content)
    if len(matches) >= 2:
        for num, text in matches[:6]:
            text = text.strip().rstrip('。.，,')
            if len(text) > 30:
                text = text[:30] + "..."
            options.append({
                "label": f"{num}. {text}",
                "value": text,
                "description": f"选项 {num}",
            })
        return options

    # 模式2: 字母列表 "A. xxx" 或 "A、xxx"
    pattern_alpha = re.compile(r'(?:^|\n)\s*([A-D])[\.、．]\s*(.+?)(?=\n\s*[A-D][\.、．]|\n\n|\n$|$)', re.IGNORECASE)
    matches = pattern_alpha.findall(content)
    if len(matches) >= 2:
        for letter, text in matches[:6]:
            text = text.strip().rstrip('。.，,')
            if len(text) > 30:
                text = text[:30] + "..."
            options.append({
                "label": f"{letter}. {text}",
                "value": text,
                "description": f"选项 {letter}",
            })
        return options

    # 模式3: 方括号 "[1] xxx"
    pattern_bracket = re.compile(r'(?:^|\n)\s*\[(\d+)\]\s*(.+?)(?=\n\s*\[\d+\]|\n\n|\n$|$)', re.DOTALL)
    matches = pattern_bracket.findall(content)
    if len(matches) >= 2:
        for num, text in matches[:6]:
            text = text.strip().rstrip('。.，,')
            if len(text) > 30:
                text = text[:30] + "..."
            options.append({
                "label": f"[{num}] {text}",
                "value": text,
                "description": f"选项 {num}",
            })
        return options

    return options


# ==================== 工具调用检测 ====================

def check_and_execute_tool(message: str) -> Optional[Dict]:
    """检查用户消息是否需要执行工具"""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ['创建项目', '新项目', '开始项目']):
        match = re.search(r'创建项目[：:]?\s*(.+?)(?:，|,|。|\n|$)', message)
        if match:
            project_name = match.group(1).split('，', 1)[0].strip()
            result = create_project(project_name, f"{project_name} 学习项目")
            return {'tool': 'create_project', 'result': result}

    if any(kw in msg_lower for kw in ['列出项目', '所有项目', '查看项目', '我的项目']):
        result = list_projects()
        return {'tool': 'list_projects', 'result': result}

    if any(kw in msg_lower for kw in ['项目状态', '进度']):
        state = get_session_state()
        project_name = state.get("current_project")
        if not project_name:
            match = re.search(r'(?:项目)?[：:]?\s*["\']?([^"\']+?)["\']?(?:的)?(?:状态|进度)', message)
            if match:
                project_name = match.group(1).strip()
        if project_name:
            result = get_project_status(project_name)
            return {'tool': 'get_project_status', 'result': result}

    if any(kw in msg_lower for kw in ['搜索文档', '搜索知识', 'qmd搜索']):
        query = message
        for prefix in ['搜索文档', '搜索知识', 'qmd搜索', '搜索']:
            if prefix in msg_lower:
                idx = msg_lower.index(prefix)
                query = message[idx + len(prefix):].strip().strip('：: ')
                break
        if query:
            result = qmd_search(query)
            return {'tool': 'qmd_search', 'result': result}

    if any(kw in msg_lower for kw in ['文档集合', '列出集合']):
        result = qmd_list_collections()
        return {'tool': 'qmd_list_collections', 'result': result}

    if any(kw in msg_lower for kw in ['索引状态', 'qmd状态']):
        result = qmd_status_tool()
        return {'tool': 'qmd_status', 'result': result}

    if any(kw in msg_lower for kw in ['清空历史', '清除历史', '清除记录']):
        return {'tool': 'clear_history', 'result': '历史记录已清空', 'action': 'clear_history'}

    if any(kw in msg_lower for kw in ['查看历史', '历史记录', '对话历史']):
        return {'tool': 'show_history', 'result': '查看历史记录', 'action': 'show_history'}

    return None


# ==================== 选项按钮系统 ====================

async def send_with_options(message: str, options: List[Dict]):
    """发送消息并附带选项按钮"""
    state = get_session_state()
    state["pending_options"] = options
    save_session_state(state)

    actions = []
    for opt in options:
        actions.append(
            cl.Action(
                name="select_option",
                payload={"value": opt["value"], "label": opt["label"]},
                label=opt["label"],
                tooltip=opt.get("description", ""),
            )
        )

    await cl.Message(content=message, actions=actions).send()


@cl.action_callback("select_option")
async def on_select_option(action: cl.Action):
    """处理用户点击选项按钮"""
    state = get_session_state()
    selected_value = action.payload.get("value", "")
    selected_label = action.payload.get("label", "")

    state["pending_options"] = None
    state["last_action"] = selected_value
    save_session_state(state)

    await cl.Message(content=f"👉 你选择了: **{selected_label}**").send()
    await process_user_input(selected_value)


# ==================== 用户输入处理 ====================

async def process_user_input(message: str):
    """处理用户输入（来自按钮或文本）"""
    tool_action = check_and_execute_tool(message)

    if tool_action:
        if tool_action.get('action') == 'show_history':
            await show_history()
            return
        elif tool_action.get('action') == 'clear_history':
            await clear_history()
            return

        await cl.Message(
            content=f"🔧 **执行工具**: `{tool_action['tool']}`\n\n{tool_action['result']}",
        ).send()
        return

    await send_to_llm(message)


async def send_to_llm(message: str):
    """发送消息到 LLM 并处理响应（流式输出）"""
    state = get_session_state()
    force_mode = state.get("force_mode", "auto")

    try:
        client = create_client(force_mode=force_mode if force_mode != "auto" else None)
    except Exception as e:
        await cl.Message(content=f"❌ LLM 连接失败: {e}").send()
        return

    if state.get("use_light_prompt", True):
        prompt = build_pulse_learning_system_prompt_light(language="中文")
    else:
        prompt = build_pulse_learning_system_prompt(language="中文")

    # 限制消息历史数量，避免本地模型过慢
    history = state.get("history", [])
    if len(history) > 12:
        history = history[-12:]

    messages = [{"role": "system", "content": prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    msg = cl.Message(content="")
    await msg.send()

    try:
        is_offline = client.provider in ("ollama", "lmstudio")

        if is_offline:
            # 本地模型使用流式输出，提升感知速度
            content = await _stream_llm_response(client, messages, msg)
        else:
            # 云端模型使用非流式
            response = client.chat(messages=messages, temperature=client.temperature)
            content = response["message"]["content"]
            msg.content = content
            await msg.update()

        state["history"].append({"role": "user", "content": message})
        state["history"].append({"role": "assistant", "content": content})
        if len(state["history"]) > 12:
            state["history"] = state["history"][-12:]
        save_session_state(state)

        # 自动检测 AI 响应中的选项
        options = extract_options_from_response(content)
        if options and len(options) >= 2:
            state["pending_options"] = options
            save_session_state(state)

            actions = []
            for opt in options:
                actions.append(
                    cl.Action(
                        name="select_option",
                        payload={"value": opt["value"], "label": opt["label"]},
                        label=opt["label"],
                        tooltip=opt.get("description", ""),
                    )
                )
            await cl.Message(
                content="👆 **请选择一个选项继续：**",
                actions=actions,
            ).send()

    except Exception as e:
        msg.content = f"❌ LLM 请求失败: {e}"
        await msg.update()


async def _stream_llm_response(client, messages: list, msg) -> str:
    """
    流式调用 LLM（仅本地模型）
    支持 Ollama 和 LM Studio (OpenAI 兼容) 两种 API 格式
    """
    import requests
    temperature = client.temperature

    full_content = ""

    if client._is_openai_compat:
        # LM Studio: OpenAI 兼容 API
        headers = {"Content-Type": "application/json"}
        if client.api_key:
            headers["Authorization"] = f"Bearer {client.api_key}"

        payload = {
            "model": client.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        resp = requests.post(client._chat_url, json=payload, headers=headers,
                             timeout=client.timeout, stream=True)
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8").strip()
            if not line_str.startswith("data: "):
                continue
            data_str = line_str[6:]
            if data_str == "[DONE]":
                break
            try:
                import json as _json
                data = _json.loads(data_str)
                delta = data.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    full_content += token
                    await msg.stream_token(token)
            except Exception:
                continue

    else:
        # Ollama 原生 API
        payload = {
            "model": client.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        resp = requests.post(client._chat_url, json=payload,
                             timeout=client.timeout, stream=True)
        resp.raise_for_status()

        import json as _json
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                data = _json.loads(line.decode("utf-8"))
                token = data.get("message", {}).get("content", "")
                if token:
                    full_content += token
                    await msg.stream_token(token)
                if data.get("done", False):
                    break
            except Exception:
                continue

    return full_content


# ==================== 模型切换 ====================

@cl.action_callback("switch_model")
async def on_switch_model(action: cl.Action):
    """处理模型切换按钮"""
    target = action.payload.get("target", "auto")
    state = get_session_state()
    state["force_mode"] = target
    save_session_state(state)

    mode_names = {
        "auto": "自动检测",
        "online": "云端 (SiliconFlow)",
        "ollama": "本地 Ollama",
        "lmstudio": "本地 LM Studio",
    }
    mode_name = mode_names.get(target, target)

    await cl.Message(
        content=f"🔄 **模型已切换**: {mode_name}\n\n{build_status_bar(target)}"
    ).send()


# ==================== Chainlit 事件处理 ====================

@cl.on_chat_start
async def start():
    """聊天开始时的初始化"""
    state = get_session_state()

    welcome = (
        "# 👋 欢迎使用脉冲学习系统\n\n"
        "我是你的脉冲学习助手，可以帮你：\n"
        "- 📚 拆解学习目标为微挑战\n"
        "- 🎮 提供即时分数、连击、进度反馈\n"
        "- 🔍 搜索你的知识库\n"
        "- 📊 跟踪学习进度\n\n"
        f"{build_status_bar(state.get('force_mode', 'auto'))}\n\n"
        "告诉我你想学什么，或者点击下方按钮开始！"
    )

    await cl.Message(
        content=welcome,
        actions=[
            cl.Action(name="quick_action", payload={"action": "new_project"}, label="🚀 新建项目"),
            cl.Action(name="quick_action", payload={"action": "list_projects"}, label="📋 查看项目"),
            cl.Action(name="quick_action", payload={"action": "search"}, label="🔍 搜索文档"),
            cl.Action(name="quick_action", payload={"action": "history"}, label="📜 历史记录"),
            cl.Action(name="quick_action", payload={"action": "help"}, label="❓ 帮助"),
        ],
    ).send()

    # 模型切换按钮
    model_actions = [
        cl.Action(name="switch_model", payload={"target": "auto"}, label="🔄 自动"),
        cl.Action(name="switch_model", payload={"target": "online"}, label="☁️ 云端"),
        cl.Action(name="switch_model", payload={"target": "ollama"}, label="🦙 Ollama"),
        cl.Action(name="switch_model", payload={"target": "lmstudio"}, label="🖥️ LM Studio"),
    ]
    await cl.Message(
        content="**🎛️ 模型切换**（点击切换 AI 模型）",
        actions=model_actions,
    ).send()


def _format_history_for_display(history: List[Dict]) -> str:
    """格式化历史对话用于显示"""
    if not history:
        return "📭 **暂无历史对话**\n\n当前会话还没有开始对话记录。"

    result = "# 📜 **历史对话记录**\n\n"
    result += f"共 **{len(history)}** 条对话记录\n\n"
    result += "---\n\n"

    for i, msg in enumerate(history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            role_display = "👤 **你**"
        elif role == "assistant":
            role_display = "🤖 **AI**"
        else:
            role_display = f"**{role}**"

        content_preview = content[:150] + "..." if len(content) > 150 else content
        content_preview = content_preview.replace("\n", " ")

        result += f"**{i}. {role_display}**\n> {content_preview}\n\n"

    result += "---\n\n💡 提示：发送 `清空历史` 可以清除当前会话的历史记录"

    return result


async def show_history():
    """显示当前会话的历史对话"""
    state = get_session_state()
    history = state.get("history", [])

    formatted_history = _format_history_for_display(history)

    await cl.Message(content=formatted_history).send()


async def clear_history():
    """清空当前会话的历史对话"""
    state = get_session_state()
    state["history"] = []
    save_session_state(state)

    await cl.Message(
        content="✅ **历史记录已清空**\n\n当前会话的所有对话记录已被清除。"
    ).send()


@cl.action_callback("quick_action")
async def on_quick_action(action: cl.Action):
    """处理快速操作按钮"""
    action_type = action.payload.get("action", "")

    if action_type == "new_project":
        await cl.Message(
            content="你想创建什么学习项目？请输入项目名称和目标：\n\n例如：`创建项目 Python爬虫实战`",
        ).send()
    elif action_type == "list_projects":
        result = list_projects()
        await cl.Message(content=result).send()
    elif action_type == "search":
        await cl.Message(
            content="请输入搜索关键词：\n\n例如：`搜索 Python基础`",
        ).send()
    elif action_type == "history":
        await show_history()
    elif action_type == "clear_history":
        await clear_history()
    elif action_type == "help":
        help_text = (
            "# 📖 使用指南\n\n"
            "## 常用命令\n"
            "| 命令 | 说明 |\n"
            "|------|------|\n"
            "| `创建项目 名称` | 创建新学习项目 |\n"
            "| `列出项目` | 查看所有项目 |\n"
            "| `项目状态` | 查看当前项目进度 |\n"
            "| `搜索 关键词` | 搜索知识库文档 |\n"
            "| `文档集合` | 查看文档集合列表 |\n\n"
            "## 交互功能\n"
            "- 🎛️ **模型切换**：点击顶部模型按钮切换 AI 模型\n"
            "- 👆 **选项按钮**：AI 给出选项时自动生成可点击按钮\n"
            "- 📝 **Markdown 渲染**：所有消息支持 Markdown 格式\n"
            "- 📜 **历史记录**：查看当前会话的对话历史\n\n"
            "## 数据目录\n"
            f"- 📁 学习数据：`{PULSE_VAULT_DIR}`\n"
            "- 每个学习方向一个文件夹\n"
            "- 每个方向有 `_index.md` 总述文件"
        )
        await cl.Message(content=help_text).send()


@cl.on_message
async def main(message: cl.Message):
    """处理用户消息"""
    user_text = message.content.strip()
    await process_user_input(user_text)


if __name__ == "__main__":
    print("✅ Chainlit UI v2.0 已加载")
    print("🌐 访问: http://localhost:8000")
    print("📝 运行: python -m chainlit run chainlit_ui.py -w")
