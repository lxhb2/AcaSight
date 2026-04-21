"""
集成系统管理工具
整合 Hook、记忆系统和模块化提示词
"""
import os
from .prompt_builder import build_pulse_learning_system_prompt
from .memory_system import LearningMemory, LearningLogger
from .hooks import hook_system, LearningEventType
from pathlib import Path


class IntegratedLearningSystem:
    """集成学习系统"""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.memory_dir = os.path.join(workspace_path, "assets", "PulseLearning", "memory")
        self.memory = LearningMemory(self.memory_dir)
        self.logger = LearningLogger(self.memory)

    def get_system_prompt(self, language: str = "中文") -> str:
        """获取系统提示词"""
        return build_pulse_learning_system_prompt(language)

    def log_challenge_completion(self, challenge_name: str, points: int, project: str, combo: int) -> None:
        """记录挑战完成并触发 Hook"""
        # 记录到日志
        self.logger.log_challenge_completion(challenge_name, points, project)

        # 触发 Hook
        hook_system.trigger(
            LearningEventType.CHALLENGE_COMPLETED,
            {
                "challenge": challenge_name,
                "points": points,
                "project": project,
                "combo": combo
            }
        )

        # 检查是否解锁成就
        if combo == 5:
            self.logger.log_achievement("5连击达人", project)
            hook_system.trigger(
                LearningEventType.ACHIEVEMENT_UNLOCKED,
                {"achievement": "5连击达人", "project": project}
            )
        elif combo == 10:
            self.logger.log_achievement("10连击大师", project)
            hook_system.trigger(
                LearningEventType.ACHIEVEMENT_UNLOCKED,
                {"achievement": "10连击大师", "project": project}
            )

    def log_module_completion(self, module_name: str, project: str, total_points: int) -> None:
        """记录模块完成并触发 Hook"""
        self.logger.log_module_completion(module_name, project, total_points)

        hook_system.trigger(
            LearningEventType.MODULE_COMPLETED,
            {
                "module": module_name,
                "project": project,
                "points": total_points
            }
        )

    def log_resource_added(self, resource_title: str, resource_type: str, project: str) -> None:
        """记录资源添加并触发 Hook"""
        self.logger.log_resource_added(resource_title, resource_type, project)

        hook_system.trigger(
            LearningEventType.RESOURCE_ADDED,
            {
                "resource": resource_title,
                "type": resource_type,
                "project": project
            }
        )

    def distill_memory(self, days: int = 7) -> str:
        """蒸馏学习日志到记忆索引"""
        return self.memory.distill_to_memory(days)

    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        return self.memory.get_memory_summary()

    def search_logs(self, keyword: str, days: int = 7) -> list:
        """搜索学习日志"""
        return self.memory.search_logs(keyword, days)


# 全局实例
integrated_system: IntegratedLearningSystem = None


def get_integrated_system() -> IntegratedLearningSystem:
    """获取集成系统实例"""
    global integrated_system
    if integrated_system is None:
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        integrated_system = IntegratedLearningSystem(workspace_path)
    return integrated_system


# === 更新现有工具以支持集成系统 ===

def patch_challenge_completion(original_function):
    """为挑战完成函数添加 Hook 和日志支持"""
    def wrapper(project_name: str, module_id: int, challenge_id: int, notes: str = "") -> str:
        # 调用原函数
        result = original_function(project_name, module_id, challenge_id, notes)

        # 触发集成系统
        try:
            system = get_integrated_system()
            # 从结果中提取信息
            import re
            combo_match = re.search(r'当前连击[：:]\s*(\d+)', result)
            points_match = re.search(r'基础分数[：:]\s*\+\s*(\d+)', result)

            if combo_match and points_match:
                combo = int(combo_match.group(1))
                points = int(points_match.group(1))

                # 提取挑战名称（从工具参数中获取）
                # 这里需要根据实际实现调整

                system.log_challenge_completion(
                    f"挑战{challenge_id}",
                    points,
                    project_name,
                    combo
                )
        except Exception as e:
            print(f"集成系统记录失败: {e}")

        return result

    return wrapper
