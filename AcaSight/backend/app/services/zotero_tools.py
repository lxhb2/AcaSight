"""
ZoteroTools — 面向 Agent Skill 的 Zotero MCP 工具封装

通过 Streamable HTTP (JSON-RPC 2.0) 与本地 Zotero MCP 插件通信，
提供全部 20 个工具的异步调用方法。

用法（在 Agent skill 中）:
    from app.services.zotero_tools import ZoteroTools
    zotero = ZoteroTools()
    papers = await zotero.search_library(q="transformer", year_range="2022-2024")
"""

import json
import uuid
import structlog
import httpx

logger = structlog.get_logger()


class ZoteroTools:
    """Zotero MCP 全工具集——Agent 直接调用"""

    ZOTERO_MCP_BASE = "http://127.0.0.1:23120"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or self.ZOTERO_MCP_BASE

    # ── 底层 RPC ──────────────────────────────────────

    async def _call(self, tool_name: str, arguments: dict | None = None) -> dict:
        """发送 JSON-RPC tools/call 请求"""
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                **({"arguments": arguments} if arguments else {}),
            },
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/mcp", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    logger.error("zotero_mcp_error", tool=tool_name, error=data["error"])
                    return {"error": data["error"]}
                return data.get("result", data)
        except httpx.ConnectError:
            logger.warning("zotero_mcp_disconnected")
            return {"error": "Zotero MCP 服务未连接", "connected": False}
        except Exception as e:
            logger.error("zotero_mcp_exception", tool=tool_name, error=str(e))
            return {"error": str(e)}

    @staticmethod
    def _extract_text(result: dict) -> str:
        """从 MCP content 数组中提取纯文本"""
        content = result.get("content", [])
        texts = []
        for item in content if isinstance(content, list) else [content]:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", str(item)))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts)

    async def connected(self) -> bool:
        """检查 MCP 连接状态"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/mcp")
                return resp.status_code == 200
        except Exception:
            return False

    # ── 一、搜索与查询（7 个） ────────────────────────

    async def search_library(
        self,
        q: str | None = None,
        title: str | None = None,
        year_range: str | None = None,
        fulltext: str | None = None,
        item_type: str | None = None,
        include_attachments: bool = False,
        mode: str = "standard",
        relevance_scoring: bool = True,
        sort: str = "relevance",
        limit: int = 20,
        offset: int = 0,
        title_operator: str | None = None,
        fulltext_mode: str | None = None,
    ) -> dict:
        args = {k: v for k, v in {
            "q": q, "title": title, "yearRange": year_range,
            "fulltext": fulltext, "itemType": item_type,
            "mode": mode, "relevanceScoring": relevance_scoring,
            "sort": sort, "limit": limit, "offset": offset,
            "titleOperator": title_operator, "fulltextMode": fulltext_mode,
        }.items() if v is not None}
        if include_attachments:
            args["includeAttachments"] = "true"
        return await self._call("search_library", args)

    async def search_annotations(
        self,
        q: str | None = None,
        item_keys: list[str] | None = None,
        types: list[str] | None = None,
        colors: list[str] | None = None,
        tags: list[str] | None = None,
        mode: str = "standard",
    ) -> dict:
        args = {k: v for k, v in {
            "q": q, "itemKeys": item_keys, "types": types,
            "colors": colors, "tags": tags, "mode": mode,
        }.items() if v is not None}
        return await self._call("search_annotations", args)

    async def search_fulltext(
        self,
        q: str,
        item_keys: list[str] | None = None,
        mode: str = "standard",
        context_length: int = 200,
        case_sensitive: bool = False,
    ) -> dict:
        args = {k: v for k, v in {
            "q": q, "itemKeys": item_keys, "mode": mode,
            "contextLength": context_length, "caseSensitive": case_sensitive,
        }.items() if v is not None}
        return await self._call("search_fulltext", args)

    async def search_collections(self, q: str, limit: int = 20) -> dict:
        return await self._call("search_collections", {"q": q, "limit": limit})

    async def get_item_details(self, item_key: str, mode: str = "standard") -> dict:
        return await self._call("get_item_details", {"itemKey": item_key, "mode": mode})

    async def get_item_abstract(self, item_key: str) -> dict:
        return await self._call("get_item_abstract", {"itemKey": item_key})

    async def get_content(
        self,
        item_key: str | None = None,
        attachment_key: str | None = None,
        mode: str = "standard",
        include: dict | None = None,
    ) -> dict:
        args = {"mode": mode}
        if item_key:
            args["itemKey"] = item_key
        if attachment_key:
            args["attachmentKey"] = attachment_key
        if include:
            args["include"] = include
        return await self._call("get_content", args)

    # ── 二、分类管理（4 个） ──────────────────────────

    async def get_collections(self, mode: str = "standard", limit: int = 50, offset: int = 0) -> dict:
        return await self._call("get_collections", {"mode": mode, "limit": limit, "offset": offset})

    async def get_collection_details(self, collection_key: str) -> dict:
        return await self._call("get_collection_details", {"collectionKey": collection_key})

    async def get_collection_items(self, collection_key: str, limit: int = 50, offset: int = 0) -> dict:
        return await self._call("get_collection_items", {"collectionKey": collection_key, "limit": limit, "offset": offset})

    async def get_subcollections(self, collection_key: str, limit: int = 50, recursive: bool = False) -> dict:
        return await self._call("get_subcollections", {"collectionKey": collection_key, "limit": limit, "recursive": recursive})

    # ── 三、语义搜索（3 个） ──────────────────────────

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        language: str | None = None,
    ) -> dict:
        args = {"query": query, "topK": top_k, "minScore": min_score}
        if language:
            args["language"] = language
        return await self._call("semantic_search", args)

    async def find_similar(self, item_key: str, top_k: int = 10, min_score: float = 0.3) -> dict:
        return await self._call("find_similar", {"itemKey": item_key, "topK": top_k, "minScore": min_score})

    async def semantic_status(self) -> dict:
        return await self._call("semantic_status", {})

    # ── 四、全文数据库（1 个） ────────────────────────

    async def fulltext_database(self, action: str, query: str | None = None, limit: int = 20) -> dict:
        args = {"action": action, "limit": limit}
        if query:
            args["query"] = query
        return await self._call("fulltext_database", args)

    # ── 五、写入操作（4 个） ──────────────────────────

    async def write_note(
        self,
        action: str,
        content: str,
        parent_key: str | None = None,
        note_key: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        args = {"action": action, "content": content}
        if parent_key:
            args["parentKey"] = parent_key
        if note_key:
            args["noteKey"] = note_key
        if tags:
            args["tags"] = tags
        return await self._call("write_note", args)

    async def write_tag(self, action: str, item_key: str, tags: list[str]) -> dict:
        return await self._call("write_tag", {"action": action, "itemKey": item_key, "tags": tags})

    async def write_metadata(
        self,
        item_key: str,
        fields: dict | None = None,
        creators: list[dict] | None = None,
    ) -> dict:
        args = {"itemKey": item_key}
        if fields:
            args["fields"] = fields
        if creators:
            args["creators"] = creators
        return await self._call("write_metadata", args)

    async def write_item(
        self,
        action: str,
        item_type: str | None = None,
        fields: dict | None = None,
        creators: list[dict] | None = None,
        tags: list[str] | None = None,
        attachment_keys: list[str] | None = None,
        parent_key: str | None = None,
    ) -> dict:
        args = {"action": action}
        for k, v in {
            "itemType": item_type, "fields": fields, "creators": creators,
            "tags": tags, "attachmentKeys": attachment_keys, "parentKey": parent_key,
        }.items():
            if v is not None:
                args[k] = v
        return await self._call("write_item", args)


# ── 单例 ─────────────────────────────────────────────

_zotero_instance: ZoteroTools | None = None


def get_zotero() -> ZoteroTools:
    """使用示例:
        from app.services.zotero_tools import get_zotero
        papers = await get_zotero().search_library(q="machine learning")
    """
    global _zotero_instance
    if _zotero_instance is None:
        _zotero_instance = ZoteroTools()
    return _zotero_instance
