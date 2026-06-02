from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import logging
import json

router = APIRouter(prefix="/literature-review", tags=["literature-review"])
logger = logging.getLogger(__name__)

DIMENSION_MAP = {
    "引言|绪论|研究背景|背景": ["research_background", "research_purpose", "research_status"],
    "理论基础|文献综述|相关工作": ["basic_theory", "research_status", "research_questions"],
    "方法|实验|设计|研究方法": ["research_methods", "basic_theory"],
    "结果|发现|评价|研究结论": ["results_and_evaluation", "innovation_points"],
    "讨论|不足|展望|局限": ["limitations_and_suggestions", "conclusions"],
}


class ReviewRequest(BaseModel):
    topic: str
    paper_ids: list[int]
    style: str = "narrative"


class OutlineRequest(BaseModel):
    topic: str
    paper_ids: list[int]


class SectionRequest(BaseModel):
    topic: str
    section_heading: str
    paper_ids: list[int]


async def _collect_ai_response(messages: list[dict], **kwargs) -> str:
    from app.services.ai_service import ai_service
    response = ""
    async for chunk in ai_service.chat(messages, **kwargs):
        response += chunk
    return response


@router.post("/outline")
async def generate_outline(req: OutlineRequest):
    papers_data = await _fetch_structured_papers(req.paper_ids)
    if not papers_data:
        raise HTTPException(status_code=404, detail="未找到指定文献")

    papers_summary = ""
    for i, p in enumerate(papers_data):
        papers_summary += f"\n{i+1}. {p['title']}"
        if p.get('research_purpose'):
            papers_summary += f"\n   研究目的: {p['research_purpose'][:150]}"
        if p.get('research_methods'):
            papers_summary += f"\n   研究方法: {p['research_methods'][:150]}"
        if p.get('conclusions'):
            papers_summary += f"\n   结论: {p['conclusions'][:150]}"

    prompt = f"""你是学术写作专家。请基于以下{len(papers_data)}篇文献，为综述主题「{req.topic}」生成一个结构化大纲。

要求：
1. 大纲应有3-5个主要章节，每个章节可有2-3个子节
2. 章节标题应体现文献间的逻辑关系（按主题/方法/时间线组织）
3. 每个章节标注使用了哪些文献（用序号引用）
4. 输出JSON格式：{{"sections": [{{"heading": "章节标题", "subsections": [{{"heading": "子节标题", "paper_refs": [1,2]}}], "paper_refs": [1,2]}}]}}

文献列表：
{papers_summary}"""

    response = await _collect_ai_response([{"role": "user", "content": prompt}])

    import re
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            outline = json.loads(json_match.group())
            return {"outline": outline, "paper_count": len(papers_data)}
        except json.JSONDecodeError:
            pass

    return {"outline": {"sections": []}, "paper_count": len(papers_data), "raw": response}


@router.post("/section")
async def write_section(req: SectionRequest):
    papers_data = await _fetch_structured_papers(req.paper_ids)
    if not papers_data:
        raise HTTPException(status_code=404, detail="未找到指定文献")

    relevant_dims = _match_dimensions(req.section_heading)
    context = _gather_section_context(req.section_heading, papers_data, relevant_dims)

    prompt = f"""你是学术写作助手，正在撰写关于「{req.topic}」的文献综述。

当前章节：{req.section_heading}

相关文献数据：
{context}

要求：
1. 撰写该章节的综述内容（500-800字）
2. 每条论述必须标注引用来源，格式如(作者, 年份)
3. 客观比较不同文献的观点和方法
4. 使用学术语言，避免主观评价"""

    content = await _collect_ai_response([{"role": "user", "content": prompt}])

    return {"section": req.section_heading, "content": content}


