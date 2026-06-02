"""
存储模块Agent — 素材归档、缓存管理、维度拆分入库、文件操作

复用现有 unified_storage_service + cache_manager + dimension_service
"""

from app.agent.base_module import BaseModule, ModuleResult, ModuleStatus
from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()


class StorageAgent(BaseModule):
    def __init__(self):
        super().__init__(name="storage", description="存储模块Agent: 素材归档/缓存管理/维度入库/文件操作")

    async def execute(self, task: str, context: dict = None) -> ModuleResult:
        self._status = ModuleStatus.RUNNING
        ctx = context or {}

        try:
            task_lower = task.lower()
            if "上传" in task or "upload" in task_lower or "保存" in task or "归档" in task:
                result = await self._handle_upload(task, ctx)
            elif "缓存" in task or "cache" in task_lower:
                result = await self._handle_cache(task, ctx)
            elif "拆分" in task or "dimension" in task_lower or "入库" in task:
                result = await self._handle_dimension(task, ctx)
            elif "列表" in task or "list" in task_lower or "查询" in task:
                result = await self._handle_list(task, ctx)
            elif "删除" in task or "delete" in task_lower or "清理" in task:
                result = await self._handle_delete(task, ctx)
            elif "统计" in task or "stat" in task_lower or "stats" in task_lower:
                result = await self._handle_stats(task, ctx)
            else:
                result = await self._handle_general(task, ctx)

            self._status = ModuleStatus.COMPLETED
            self._last_result = result
            self._record_history(task, result)
            return result

        except Exception as e:
            self._status = ModuleStatus.FAILED
            result = ModuleResult(success=False, error=str(e))
            self._last_result = result
            self._record_history(task, result)
            logger.error("StorageAgent failed", error=str(e))
            return result

    async def _handle_upload(self, task: str, ctx: dict) -> ModuleResult:
        file_data = ctx.get("file_data")
        filename = ctx.get("filename", "unnamed")
        category = ctx.get("category", "other")
        paper_id = ctx.get("paper_id")
        metadata = ctx.get("metadata", {})

        if not file_data:
            return ModuleResult(success=False, error="需要 file_data")

        try:
            from app.services.unified_storage_service import get_unified_storage
            svc = get_unified_storage()
            result = svc.save_material(
                file_data=file_data,
                filename=filename,
                category=category,
                paper_id=paper_id,
                metadata=metadata,
            )
            return ModuleResult(success=True, data={"type": "upload", "path": result.get("path", ""), "filename": filename, "category": category})
        except Exception as e:
            return ModuleResult(success=False, error=f"上传失败: {e}")

    async def _handle_cache(self, task: str, ctx: dict) -> ModuleResult:
        action = ctx.get("action", "put")

        try:
            from app.services.cache_manager import get_cache_manager
            cache = get_cache_manager()

            if action == "put":
                key = ctx.get("key", "")
                data = ctx.get("data", {})
                category = ctx.get("category", "temp")
                ttl_hours = ctx.get("ttl_hours", 24)
                if not key:
                    return ModuleResult(success=False, error="缓存put需要key")
                cache_id = cache.put(key=key, data=data, category=category, ttl_hours=ttl_hours)
                return ModuleResult(success=True, data={"type": "cache_put", "cache_id": cache_id, "key": key})

            elif action == "get":
                cache_id = ctx.get("cache_id", "")
                if not cache_id:
                    return ModuleResult(success=False, error="缓存get需要cache_id")
                entry = cache.get(cache_id)
                if entry:
                    return ModuleResult(success=True, data={"type": "cache_get", "entry": {"id": entry.id, "key": entry.key, "category": entry.category, "data": entry.data}})
                return ModuleResult(success=False, error="缓存条目不存在或已过期")

            elif action == "persist":
                cache_id = ctx.get("cache_id", "")
                if not cache_id:
                    return ModuleResult(success=False, error="缓存persist需要cache_id")
                success = cache.persist(cache_id)
                return ModuleResult(success=success, data={"type": "cache_persist", "cache_id": cache_id})

            elif action == "cleanup":
                removed = cache.cleanup_expired()
                return ModuleResult(success=True, data={"type": "cache_cleanup", "removed_count": removed})

            else:
                return ModuleResult(success=False, error=f"未知缓存操作: {action}")

        except Exception as e:
            return ModuleResult(success=False, error=f"缓存操作失败: {e}")

    async def _handle_dimension(self, task: str, ctx: dict) -> ModuleResult:
        paper_id = ctx.get("paper_id")
        full_text = ctx.get("full_text", "")
        if not paper_id or not full_text:
            return ModuleResult(success=False, error="需要 paper_id 和 full_text")

        try:
            from app.services.dimension_service import extract_dimensions
            dimensions = await extract_dimensions(paper_id, full_text)
            return ModuleResult(success=True, data={"type": "dimension", "paper_id": paper_id, "dimensions": dimensions})
        except Exception as e:
            return ModuleResult(success=False, error=f"维度拆分入库失败: {e}")

    async def _handle_list(self, task: str, ctx: dict) -> ModuleResult:
        category = ctx.get("category", "all")
        paper_id = ctx.get("paper_id")
        limit = ctx.get("limit", 50)
        offset = ctx.get("offset", 0)

        try:
            from app.services.unified_storage_service import get_unified_storage
            svc = get_unified_storage()
            items = svc.list_materials(category=category, paper_id=paper_id, limit=limit, offset=offset)
            return ModuleResult(success=True, data={"type": "list", "items": items, "count": len(items), "category": category})
        except Exception as e:
            return ModuleResult(success=False, error=f"列表查询失败: {e}")

    async def _handle_delete(self, task: str, ctx: dict) -> ModuleResult:
        material_id = ctx.get("material_id")
        if not material_id:
            return ModuleResult(success=False, error="需要 material_id")

        try:
            from app.services.unified_storage_service import get_unified_storage
            svc = get_unified_storage()
            success = svc.delete_material(material_id)
            return ModuleResult(success=success, data={"type": "delete", "material_id": material_id})
        except Exception as e:
            return ModuleResult(success=False, error=f"删除失败: {e}")

    async def _handle_stats(self, task: str, ctx: dict) -> ModuleResult:
        try:
            from app.services.unified_storage_service import get_unified_storage
            from app.services.cache_manager import get_cache_manager
            storage = get_unified_storage()
            cache = get_cache_manager()
            storage_stats = storage.get_stats() if hasattr(storage, 'get_stats') else {}
            cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
            return ModuleResult(success=True, data={"type": "stats", "storage": storage_stats, "cache": cache_stats})
        except Exception as e:
            return ModuleResult(success=False, error=f"统计查询失败: {e}")

    async def _handle_general(self, task: str, ctx: dict) -> ModuleResult:
        messages = [
            {"role": "system", "content": "你是学术素材管理助手，擅长文件归档、缓存管理和数据组织。"},
            {"role": "user", "content": task},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "general", "response": response})
