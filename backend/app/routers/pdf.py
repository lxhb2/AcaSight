"""
PDF 路由器 - 融合 PaperPal + pdf-research-assistant 功能
"""

import os
import ipaddress
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Request, Body
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel
from urllib.parse import urlparse

from app.services.pdf_service import pdf_service

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _validate_url(url: str):
    """验证 URL 防止 SSRF 攻击: 仅允许 http/https, 屏蔽私有/内部 IP"""
    parsed = urlparse(url)
    # 仅允许 http/https 协议
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "仅允许 http/https 协议的 URL")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(400, "URL 中缺少主机名")
    # 解析域名对应的 IP，检查是否为私有地址
    import socket
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(400, f"无法解析主机名: {hostname}")
    for family, _, _, _, sockaddr in resolved_ips:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(400, "不允许访问内部/私有网络地址")
        except ValueError:
            continue


class ExtractTextRequest(BaseModel):
    """从 URL 或上传文件提取全文"""
    url: Optional[str] = None
    max_chars: int = 50000


class HashRequest(BaseModel):
    """计算 PDF 哈希"""
    url: Optional[str] = None


class WatermarkRequest(BaseModel):
    file_path: str
    text: str
    opacity: float = 0.3


class MergeRequest(BaseModel):
    file_paths: List[str]


class SplitRequest(BaseModel):
    file_path: str
    pages_per_file: int = 1


class RotateRequest(BaseModel):
    file_path: str
    rotation: int = 90


class SearchRequest(BaseModel):
    file_path: str
    query: str


@router.get("/hash")
async def get_pdf_hash(url: str = Query(..., description="PDF URL 或本地路径")):
    """计算 PDF 文件的 SHA256 哈希（用于批注关联）"""
    import hashlib

    # 本地文件路径
    if not url.startswith(("http://", "https://")):
        full_path = _resolve_path(url)
        sha256 = hashlib.sha256(open(full_path, "rb").read()).hexdigest()
        size = os.path.getsize(full_path)
        return {"hash": sha256, "size": size}

    _validate_url(url)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(400, f"下载失败: HTTP {resp.status_code}")
            sha256 = hashlib.sha256(resp.content).hexdigest()
            return {"hash": sha256, "size": len(resp.content)}
    except httpx.TimeoutException:
        raise HTTPException(408, "下载超时")
    except httpx.HTTPError as e:
        raise HTTPException(400, f"下载失败: {str(e)}")


@router.get("/proxy")
async def proxy_pdf(url: str = Query(..., description="PDF URL or local file path")):
    """代理 PDF 获取 — 支持远程 URL 和本地上传的文件"""
    import httpx
    
    # 本地文件路径：Windows 绝对路径或 DATA_DIR 中的文件
    if not url.startswith(("http://", "https://")):
        full_path = _resolve_path(url)
        if not os.path.exists(full_path):
            raise HTTPException(404, f"文件不存在: {url}")
        return FileResponse(full_path, media_type="application/pdf")
    
    _validate_url(url)
    
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(400, f"下载失败: HTTP {resp.status_code}")
            content_type = resp.headers.get("content-type", "application/pdf")
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                raise HTTPException(400, f"目标不是 PDF 文件: {content_type}")
            return Response(content=resp.content, media_type="application/pdf")
    except httpx.TimeoutException:
        raise HTTPException(408, "下载超时")
    except httpx.HTTPError as e:
        raise HTTPException(400, f"下载失败: {str(e)}")