@router.post("/generate")
async def generate_review_stream(req: ReviewRequest):
    async def event_generator():
        try:
            papers_data = await _fetch_structured_papers(req.paper_ids)
            if not papers_data:
                yield f"data: {json.dumps({'type': 'error', 'message': '未找到指定文献'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'start', 'paper_count': len(papers_data)})}\n\n"

            papers_summary = ""
            for i, p in enumerate(papers_data):
                papers_summary += f"\n{i+1}. {p['title']}"
                if p.get('research_purpose'):
                    papers_summary += f"\n   研究目的: {p['research_purpose'][:150]}"
                if p.get('research_methods'):
                    papers_summary += f"\n   研究方法: {p['research_methods'][:150]}"

            outline_prompt = f"""基于以下{len(papers_data)}篇文献，为「{req.topic}」生成文献综述大纲。
输出JSON: {{"sections": [{{"heading": "标题", "paper_refs": [1]}}]}}

文献：{papers_summary}"""

            outline_response = await _collect_ai_response([{"role": "user", "content": outline_prompt}])

            import re
            json_match = re.search(r'\{.*\}', outline_response, re.DOTALL)
            outline = {"sections": []}
            if json_match:
                try:
                    outline = json.loads(json_match.group())
                except:
                    pass

            yield f"data: {json.dumps({'type': 'outline', 'data': outline})}\n\n"

            sections_content = []
            for section in outline.get("sections", []):
                heading = section.get("heading", "未命名章节")
                relevant_dims = _match_dimensions(heading)
                context = _gather_section_context(heading, papers_data, relevant_dims)

                section_prompt = f"""撰写文献综述章节「{heading}」，主题：{req.topic}

文献数据：{context}

要求：500-800字，每条论述标注(作者,年份)，客观比较不同文献。"""

                section_text = await _collect_ai_response([{"role": "user", "content": section_prompt}])

                sections_content.append({"heading": heading, "content": section_text})
                yield f"data: {json.dumps({'type': 'section_complete', 'heading': heading})}\n\n"

            full_content = f"# {req.topic}\n\n"
            for s in sections_content:
                full_content += f"## {s['heading']}\n\n{s['content']}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'content': full_content, 'sections': sections_content})}\n\n"

        except Exception as e:
            logger.error("Review generation failed", extra={"error": str(e)})
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _fetch_structured_papers(paper_ids: list[int]) -> list[dict]:
    from sqlalchemy import select
    from app.database import get_session
    from app.models.paper import Paper
    from app.models.paper_dimensions import PaperDimensions

    async with get_session() as db:
        result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        papers = result.scalars().all()

        data = []
        for paper in papers:
            item = {
                "id": paper.id,
                "title": paper.title or "",
                "authors": ", ".join(paper.authors) if paper.authors else "",
                "year": paper.year,
                "abstract": paper.abstract or "",
            }

            dim_result = await db.execute(
                select(PaperDimensions).where(PaperDimensions.paper_id == paper.id)
            )
            dims = dim_result.scalar_one_or_none()
            if dims:
                dim_dict = dims.to_dict() if hasattr(dims, 'to_dict') else {}
                item.update(dim_dict)

            data.append(item)

        return data


def _match_dimensions(section_heading: str) -> list[str]:
    for keyword, dims in DIMENSION_MAP.items():
        if any(k in section_heading for k in keyword.split("|")):
            return dims
    return ["abstract", "research_status"]


def _gather_section_context(heading: str, papers: list[dict], target_dims: list[str]) -> str:
    context_parts = []
    for i, paper in enumerate(papers):
        parts = [f"论文{i+1}: {paper.get('title', '')}"]
        for dim in target_dims:
            val = paper.get(dim, "")
            if val:
                dim_label = {
                    "research_background": "研究背景", "research_purpose": "研究目的",
                    "research_status": "研究现状", "research_questions": "研究问题",
                    "basic_theory": "基本理论", "research_methods": "研究方法",
                    "results_and_evaluation": "结果与评价", "innovation_points": "创新点",
                    "limitations_and_suggestions": "局限与建议", "conclusions": "结论",
                    "abstract": "摘要",
                }.get(dim, dim)
                parts.append(f"  {dim_label}: {val[:200]}")
        context_parts.append("\n".join(parts))
    return "\n\n".join(context_parts)
