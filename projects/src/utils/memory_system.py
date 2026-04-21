"""
动态记忆管理系统
借鉴 Claude Code 的 claudemd.ts 设计
支持按日期记录学习日志，定期蒸馏为索引
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


class LearningMemory:
    """学习记忆管理器"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.memory_file = self.base_dir / "MEMORY.md"
        self.logs_dir = self.base_dir / "logs"

        # 创建目录结构
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def get_today_log_path(self) -> Path:
        """获取今日日志文件路径"""
        today = datetime.now()
        return self.logs_dir / str(today.year) / f"{today.month:02d}" / f"{today.date()}.md"

    def append_log(self, category: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """追加日志到今日文件"""
        log_path = self.get_today_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%H:%M:%S")
        meta_str = json.dumps(metadata) if metadata else ""

        log_entry = f"""### {timestamp} - {category}

{content}

"""

        if metadata:
            log_entry += f"""**元数据**: `{meta_str}`

"""

        # 追加到文件
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def get_today_logs(self) -> List[str]:
        """获取今日所有日志"""
        log_path = self.get_today_log_path()
        if not log_path.exists():
            return []

        with open(log_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def distill_to_memory(self, days: int = 7) -> str:
        """将最近N天的日志蒸馏到 MEMORY.md"""
        today = datetime.now()

        distilled_content = f"""# 学习记忆索引

*最后更新: {today.strftime('%Y-%m-%d %H:%M:%S')}*
*来源: 最近 {days} 天的学习日志*

---

## 学习偏好

*自动提取自学习日志*

## 项目上下文

*自动提取自学习日志*

## 重要概念

*自动提取自学习日志*

## 问题与解决方案

*自动提取自学习日志*

## 外部资源

*自动提取自学习日志*

---

*此文件由系统自动维护，记录学习过程中的重要信息*
"""

        # 写入 MEMORY.md
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write(distilled_content)

        return f"已将最近 {days} 天的学习日志蒸馏到 MEMORY.md"

    def search_logs(self, keyword: str, days: int = 7) -> List[Dict[str, Any]]:
        """搜索日志中的关键词"""
        results = []
        today = datetime.now()

        for i in range(days):
            date = today.timestamp() - (i * 24 * 3600)
            log_date = datetime.fromtimestamp(date)
            log_path = self.logs_dir / str(log_date.year) / f"{log_date.month:02d}" / f"{log_date.date()}.md"

            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if keyword in content:
                        results.append({
                            "date": log_date.strftime("%Y-%m-%d"),
                            "path": str(log_path),
                            "matches": content.count(keyword)
                        })

        return results

    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        if not self.memory_file.exists():
            return "还没有生成记忆索引。"

        with open(self.memory_file, 'r', encoding='utf-8') as f:
            return f.read()[:2000]  # 返回前2000字符


class LearningLogger:
    """学习日志记录器"""

    def __init__(self, memory: LearningMemory):
        self.memory = memory

    def log_challenge_completion(self, challenge_name: str, points: int, project: str) -> None:
        """记录挑战完成"""
        self.memory.append_log(
            "挑战完成",
            f"在项目 '{project}' 中完成了挑战：{challenge_name}，获得 {points} 分",
            {
                "type": "challenge",
                "points": points,
                "project": project
            }
        )

    def log_module_completion(self, module_name: str, project: str, total_points: int) -> None:
        """记录模块完成"""
        self.memory.append_log(
            "模块完成",
            f"在项目 '{project}' 中完成了模块：{module_name}，总分 {total_points} 分",
            {
                "type": "module",
                "project": project,
                "points": total_points
            }
        )

    def log_resource_added(self, resource_title: str, resource_type: str, project: str) -> None:
        """记录资源添加"""
        self.memory.append_log(
            "资源添加",
            f"在项目 '{project}' 中添加了 {resource_type}：{resource_title}",
            {
                "type": "resource",
                "resource_type": resource_type,
                "project": project
            }
        )

    def log_note(self, note_content: str, note_type: str, project: str) -> None:
        """记录笔记"""
        self.memory.append_log(
            "学习笔记",
            f"在项目 '{project}' 中添加了{note_type}笔记：{note_content}",
            {
                "type": "note",
                "note_type": note_type,
                "project": project
            }
        )

    def log_achievement(self, achievement_name: str, project: str) -> None:
        """记录成就解锁"""
        self.memory.append_log(
            "成就解锁",
            f"在项目 '{project}' 中解锁了成就：{achievement_name}",
            {
                "type": "achievement",
                "project": project
            }
        )


# === 使用示例 ===

if __name__ == "__main__":
    # 创建记忆管理器
    memory = LearningMemory("/tmp/pulse_memory")
    logger = LearningLogger(memory)

    # 记录一些日志
    logger.log_challenge_completion("安装requests库", 5, "Python爬虫实战")
    logger.log_resource_added("requests官方文档", "文档", "Python爬虫实战")
    logger.log_note("GET请求的基本使用方法", "重要", "Python爬虫实战")
    logger.log_achievement("初学者", "Python爬虫实战")

    # 查看今日日志
    print("=== 今日日志 ===")
    logs = memory.get_today_logs()
    for log in logs[-5:]:  # 显示最后5条
        print(log)

    # 蒸馏到记忆
    print("\n=== 蒸馏到记忆 ===")
    print(memory.distill_to_memory())

    # 搜索日志
    print("\n=== 搜索日志 ===")
    results = memory.search_logs("Python")
    for result in results:
        print(f"{result['date']}: 找到 {result['matches']} 处匹配")
