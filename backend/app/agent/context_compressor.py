"""
Context Compressor — 上下文压缩器

当 Agent 消息历史接近 token 限制时，自动压缩历史消息。
参考 Hermes Agent 的 context_engine.py 和 context_compressor.py 设计。

策略：
1. 移除最早的非关键 tool 结果（截断到摘要）
2. 将早期的 user/assistant 对话合并为摘要
3. 始终保留 system prompt 和最近 N 轮对话
"""

import structlog
from typing import List, Dict, Optional

logger = structlog.get_logger()


# Token 估算（粗略，中英混合按 2 字符/token）
def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数"""
    # 英文约 4 字符/token，中文约 2 字符/token
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    unicode_chars = len(text) - ascii_chars
    return ascii_chars // 4 + unicode_chars // 2 + 1


def _estimate_messages_tokens(messages: List[Dict]) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        total += _estimate_tokens(msg.get("content", "") or "")
        total += _estimate_tokens(msg.get("role", ""))
        # tool 消息还有 name
        if msg.get("name"):
            total += _estimate_tokens(msg["name"])
        # assistant 消息可能有 tool_calls
        if msg.get("tool_calls"):
            for tc in msg.get("tool_calls", []):
                total += _estimate_tokens(tc.get("name", ""))
                total += _estimate_tokens(str(tc.get("arguments", {})))
    return total


class ContextCompressor:
    """上下文压缩器 - 管理 token 预算"""
    
    def __init__(self, max_tokens: int = 32000, safety_margin: float = 0.85):
        """
        Args:
            max_tokens: 最大 token 数（模型上下文窗口）
            safety_margin: 触发压缩的阈值比例（0.0~1.0）
        """
        self.max_tokens = max_tokens
        self.threshold = int(max_tokens * safety_margin)
        self.protect_first_n = 3  # 始终保留前 N 条非 system 消息
        self.protect_last_n = 6   # 始终保留最近 N 条消息
        self.compression_count = 0
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """检查是否需要压缩"""
        total = _estimate_messages_tokens(messages)
        return total > self.threshold
    
    def compress(self, messages: List[Dict]) -> List[Dict]:
        """压缩消息历史"""
        self.compression_count += 1
        
        if len(messages) <= self.protect_first_n + self.protect_last_n:
            return messages  # 太短，无需压缩
        
        # 分离 system 消息
        system_msgs = [m for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        
        if len(non_system) <= self.protect_first_n + self.protect_last_n:
            return messages
        
        # 保留头部和尾部
        head = non_system[:self.protect_first_n]
        tail = non_system[-self.protect_last_n:]
        middle = non_system[self.protect_first_n:-self.protect_last_n]
        
        if not middle:
            return system_msgs + head + tail
        
        # 压缩中间部分：找到 tool 结果消息并截断
        compressed_middle = []
        for msg in middle:
            if msg["role"] == "tool":
                content = msg.get("content", "") or ""
                if len(content) > 200:
                    # 截断 tool 结果为前 200 字符摘要
                    msg = {**msg, "content": content[:200] + f"\n... (截断, 原 {len(content)} 字符)"}
                compressed_middle.append(msg)
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # 保留 assistant 工具调用消息，但截断内容
                orig = msg.get("content", "") or ""
                if len(orig) > 300:
                    msg = {**msg, "content": orig[:300] + "..."}
                compressed_middle.append(msg)
            else:
                compressed_middle.append(msg)
        
        result = system_msgs + head + compressed_middle + tail
        compressed = _estimate_messages_tokens(result)
        original = _estimate_messages_tokens(messages)
        
        logger.info(
            f"Context compressed: {original} → {compressed} tokens "
            f"(saved {original - compressed} tokens, "
            f"compression #{self.compression_count})"
        )
        
        return result


# 全局实例
context_compressor = ContextCompressor()
