"""
Zotero MCP 代理路由
通过 Streamable HTTP 协议 (JSON-RPC 2.0) 与本地 Zotero MCP 插件通信
"""

import uuid
import os
import glob
import base64
import json
from urllib.parse import quote
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
import structlog

logger = structlog.get_logger()
router = APIRouter()

ZOTERO_MCP_BASE = "http://127.0.0.1:23120"
ZOTERO_STORAGE_DIR = os.path.join(os.path.expandvars(r"%USERPROFILE%"), "Zotero", "storage")


def _rpc(method: str, params: dict | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        **({"params": params} if params else {}),
    }


async def zotero_mcp_call(tool_name: str, arguments: dict | None = None) -> dict:
    payload = _rpc("tools/call", {"name": tool_name, **({"arguments": arguments} if arguments else {})})
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{ZOTERO_MCP_BASE}/mcp", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise HTTPException(status_code=502, detail=f"Zotero MCP 错误: {data['error']}")
            return data.get("result", data)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Zotero MCP 服务未连接")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Zotero MCP 请求超时")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Zotero MCP 错误: {e.response.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zotero MCP 请求失败: {str(e)}")


async def zotero_list_tools() -> list:
    payload = _rpc("tools/list")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ZOTERO_MCP_BASE}/mcp", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("tools", [])
    except:
        return []


class ZoteroSearchRequest(BaseModel):
    q: Optional[str] = None
    title: Optional[str] = None
    year_range: Optional[str] = Field(None, alias="yearRange")
    fulltext: Optional[str] = None
    item_type: Optional[str] = Field(None, alias="itemType")
    mode: Optional[str] = "standard"
    limit: Optional[int] = 20
    sort: Optional[str] = "relevance"


class ZoteroNoteRequest(BaseModel):
    action: str
    parent_key: Optional[str] = Field(None, alias="parentKey")
    note_key: Optional[str] = Field(None, alias="noteKey")
    content: str
    tags: Optional[List[str]] = None


class ZoteroTagRequest(BaseModel):
    action: str
    item_key: str = Field(alias="itemKey")
    tags: List[str]


class ZoteroMetadataRequest(BaseModel):
    item_key: str = Field(alias="itemKey")
    fields: Optional[dict] = None
    creators: Optional[List[dict]] = None


class ZoteroWriteItemRequest(BaseModel):
    action: str
    item_type: Optional[str] = Field(None, alias="itemType")
    fields: Optional[dict] = None
    creators: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    attachment_keys: Optional[List[str]] = Field(None, alias="attachmentKeys")
    parent_key: Optional[str] = Field(None, alias="parentKey")


class FulltextDatabaseRequest(BaseModel):
    action: str
    query: Optional[str] = None
    item_keys: Optional[List[str]] = Field(None, alias="itemKeys")
    limit: Optional[int] = 20


class SemanticFindSimilarRequest(BaseModel):
    item_key: str = Field(alias="itemKey")
    top_k: Optional[int] = Field(10, alias="topK")
    min_score: Optional[float] = Field(0.3, alias="minScore")


@router.get("/status")
async def zotero_status():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ZOTERO_MCP_BASE}/mcp")
            if resp.status_code == 200:
                tools = await zotero_list_tools()
                return {"connected": True, "url": ZOTERO_MCP_BASE, "tools_count": len(tools)}
        return {"connected": False, "url": ZOTERO_MCP_BASE}
    except:
        return {"connected": False, "url": ZOTERO_MCP_BASE}


@router.get("/tools")
async def zotero_tools():
    tools = await zotero_list_tools()
    return {"tools": tools}


@router.post("/search")
async def zotero_search(req: ZoteroSearchRequest):
    args = {k: v for k, v in req.model_dump(by_alias=True).items() if v is not None}
    return await zotero_mcp_call("search_library", args)


@router.post("/annotations")
async def zotero_search_annotations(
    q: Optional[str] = None,
    colors: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    mode: str = "standard"
):
    args = {k: v for k, v in {"q": q, "colors": colors, "tags": tags, "mode": mode}.items() if v is not None}
    return await zotero_mcp_call("search_annotations", args)


@router.post("/fulltext")
async def zotero_search_fulltext(q: str, item_keys: Optional[List[str]] = None, mode: str = "standard"):
    args = {"q": q, "mode": mode}
    if item_keys:
        args["itemKeys"] = item_keys
    return await zotero_mcp_call("search_fulltext", args)