# ==================== 文件上传 ====================

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """上传 PDF 文件"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")

    file_path = os.path.join(DATA_DIR, file.filename)
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = pdf_service.file_hash(file_path)

    return {
        "filename": file.filename,
        "path": file_path,
        "size": len(content),
        "hash": file_hash,
    }


# ==================== 全文提取（后端 PyMuPDF） ====================

@router.post("/extract-text")
async def extract_full_text(req: ExtractTextRequest):
    """从 URL 或本地路径对应的 PDF 提取全文文本（后端 PyMuPDF，稳定可靠）

    前端打开 PDF 后调用此端点，替代前端 pdf.js onRenderSuccess 逐页提取。
    """
    if not req.url:
        raise HTTPException(400, "必须提供 url 参数")

    # 本地文件路径
    if not req.url.startswith(("http://", "https://")):
        full_path = _resolve_path(req.url)
        result = pdf_service.extract_text(full_path)
        text = result.get("text", "")
        pages = result.get("pages", 0)
        metadata = result.get("metadata", {})
        truncated = len(text) > req.max_chars
        if truncated:
            text = text[:req.max_chars]
        return {
            "text": text,
            "pages": pages,
            "metadata": metadata,
            "truncated": truncated,
            "char_count": len(text),
        }

    # 远程 URL
    import httpx

    _validate_url(req.url)

    # 下载 PDF
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(req.url)
            if resp.status_code != 200:
                raise HTTPException(400, f"下载 PDF 失败: HTTP {resp.status_code}")
            pdf_bytes = resp.content
    except httpx.TimeoutException:
        raise HTTPException(408, "下载 PDF 超时")
    except httpx.HTTPError as e:
        raise HTTPException(400, f"下载 PDF 失败: {str(e)}")

    # 验证是 PDF
    if not pdf_bytes or len(pdf_bytes) < 5 or pdf_bytes[:4] != b"%PDF":
        raise HTTPException(400, "下载的内容不是有效的 PDF")

    # 用 PyMuPDF 提取全文
    result = pdf_service.extract_text_from_bytes(pdf_bytes)
    text = result.get("text", "")
    pages = result.get("pages", 0)
    metadata = result.get("metadata", {})

    # 截断
    truncated = len(text) > req.max_chars
    if truncated:
        text = text[:req.max_chars]

    return {
        "text": text,
        "pages": pages,
        "metadata": metadata,
        "truncated": truncated,
        "char_count": len(text),
    }


# ==================== 文本提取 ====================

@router.get("/{file_path:path}/text")
async def extract_text(file_path: str, page: Optional[int] = None):
    """提取 PDF 文本"""
    full_path = _resolve_path(file_path)

    if page is not None:
        result = pdf_service.extract_page(full_path, page - 1)
    else:
        result = pdf_service.extract_text(full_path)

    return result


# ==================== 读取供AI精读 ====================

@router.get("/{file_path:path}/reading")
async def extract_for_reading(file_path: str, max_chars: int = 8000):
    """提取用于 AI 精读的文本"""
    full_path = _resolve_path(file_path)
    return pdf_service.extract_for_reading(full_path, max_chars)


# ==================== 信息与目录 ====================

@router.get("/{file_path:path}/info")
async def get_pdf_info(file_path: str):
    """获取 PDF 信息"""
    full_path = _resolve_path(file_path)
    return pdf_service.get_info(full_path)


@router.get("/{file_path:path}/toc")
async def get_toc(file_path: str):
    """获取 PDF 目录"""
    full_path = _resolve_path(file_path)
    return {"toc": pdf_service.get_toc(full_path)}


# ==================== 渲染 ====================

@router.get("/{file_path:path}/page/{page_num}/image")
async def render_page(file_path: str, page_num: int, zoom: float = 1.5):
    """渲染 PDF 页面为图片"""
    full_path = _resolve_path(file_path)
    try:
        img_bytes = pdf_service.render_page_image(full_path, page_num - 1, zoom)
        return Response(content=img_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{file_path:path}/thumbnails")
async def get_thumbnails(file_path: str):
    """获取所有页面缩略图"""
    full_path = _resolve_path(file_path)
    thumbs = pdf_service.get_thumbnails(full_path)
    return {
        "total": len(thumbs),
        # 缩略图以 base64 返回（前端方便直接渲染）
        "thumbnails": [t.hex() for t in thumbs],  # 返回 hex 保证传输
    }


# ==================== 搜索 ====================

@router.post("/search")
async def search_in_pdf(req: SearchRequest):
    """在 PDF 中搜索文本"""
    full_path = _resolve_path(req.file_path)
    results = pdf_service.search_text(full_path, req.query)
    return {
        "query": req.query,
        "count": len(results),
        "matches": results,
    }


# ==================== 操作 ====================

@router.post("/merge")
async def merge_pdfs(req: MergeRequest):
    """合并多个 PDF"""
    paths = [_resolve_path(p) for p in req.file_paths]
    output = os.path.join(DATA_DIR, f"merged_{_timestamp()}.pdf")
    result = pdf_service.merge_pdfs(paths, output)
    return {"output": result, "filename": os.path.basename(result)}


@router.post("/split")
async def split_pdf(req: SplitRequest):
    """拆分 PDF"""
    full_path = _resolve_path(req.file_path)
    out_dir = os.path.join(DATA_DIR, f"split_{_timestamp()}")
    results = pdf_service.split_pdf(full_path, out_dir, req.pages_per_file)
    return {"outputs": results, "count": len(results)}


@router.post("/rotate")
async def rotate_pdf(req: RotateRequest):
    """旋转 PDF 页面"""
    full_path = _resolve_path(req.file_path)
    output = os.path.join(DATA_DIR, f"rotated_{_timestamp()}.pdf")
    result = pdf_service.rotate_pages(full_path, output, req.rotation)
    return {"output": result, "filename": os.path.basename(result)}


@router.post("/watermark")
async def add_watermark(req: WatermarkRequest):
    """添加文字水印"""
    full_path = _resolve_path(req.file_path)
    output = os.path.join(DATA_DIR, f"watermarked_{_timestamp()}.pdf")
    result = pdf_service.add_watermark(full_path, output, req.text, req.opacity)
    return {"output": result, "filename": os.path.basename(result)}


@router.get("/{file_path:path}/images")
async def extract_images(file_path: str):
    """提取 PDF 中的图片"""
    full_path = _resolve_path(file_path)
    out_dir = os.path.join(DATA_DIR, f"images_{_timestamp()}")
    results = pdf_service.extract_images(full_path, out_dir)
    return {"images": results, "count": len(results)}


# ==================== 下载 ====================

@router.get("/download/{filename}")
async def download_file(filename: str):
    """下载处理后的 PDF"""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "文件不存在")
    return FileResponse(path, filename=filename, media_type="application/pdf")


# ==================== 工具 ====================

def _resolve_path(file_path: str) -> str:
    """解析文件路径（含路径遍历防护）

    桌面模式（DESKTOP_MODE=1 或请求来自 Tauri）：允许任意本地绝对路径
    服务器模式：仅允许 DATA_DIR 和 workspace 目录
    """
    # 支持传入完整路径或仅文件名
    if os.path.isabs(file_path) and os.path.exists(file_path):
        resolved = os.path.realpath(file_path)
    else:
        # 尝试在 DATA_DIR 中查找
        data_path = os.path.join(DATA_DIR, os.path.basename(file_path))
        if os.path.exists(data_path):
            resolved = os.path.realpath(data_path)
        else:
            # 还尝试在 AcaSight workspace 中找
            workspace_path = os.path.join(DATA_DIR, "..", "..", os.path.basename(file_path))
            if os.path.exists(workspace_path):
                resolved = os.path.realpath(workspace_path)
            else:
                raise HTTPException(404, f"文件不存在: {file_path}")

    # 桌面模式：允许任意本地路径（Tauri 桌面端用户主动选择文件）
    # 检测方式：DESKTOP_MODE 环境变量，或路径是绝对路径（桌面端特征）
    is_desktop = os.environ.get("DESKTOP_MODE", "0") == "1" or os.path.isabs(file_path)
    if is_desktop:
        return resolved

    # 服务器模式：路径遍历防护
    allowed_dirs = [
        os.path.realpath(DATA_DIR),
        os.path.realpath(os.path.join(DATA_DIR, "..", "..")),
    ]
    if not any(resolved.startswith(d + os.sep) or resolved == d for d in allowed_dirs):
        raise HTTPException(403, "路径不在允许的目录范围内")
    return resolved


def _timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")