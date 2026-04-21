"""
测试 OpenClaw 客户端模块

验证目标:
1. OpenClawClient 能正确初始化和连接
2. 工具调用接口正常工作
3. 响应解析正确
4. 健康检查功能正常
"""

import os
import sys
import unittest
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openclaw_client.client import OpenClawClient
from openclaw_client.tools import OpenClawToolExecutor
from openclaw_client.response_parser import parse_tool_response, parse_health_response


class TestOpenClawClient(unittest.TestCase):
    """OpenClaw 客户端测试"""

    def setUp(self):
        """创建测试客户端"""
        self.client = OpenClawClient(
            gateway_url="http://localhost:3000",
            timeout=5.0,
        )

    def tearDown(self):
        """关闭客户端"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.client.close())
            else:
                loop.run_until_complete(self.client.close())
        except Exception:
            pass

    def test_client_init(self):
        """测试客户端初始化"""
        self.assertEqual(self.client.gateway_url, "http://localhost:3000")
        self.assertEqual(self.client.timeout, 5.0)

    def test_health_check_unavailable(self):
        """测试健康检查（Gateway 不可用时的处理）"""
        async def run_check():
            result = await self.client.health_check()
            return result

        result = asyncio.get_event_loop().run_until_complete(run_check())
        # Gateway 不可用时应返回失败
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestOpenClawToolExecutor(unittest.TestCase):
    """OpenClaw 工具执行器测试"""

    def setUp(self):
        """创建测试执行器"""
        self.executor = OpenClawToolExecutor(
            gateway_url="http://localhost:3000",
        )

    def test_executor_init(self):
        """测试执行器初始化"""
        self.assertIsNotNone(self.executor.client)

    def test_execute_unavailable_gateway(self):
        """测试 Gateway 不可用时的处理"""
        async def run_execute():
            result = await self.executor.execute("test_tool", {"arg1": "value1"})
            return result

        result = asyncio.get_event_loop().run_until_complete(run_execute())
        # 应该返回错误信息
        self.assertIn("❌", result)


class TestResponseParser(unittest.TestCase):
    """响应解析器测试"""

    def test_parse_tool_response_success(self):
        """测试成功响应解析"""
        response = {
            "success": True,
            "result": "文件写入成功: test.txt (10 bytes)",
            "metadata": {"execution_time": 0.123},
        }
        result = parse_tool_response(response)
        self.assertIn("文件写入成功", result)
        self.assertIn("0.123s", result)

    def test_parse_tool_response_failure(self):
        """测试失败响应解析"""
        response = {
            "success": False,
            "error": "文件不存在",
        }
        result = parse_tool_response(response)
        self.assertIn("❌", result)
        self.assertIn("文件不存在", result)

    def test_parse_tool_response_empty(self):
        """测试空响应解析"""
        result = parse_tool_response(None)
        self.assertIn("❌", result)
        self.assertIn("响应为空", result)

    def test_parse_health_response_success(self):
        """测试健康检查成功响应解析"""
        response = {
            "success": True,
            "status": {"version": "1.0.0", "status": "healthy"},
        }
        result = parse_health_response(response)
        self.assertIn("✅", result)
        self.assertIn("运行正常", result)

    def test_parse_health_response_failure(self):
        """测试健康检查失败响应解析"""
        response = {
            "success": False,
            "error": "连接失败",
        }
        result = parse_health_response(response)
        self.assertIn("❌", result)
        self.assertIn("连接失败", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
