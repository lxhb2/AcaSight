"""
SQLite 持久化翻译缓存 — BabelDOC 风格

特性:
- peewee + SQLite WAL 模式
- 自动清理旧记录（保留最近 50,000 条）
- 冲突时自动替换（ON CONFLICT REPLACE）
- 线程安全（概率触发清理，防锁竞争）
- 操作失败时静默降级
"""

import json
import random
import threading
from pathlib import Path

import peewee
from peewee import SQL, AutoField, CharField, Model, SqliteDatabase, TextField, fn

db = SqliteDatabase(None)
CLEAN_PROBABILITY = 0.001  # 0.1% 概率触发清理
MAX_CACHE_ROWS = 50_000
_cleanup_lock = threading.Lock()


class _TranslationCache(Model):
    id = AutoField()
    translate_engine = CharField(max_length=20)
    translate_engine_params = TextField()
    original_text = TextField()
    translation = TextField()

    class Meta:
        database = db
        constraints = [
            SQL("""
                UNIQUE (translate_engine, translate_engine_params, original_text)
                ON CONFLICT REPLACE
            """)
        ]


class TranslationCache:
    """SQLite 持久化缓存，支持多引擎独立缓存"""

    def __init__(self, translate_engine: str, params: dict | None = None):
        self.translate_engine = translate_engine
        self.params = params or {}
        self._init_db()

    def _init_db(self):
        cache_path = Path("./cache/translation_cache.v1.db")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        db.init(
            str(cache_path),
            pragmas={"journal_mode": "wal", "busy_timeout": 1000},
        )
        db.create_tables([_TranslationCache], safe=True)

    def get(self, text: str) -> str | None:
        """获取缓存，失败时返回 None"""
        try:
            result = _TranslationCache.get_or_none(
                translate_engine=self.translate_engine,
                translate_engine_params=json.dumps(self.params, sort_keys=True),
                original_text=text,
            )
            if result and random.random() < CLEAN_PROBABILITY:
                self._cleanup()
            return result.translation if result else None
        except peewee.OperationalError:
            return None

    def set(self, text: str, translation: str):
        """写入缓存，失败时静默忽略"""
        try:
            _TranslationCache.create(
                translate_engine=self.translate_engine,
                translate_engine_params=json.dumps(self.params, sort_keys=True),
                original_text=text,
                translation=translation,
            )
            if random.random() < CLEAN_PROBABILITY:
                self._cleanup()
        except peewee.OperationalError:
            pass

    def _cleanup(self):
        """清理旧记录，只保留最近 MAX_CACHE_ROWS 条"""
        if not _cleanup_lock.acquire(blocking=False):
            return
        try:
            max_id = _TranslationCache.select(fn.MAX(_TranslationCache.id)).scalar()
            if max_id and max_id > MAX_CACHE_ROWS:
                threshold = max_id - MAX_CACHE_ROWS
                _TranslationCache.delete().where(
                    _TranslationCache.id <= threshold
                ).execute()
        finally:
            _cleanup_lock.release()