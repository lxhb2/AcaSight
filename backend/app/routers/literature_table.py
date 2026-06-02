from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter(prefix="/literature-table", tags=["literature-table"])
logger = logging.getLogger(__name__)

STRUCTURED_FIELDS = {
    "purpose": "research_purpose",
    "method": "research_methods",
    "results": "results_and_evaluation",
    "innovation": "innovation_points",
    "limitations": "limitations_and_suggestions",
    "background": "research_background",
    "status": "research_status",
    "questions": "research_questions",
    "theory": "basic_theory",
    "conclusions": "conclusions",
}


class TableRequest(BaseModel):
    paper_ids: list[int]
    columns: Optional[list[str]] = None


class TableResponse(BaseModel):
    columns: list[dict]
    data: list[dict]
    paper_count: int


DEFAULT_COLUMNS = [
    {"key": "title", "label": "标题", "source": "metadata"},
    {"key": "authors", "label": "作者", "source": "metadata"},
    {"key": "year", "label": "年份", "source": "metadata"},
    {"key": "purpose", "label": "研究目的", "source": "11维度"},
    {"key": "method", "label": "研究方法", "source": "11维度"},
    {"key": "results", "label": "主要结果", "source": "11维度"},
    {"key": "innovation", "label": "创新点", "source": "11维度"},
    {"key": "limitations", "label": "局限性", "source": "11维度"},
]


@router.post("/generate", response_model=TableResponse)
async def generate_literature_table(req: TableRequest):
    from sqlalchemy import select
    from app.database import get_session
    from app.models.paper import Paper
    from app.models.paper_dimensions import PaperDimensions

    columns = req.columns or [c["key"] for c in DEFAULT_COLUMNS]
    col_defs = []
    for col_key in columns:
        default_col = next((c for c in DEFAULT_COLUMNS if c["key"] == col_key), None)
        if default_col:
            col_defs.append(default_col)
        else:
            col_defs.append({"key": col_key, "label": col_key, "source": "ai"})

    async with get_session() as db:
        result = await db.execute(select(Paper).where(Paper.id.in_(req.paper_ids)))
        papers = result.scalars().all()

        if not papers:
            raise HTTPException(status_code=404, detail="未找到指定文献")

        base_data = []
        for paper in papers:
            row = {"_id": paper.id}

            row["title"] = paper.title or ""
            row["authors"] = ", ".join(paper.authors) if paper.authors else ""
            row["year"] = str(paper.year) if paper.year else ""
            row["journal"] = paper.journal or ""

            dim_result = await db.execute(
                select(PaperDimensions).where(PaperDimensions.paper_id == paper.id)
            )
            dims = dim_result.scalar_one_or_none()

            if dims:
                dim_dict = dims.to_dict() if hasattr(dims, 'to_dict') else {}
                for col in columns:
                    dim_field = STRUCTURED_FIELDS.get(col)
                    if dim_field:
                        row[col] = dim_dict.get(dim_field, "待提取")

            for col in columns:
                if col not in row:
                    row[col] = None

            base_data.append(row)

    ai_columns = [c for c in col_defs if c["source"] == "ai"]
    if ai_columns:
        try:
            from app.services.ai_service import ai_service
            for col_def in ai_columns:
                col_key = col_def["key"]
                papers_summary = "\n".join([
                    f"论文{i+1}: {p.get('title', '')} - {p.get('purpose', p.get('abstract', '无摘要'))[:100]}"
                    for i, p in enumerate(base_data)
                ])
                prompt = f"""基于以下论文信息，为每篇论文填写"{col_def['label']}"列的内容。
要求简洁（50字以内），直接输出每篇论文对应的内容，用换行分隔。

论文列表：
{papers_summary}"""
                response = ""
                async for chunk in ai_service.chat([{"role": "user", "content": prompt}]):
                    response += chunk
                lines = response.strip().split("\n") if isinstance(response, str) else []
                for i, line in enumerate(lines[:len(base_data)]):
                    base_data[i][col_key] = line.strip()
        except Exception as e:
            logger.warning("AI column fill failed", extra={"error": str(e)})
            for row in base_data:
                for col_def in ai_columns:
                    if row.get(col_def["key"]) is None:
                        row[col_def["key"]] = "AI填充失败"

    return TableResponse(columns=col_defs, data=base_data, paper_count=len(papers))


@router.post("/export")
async def export_table(req: TableRequest):
    table = await generate_literature_table(req)

    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([c["label"] for c in table.columns])

    for row in table.data:
        writer.writerow([row.get(c["key"], "") for c in table.columns])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=literature_table.csv"},
    )
