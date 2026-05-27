from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.format_service import get_format_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportRequest(BaseModel):
    markdown: str
    title: str = "document"
    format: str = "docx"
    csl_style: str | None = None
    bibliography: str | None = None


@router.get("/styles")
async def list_csl_styles():
    svc = get_format_service()
    return {"styles": svc.list_csl_styles(), "pandoc_available": svc.available}


@router.post("/export")
async def export_document(req: ExportRequest):
    svc = get_format_service()

    if not svc.available:
        raise HTTPException(status_code=503, detail="Pandoc 未安装，格式导出不可用")

    try:
        if req.format == "docx":
            data = await svc.markdown_to_docx(
                markdown=req.markdown,
                title=req.title,
                csl_style=req.csl_style,
                bibliography=req.bibliography,
            )
            return Response(
                content=data,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{req.title}.docx"'},
            )

        elif req.format == "latex":
            latex = await svc.markdown_to_latex(
                markdown=req.markdown,
                title=req.title,
                csl_style=req.csl_style,
                bibliography=req.bibliography,
            )
            return Response(
                content=latex.encode("utf-8"),
                media_type="application/x-latex",
                headers={"Content-Disposition": f'attachment; filename="{req.title}.tex"'},
            )

        elif req.format == "pdf":
            data = await svc.markdown_to_pdf(
                markdown=req.markdown,
                title=req.title,
                csl_style=req.csl_style,
                bibliography=req.bibliography,
            )
            return Response(
                content=data,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{req.title}.pdf"'},
            )

        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {req.format}")

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