@router.get("/collections")
async def zotero_get_collections(mode: str = "standard"):
    return await zotero_mcp_call("get_collections", {"mode": mode})


@router.get("/collections/{collection_key}")
async def zotero_get_collection_details(collection_key: str):
    return await zotero_mcp_call("get_collection_details", {"collectionKey": collection_key})


@router.get("/collections/{collection_key}/items")
async def zotero_get_collection_items(collection_key: str, limit: int = 50):
    return await zotero_mcp_call("get_collection_items", {"collectionKey": collection_key, "limit": limit})


@router.get("/items/{item_key}")
async def zotero_get_item_details(item_key: str, mode: str = "standard"):
    return await zotero_mcp_call("get_item_details", {"itemKey": item_key, "mode": mode})


@router.get("/items/{item_key}/abstract")
async def zotero_get_item_abstract(item_key: str):
    return await zotero_mcp_call("get_item_abstract", {"itemKey": item_key})


@router.post("/content")
async def zotero_get_content(item_key: Optional[str] = None, attachment_key: Optional[str] = None, mode: str = "standard"):
    args = {"mode": mode}
    if item_key:
        args["itemKey"] = item_key
    if attachment_key:
        args["attachmentKey"] = attachment_key
    return await zotero_mcp_call("get_content", args)


@router.post("/notes")
async def zotero_write_note(req: ZoteroNoteRequest):
    args = {"action": req.action, "content": req.content}
    if req.parent_key:
        args["parentKey"] = req.parent_key
    if req.note_key:
        args["noteKey"] = req.note_key
    if req.tags:
        args["tags"] = req.tags
    return await zotero_mcp_call("write_note", args)


@router.post("/tags")
async def zotero_write_tag(req: ZoteroTagRequest):
    return await zotero_mcp_call("write_tag", req.model_dump(by_alias=True))


@router.post("/metadata")
async def zotero_write_metadata(req: ZoteroMetadataRequest):
    args = {"itemKey": req.item_key}
    if req.fields:
        args["fields"] = req.fields
    if req.creators:
        args["creators"] = req.creators
    return await zotero_mcp_call("write_metadata", args)


@router.get("/items/{item_key}/pdf")
async def zotero_get_item_pdf(item_key: str):
    """获取 Zotero 文献的 PDF - 通过 MCP 获取附件信息后直读文件"""

    def _extract_mcp_text(result: dict) -> str:
        """从 MCP 响应中提取文本内容，兼容多种返回格式"""
        # 格式1: {"content": [{"type": "text", "text": "..."}]}
        if isinstance(result.get("content"), list):
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                    return item["text"]
        # 格式2: 直接文本
        if isinstance(result.get("text"), str) and result["text"]:
            return result["text"]
        # 格式3: content 是字符串
        if isinstance(result.get("content"), str) and result["content"]:
            return result["content"]
        return ""

    def _resolve_zotero_path(raw_path: str) -> str | None:
        """解析 Zotero 附件路径为绝对路径
        Zotero 路径格式：
        - 绝对路径：C:\\Users\\...\\file.pdf
        - storage 格式：storage:ABCD1234/file.pdf
        - 相对路径（storage 子目录）：ABCD1234/file.pdf
        """
        if not raw_path:
            return None
        # 绝对路径直接返回
        if os.path.isabs(raw_path):
            return raw_path if os.path.isfile(raw_path) else None
        # storage: 前缀格式
        if raw_path.startswith("storage:"):
            rel = raw_path[len("storage:"):]
            abs_path = os.path.join(ZOTERO_STORAGE_DIR, rel)
            return abs_path if os.path.isfile(abs_path) else None
        # 纯文件名或相对路径 → 在 Zotero storage 下搜索
        parts = raw_path.replace("/", os.sep).replace("\\", os.sep).split(os.sep)
        if len(parts) >= 2:
            # 格式：ABCD1234/file.pdf
            abs_path = os.path.join(ZOTERO_STORAGE_DIR, *parts)
            if os.path.isfile(abs_path):
                return abs_path
        # 兜底：在 storage 下递归搜索文件名
        filename = os.path.basename(raw_path)
        for root, dirs, files in os.walk(ZOTERO_STORAGE_DIR):
            if filename in files:
                return os.path.join(root, filename)
        return None

    # Step 1: 通过 MCP 获取条目详情
    result = await zotero_mcp_call("get_item_details", {"itemKey": item_key, "mode": "standard"})

    # Step 2: 提取文本并解析 JSON
    text_data = _extract_mcp_text(result)
    if not text_data:
        raise HTTPException(404, "Zotero MCP 返回数据为空")

    try:
        item = json.loads(text_data)
    except json.JSONDecodeError:
        raise HTTPException(502, f"Zotero MCP 返回数据格式错误，无法解析 JSON")

    # Step 3: 遍历附件，找到 PDF 并读取
    attachments = item.get("attachments", [])
    if not attachments and isinstance(item, dict):
        # 某些 MCP 返回附件在 data 字段下
        attachments = item.get("data", {}).get("attachments", [])

    for att in attachments:
        if att.get("contentType") != "application/pdf":
            continue
        raw_path = att.get("path", "")
        resolved = _resolve_zotero_path(raw_path)
        if not resolved:
            continue
        try:
            with open(resolved, "rb") as f:
                data = f.read()
            if data[:4] == b"%PDF":
                fn = os.path.basename(resolved)
                return Response(
                    content=data,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(fn)}"},
                )
        except OSError:
            continue

    # Step 4: 如果 MCP 方式找不到，尝试直接在 storage 目录搜索
    # 某些条目的 key 就是 storage 子目录名
    storage_subdir = os.path.join(ZOTERO_STORAGE_DIR, item_key)
    if os.path.isdir(storage_subdir):
        for fname in os.listdir(storage_subdir):
            if fname.lower().endswith(".pdf"):
                fpath = os.path.join(storage_subdir, fname)
                try:
                    with open(fpath, "rb") as f:
                        data = f.read()
                    if data[:4] == b"%PDF":
                        return Response(
                            content=data,
                            media_type="application/pdf",
                            headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(fname)}"},
                        )
                except OSError:
                    continue

    raise HTTPException(404, "未找到 PDF 附件")


