"""
Zotero 同步路由 - Layer 0
/api/sync/ 端点: Zotero 批量导入 / 扫描 / 导入
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.zotero_sync import get_sync_service
from app.services.storage_service import get_storage_service

router = APIRouter()


class SyncScanRequest(BaseModel):
    limit: Optional[int] = None


class SyncImportRequest(BaseModel):
    zotero_keys: List[str]
    auto_vectorize: bool = False


@router.get("/status")
async def sync_status():
    """Zotero 连接状态"""
    svc = get_sync_service()
    status = await svc.check_connection()
    return status


@router.get("/collections")
async def sync_collections():
    """列出 Zotero 集合"""
    svc = get_sync_service()
    try:
        collections = await svc.list_collections()
        return {"collections": collections, "count": len(collections)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/collections/{collection_key}/items")
async def sync_collection_items(collection_key: str, limit: int = 100):
    """获取集合中的文献"""
    svc = get_sync_service()
    try:
        items = await svc.get_collection_items(collection_key, limit=limit)
        return {"items": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/scan")
async def sync_scan_all():
    """扫描 Zotero 中所有 PDF 文献"""
    svc = get_sync_service()
    try:
        result = await svc.scan_all_pdfs()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Scan failed: {e}")


@router.post("/import")
async def sync_import_papers(req: SyncImportRequest):
    """批量导入 Zotero 文献到本地 PDF 仓库"""
    sync_svc = get_sync_service()
    storage_svc = get_storage_service()

    results = []
    imported = 0
    skipped = 0
    failed = 0

    for zotero_key in req.zotero_keys:
        try:
            pdf_path = await sync_svc.find_pdf_path(zotero_key)
            if not pdf_path:
                results.append({"key": zotero_key, "status": "no_pdf"})
                skipped += 1
                continue

            # 导入到本地仓库
            detail = await sync_svc.get_item_detail(zotero_key)
            ok, path, file_hash = storage_svc.save_pdf(pdf_path)
            if not ok:
                results.append({"key": zotero_key, "status": "save_failed"})
                failed += 1
                continue

            imported += 1
            paper_info = {
                "key": zotero_key,
                "status": "imported",
                "hash": file_hash,
                "title": detail.get("title", "") if detail else "",
                "year": detail.get("year") if detail else None,
            }
            results.append(paper_info)

        except HTTPException as e:
            results.append({"key": zotero_key, "status": "error", "error": str(e.detail)})
            failed += 1
        except Exception as e:
            results.append({"key": zotero_key, "status": "error", "error": str(e)})
            failed += 1

    return {
        "total": len(req.zotero_keys),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }