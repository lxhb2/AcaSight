"""
临时缓存管理器

管理网络检索未使用的文献数据、临时缓存素材、单次写作临时交互数据。
用户确认留存的素材自动转为持久化存储，未确认的定时清理。
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import structlog

logger = structlog.get_logger()


class CacheManager:
    """临时缓存管理器，支持TTL和定时清理"""

    DEFAULT_TTL_HOURS = 24

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        self.index_file = os.path.join(self.base_dir, "_index.json")
        self._index: Dict = self._load_index()
        logger.info("CacheManager init", base_dir=self.base_dir)

    def put(
        self,
        key: str,
        data: dict,
        category: str = "general",
        ttl_hours: float = None,
    ) -> str:
        """
        存入临时缓存

        Args:
            key: 缓存键（如搜索结果的DOI、文献ID等）
            data: 缓存数据
            category: 分类 (search_result / writing_temp / upload_temp / general)
            ttl_hours: 生存时间（小时），默认24h

        Returns:
            str: cache_id
        """
        cache_id = str(uuid.uuid4())[:8]
        ttl = ttl_hours if ttl_hours is not None else self.DEFAULT_TTL_HOURS
        expires_at = (datetime.now() + timedelta(hours=ttl)).isoformat()

        entry = {
            "cache_id": cache_id,
            "key": key,
            "category": category,
            "data": data,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "persisted": False,
        }

        self._index[cache_id] = entry
        self._save_index()
        logger.info("Cache put", cache_id=cache_id, key=key, category=category, ttl=ttl)
        return cache_id

    def get(self, cache_id: str) -> Optional[dict]:
        """获取缓存数据"""
        entry = self._index.get(cache_id)
        if not entry:
            return None
        if self._is_expired(entry):
            self.delete(cache_id)
            return None
        return entry.get("data")

    def get_by_key(self, key: str, category: str = None) -> List[dict]:
        """按键查找缓存"""
        results = []
        for cid, entry in list(self._index.items()):
            if entry.get("key") == key:
                if category and entry.get("category") != category:
                    continue
                if self._is_expired(entry):
                    self.delete(cid)
                    continue
                results.append(entry.get("data"))
        return results

    def delete(self, cache_id: str) -> bool:
        """删除缓存条目"""
        if cache_id in self._index:
            del self._index[cache_id]
            self._save_index()
            logger.info("Cache deleted", cache_id=cache_id)
            return True
        return False

    def persist(self, cache_id: str) -> Optional[dict]:
        """
        将缓存标记为已持久化（用户确认留存）
        返回数据供调用方写入持久化存储
        """
        entry = self._index.get(cache_id)
        if not entry:
            return None
        entry["persisted"] = True
        entry["persisted_at"] = datetime.now().isoformat()
        self._save_index()
        logger.info("Cache persisted", cache_id=cache_id)
        return entry.get("data")

    def cleanup_expired(self) -> int:
        """清理所有过期缓存，返回清理数量"""
        expired = []
        for cid, entry in list(self._index.items()):
            if self._is_expired(entry) and not entry.get("persisted"):
                expired.append(cid)
        for cid in expired:
            del self._index[cid]
        if expired:
            self._save_index()
            logger.info("Cache cleanup", removed=len(expired))
        return len(expired)

    def list_cache(
        self,
        category: str = None,
        include_expired: bool = False,
        limit: int = 50,
    ) -> List[dict]:
        """列出缓存条目"""
        results = []
        for cid, entry in list(self._index.items()):
            if category and entry.get("category") != category:
                continue
            if not include_expired and self._is_expired(entry):
                continue
            results.append({
                "cache_id": cid,
                "key": entry.get("key"),
                "category": entry.get("category"),
                "created_at": entry.get("created_at"),
                "expires_at": entry.get("expires_at"),
                "persisted": entry.get("persisted", False),
            })
        return results[:limit]

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = len(self._index)
        expired = sum(1 for e in self._index.values() if self._is_expired(e))
        persisted = sum(1 for e in self._index.values() if e.get("persisted"))
        by_category: Dict[str, int] = {}
        for entry in self._index.values():
            cat = entry.get("category", "general")
            by_category[cat] = by_category.get(cat, 0) + 1
        return {
            "total": total,
            "expired": expired,
            "persisted": persisted,
            "active": total - expired,
            "by_category": by_category,
        }

    def _is_expired(self, entry: dict) -> bool:
        expires = entry.get("expires_at")
        if not expires:
            return False
        try:
            return datetime.now() > datetime.fromisoformat(expires)
        except:
            return False

    def _load_index(self) -> dict:
        if os.path.isfile(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)


_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