@router.get("/collections/search")
async def zotero_search_collections(q: str, limit: int = 20):
    """search_collections: 按名称搜索分类"""
    return await zotero_mcp_call("search_collections", {"q": q, "limit": limit})


@router.get("/collections/{collection_key}/subcollections")
async def zotero_get_subcollections(collection_key: str, limit: int = 50, recursive: bool = False):
    """get_subcollections: 获取子分类列表"""
    return await zotero_mcp_call("get_subcollections", {
        "collectionKey": collection_key,
        "limit": limit,
        "recursive": recursive,
    })


@router.get("/items/{item_key}/similar")
async def zotero_find_similar(item_key: str, top_k: int = 10, min_score: float = 0.3):
    """find_similar: 基于指定条目发现语义相似的文献"""
    return await zotero_mcp_call("find_similar", {
        "itemKey": item_key,
        "topK": top_k,
        "minScore": min_score,
    })


@router.get("/semantic-status")
async def zotero_semantic_status():
    """semantic_status: 查看语义搜索服务状态、索引统计和覆盖率"""
    return await zotero_mcp_call("semantic_status", {})


@router.get("/fulltext-database")
async def zotero_fulltext_database(
    action: str,
    query: Optional[str] = None,
    limit: int = 20,
):
    """fulltext_database: 访问缓存的 PDF 全文内容数据库（list/search/get/stats）"""
    args = {"action": action, "limit": limit}
    if query:
        args["query"] = query
    return await zotero_mcp_call("fulltext_database", args)


@router.post("/items")
async def zotero_write_item(req: ZoteroWriteItemRequest):
    """write_item: 创建新的文献条目或重新关联附件"""
    args = {"action": req.action}
    if req.item_type:
        args["itemType"] = req.item_type
    if req.fields:
        args["fields"] = req.fields
    if req.creators:
        args["creators"] = req.creators
    if req.tags:
        args["tags"] = req.tags
    if req.attachment_keys:
        args["attachmentKeys"] = req.attachment_keys
    if req.parent_key:
        args["parentKey"] = req.parent_key
    return await zotero_mcp_call("write_item", args)


@router.post("/semantic-search")
async def zotero_semantic_search(query: str, top_k: int = 10, min_score: float = 0.3):
    return await zotero_mcp_call("semantic_search", {"query": query, "topK": top_k, "minScore": min_score})
