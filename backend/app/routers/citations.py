from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter(prefix="/citations", tags=["citations"])
logger = logging.getLogger(__name__)


class ExtractRequest(BaseModel):
    paper_id: int
    format: str = "gbt7714"


class ExtractResponse(BaseModel):
    references: list[dict]
    count: int
    format: str


@router.post("/extract", response_model=ExtractResponse)
async def extract_references(req: ExtractRequest):
    from sqlalchemy import select
    from app.database import get_session
    from app.models.paper import Paper

    async with get_session() as db:
        result = await db.execute(select(Paper).where(Paper.id == req.paper_id))
        paper = result.scalar_one_or_none()
        if not paper:
            raise HTTPException(status_code=404, detail="文献不存在")

        full_text = ""
        if paper.pdf_path:
            try:
                from app.services.pdf_service import pdf_service
                text_result = pdf_service.extract_text(paper.pdf_path)
                full_text = text_result.get("text", "")
            except Exception as e:
                logger.warning("PDF text extraction failed", extra={"paper_id": req.paper_id, "error": str(e)})

        if not full_text:
            raise HTTPException(status_code=400, detail="无法提取PDF文本")

    ref_section = _locate_reference_section(full_text)
    if not ref_section:
        raise HTTPException(status_code=400, detail="未找到参考文献部分")

    from app.services.ai_service import ai_service
    parse_prompt = f"""请将以下参考文献文本解析为结构化JSON数组。每条引用包含以下字段：
- authors: 作者列表（字符串）
- title: 论文/书籍标题
- year: 出版年份
- journal: 期刊/会议名称（如有）
- doi: DOI（如有，否则为null）
- type: 类型(article/conference/book/thesis/other)

参考文献文本：
{ref_section[:6000]}

请直接输出JSON数组，不要包含其他文字。"""

    try:
        import json
        import re
        response = ""
        async for chunk in ai_service.chat([{"role": "user", "content": parse_prompt}]):
            response += chunk

        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            refs = json.loads(json_match.group())
        else:
            refs = json.loads(response)

        if not isinstance(refs, list):
            refs = [refs]
    except Exception as e:
        logger.error("Failed to parse references", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"参考文献解析失败: {str(e)}")

    if req.format != "raw":
        formatted = [_format_citation(ref, req.format) for ref in refs]
        return ExtractResponse(
            references=[{"formatted": f, "raw": refs[i]} for i, f in enumerate(formatted)],
            count=len(formatted),
            format=req.format,
        )

    return ExtractResponse(references=refs, count=len(refs), format="raw")


def _locate_reference_section(text: str) -> str:
    import re
    patterns = [
        r'(?:References|Bibliography|REFERENCES|BIBLIOGRAPHY|参考文献)\s*\n(.*)',
        r'(?:References|Bibliography|REFERENCES|BIBLIOGRAPHY|参考文献)\s*\n\s*\n(.*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()[:8000]
    return ""


def _format_citation(ref: dict, format: str) -> str:
    authors = ref.get("authors", "Unknown")
    title = ref.get("title", "Untitled")
    year = ref.get("year", "n.d.")
    journal = ref.get("journal", "")
    doi = ref.get("doi", "")

    if format == "gbt7714":
        result = f"{authors}. {title}[J]. {journal}, {year}."
        if doi:
            result += f" DOI: {doi}"
        return result
    elif format == "apa":
        result = f"{authors} ({year}). {title}. {journal}."
        if doi:
            result += f" https://doi.org/{doi}"
        return result
    elif format == "ieee":
        result = f'{authors}, "{title}," {journal}, {year}.'
        if doi:
            result += f" doi: {doi}"
        return result
    return f"{authors}. {title}. {journal}, {year}."
