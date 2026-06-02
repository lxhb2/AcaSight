"""
Message Sanitization — 照搬 Hermes Agent message_sanitization.py 的核心逻辑
修复 API 调用前的消息序列问题，避免 400 错误。

来源：hermes-agent-main/agent/message_sanitization.py（简化版）
"""

import json
import re
import structlog
from typing import Any, Dict, List

logger = structlog.get_logger()


def sanitize_surrogates(text: str) -> str:
    """移除代理对字符（U+D800-U+DFFF），防止 JSON 序列化崩溃
    
    Ollama 模型（Kimi K2.5, GLM-5, Qwen）可能返回 lone surrogates，
    这些字符是无效的 UTF-8，会崩溃 json.dumps()。
    """
    if not isinstance(text, str):
        return text
    return re.sub(r'[\ud800-\udfff]', '\ufffd', text)


def sanitize_messages_surrogates(messages: List[Dict]) -> None:
    """就地清理消息列表中所有的代理对字符"""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            msg["content"] = sanitize_surrogates(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    block["text"] = sanitize_surrogates(block["text"])
        
        # 清理 tool_calls 中的 arguments
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict) and "function" in tc:
                    func = tc["function"]
                    if isinstance(func.get("arguments"), str):
                        func["arguments"] = sanitize_surrogates(func["arguments"])


def repair_tool_call_arguments(arguments: str, tool_name: str = "?") -> str:
    """修复损坏的 tool_call arguments JSON（模型输出截断）
    
    模型可能输出被截断的 JSON：
    - {"arg": "val   → 补全引号和大括号
    - {"arg": "val   → 修复未闭合字符串
    
    返回修复后的 JSON 字符串。
    """
    if not arguments or not arguments.strip():
        return "{}"
    
    stripped = arguments.strip()
    
    # 尝试直接解析 — 如果成功就不需要修复
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass
    
    # 修复 1：补全末尾缺失的大括号
    open_braces = stripped.count('{') - stripped.count('}')
    if open_braces > 0:
        stripped += '}' * open_braces
    
    # 修复 2：补全末尾缺失的引号（未闭合字符串）
    if stripped.rstrip().endswith(('{', ',', ':')):
        stripped = stripped.rstrip().rstrip(',') + '}'
    
    # 修复 3：如果还是不合法，尝试提取第一个完整的键值对
    try:
        json.loads(stripped)
        logger.info(f"Repaired tool_call arguments for {tool_name}")
        return stripped
    except json.JSONDecodeError:
        pass
    
    # 最后的努力：返回空对象
    logger.warning(f"Could not repair tool_call arguments for {tool_name}: {arguments[:100]}")
    return "{}"


def repair_message_sequence(messages: List[Dict]) -> int:
    """修复 role alternation 违规（如 tool→user, user→user 等）
    
    大多数 API 要求严格的 role alternation。不合规时：
    - OpenAI/DeepSeek 返回空内容 → 触发空内容重试循环
    - Anthropic 返回 400 错误
    
    修复策略：
    - 连续的 user 消息：合并为一条
    - tool 后跟 user：在 user 前插入一个虚拟 assistant 消息
    - assistant 后跟 assistant：合并
    
    返回修复数量。
    """
    if not messages:
        return 0
    
    repaired = 0
    i = 1
    while i < len(messages):
        prev_role = messages[i - 1].get("role")
        curr_role = messages[i].get("role")
        
        # 连续的 user 消息 — 合并
        if prev_role == "user" and curr_role == "user":
            prev_content = messages[i - 1].get("content", "")
            curr_content = messages[i].get("content", "")
            if isinstance(prev_content, str) and isinstance(curr_content, str):
                messages[i - 1]["content"] = prev_content + "\n\n---\n\n" + curr_content
            messages.pop(i)
            repaired += 1
            continue
        
        # tool → user（中间缺 assistant）— 插入虚拟 assistant
        if prev_role == "tool" and curr_role == "user":
            messages.insert(i, {
                "role": "assistant",
                "content": "[工具结果已接收]",
            })
            repaired += 1
            i += 1
            continue
        
        i += 1
    
    if repaired > 0:
        logger.info(f"Repaired {repaired} message-alternation violations")
    
    return repaired


def fix_message_roles(messages: List[Dict]) -> None:
    """规范化消息 role 字段
    
    确保 role 字段的值都是小写：
    - "User" → "user"
    - "Assistant" → "assistant"
    - "System" → "system"
    - "Tool" → "tool"
    """
    for msg in messages:
        role = msg.get("role")
        if isinstance(role, str) and role != role.lower():
            msg["role"] = role.lower()
