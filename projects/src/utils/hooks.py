"""
Hook 事件系统
借鉴 Claude Code 的 hooks 设计
在关键学习事件时触发自定义操作
"""
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
import json
import os
from datetime import datetime


class LearningEventType(Enum):
    """学习事件类型"""
    PROJECT_CREATED = "project_created"
    MODULE_CREATED = "module_created"
    CHALLENGE_ADDED = "challenge_added"
    CHALLENGE_COMPLETED = "challenge_completed"
    MODULE_COMPLETED = "module_completed"
    BOSS_TASK_GENERATED = "boss_task_generated"
    BOSS_TASK_COMPLETED = "boss_task_completed"
    RESOURCE_ADDED = "resource_added"
    NOTE_ADDED = "note_added"
    COMBO_RESET = "combo_reset"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"


class Hook:
    """Hook 定义"""

    def __init__(
        self,
        event_type: LearningEventType,
        handler: Callable[[Dict[str, Any]], Optional[str]],
        name: Optional[str] = None,
        enabled: bool = True
    ):
        self.event_type = event_type
        self.handler = handler
        self.name = name or f"hook_{event_type.value}"
        self.enabled = enabled
        self.call_count = 0


class HookSystem:
    """Hook 系统"""

    def __init__(self):
        self.hooks: Dict[LearningEventType, List[Hook]] = {}
        for event_type in LearningEventType:
            self.hooks[event_type] = []

    def register(self, hook: Hook) -> "HookSystem":
        """注册 Hook"""
        self.hooks[hook.event_type].append(hook)
        return self

    def trigger(self, event_type: LearningEventType, context: Dict[str, Any]) -> List[str]:
        """触发 Hook"""
        results = []

        for hook in self.hooks.get(event_type, []):
            if hook.enabled:
                try:
                    hook.call_count += 1
                    result = hook.handler(context)
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Hook '{hook.name}' 执行失败: {str(e)}")

        return results

    def enable_hook(self, hook_name: str) -> bool:
        """启用 Hook"""
        for hooks in self.hooks.values():
            for hook in hooks:
                if hook.name == hook_name:
                    hook.enabled = True
                    return True
        return False

    def disable_hook(self, hook_name: str) -> bool:
        """禁用 Hook"""
        for hooks in self.hooks.values():
            for hook in hooks:
                if hook.name == hook_name:
                    hook.enabled = False
                    return True
        return False


# === 内置 Hook Handlers ===

def achievement_notifier(context: Dict[str, Any]) -> Optional[str]:
    """成就解锁通知"""
    achievement = context.get("achievement", "")
    if achievement:
        return f"🏆 解锁成就：{achievement}"
    return None


def combo_milestone_notifier(context: Dict[str, Any]) -> Optional[str]:
    """连击里程碑通知"""
    combo = context.get("combo", 0)
    if combo == 5:
        return "🔥 达成 5 连击！继续保持！"
    elif combo == 10:
        return "💎 达成 10 连击！连击大师！"
    elif combo == 20:
        return "👑 达成 20 连击！传奇连击！"
    return None


def learning_streak_reminder(context: Dict[str, Any]) -> Optional[str]:
    """学习连续性提醒"""
    days = context.get("consecutive_days", 0)
    if days >= 7:
        return f"📅 你已经连续学习 {days} 天了！太棒了！"
    return None


def daily_summary_generator(context: Dict[str, Any]) -> Optional[str]:
    """生成每日总结提示"""
    return "💡 今天完成了很多挑战，要不要生成一个学习总结？"


# === 全局 Hook 系统 ===

hook_system = HookSystem()

# 注册内置 Hooks
hook_system.register(Hook(
    LearningEventType.ACHIEVEMENT_UNLOCKED,
    achievement_notifier,
    "achievement_notifier"
))

hook_system.register(Hook(
    LearningEventType.CHALLENGE_COMPLETED,
    combo_milestone_notifier,
    "combo_milestone_notifier"
))

hook_system.register(Hook(
    LearningEventType.CHALLENGE_COMPLETED,
    learning_streak_reminder,
    "learning_streak_reminder"
))

hook_system.register(Hook(
    LearningEventType.MODULE_COMPLETED,
    daily_summary_generator,
    "daily_summary_generator"
))


# === 使用示例 ===

if __name__ == "__main__":
    # 触发事件
    print("=== 触发成就解锁事件 ===")
    results = hook_system.trigger(
        LearningEventType.ACHIEVEMENT_UNLOCKED,
        {"achievement": "初学者"}
    )
    for result in results:
        print(result)

    print("\n=== 触发挑战完成事件（5连击） ===")
    results = hook_system.trigger(
        LearningEventType.CHALLENGE_COMPLETED,
        {"combo": 5, "consecutive_days": 7}
    )
    for result in results:
        print(result)
