"""
OpenClaw Response Parser

解析 OpenClaw Gateway 返回的响应数据。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("pulse_learning.openclaw_parser")


def parse_tool_response(response: Dict[str, Any]) -> str:
    """
    解析工具调用响应

    Args:
        response: OpenClaw 响应数据

    Returns:
        解析后的结果字符串
    """
    if not response:
        return "❌ 响应为空"

    # 检查成功标志
    if response.get("success"):
        result = response.get("result", "")
        metadata = response.get("metadata", {})

        output = result

        # 添加元数据信息（可选）
        if metadata:
            exec_time = metadata.get("execution_time")
            if exec_time:
                output += f"\n\n⏱️ 执行时间: {exec_time:.3f}s"

        return output
    else:
        error = response.get("error", "未知错误")
        return f"❌ 工具调用失败: {error}"


def parse_health_response(response: Dict[str, Any]) -> str:
    """
    解析健康检查响应

    Args:
        response: OpenClaw 健康检查响应

    Returns:
        解析后的健康状态字符串
    """
    if not response:
        return "❌ 响应为空"

    if response.get("success"):
        status = response.get("status", {})
        return f"✅ OpenClaw Gateway 运行正常\n\n状态: {status}"
    else:
        error = response.get("error", "未知错误")
        return f"❌ OpenClaw Gateway 不可用: {error}"


def parse_tools_list_response(response: Dict[str, Any]) -> str:
    """
    解析工具列表响应

    Args:
        response: OpenClaw 工具列表响应

    Returns:
        解析后的工具列表字符串
    """
    if not response:
        return "❌ 响应为空"

    if response.get("success"):
        tools = response.get("tools", [])
        if not tools:
            return "📋 暂无可用工具"

        result = "📋 **可用工具列表**\n\n"
        for tool in tools:
            name = tool.get("name", "未知")
            desc = tool.get("description", "")
            result += f"- **{name}**: {desc}\n"
        return result
    else:
        error = response.get("error", "未知错误")
        return f"❌ 获取工具列表失败: {error}"
