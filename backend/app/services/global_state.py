"""
全局状态管理器 (GlobalStateManager)
与 CapabilityRegistry 配合，实现：
1. 全局状态字典维护
2. 状态变更历史（50条）
3. 模块间数据流转（module_outputs 缓存）
4. 共享上下文（跨模块通信）
5. 状态快照供 Agent LLM 决策
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import json
import threading

# ─── 数据结构 ───

@dataclass
class StateRecord:
    """状态变更记录"""
    timestamp: datetime
    module: str
    operation: str
    key: str
    before: Any
    after: Any
    trigger: str  # "user" | "agent" | "workflow"

@dataclass
class ModuleOutput:
    """模块输出缓存"""
    data: Any
    operation: str
    timestamp: datetime
    module: str = ""
    expires_at: Optional[datetime] = None  # None = 不自动过期


class GlobalStateManager:
    """
    全局状态管理器（线程安全单例）
    
    设计原理：
    - `_state`: 全局状态字典（JSON 可序列化）
    - `_outputs`: 模块输出缓存（支持过期）
    - `_history`: 状态变更历史（环形缓冲）
    - `_waiters`: 异步等待者（生产者-消费者模式）
    """
    
    _instance: Optional[GlobalStateManager] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> GlobalStateManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 核心状态
        self._state: Dict[str, Any] = {
            "session_id": None,
            "user_id": None,
            "current_task": None,
            "task_stage": None,          # 当前任务阶段
            "active_modules": [],         # 活跃模块列表
            "workflow_id": None,
            "workflow_step": None,
            "shared_context": {           # 共享上下文（写作主题/论文ID等）
                "writing_topic": "",
                "current_paper_ids": [],
                "search_results": [],
                "chart_data": {},
            },
            "mode": "assist",             # 默认辅助模式
            "user_preferences": {},
        }
        
        # 输出缓存
        self._outputs: Dict[str, ModuleOutput] = {}
        
        # 变更历史
        self._history: List[StateRecord] = []
        self._max_history = 50
        self._next_version = 0
    
    # ─── 基础操作 ───
    
    def get(self, key: str, default: Any = None) -> Any:
        """安全获取状态值"""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any,
            module: str = "system", operation: str = "set",
            trigger: str = "agent") -> None:
        """设置状态值（带历史记录）"""
        before = self._state.get(key)
        self._state[key] = value
        
        self._history.append(StateRecord(
            timestamp=datetime.now(),
            module=module,
            operation=operation,
            key=key,
            before=before,
            after=value,
            trigger=trigger,
        ))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        self._next_version += 1
    
    def update(self, updates: Dict[str, Any],
               module: str = "system", operation: str = "update",
               trigger: str = "agent") -> None:
        """批量更新"""
        for key, value in updates.items():
            self.set(key, value, module, operation, trigger)
    
    def snapshot(self) -> Dict[str, Any]:
        """深拷贝当前状态（供 LLM 决策使用）"""
        import copy
        return copy.deepcopy(self._state)
    
    # ─── 模块输出缓存 ───
    
    def set_module_output(self, module_id: str, output: Any,
                          operation: str = "", ttl_seconds: int = 0) -> None:
        """缓存模块输出"""
        expires = None
        if ttl_seconds > 0:
            from datetime import timedelta
            expires = datetime.now() + timedelta(seconds=ttl_seconds)
        
        self._outputs[module_id] = ModuleOutput(
            data=output,
            operation=operation,
            timestamp=datetime.now(),
            module=module_id,
            expires_at=expires,
        )
    
    def get_module_output(self, module_id: str) -> Optional[Any]:
        """获取模块输出（自动处理过期）"""
        out = self._outputs.get(module_id)
        if not out:
            return None
        if out.expires_at and out.expires_at < datetime.now():
            del self._outputs[module_id]
            return None
        return out.data
    
    def clear_module_output(self, module_id: str = ""):
        """清除模块输出"""
        if module_id:
            self._outputs.pop(module_id, None)
        else:
            self._outputs.clear()
    
    # ─── 共享上下文 ───
    
    def set_context(self, key: str, value: Any) -> None:
        """设置共享上下文"""
        self._state["shared_context"][key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取共享上下文"""
        return self._state["shared_context"].get(key, default)
    
    def set_writing_topic(self, topic: str) -> None:
        self.set_context("writing_topic", topic)
    
    def add_paper_to_context(self, paper_id: str) -> None:
        """添加论文到当前上下文"""
        ids = self._state["shared_context"].get("current_paper_ids", [])
        if paper_id not in ids:
            ids.append(paper_id)
            self._state["shared_context"]["current_paper_ids"] = ids
    
    # ─── 模块状态管理 ───
    
    def activate_module(self, module_id: str) -> None:
        """标记模块为活跃"""
        modules = self._state["active_modules"]
        if module_id not in modules:
            modules.append(module_id)
            self._state["active_modules"] = modules
    
    def deactivate_module(self, module_id: str) -> None:
        """取消模块活跃标记"""
        modules = [m for m in self._state["active_modules"] if m != module_id]
        self._state["active_modules"] = modules
    
    # ─── 任务状态 ───
    
    def set_task(self, task: str, stage: str = "started") -> None:
        """设置当前任务"""
        self._state["current_task"] = task
        self._state["task_stage"] = stage
    
    def clear_task(self) -> None:
        self._state["current_task"] = None
        self._state["task_stage"] = None
    
    # ─── 模式切换 ───
    
    def set_mode(self, mode: str) -> None:
        """切换操作模式: assist | full_control"""
        if mode in ("assist", "full_control"):
            old = self._state["mode"]
            self._state["mode"] = mode
            self._history.append(StateRecord(
                timestamp=datetime.now(),
                module="global_state",
                operation="set_mode",
                key="mode",
                before=old,
                after=mode,
                trigger="user",
            ))
    
    def is_full_control(self) -> bool:
        return self._state["mode"] == "full_control"
    
    def is_assist(self) -> bool:
        return self._state["mode"] == "assist"
    
    # ─── 上下文概述（供 LLM 决策） ───
    
    def generate_context_summary(self) -> str:
        """生成当前上下文的文本描述"""
        lines = []
        
        if self._state["current_task"]:
            lines.append(f"当前任务: {self._state['current_task']}")
            if self._state["task_stage"]:
                lines.append(f"任务阶段: {self._state['task_stage']}")
        
        if self._state["active_modules"]:
            lines.append(f"活跃模块: {', '.join(self._state['active_modules'])}")
        
        ctx = self._state["shared_context"]
        if ctx.get("writing_topic"):
            lines.append(f"写作主题: {ctx['writing_topic']}")
        if ctx.get("current_paper_ids"):
            lines.append(f"当前论文: {len(ctx['current_paper_ids'])} 篇")
        
        if self._outputs:
            non_expired = [
                f"  - {mid}: {out.operation} ({out.timestamp.strftime('%H:%M:%S')})"
                for mid, out in self._outputs.items()
                if not (out.expires_at and out.expires_at < datetime.now())
            ]
            if non_expired:
                lines.append("模块输出缓存:\n" + "\n".join(non_expired))
        
        lines.append(f"操作模式: {'全权' if self.is_full_control() else '辅助'}")
        return "\n".join(lines) if lines else "当前无活跃任务"
    
    # ─── 持久化 ───
    
    def export_state(self) -> str:
        """导出状态为 JSON"""
        export = {
            "state": {
                k: v for k, v in self._state.items()
                if k != "active_modules"
            },
            "active_modules": list(self._state["active_modules"]),
            "history": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "module": r.module,
                    "key": r.key,
                    "trigger": r.trigger,
                }
                for r in self._history[-20:]
            ],
        }
        return json.dumps(export, ensure_ascii=False, indent=2)
    
    def load_state(self, json_str: str) -> None:
        """从 JSON 加载状态"""
        try:
            data = json.loads(json_str)
            if "state" in data:
                self._state.update(data["state"])
            if "active_modules" in data:
                self._state["active_modules"] = data["active_modules"]
        except (json.JSONDecodeError, KeyError):
            pass


# ─── 便捷访问 ───

def get_global_state() -> GlobalStateManager:
    return GlobalStateManager()