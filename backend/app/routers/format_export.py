from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from app.services.format_service import get_format_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportRequest(BaseModel):
    markdown: str
    title: str = "document"
    format: str = "docx"
    csl_style: Optional[str] = None
    bibliography: Optional[str] = None


class BibGenerateRequest(BaseModel):
    papers: List[dict]


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

        elif req.format == "html":
            html = await svc.markdown_to_html(
                markdown=req.markdown,
                title=req.title,
                csl_style=req.csl_style,
                bibliography=req.bibliography,
            )
            return Response(
                content=html.encode("utf-8"),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{req.title}.html"'},
            )

        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {req.format}，可选: docx, latex, pdf, html")

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-bib")
async def generate_bibliography(req: BibGenerateRequest):
    """从论文数据生成 BibTeX 文件"""
    svc = get_format_service()
    bib_content = svc.generate_bib_from_papers(req.papers)
    return Response(
        content=bib_content.encode("utf-8"),
        media_type="application/x-bibtex; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="references.bib"'},
    )
