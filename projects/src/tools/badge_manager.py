#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脉冲学习系统 - 徽章管理器
简单文本徽章系统，基于累计分数解锁
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

# 徽章定义
BADGES = {
    # 等级徽章
    "novice": {
        "id": "novice",
        "name": "🌱 初学者",
        "description": "完成第一个微挑战",
        "condition": "total_score >= 10",
        "icon": "🌱"
    },
    "explorer": {
        "id": "explorer", 
        "name": "🔍 探索者",
        "description": "累计获得 50 分",
        "condition": "total_score >= 50",
        "icon": "🔍"
    },
    "learner": {
        "id": "learner",
        "name": "📚 学习者", 
        "description": "累计获得 100 分",
        "condition": "total_score >= 100",
        "icon": "📚"
    },
    "practitioner": {
        "id": "practitioner",
        "name": "⚡ 实践者",
        "description": "累计获得 250 分",
        "condition": "total_score >= 250",
        "icon": "⚡"
    },
    "expert": {
        "id": "expert",
        "name": "🎯 专家",
        "description": "累计获得 500 分",
        "condition": "total_score >= 500",
        "icon": "🎯"
    },
    "master": {
        "id": "master",
        "name": "👑 大师",
        "description": "累计获得 1000 分",
        "condition": "total_score >= 1000",
        "icon": "👑"
    },
    # 连击徽章
    "combo_3": {
        "id": "combo_3",
        "name": "🔥 三连击",
        "description": "达成 3 连击",
        "condition": "max_combo >= 3",
        "icon": "🔥"
    },
    "combo_5": {
        "id": "combo_5",
        "name": "⚡ 五连击",
        "description": "达成 5 连击",
        "condition": "max_combo >= 5",
        "icon": "⚡"
    },
    "combo_10": {
        "id": "combo_10",
        "name": "🌟 十连击",
        "description": "达成 10 连击",
        "condition": "max_combo >= 10",
        "icon": "🌟"
    },
    # 项目徽章
    "first_project": {
        "id": "first_project",
        "name": "🚀 项目启动",
        "description": "创建第一个学习项目",
        "condition": "projects_count >= 1",
        "icon": "🚀"
    },
    "project_master": {
        "id": "project_master",
        "name": "📁 项目达人",
        "description": "完成 3 个项目",
        "condition": "completed_projects >= 3",
        "icon": "📁"
    },
    # 挑战徽章
    "challenge_10": {
        "id": "challenge_10",
        "name": "🎮 挑战者",
        "description": "完成 10 个微挑战",
        "condition": "total_challenges >= 10",
        "icon": "🎮"
    },
    "challenge_50": {
        "id": "challenge_50",
        "name": "🏆 挑战大师",
        "description": "完成 50 个微挑战",
        "condition": "total_challenges >= 50",
        "icon": "🏆"
    },
    # Boss 徽章
    "boss_slayer": {
        "id": "boss_slayer",
        "name": "🐉 Boss 猎人",
        "description": "完成第一个 Boss 挑战",
        "condition": "boss_completed >= 1",
        "icon": "🐉"
    },
    "boss_master": {
        "id": "boss_master",
        "name": "👹 Boss 终结者",
        "description": "完成 5 个 Boss 挑战",
        "condition": "boss_completed >= 5",
        "icon": "👹"
    }
}


