"""
文献11维度结构化拆分服务

优先使用 OpenDataLoader PDF 结构化解析（确定性、快速、无需 AI），
结构化提取不足时回退到 AI 提示词提取。
"""

import json
import asyncio
from typing import Optional
from app.models.paper_dimensions import PaperDimensions
from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()

EXTRACTION_PROMPT = """你是一位学术论文结构化分析专家。请从以下论文全文中，精确提取11个维度的内容。

要求：
1. 每个维度必须从原文中提取，不得编造
2. 如果原文中某维度内容缺失，该维度填空字符串""
3. 每个维度的内容保留原文关键信息，可适当精简但不可丢失核心论点
4. 输出严格为JSON格式，不要包含任何其他文字

11个维度定义：
- abstract: 摘要（原文摘要或从全文概括）
- research_background: 研究背景（问题来源、领域现状）
- research_purpose: 研究目的与意义（要解决什么问题、为什么重要）
- research_status: 研究现状（已有工作的综述）
- research_questions: 研究问题（具体的研究假设或问题）
- basic_theory: 基本理论（理论基础、概念定义、理论框架）
- research_methods: 研究方法（实验设计、数据采集、分析方法）
- results_and_evaluation: 结果与评价（实验结果、性能指标、对比评价）
- innovation_points: 创新点（与已有工作的区别、核心贡献）
- limitations_and_suggestions: 局限与建议（不足之处、未来方向）
- conclusions: 结论（核心结论、研究意义）

论文全文：
---
{content}
---

请输出JSON：
"""

BATCH_EXTRACTION_PROMPT = """你是科研文献解析专家，对批量传入的多篇学术论文进行标准化11维度结构化拆解，严格遵循要求：
1. 输出格式：一篇文献对应一个JSON对象，11个字段严格匹配预设11个维度，禁止多余解释、冗余文本；
2. 内容规则：提炼原文关键信息，精简凝练，不摘抄大段原文，客观总结，不主观扩写；
3. 缺失信息标注空字符串""，不得留白；
4. 多份文献分开输出，放在一个JSON数组中。

固定11维度：abstract, research_background, research_purpose, research_status, research_questions, basic_theory, research_methods, results_and_evaluation, innovation_points, limitations_and_suggestions, conclusions

论文全文：
---
{content}
---

请输出JSON数组：
"""

DETAILED_EXTRACTION_PROMPT = """你是学术论文结构化深度分析专家。针对当前单篇文献深度拆解11个维度，除基础提炼外：
1. 研究缺口、创新点维度优先提炼作者文中提出的不足与未来研究方向；
2. 方法维度细化：实验模型、测试手段、参数范围；
3. 结论维度区分正向成果与局限性；
4. 最终输出单行结构化数据，适配数据库入库格式。
5. 缺失信息标注空字符串""，不得留白。

固定11维度：abstract, research_background, research_purpose, research_status, research_questions, basic_theory, research_methods, results_and_evaluation, innovation_points, limitations_and_suggestions, conclusions

论文全文：
---
{content}
---

请输出JSON：
"""


async def extract_dimensions(paper_id: int, full_text: str, db_session=None, pdf_path: str = None) -> dict:
    """
    对一篇论文执行11维度拆分

    优先级：
    1. OpenDataLoader 结构化解析（确定性、快速、无需 AI）
    2. AI 提示词提取（兜底）

    Args:
        paper_id: 论文ID
        full_text: 论文全文
        db_session: 可选的数据库会话（传入则自动持久化）
        pdf_path: PDF 文件路径（用于结构化解析，可选）

    Returns:
        dict: 11维度提取结果，失败的维度为空字符串
    """
    if not full_text or len(full_text.strip()) < 50:
        logger.warning("Text too short for dimension extraction", paper_id=paper_id)
        return _empty_dimensions()

    dimensions = _empty_dimensions()

    # ── 优先尝试结构化解析 ──
    if pdf_path:
        try:
            dimensions = await _extract_structured(pdf_path)
            filled = sum(1 for v in dimensions.values() if v)
            if filled >= 3:
                logger.info("Structured extraction succeeded", paper_id=paper_id, filled=filled)
                if db_session is not None:
                    await _save_dimensions(paper_id, dimensions, db_session)
                return dimensions
            else:
                logger.info("Structured extraction sparse, falling back to AI", paper_id=paper_id, filled=filled)
        except Exception as e:
            logger.warning("Structured extraction failed, falling back to AI", paper_id=paper_id, error=str(e))

    # ── AI 兜底 ──
    truncated = full_text[:12000]
    prompt = EXTRACTION_PROMPT.format(content=truncated)

    raw_result = {}
    try:
        messages = [
            {"role": "system", "content": "你是学术论文结构化分析专家，只输出JSON，不输出其他内容。"},
            {"role": "user", "content": prompt},
        ]
        response = await _collect_chat_response(messages)
        raw_result = _parse_json_response(response)
    except Exception as e:
        logger.error("AI dimension extraction failed", paper_id=paper_id, error=str(e))
        raw_result = {}

    for key in PaperDimensions.DIMENSION_KEYS:
        dimensions[key] = raw_result.get(key, "") or ""

    filled = sum(1 for v in dimensions.values() if v)
    logger.info("AI dimension extraction done", paper_id=paper_id, filled=filled, total=11)

    if db_session is not None:
        await _save_dimensions(paper_id, dimensions, db_session)

    return dimensions


