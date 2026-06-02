"""
Loop Detector — Agent 循环检测 (方向P.3)

设计参考: agentic-data-scientist LoopDetection
核心功能:
- 检测 Agent ReAct 循环中的重复模式
- 三种检测策略:
  1. 工具调用重复 (同一工具+参数多次调用)
  2. 输出相似度 (连续输出高度相似)
  3. 状态回环 (状态序列出现环)

使用方式:
  detector = LoopDetector(max_repeats=3, similarity_threshold=0.85)
  
  # 在 Agent 循环中调用
  for turn in agent_loop:
      detector.record_tool_call(tool_name, args)
      if detector.is_looping():
          break  # 或 yield warning
"""

import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


class LoopType(str, Enum):
    TOOL_REPEAT = "tool_repeat"          # 同一工具+参数重复调用
    OUTPUT_SIMILARITY = "output_similarity"  # 输出高度相似
    STATE_CYCLE = "state_cycle"           # 状态序列出现环


@dataclass
class LoopDetection:
    """循环检测结果"""
    is_looping: bool = False
    loop_type: Optional[LoopType] = None
    details: str = ""
    repeat_count: int = 0
    suggestion: str = ""


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    args_hash: str         # 参数哈希
    timestamp: float
    args_summary: str = ""  # 参数摘要 (用于日志)


class LoopDetector:
    """
    Agent 循环检测器
    
    三层检测:
    1. 工具调用重复: 同一工具+相同参数在窗口内出现 N 次
    2. 输出相似度: 连续输出的 Jaccard 相似度超过阈值
    3. 状态回环: 状态序列中检测到环 (Floyd 算法)
    """

    def __init__(
        self,
        max_repeats: int = 3,
        similarity_threshold: float = 0.85,
        window_size: int = 10,
        state_window: int = 20,
    ):
        """
        Args:
            max_repeats: 同一工具调用最大允许重复次数
            similarity_threshold: 输出相似度阈值 (0-1)
            window_size: 工具调用滑动窗口大小
            state_window: 状态序列窗口大小
        """
        self.max_repeats = max_repeats
        self.similarity_threshold = similarity_threshold
        self.window_size = window_size
        self.state_window = state_window

        # 工具调用历史
        self._tool_calls: Deque[ToolCallRecord] = deque(maxlen=window_size)
        
        # 输出历史 (token 集合)
        self._output_history: Deque[str] = deque(maxlen=5)
        
        # 状态历史 (哈希序列)
        self._state_history: Deque[str] = deque(maxlen=state_window)
        
        # 检测统计
        self._detections: List[LoopDetection] = []
        self._total_turns = 0

    def record_tool_call(self, tool_name: str, args: Dict[str, Any]) -> LoopDetection:
        """
        记录工具调用并检测重复
        
        Returns:
            LoopDetection 结果
        """
        self._total_turns += 1

        # 计算参数哈希
        args_str = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()
        args_summary = args_str[:80]

        record = ToolCallRecord(
            tool_name=tool_name,
            args_hash=args_hash,
            timestamp=time.time(),
            args_summary=args_summary,
        )
        self._tool_calls.append(record)

        # 检测重复
        same_calls = [
            r for r in self._tool_calls
            if r.tool_name == tool_name and r.args_hash == args_hash
        ]

        if len(same_calls) >= self.max_repeats:
            detection = LoopDetection(
                is_looping=True,
                loop_type=LoopType.TOOL_REPEAT,
                details=f"Tool '{tool_name}' called with identical args {len(same_calls)} times",
                repeat_count=len(same_calls),
                suggestion=f"Tool '{tool_name}' is being called repeatedly with the same arguments. "
                           f"Consider using a different approach or checking if the tool is working correctly.",
            )
            self._detections.append(detection)
            logger.warning("Loop detected: tool repeat", tool=tool_name, count=len(same_calls))
            return detection

        return LoopDetection(is_looping=False)

    def record_output(self, output: str) -> LoopDetection:
        """
        记录输出并检测相似度
        
        Returns:
            LoopDetection 结果
        """
        self._output_history.append(output)

        if len(self._output_history) >= 2:
            current = self._output_history[-1]
            previous = self._output_history[-2]

            similarity = self._jaccard_similarity(current, previous)

            if similarity >= self.similarity_threshold:
                detection = LoopDetection(
                    is_looping=True,
                    loop_type=LoopType.OUTPUT_SIMILARITY,
                    details=f"Output similarity {similarity:.2%} exceeds threshold {self.similarity_threshold:.2%}",
                    repeat_count=2,
                    suggestion="The agent is producing highly similar outputs. "
                               "Consider changing the approach or providing more specific instructions.",
                )
                self._detections.append(detection)
                logger.warning("Loop detected: output similarity", similarity=similarity)
                return detection

        return LoopDetection(is_looping=False)

    def record_state(self, state: Dict[str, Any]) -> LoopDetection:
        """
        记录状态并检测回环
        
        Returns:
            LoopDetection 结果
        """
        state_hash = hashlib.md5(
            json.dumps(state, sort_keys=True, default=str).encode()
        ).hexdigest()
        self._state_history.append(state_hash)

        # 检测状态回环: 如果同一哈希出现2次以上
        if self._state_history.count(state_hash) >= 2:
            # 找到回环长度
            indices = [i for i, h in enumerate(self._state_history) if h == state_hash]
            if len(indices) >= 2:
                cycle_length = indices[-1] - indices[-2]
                detection = LoopDetection(
                    is_looping=True,
                    loop_type=LoopType.STATE_CYCLE,
                    details=f"State cycle detected with length {cycle_length}",
                    repeat_count=len(indices),
                    suggestion=f"The agent has entered a cycle of length {cycle_length}. "
                               f"Breaking out of the loop is recommended.",
                )
                self._detections.append(detection)
                logger.warning("Loop detected: state cycle", cycle_length=cycle_length)
                return detection

        return LoopDetection(is_looping=False)

    def is_looping(self) -> bool:
        """快速检查是否正在循环"""
        if self._detections:
            return self._detections[-1].is_looping
        return False

    def get_last_detection(self) -> Optional[LoopDetection]:
        """获取最近一次检测结果"""
        return self._detections[-1] if self._detections else None

    def get_all_detections(self) -> List[LoopDetection]:
        """获取所有检测结果"""
        return list(self._detections)

    def get_stats(self) -> Dict[str, Any]:
        """获取检测统计"""
        by_type = {}
        for d in self._detections:
            key = d.loop_type.value if d.loop_type else "unknown"
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_turns": self._total_turns,
            "total_detections": len(self._detections),
            "detections_by_type": by_type,
            "is_looping": self.is_looping(),
        }

    def reset(self) -> None:
        """重置检测器"""
        self._tool_calls.clear()
        self._output_history.clear()
        self._state_history.clear()
        self._detections.clear()
        self._total_turns = 0

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str) -> float:
        """Jaccard 相似度 (基于 token 集合)"""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = set1 & set2
        union = set1 | set2

        return len(intersection) / len(union)


# ── Agent 集成辅助 ──

def create_loop_detector_for_agent(
    max_repeats: int = 3,
    similarity_threshold: float = 0.85,
) -> LoopDetector:
    """为 Agent 创建循环检测器 (推荐配置)"""
    return LoopDetector(
        max_repeats=max_repeats,
        similarity_threshold=similarity_threshold,
        window_size=10,
        state_window=20,
    )
