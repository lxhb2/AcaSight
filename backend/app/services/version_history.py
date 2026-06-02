"""
版本历史服务 (方向U.1)

功能:
1. diff 存储 (增量差异)
2. 版本列表
3. 版本对比
4. 一键恢复
5. 版本备注

存储: JSON 文件 (data/version_history/)
"""

import difflib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()

DEFAULT_HISTORY_DIR = os.path.join(os.getcwd(), "data", "version_history")


class VersionHistoryService:
    """
    版本历史服务
    
    存储结构:
    data/version_history/
    ├── {document_id}/
    │   ├── meta.json            # 文档元数据
    │   ├── versions/
    │   │   ├── v001.json        # 完整版本 (每N个版本存完整)
    │   │   ├── v002.json        # diff版本
    │   │   └── ...
    │   └── index.json           # 版本索引
    """
    
    # 每隔多少版本存一次完整版本
    FULL_SNAPSHOT_INTERVAL = 5
    
    def __init__(self, history_dir: Optional[str] = None):
        self._history_dir = history_dir or DEFAULT_HISTORY_DIR
        os.makedirs(self._history_dir, exist_ok=True)
    
    def save_version(
        self,
        document_id: str,
        content: str,
        note: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict:
        """
        保存新版本
        
        Returns:
            版本信息
        """
        doc_dir = os.path.join(self._history_dir, document_id)
        versions_dir = os.path.join(doc_dir, "versions")
        os.makedirs(versions_dir, exist_ok=True)
        
        now = time.time()
        
        # 读取索引
        index_path = os.path.join(doc_dir, "index.json")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"document_id": document_id, "versions": []}
        
        version_num = len(index["versions"]) + 1
        version_id = f"v{version_num:03d}"
        
        # 决定存储方式: 完整版 or diff
        is_full = version_num % self.FULL_SNAPSHOT_INTERVAL == 1 or version_num == 1
        
        version_data = {
            "version_id": version_id,
            "version_num": version_num,
            "timestamp": now,
            "note": note or "",
            "author": author or "system",
            "is_full": is_full,
            "content_length": len(content),
        }
        
        if is_full:
            # 存储完整内容
            version_data["content"] = content
            version_data["diff"] = None
        else:
            # 存储 diff
            prev_content = self._get_previous_content(doc_dir, index)
            if prev_content is not None:
                diff = self._compute_diff(prev_content, content)
                version_data["diff"] = diff
                version_data["content"] = None
                version_data["diff_stats"] = {
                    "added": diff.count("+ ") - 1,  # 减去header行
                    "removed": diff.count("- ") - 1,
                }
            else:
                # 无法获取前版本，存完整
                version_data["content"] = content
                version_data["diff"] = None
                version_data["is_full"] = True
        
        # 写入版本文件
        version_path = os.path.join(versions_dir, f"{version_id}.json")
        with open(version_path, "w", encoding="utf-8") as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index["versions"].append({
            "version_id": version_id,
            "version_num": version_num,
            "timestamp": now,
            "note": note or "",
            "author": author or "system",
            "is_full": is_full,
            "content_length": len(content),
        })
        
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        logger.info("Version saved", document_id=document_id, version=version_id, is_full=is_full)
        
        return {
            "version_id": version_id,
            "version_num": version_num,
            "timestamp": now,
            "is_full": is_full,
        }
    
    def get_version(self, document_id: str, version_id: Optional[str] = None) -> Optional[Dict]:
        """
        获取特定版本 (自动重建 diff 链)
        
        Args:
            version_id: 版本ID (None=最新)
        """
        doc_dir = os.path.join(self._history_dir, document_id)
        if not os.path.exists(doc_dir):
            return None
        
        index_path = os.path.join(doc_dir, "index.json")
        if not os.path.exists(index_path):
            return None
        
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        
        if not index["versions"]:
            return None
        
        if version_id is None:
            version_id = index["versions"][-1]["version_id"]
        
        # 重建版本内容
        content = self._reconstruct_content(doc_dir, version_id, index)
        if content is None:
            return None
        
        # 获取版本元数据
        version_path = os.path.join(doc_dir, "versions", f"{version_id}.json")
        if not os.path.exists(version_path):
            return None
        
        with open(version_path, "r", encoding="utf-8") as f:
            version_data = json.load(f)
        
        return {
            "version_id": version_data["version_id"],
            "version_num": version_data["version_num"],
            "timestamp": version_data["timestamp"],
            "note": version_data["note"],
            "author": version_data["author"],
            "content": content,
        }
    
    def list_versions(self, document_id: str) -> List[Dict]:
        """列出所有版本"""
        doc_dir = os.path.join(self._history_dir, document_id)
        if not os.path.exists(doc_dir):
            return []
        
        index_path = os.path.join(doc_dir, "index.json")
        if not os.path.exists(index_path):
            return []
        
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        
        return index["versions"]
    
    def compare_versions(self, document_id: str, version_id_a: str, version_id_b: str) -> Optional[Dict]:
        """对比两个版本"""
        content_a = self.get_version(document_id, version_id_a)
        content_b = self.get_version(document_id, version_id_b)
        
        if content_a is None or content_b is None:
            return None
        
        diff = self._compute_diff(content_a["content"], content_b["content"])
        
        return {
            "version_a": version_id_a,
            "version_b": version_id_b,
            "diff": diff,
            "stats": {
                "added": sum(1 for l in diff.split("\n") if l.startswith("+ ") and not l.startswith("+++")),
                "removed": sum(1 for l in diff.split("\n") if l.startswith("- ") and not l.startswith("---")),
            },
        }
    
    def restore_version(self, document_id: str, version_id: str, note: Optional[str] = None) -> Optional[Dict]:
        """恢复到指定版本 (创建新版本)"""
        version = self.get_version(document_id, version_id)
        if version is None:
            return None
        
        return self.save_version(
            document_id=document_id,
            content=version["content"],
            note=note or f"Restored from {version_id}",
            author="restore",
        )
    
    def _compute_diff(self, old: str, new: str) -> str:
        """计算 unified diff"""
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
        return "\n".join(diff)
    
    def _get_previous_content(self, doc_dir: str, index: Dict) -> Optional[str]:
        """获取前一个版本的完整内容"""
        if not index["versions"]:
            return None
        
        last_version_id = index["versions"][-1]["version_id"]
        return self._reconstruct_content(doc_dir, last_version_id, index)
    
    def _reconstruct_content(self, doc_dir: str, target_version_id: str, index: Dict) -> Optional[str]:
        """重建版本内容 (从最近的完整版本开始应用 diff 链)"""
        versions_dir = os.path.join(doc_dir, "versions")
        
        # 找到目标版本
        target_num = None
        for v in index["versions"]:
            if v["version_id"] == target_version_id:
                target_num = v["version_num"]
                break
        
        if target_num is None:
            return None
        
        # 找到目标之前最近的完整版本
        base_num = None
        for v in reversed(index["versions"]):
            if v["version_num"] <= target_num and v.get("is_full", True):
                base_num = v["version_num"]
                break
        
        if base_num is None:
            base_num = 1
        
        # 读取基础版本
        base_path = os.path.join(versions_dir, f"v{base_num:03d}.json")
        if not os.path.exists(base_path):
            return None
        
        with open(base_path, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        
        content = base_data.get("content", "")
        if content is None:
            return None
        
        # 逐步应用 diff
        for v_num in range(base_num + 1, target_num + 1):
            v_path = os.path.join(versions_dir, f"v{v_num:03d}.json")
            if not os.path.exists(v_path):
                continue
            
            with open(v_path, "r", encoding="utf-8") as f:
                v_data = json.load(f)
            
            if v_data.get("content") is not None:
                # 完整版本
                content = v_data["content"]
            elif v_data.get("diff") is not None:
                # 应用 diff
                content = self._apply_diff(content, v_data["diff"])
        
        return content
    
    def _apply_diff(self, original: str, diff_text: str) -> str:
        """应用 unified diff 到原始文本"""
        # 简化实现: 使用 difflib 还原
        # 对于复杂场景，生产环境应使用 patch 库
        original_lines = original.splitlines()
        diff_lines = diff_text.splitlines()
        
        result_lines = []
        original_idx = 0
        
        for line in diff_lines:
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                continue
            elif line.startswith("+ "):
                result_lines.append(line[2:])
            elif line.startswith("- "):
                original_idx += 1  # 跳过已删除的行
            elif line.startswith(" "):
                if original_idx < len(original_lines):
                    result_lines.append(original_lines[original_idx])
                original_idx += 1
        
        # 添加剩余的原始行
        while original_idx < len(original_lines):
            result_lines.append(original_lines[original_idx])
            original_idx += 1
        
        return "\n".join(result_lines)


# Singleton
_version_history_service: Optional[VersionHistoryService] = None


def get_version_history_service() -> VersionHistoryService:
    global _version_history_service
    if _version_history_service is None:
        _version_history_service = VersionHistoryService()
    return _version_history_service