async def _extract_structured(pdf_path: str) -> dict:
    """使用 OpenDataLoader 结构化解析提取维度（在线程中执行以避免阻塞）"""
    from app.services.structured_pdf_service import (
        is_available, convert_pdf_to_structured, extract_dimensions_from_structured,
    )
    if not is_available():
        return _empty_dimensions()

    result = await asyncio.to_thread(convert_pdf_to_structured, pdf_path)
    document = result.get("document", {})
    if not document:
        return _empty_dimensions()

    return extract_dimensions_from_structured(document)


async def _save_dimensions(paper_id: int, dimensions: dict, db_session) -> PaperDimensions:
    """持久化维度数据到数据库（upsert）"""
    from sqlalchemy import select
    from sqlalchemy.dialects.sqlite import insert

    result = await db_session.execute(
        select(PaperDimensions).where(PaperDimensions.paper_id == paper_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        for key, value in dimensions.items():
            setattr(existing, key, value)
        await db_session.flush()
        await db_session.refresh(existing)
        logger.info("Dimensions updated", paper_id=paper_id)
        return existing
    else:
        record = PaperDimensions(paper_id=paper_id, **dimensions)
        db_session.add(record)
        await db_session.flush()
        await db_session.refresh(record)
        logger.info("Dimensions created", paper_id=paper_id)
        return record


def _parse_json_response(response: str) -> dict | list:
    """从AI响应中解析JSON，容忍markdown代码块包裹"""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        if start < 0:
            start = text.find("{")
        if start == 0 or (start > 0 and text[start] == "["):
            end = text.rfind("]") + 1 if text[start] == "[" else text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        elif start >= 0:
            end = text.rfind("}") + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        logger.warning("Failed to parse JSON from AI response", preview=text[:200])
        return {}


def _empty_dimensions() -> dict:
    return {key: "" for key in PaperDimensions.DIMENSION_KEYS}


async def _collect_chat_response(messages: list) -> str:
    parts = []
    async for chunk in ai_service.chat(messages):
        parts.append(chunk)
    return "".join(parts)


async def extract_dimensions_batch(papers_text: list[dict], db_session=None) -> list[dict]:
    """
    批量多篇文献11维度拆分（精简版提示词）

    Args:
        papers_text: [{"paper_id": 1, "text": "..."}]
        db_session: 可选数据库会话

    Returns:
        list[dict]: 每篇文献的11维度提取结果
    """
    if not papers_text:
        return []

    combined = ""
    for i, item in enumerate(papers_text):
        combined += f"\n=== 文献{i+1} (ID:{item['paper_id']}) ===\n{item['text'][:6000]}\n"

    prompt = BATCH_EXTRACTION_PROMPT.format(content=combined[:20000])

    results = []
    try:
        messages = [
            {"role": "system", "content": "你是科研文献解析专家，只输出JSON数组，不输出其他内容。"},
            {"role": "user", "content": prompt},
        ]
        response = await _collect_chat_response(messages)
        raw = _parse_json_response(response)

        if isinstance(raw, list):
            for item in raw:
                dimensions = {}
                for key in PaperDimensions.DIMENSION_KEYS:
                    dimensions[key] = item.get(key, "") or ""
                results.append(dimensions)
        elif isinstance(raw, dict):
            dimensions = {}
            for key in PaperDimensions.DIMENSION_KEYS:
                dimensions[key] = raw.get(key, "") or ""
            results.append(dimensions)
    except Exception as e:
        logger.error("Batch dimension extraction failed", error=str(e))
        for _ in papers_text:
            results.append(_empty_dimensions())

    if db_session is not None and len(results) == len(papers_text):
        for i, dimensions in enumerate(results):
            await _save_dimensions(papers_text[i]["paper_id"], dimensions, db_session)

    return results


async def extract_dimensions_detailed(paper_id: int, full_text: str, db_session=None) -> dict:
    """
    单篇精细化拆解（用户手动触发深度解析时调用）
    """
    if not full_text or len(full_text.strip()) < 50:
        return _empty_dimensions()

    truncated = full_text[:15000]
    prompt = DETAILED_EXTRACTION_PROMPT.format(content=truncated)

    raw_result = {}
    try:
        messages = [
            {"role": "system", "content": "你是学术论文结构化深度分析专家，只输出JSON，不输出其他内容。"},
            {"role": "user", "content": prompt},
        ]
        response = await _collect_chat_response(messages)
        raw_result = _parse_json_response(response)
    except Exception as e:
        logger.error("Detailed dimension extraction failed", paper_id=paper_id, error=str(e))
        raw_result = {}

    dimensions = {}
    for key in PaperDimensions.DIMENSION_KEYS:
        dimensions[key] = raw_result.get(key, "") or ""

    filled = sum(1 for v in dimensions.values() if v)
    logger.info("Detailed dimension extraction done", paper_id=paper_id, filled=filled, total=11)

    if db_session is not None:
        await _save_dimensions(paper_id, dimensions, db_session)

    return dimensions
