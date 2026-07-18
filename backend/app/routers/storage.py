"""
全类型数据统一存储路由 - 方向四
/api/storage/ 端点: 素材上传/列表/删除/统计 + 缓存管理 + 绘图数据管理
"""

import os
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from fastapi import Form
from pydantic import BaseModel
from typing import Optional, List

from app.services.storage_service import get_storage_service
from app.services.unified_storage_service import get_unified_storage
from app.services.cache_manager import get_cache_manager

router = APIRouter()


class StorageStats(BaseModel):
    total_pdfs: int
    total_size_bytes: int
    total_size_mb: float
    base_dir: str


class PDFListItem(BaseModel):
    path: str
    rel_path: str
    size: int
    mtime: float


# ==================== PDF 存储 (原有) ====================

@router.get("/stats", response_model=StorageStats)
async def storage_stats():
    """获取 PDF 仓库统计"""
    svc = get_storage_service()
    return svc.get_stats()


@router.get("/list")
async def storage_list(limit: int = 100, offset: int = 0):
    """列出 PDF 文件"""
    svc = get_storage_service()
    pdfs = svc.list_pdfs(limit=limit, offset=offset)
    return {"pdfs": pdfs, "count": len(pdfs)}


@router.post("/upload")
async def storage_upload(file: UploadFile = File(...)):
    """上传 PDF 文件到本地仓库"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    data = await file.read()
    if len(data) < 100:
        raise HTTPException(400, "File too small")

    svc = get_storage_service()
    ok, path, file_hash = svc.save_pdf_bytes(
        data=data,
        filename=file.filename,
    )
    if not ok:
        raise HTTPException(500, "Save failed")

    return {
        "ok": True,
        "filename": file.filename,
        "path": path,
        "rel_path": os.path.relpath(path, svc.base_dir),
        "hash": file_hash,
        "size": len(data),
    }


@router.get("/download/{hash_prefix}")
async def storage_download(hash_prefix: str):
    """通过哈希前缀下载 PDF"""
    svc = get_storage_service()
    target = os.path.join(svc.base_dir, hash_prefix[:2], hash_prefix[2:4], hash_prefix + ".pdf")
    if not os.path.isfile(target):
        for root, _, files in os.walk(svc.base_dir):
            for fn in files:
                if fn.startswith(hash_prefix) and fn.endswith(".pdf"):
                    target = os.path.join(root, fn)
                    break
    if not os.path.isfile(target):
        raise HTTPException(404, "PDF not found")

    data = svc.get_pdf(target)
    return Response(content=data, media_type="application/pdf")


@router.delete("/delete")
async def storage_delete(path: str):
    """删除 PDF 文件"""
    svc = get_storage_service()
    # 路径遍历防护: 确保路径在存储目录内
    real_path = os.path.realpath(path)
    base_dir = os.path.realpath(svc.base_dir)
    if not (real_path.startswith(base_dir + os.sep) or real_path == base_dir):
        raise HTTPException(403, "路径不在允许的存储目录范围内")
    if not os.path.isfile(real_path):
        raise HTTPException(404, "File not found")
    ok = svc.delete_pdf(real_path)
    return {"ok": ok}


# ==================== 统一素材存储 (方向四) ====================

MATERIAL_CATEGORIES = ["images", "data", "reports", "charts", "chart_products", "chart_raw", "templates", "other", "pdf", "image", "svg", "doc"]


@router.get("/unified/stats")
async def unified_stats():
    """获取统一存储统计"""
    svc = get_unified_storage()
    return svc.get_stats()


@router.get("/unified/list")
async def unified_list(
    category: Optional[str] = Query(None, description="分类筛选"),
    paper_id: Optional[int] = Query(None, description="关联论文ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """列出统一存储中的素材"""
    svc = get_unified_storage()
    items = svc.list_materials(category=category, paper_id=paper_id, limit=limit, offset=offset)
    return {"items": items, "count": len(items)}


@router.post("/unified/upload")
async def unified_upload(
    file: UploadFile = File(...),
    category: str = Form("other"),
    paper_id: Optional[int] = Form(None),
):
    """上传素材到统一存储"""
    if category not in MATERIAL_CATEGORIES:
        raise HTTPException(400, f"无效分类，可选: {', '.join(MATERIAL_CATEGORIES)}")

    data = await file.read()
    svc = get_unified_storage()
    result = svc.save_material(
        file_data=data,
        filename=file.filename,
        category=category,
        paper_id=paper_id,
    )
    return result


@router.get("/unified/download/{material_id}")
async def unified_download(material_id: str):
    """下载素材文件"""
    svc = get_unified_storage()
    items = svc.list_materials(limit=500)
    for item in items:
        if material_id in item.get("filename", ""):
            data = svc.get_material(item["path"])
            if data:
                return Response(content=data)
    raise HTTPException(404, "素材不存在")


@router.get("/unified/file")
async def unified_file(path: str = Query(..., description="素材文件路径")):
    """通过路径获取素材文件（用于预览）"""
    import mimetypes
    svc = get_unified_storage()
    # 路径遍历防护
    real_path = os.path.realpath(path)
    base_dir = os.path.realpath(svc.base_dir)
    if not (real_path.startswith(base_dir + os.sep) or real_path == base_dir):
        raise HTTPException(403, "路径不在允许的存储目录范围内")
    if not os.path.isfile(real_path):
        raise HTTPException(404, "文件不存在")

    data = svc.get_material(real_path)
    if data is None:
        raise HTTPException(404, "文件读取失败")

    # 根据扩展名推断 MIME 类型
    mime_type, _ = mimetypes.guess_type(real_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    return Response(content=data, media_type=mime_type)


@router.delete("/unified/delete")
async def unified_delete(path: str):
    """删除素材文件"""
    svc = get_unified_storage()
    # 路径遍历防护: 确保路径在统一存储目录内
    real_path = os.path.realpath(path)
    base_dir = os.path.realpath(svc.base_dir)
    if not (real_path.startswith(base_dir + os.sep) or real_path == base_dir):
        raise HTTPException(403, "路径不在允许的存储目录范围内")
    ok = svc.delete_material(real_path)
    if not ok:
        raise HTTPException(404, "文件不存在")
    return {"ok": True}


@router.post("/unified/chart-product")
async def save_chart_product(
    image: UploadFile = File(..., description="图表成品图片"),
    raw_data: Optional[UploadFile] = File(None, description="原始数据文件"),
    edit_params: Optional[str] = Form(None, description="编辑参数JSON"),
    paper_id: Optional[int] = Form(None),
):
    """保存绘图成品+原始数据+编辑参数（三类数据分离存储）"""
    svc = get_unified_storage()
    image_bytes = await image.read()
    raw_bytes = await raw_data.read() if raw_data else None
    params = json.loads(edit_params) if edit_params else None

    result = svc.save_chart_product(
        image_data=image_bytes,
        filename=image.filename,
        raw_data=raw_bytes,
        edit_params=params,
        paper_id=paper_id,
    )
    return result


# ==================== 临时缓存管理 (方向四) ====================

@router.get("/cache/stats")
async def cache_stats():
    """获取缓存统计"""
    mgr = get_cache_manager()
    return mgr.get_stats()


@router.get("/cache/list")
async def cache_list(
    category: Optional[str] = Query(None, description="分类筛选"),
    limit: int = Query(50, ge=1, le=200),
):
    """列出缓存条目"""
    mgr = get_cache_manager()
    return {"items": mgr.list_cache(category=category, limit=limit)}


@router.post("/cache/put")
async def cache_put(
    key: str = Query(..., description="缓存键"),
    category: str = Query("general", description="分类"),
    ttl_hours: float = Query(24, description="TTL(小时)"),
    data: dict = None,
):
    """存入临时缓存"""
    mgr = get_cache_manager()
    cache_id = mgr.put(key=key, data=data or {}, category=category, ttl_hours=ttl_hours)
    return {"cache_id": cache_id, "key": key}


@router.get("/cache/{cache_id}")
async def cache_get(cache_id: str):
    """获取缓存数据"""
    mgr = get_cache_manager()
    data = mgr.get(cache_id)
    if data is None:
        raise HTTPException(404, "缓存不存在或已过期")
    return {"cache_id": cache_id, "data": data}


@router.post("/cache/{cache_id}/persist")
async def cache_persist(cache_id: str):
    """将缓存标记为已持久化（用户确认留存）"""
    mgr = get_cache_manager()
    data = mgr.persist(cache_id)
    if data is None:
        raise HTTPException(404, "缓存不存在")
    return {"cache_id": cache_id, "data": data, "persisted": True}


@router.delete("/cache/{cache_id}")
async def cache_delete(cache_id: str):
    """删除缓存条目"""
    mgr = get_cache_manager()
    ok = mgr.delete(cache_id)
    return {"ok": ok}


@router.post("/cache/cleanup")
async def cache_cleanup():
    """手动触发过期缓存清理"""
    mgr = get_cache_manager()
    removed = mgr.cleanup_expired()
    return {"removed": removed}