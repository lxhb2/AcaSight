"""
BaseModule — 六大模块独立Agent的抽象基类

所有模块Agent继承此基类，实现统一接口：
- execute(): 执行任务
- interrupt(): 中断执行（等待用户确认）
- resume(): 恢复执行（用户确认后）
- get_status(): 获取当前状态
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ModuleStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ModuleResult:
    success: bool
    data: Any = None
    error: str = ""
    interrupt_reason: str = ""
    interrupt_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterruptInfo:
    reason: str
    section_index: int = -1
    section_title: str = ""
    required_type: str = ""
    options: List[Dict[str, str]] = field(default_factory=list)
    user_choice: Optional[Dict[str, Any]] = None


class BaseModule(ABC):
    """六大模块独立Agent抽象基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._status = ModuleStatus.IDLE
        self._interrupt_info: Optional[InterruptInfo] = None
        self._last_result: Optional[ModuleResult] = None
        self._history: List[Dict[str, Any]] = []

    @property
    def status(self) -> ModuleStatus:
        return self._status

    @property
    def interrupt_info(self) -> Optional[InterruptInfo]:
        return self._interrupt_info

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any] = None) -> ModuleResult:
        """执行任务"""
        ...

    async def interrupt(self, reason: str, section_index: int = -1,
                        section_title: str = "", required_type: str = "",
                        options: List[Dict[str, str]] = None) -> None:
        """中断执行，等待用户确认"""
        self._status = ModuleStatus.INTERRUPTED
        self._interrupt_info = InterruptInfo(
            reason=reason,
            section_index=section_index,
            section_title=section_title,
            required_type=required_type,
            options=options or [],
        )
        logger.info("Module interrupted", module=self.name, reason=reason)

    async def resume(self, user_choice: Dict[str, Any] = None) -> ModuleResult:
        """恢复执行（用户确认后）"""
        if self._status != ModuleStatus.INTERRUPTED:
            return ModuleResult(success=False, error="Not in interrupted state")
        if self._interrupt_info:
            self._interrupt_info.user_choice = user_choice
        self._status = ModuleStatus.RUNNING
        logger.info("Module resumed", module=self.name)
        return ModuleResult(success=True, data={"resumed": True})

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "module": self.name,
            "description": self.description,
            "status": self._status.value,
            "interrupt_info": {
                "reason": self._interrupt_info.reason,
                "section_index": self._interrupt_info.section_index,
                "section_title": self._interrupt_info.section_title,
                "required_type": self._interrupt_info.required_type,
                "options": self._interrupt_info.options,
            } if self._interrupt_info else None,
            "last_result": {
                "success": self._last_result.success,
                "error": self._last_result.error,
            } if self._last_result else None,
            "history_count": len(self._history),
        }

    def _record_history(self, task: str, result: ModuleResult):
        self._history.append({
            "task": task,
            "success": result.success,
            "timestamp": datetime.now().isoformat(),
            "error": result.error,
        })
