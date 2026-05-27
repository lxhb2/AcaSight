"""
Zotero 同步桥 - Layer 0
批量导入 Zotero 文献库中的论文到本地 PDF 仓库
"""

import os
import hashlib
import time
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
import structlog

logger = structlog.get_logger()


class ZoteroSyncService:
    """Zotero → AcaSight 文献同步"""

    # Zotero MCP 基础地址
    ZOTERO_MCP_BASE = "http://127.0.0.1:23120"
    ZOTERO_STORAGE = os.path.join(os.path.expandvars(r"%USERPROFILE%"), "Zotero", "storage")

    def __init__(self):
        self._async_client = None

    async def _mcp_call(self, tool_name: str, arguments: dict = None) -> dict:
        """调用 Zotero MCP"""
        import httpx
        import uuid
        import json

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, **({"arguments": arguments} if arguments else {})},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.ZOTERO_MCP_BASE}/mcp", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise HTTPException(502, f"Zotero MCP error: {data['error']}")
                return data.get("result", data)
        except httpx.ConnectError:
            raise HTTPException(503, "Zotero MCP not connected - start Zotero desktop first")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Zotero MCP request failed: {e}")

    async def check_connection(self) -> Dict[str, Any]:
        """检查 Zotero 连接状态"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ZOTERO_MCP_BASE}/mcp")
                return {"connected": resp.status_code == 200}
        except:
            return {"connected": False, "hint": "请先打开 Zotero 桌面应用"}

    async def list_collections(self) -> List[Dict]:
        """列出所有 Zotero 文献集合"""
        result = await self._mcp_call("get_collections", {"mode": "standard"})
        content = result.get("content", [])
        if content and isinstance(content[0], dict):
            return self._parse_content_list(content)
        return []

    async def get_collection_items(self, collection_key: str, limit: int = 100) -> List[Dict]:
        """获取集合中的文献列表"""
        result = await self._mcp_call("get_collection_items", {
            "collectionKey": collection_key,
            "limit": limit,
        })
        content = result.get("content", [])
        if content and isinstance(content[0], dict):
            return self._parse_content_list(content)
        return []

    async def get_item_detail(self, item_key: str) -> Optional[Dict]:
        """获取单篇文献详细信息"""
        import json
        result = await self._mcp_call("get_item_details", {
            "itemKey": item_key,
            "mode": "standard",
        })
        content = result.get("content", [])
        if content and isinstance(content[0], dict):
            text_data = content[0].get("text", "")
            if text_data:
                try:
                    return json.loads(text_data)
                except json.JSONDecodeError:
                    return {"raw": text_data}
        return None

    async def find_pdf_path(self, item_key: str) -> Optional[str]:
        """查找文献对应的 PDF 文件路径"""
        detail = await self.get_item_detail(item_key)
        if not detail:
            return None
        for att in detail.get("attachments", []):
            if att.get("contentType") != "application/pdf":
                continue
            path = att.get("path", "")
            if path and os.path.isfile(path):
                return path
        return None

    async def scan_all_pdfs(self, progress_callback=None) -> Dict[str, Any]:
        """
        扫描 Zotero 中所有 PDF 文献
        返回: {total, papers: [{key, title, year, pdf_path, doi, ...}]}
        """
        papers = []
        seen = set()

        # Step 1: 获取所有集合
        collections = await self.list_collections()
        logger.info("Zotero sync: found collections", count=len(collections))

        # Step 2: 遍历每个集合获取文献
        for col in collections:
            col_key = col.get("key", "")
            col_name = col.get("name", "")
            if not col_key:
                continue

            try:
                items = await self.get_collection_items(col_key, limit=200)
            except Exception as e:
                logger.warning("Zotero sync: skip collection", name=col_name, error=str(e))
                continue

            for item in items:
                item_key = item.get("key", "")
                if not item_key or item_key in seen:
                    continue
                seen.add(item_key)

                item_type = item.get("type", "")
                if item_type not in ("document", "attachment"):
                    continue
                if item_type == "attachment":
                    # 附件类型: 拿 parent 去查
                    parent_key = item.get("parentKey", "")
                    if parent_key and parent_key not in seen:
                        # parent 一定会在后续出现，先跳过
                        continue

                # 获取详情
                try:
                    detail = await self.get_item_detail(item_key)
                except:
                    continue
                if not detail:
                    continue

                # 提取 PDF 路径
                pdf_path = None
                for att in detail.get("attachments", []):
                    if att.get("contentType") == "application/pdf":
                        p = att.get("path", "")
                        if p and os.path.isfile(p):
                            pdf_path = p
                            break

                paper_info = {
                    "zotero_key": item_key,
                    "title": detail.get("title", item.get("title", "Unknown")),
                    "authors": self._extract_authors(detail),
                    "year": detail.get("year", item.get("year")),
                    "doi": detail.get("DOI", detail.get("doi", "")),
                    "journal": detail.get("publicationTitle", ""),
                    "pdf_path": pdf_path,
                    "collection": col_name,
                    "abstract": detail.get("abstractNote", ""),
                    "item_type": detail.get("itemType", item_type),
                }
                papers.append(paper_info)

            if progress_callback:
                progress_callback(len(papers), len(seen))

        # 统计
        with_pdf = sum(1 for p in papers if p["pdf_path"])
        logger.info("Zotero sync: scan complete",
                     total=len(papers), with_pdf=with_pdf)
        return {
            "total_papers": len(papers),
            "papers_with_pdf": with_pdf,
            "papers": papers,
        }

    def _extract_authors(self, detail: dict) -> List[str]:
        """提取作者列表"""
        creators = detail.get("creators", [])
        if not creators:
            return detail.get("authors", [])
        return [f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                for c in creators if c.get("creatorType") == "author"]

    def _parse_content_list(self, content: List[Dict]) -> List[Dict]:
        """解析 MCP 返回的 content 列表"""
        import json
        results = []
        for block in content:
            if block.get("type") == "text":
                try:
                    text = block.get("text", "")
                    if text.strip().startswith("[") or text.strip().startswith("{"):
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            results.extend(parsed)
                        elif isinstance(parsed, dict):
                            results.append(parsed)
                except json.JSONDecodeError:
                    continue
            elif block.get("type") == "resource":
                data = block.get("resource", {})
                text = data.get("text", "")
                if text:
                    try:
                        results.append(json.loads(text))
                    except:
                        continue
        return results


# 全局实例
_sync_service: Optional[ZoteroSyncService] = None


def get_sync_service() -> ZoteroSyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = ZoteroSyncService()
    return _sync_service