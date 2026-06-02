from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import logging
import json

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
logger = logging.getLogger(__name__)


class BrainstormRequest(BaseModel):
    paper_ids: list[int]
    focus: Optional[str] = None

BRAINSTORM_PROMPT = """基于下方多篇文献的11维度结构化数据（附带文献编号），开展科研选题头脑风暴：

1. 横向对比多篇文献的研究方向、所用方法、现存缺陷；
2. 梳理现有研究空白、未解决问题、方法改进空间；
3. 输出3~5个可行新研究选题，每个选题附带选题依据（对应参考文献编号）；
4. 支持分层思维导图格式输出，可直接落稿为开题大纲。

文献维度数据：
{papers_data}

{focus_instruction}"""


@router.post("/generate")
async def generate_brainstorm(req: BrainstormRequest):
    """生成AI白板头脑风暴"""
    from sqlalchemy import select
    from app.database import get_session
    from app.models.paper import Paper
    from app.models.paper_dimensions import PaperDimensions

    async with get_session() as db:
        result = await db.execute(select(Paper).where(Paper.id.in_(req.paper_ids)))
        papers = result.scalars().all()

        if not papers:
            raise HTTPException(status_code=404, detail="未找到指定文献")

        papers_data = ""
        for i, paper in enumerate(papers):
            entry = f"\n文献{i+1} [{paper.paper_code or f'P{paper.id}'}]: {paper.title}"
            entry += f"\n  作者: {', '.join(paper.authors) if paper.authors else '未知'}"
            entry += f"\n  年份: {paper.year or '未知'}"
            entry += f"\n  期刊: {paper.journal or '未知'}"

            dim_result = await db.execute(
                select(PaperDimensions).where(PaperDimensions.paper_id == paper.id)
            )
            dims = dim_result.scalar_one_or_none()
            if dims:
                dim_dict = dims.to_dict()
                for key, label in PaperDimensions.DIMENSION_LABELS.items():
                    val = dim_dict.get(key, "")
                    if val:
                        entry += f"\n  {label}: {val[:200]}"

            papers_data += entry + "\n"

    focus_instruction = f"请特别聚焦于：{req.focus}" if req.focus else ""
    prompt = BRAINSTORM_PROMPT.format(papers_data=papers_data, focus_instruction=focus_instruction)

    from app.services.ai_service import ai_service
    response_parts = []
    async for chunk in ai_service.chat([
        {"role": "system", "content": "你是科研选题顾问，擅长从多篇文献中挖掘研究空白和创新方向。"},
        {"role": "user", "content": prompt},
    ]):
        response_parts.append(chunk)

    content = "".join(response_parts)

    return {
        "content": content,
        "paper_count": len(papers),
        "focus": req.focus,
    }


@router.post("/generate/stream")
async def generate_brainstorm_stream(req: BrainstormRequest):
    """流式生成AI白板头脑风暴（SSE）"""
    from sqlalchemy import select
    from app.database import get_session
    from app.models.paper import Paper
    from app.models.paper_dimensions import PaperDimensions

    async def event_generator():
        try:
            async with get_session() as db:
                result = await db.execute(select(Paper).where(Paper.id.in_(req.paper_ids)))
                papers = result.scalars().all()

                if not papers:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未找到指定文献'})}\n\n"
                    return

                papers_data = ""
                for i, paper in enumerate(papers):
                    entry = f"\n文献{i+1} [{paper.paper_code or f'P{paper.id}'}]: {paper.title}"
                    entry += f"\n  作者: {', '.join(paper.authors) if paper.authors else '未知'}"
                    entry += f"\n  年份: {paper.year or '未知'}"

                    dim_result = await db.execute(
                        select(PaperDimensions).where(PaperDimensions.paper_id == paper.id)
                    )
                    dims = dim_result.scalar_one_or_none()
                    if dims:
                        dim_dict = dims.to_dict()
                        for key, label in PaperDimensions.DIMENSION_LABELS.items():
                            val = dim_dict.get(key, "")
                            if val:
                                entry += f"\n  {label}: {val[:200]}"

                    papers_data += entry + "\n"

            focus_instruction = f"请特别聚焦于：{req.focus}" if req.focus else ""
            prompt = BRAINSTORM_PROMPT.format(papers_data=papers_data, focus_instruction=focus_instruction)

            yield f"data: {json.dumps({'type': 'start', 'paper_count': len(papers)})}\n\n"

            from app.services.ai_service import ai_service
            full_content = []
            async for chunk in ai_service.chat([
                {"role": "system", "content": "你是科研选题顾问，擅长从多篇文献中挖掘研究空白和创新方向。"},
                {"role": "user", "content": prompt},
            ]):
                full_content.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'content': ''.join(full_content)})}\n\n"

        except Exception as e:
            logger.error("Brainstorm generation failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
