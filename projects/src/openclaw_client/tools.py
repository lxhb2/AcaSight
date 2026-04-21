"""
OpenClaw Tool Executor

提供工具执行接口，将工具调用请求转发到 OpenClaw。
"""

import logging
from typing import Dict, Any, Optional

from .client import OpenClawClient

logger = logging.getLogger("pulse_learning.openclaw_executor")


class OpenClawToolExecutor:
    """OpenClaw 工具执行器"""

    def __init__(
        self,
        client: Optional[OpenClawClient] = None,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        初始化工具执行器

        Args:
            client: OpenClaw 客户端实例
            gateway_url: Gateway URL（如果未提供 client）
            api_key: API 密钥（如果未提供 client）
        """
        if client:
            self.client = client
        else:
            self.client = OpenClawClient(gateway_url=gateway_url, api_key=api_key)

    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        thought: str = "",
    ) -> str:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            args: 工具参数
            thought: 调用原因（可选）

        Returns:
            工具调用结果（格式化字符串）
        """
        try:
            response = await self.client.call_tool(tool_name, args, thought)

            if response.get("success"):
                result = response.get("result", "")
                return result
            else:
                error = response.get("error", "未知错误")
                return f"❌ 工具执行失败: {error}"

        except Exception as e:
            logger.error(f"执行工具 {tool_name} 时发生异常: {e}")
            return f"❌ 工具执行异常: {e}"

    async def list_available_tools(self) -> str:
        """
        列出可用工具

        Returns:
            可用工具列表（格式化字符串）
        """
        try:
            response = await self.client.list_tools()

            if response.get("success"):
                tools = response.get("tools", [])
                result = "📋 **可用工具列表**\n\n"
                for tool in tools:
                    name = tool.get("name", "未知")
                    desc = tool.get("description", "")
                    result += f"- **{name}**: {desc}\n"
                return result
            else:
                error = response.get("error", "未知错误")
                return f"❌ 获取工具列表失败: {error}"

        except Exception as e:
            logger.error(f"获取工具列表时发生异常: {e}")
            return f"❌ 获取工具列表异常: {e}"

    async def health_check(self) -> str:
        """
        检查 OpenClaw Gateway 健康状态

        Returns:
            健康状态信息（格式化字符串）
        """
        try:
            response = await self.client.health_check()

            if response.get("success"):
                status = response.get("status", {})
                return f"✅ OpenClaw Gateway 运行正常\n\n状态: {status}"
            else:
                error = response.get("error", "未知错误")
                return f"❌ OpenClaw Gateway 不可用: {error}"

        except Exception as e:
            logger.error(f"健康检查时发生异常: {e}")
            return f"❌ 健康检查异常: {e}"

    async def close(self):
        """关闭客户端连接"""
        await self.client.close()
