"""
PDF 存储管理路由 - Layer 0
/api/storage/ 端点: 上传 / 列表 / 删除 / 统计
"""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List

from app.services.storage_service import get_storage_service

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
    # 查找匹配的文件
    target = os.path.join(svc.base_dir, hash_prefix[:2], hash_prefix[2:4], hash_prefix + ".pdf")
    if not os.path.isfile(target):
        # 模糊搜索
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
    if not os.path.isfile(path):
        raise HTTPException(404, "File not found")
    ok = svc.delete_pdf(path)
    return {"ok": ok}