"""
OpenClaw Gateway Client

负责与 OpenClaw Gateway 通信，发送工具调用请求并接收响应。
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger("pulse_learning.openclaw_client")

# 默认配置
DEFAULT_GATEWAY_URL = "http://localhost:3000"
DEFAULT_API_KEY = ""
DEFAULT_TIMEOUT = 30.0


class OpenClawClient:
    """OpenClaw Gateway 客户端"""

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        初始化 OpenClaw 客户端

        Args:
            gateway_url: OpenClaw Gateway URL
            api_key: API 密钥（可选）
            timeout: 请求超时时间（秒）
        """
        self.gateway_url = gateway_url or os.getenv(
            "OPENCLAW_GATEWAY_URL", DEFAULT_GATEWAY_URL
        )
        self.api_key = api_key or os.getenv("OPENCLAW_API_KEY", DEFAULT_API_KEY)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.gateway_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def call_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        thought: str = "",
    ) -> Dict[str, Any]:
        """
        调用 OpenClaw 工具

        Args:
            tool_name: 工具名称
            args: 工具参数
            thought: 调用原因（可选）

        Returns:
            工具调用响应
        """
        payload = {
            "tool_call": {
                "name": tool_name,
                "args": args,
                "thought": thought,
            }
        }

        logger.info(f"调用 OpenClaw 工具: {tool_name} with args: {args}")

        try:
            client = await self._get_client()
            response = await client.post("/api/tools/call", json=payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"OpenClaw 工具 {tool_name} 调用成功")
            return result

        except httpx.ConnectError as e:
            error_msg = f"无法连接到 OpenClaw Gateway ({self.gateway_url}): {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "result": "",
                "metadata": {},
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"OpenClaw API 错误 ({e.response.status_code}): {e.response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "result": "",
                "metadata": {},
            }

        except Exception as e:
            error_msg = f"OpenClaw 工具调用失败: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "result": "",
                "metadata": {},
            }

    async def list_tools(self) -> Dict[str, Any]:
        """
        列出 OpenClaw 可用的工具

        Returns:
            可用工具列表
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tools")
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"获取工具列表失败: {e}")
            return {"success": False, "error": str(e), "tools": []}

    async def health_check(self) -> Dict[str, Any]:
        """
        检查 OpenClaw Gateway 健康状态

        Returns:
            健康状态信息
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/health")
            response.raise_for_status()
            return {"success": True, "status": response.json()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