class BadgeManager:
    """徽章管理器"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化徽章管理器
        
        Args:
            storage_path: 徽章存储路径，默认使用 PulseLearning 目录
        """
        if storage_path is None:
            # 使用数据路径管理器
            from ..utils.data_paths import get_badges_file
            self.storage_path = get_badges_file()
        else:
            self.storage_path = storage_path
        
        self.badges = BADGES
        self.user_badges = self._load_user_badges()
    
    def _load_user_badges(self) -> Dict:
        """加载用户已获得的徽章"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "unlocked": [],
            "unlock_dates": {},
            "stats": {
                "total_score": 0,
                "max_combo": 0,
                "projects_count": 0,
                "completed_projects": 0,
                "total_challenges": 0,
                "boss_completed": 0
            }
        }
    
    def _save_user_badges(self):
        """保存用户徽章数据"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.user_badges, f, ensure_ascii=False, indent=2)
    
    def update_stats(self, **kwargs):
        """
        更新统计数据
        
        Args:
            total_score: 总分数
            max_combo: 最大连击
            projects_count: 项目数量
            completed_projects: 完成的项目数
            total_challenges: 完成的挑战数
            boss_completed: 完成的 Boss 挑战数
        """
        for key, value in kwargs.items():
            if key in self.user_badges["stats"]:
                self.user_badges["stats"][key] = value
        
        self._save_user_badges()
    
    def check_unlocks(self) -> List[Dict]:
        """
        检查新解锁的徽章
        
        Returns:
            新解锁的徽章列表
        """
        newly_unlocked = []
        stats = self.user_badges["stats"]
        
        for badge_id, badge in self.badges.items():
            if badge_id in self.user_badges["unlocked"]:
                continue
            
            # 解析条件
            condition = badge["condition"]
            if self._evaluate_condition(condition, stats):
                self.user_badges["unlocked"].append(badge_id)
                self.user_badges["unlock_dates"][badge_id] = datetime.now().isoformat()
                newly_unlocked.append(badge)
        
        if newly_unlocked:
            self._save_user_badges()
        
        return newly_unlocked
    
    def _evaluate_condition(self, condition: str, stats: Dict) -> bool:
        """评估徽章条件"""
        try:
            # 安全评估：只允许简单的比较表达式
            if ">=" in condition:
                key, value = condition.split(">=")
                key = key.strip()
                value = int(value.strip())
                return stats.get(key, 0) >= value
            elif ">" in condition:
                key, value = condition.split(">")
                key = key.strip()
                value = int(value.strip())
                return stats.get(key, 0) > value
            elif "==" in condition:
                key, value = condition.split("==")
                key = key.strip()
                value = int(value.strip())
                return stats.get(key, 0) == value
        except:
            pass
        return False
    
    def get_unlocked_badges(self) -> List[Dict]:
        """获取已解锁的徽章"""
        return [self.badges[bid] for bid in self.user_badges["unlocked"] if bid in self.badges]
    
    def get_locked_badges(self) -> List[Dict]:
        """获取未解锁的徽章"""
        return [badge for bid, badge in self.badges.items() if bid not in self.user_badges["unlocked"]]
    
    def get_next_badge(self) -> Optional[Dict]:
        """获取下一个即将解锁的徽章"""
        locked = self.get_locked_badges()
        if not locked:
            return None
        
        # 按分数要求排序
        score_badges = []
        for badge in locked:
            condition = badge["condition"]
            if ">=" in condition:
                try:
                    score = int(condition.split(">=")[1].strip())
                    score_badges.append((score, badge))
                except:
                    pass
        
        if score_badges:
            score_badges.sort(key=lambda x: x[0])
            return score_badges[0][1]
        
        return locked[0] if locked else None
    
    def get_progress_to_next(self) -> Dict:
        """获取下一个徽章的进度"""
        next_badge = self.get_next_badge()
        if not next_badge:
            return {"message": "🎉 所有徽章已解锁！", "percent": 100}
        
        condition = next_badge["condition"]
        stats = self.user_badges["stats"]
        
        if ">=" in condition:
            key, target = condition.split(">=")
            key = key.strip()
            target = int(target.strip())
            current = stats.get(key, 0)
            percent = min(100, int(current / target * 100))
            remaining = max(0, target - current)
            
            return {
                "badge": next_badge,
                "current": current,
                "target": target,
                "remaining": remaining,
                "percent": percent,
                "message": f"距离 {next_badge['name']} 还需 {remaining} {key.replace('_', ' ')}"
            }
        
        return {"badge": next_badge, "message": "继续加油！"}
    
    def format_badge_display(self, badge: Dict) -> str:
        """格式化徽章显示"""
        return f"{badge['icon']} **{badge['name']}** - {badge['description']}"
    
    def get_status_text(self) -> str:
        """获取徽章状态文本（用于显示）"""
        lines = []
        lines.append("## 🏅 徽章墙")
        lines.append("")
        
        unlocked = self.get_unlocked_badges()
        if unlocked:
            lines.append(f"**已解锁 ({len(unlocked)}/{len(self.badges)})：**")
            for badge in unlocked:
                lines.append(f"  ✅ {self.format_badge_display(badge)}")
        else:
            lines.append("*还没有徽章，开始你的第一个挑战吧！*")
        
        lines.append("")
        
        # 下一个徽章进度
        progress = self.get_progress_to_next()
        if "percent" in progress and progress["percent"] < 100:
            lines.append(f"**下一个徽章：**")
            lines.append(f"  🎯 {progress['badge']['name']}")
            lines.append(f"  进度: [{'█' * (progress['percent'] // 10)}{'░' * (10 - progress['percent'] // 10)}] {progress['percent']}%")
            lines.append(f"  {progress['message']}")
        
        return "\n".join(lines)


# 便捷函数
def get_badge_manager() -> BadgeManager:
    """获取全局徽章管理器"""
    return BadgeManager()


if __name__ == "__main__":
    # 测试
    bm = get_badge_manager()
    
    print("=== 徽章系统测试 ===")
    print()
    
    # 模拟获得分数
    bm.update_stats(total_score=25, max_combo=2, total_challenges=3)
    print(f"当前统计: {bm.user_badges['stats']}")
    
    # 检查解锁
    new = bm.check_unlocks()
    if new:
        print(f"🎉 新解锁徽章: {[b['name'] for b in new]}")
    
    print()
    print(bm.get_status_text())
    
    # 继续增加分数
    bm.update_stats(total_score=60, max_combo=4, total_challenges=8)
    new = bm.check_unlocks()
    if new:
        print(f"\n🎉 新解锁徽章: {[b['name'] for b in new]}")
        print(bm.get_status_text())
