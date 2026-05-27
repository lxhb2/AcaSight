"""
模板 API 路由 — Word 模板管理、生成、导出
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from app.services.template_service import get_template_service
import structlog

logger = structlog.get_logger()
router = APIRouter()


class TemplateGenerateRequest(BaseModel):
    template_id: str = "gbt7714"
    font_body: Optional[str] = None
    font_heading: Optional[str] = None
    font_size_body: Optional[int] = None
    font_size_heading: Optional[int] = None
    line_spacing: Optional[float] = None
    margin_top: Optional[float] = None
    margin_bottom: Optional[float] = None
    margin_left: Optional[float] = None
    margin_right: Optional[float] = None


class TemplateExportRequest(BaseModel):
    markdown: str
    template_id: str = "gbt7714"
    title: str = "document"


@router.get("")
async def list_templates():
    svc = get_template_service()
    return {"templates": svc.list_templates(), "available": svc.available}


@router.post("/generate")
async def generate_template(req: TemplateGenerateRequest):
    svc = get_template_service()
    if not svc.available:
        raise HTTPException(status_code=503, detail="python-docx 未安装，模板生成不可用")

    import tempfile
    config = req.model_dump(exclude_none=True)
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = svc.generate_template(config, f.name)
            with open(path, "rb") as doc_file:
                data = doc_file.read()
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="template-{req.template_id}.docx"'},
        )
    except Exception as e:
        logger.error("Template generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_with_template(req: TemplateExportRequest):
    svc = get_template_service()
    if not svc.available:
        raise HTTPException(status_code=503, detail="python-docx 未安装，模板导出不可用")

    try:
        data = await svc.export_markdown_to_docx(
            markdown=req.markdown,
            template_id=req.template_id,
            title=req.title,
        )
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{req.title}.docx"'},
        )
    except Exception as e:
        logger.error("Template export failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
