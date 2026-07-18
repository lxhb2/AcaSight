"""
格式转换 API — Phase 2

提供 Markdown ↔ docx、Markdown → PDF 等格式转换端点。
基于 pypandoc 实现。
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
import structlog

from app.services.convert_service import get_convert_service

logger = structlog.get_logger()
router = APIRouter()


# ==================== Schemas ====================

class MdToDocxRequest(BaseModel):
    """Markdown 转 docx 请求"""
    markdown: str = Field(..., min_length=1, description="Markdown 内容")
    template_path: Optional[str] = Field(None, description="Pandoc 模板路径")
    reference_docx: Optional[str] = Field(None, description="参考 docx 样式文件路径")


class DocxToMdRequest(BaseModel):
    """docx 转 Markdown 请求"""
    docx_base64: str = Field(..., min_length=1, description="docx 文件的 Base64 编码")


class MdToPdfRequest(BaseModel):
    """Markdown 转 PDF 请求"""
    markdown: str = Field(..., min_length=1, description="Markdown 内容")
    template_path: Optional[str] = Field(None, description="Pandoc 模板路径")


# ==================== Endpoints ====================

@router.post("/md-to-docx")
async def md_to_docx(req: MdToDocxRequest):
    """Markdown 转 docx"""
    svc = get_convert_service()
    if not svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    try:
        data = await svc.md_to_docx(
            md_content=req.markdown,
            template_path=req.template_path,
            reference_docx=req.reference_docx,
        )
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="output.docx"'},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/docx-to-md")
async def docx_to_md(req: DocxToMdRequest):
    """docx 转 Markdown"""
    svc = get_convert_service()
    if not svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    try:
        import base64
        docx_bytes = base64.b64decode(req.docx_base64)
        md_content = await svc.docx_to_md(docx_bytes)
        return Response(
            content=md_content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="output.md"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/md-to-pdf")
async def md_to_pdf(req: MdToPdfRequest):
    """Markdown 转 PDF（需要 XeLaTeX）"""
    svc = get_convert_service()
    if not svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    try:
        data = await svc.md_to_pdf(
            md_content=req.markdown,
            template_path=req.template_path,
        )
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="output.pdf"'},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_convert_templates():
    """列出可用的 Pandoc 模板"""
    svc = get_convert_service()
    templates = svc.list_templates()
    return {"templates": templates, "pandoc_available": svc.available}
