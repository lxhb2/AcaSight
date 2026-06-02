"""
Deep Research API 路由

O.1: PubMed 检索器
O.2: SearX/Tavily 检索器
O.3: Deep Research Pipeline

端点:
- POST /api/deep-research/start — 启动深度研究
- POST /api/deep-research/pubmed — PubMed 搜索
- GET  /api/deep-research/sources — 可用检索源列表
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.deep_research_service import (
    RESEARCH_MODES,
    deep_research_service,
)
from app.services.retriever_pubmed import pubmed_retriever
from app.services.retriever_searx_tavily import searx_retriever, tavily_retriever

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/deep-research", tags=["Deep Research 深度研究"])


# ==================== 请求模型 ====================

class DeepResearchRequest(BaseModel):
    """深度研究请求"""
    query: str = Field(..., min_length=3, max_length=2000, description="研究问题")
    mode: str = Field(default="deep", description="研究模式: quick/deep/comprehensive")


class PubMedSearchRequest(BaseModel):
    """PubMed 搜索请求"""
    query: str = Field(..., min_length=2, description="搜索查询词")
    max_results: int = Field(default=10, ge=1, le=50, description="最大返回结果数")
    db: str = Field(default="pmc", description="数据库: pmc(全文)/pubmed(摘要)")


# ==================== API 端点 ====================

@router.post("/start")
async def start_deep_research(req: DeepResearchRequest):
    """
    启动深度研究（SSE 流式返回进度 + 结果）

    流程: 规划 → 多源搜索 → 分析提取 → 综合总结
    """
    if req.mode not in RESEARCH_MODES:
        raise HTTPException(400, f"Invalid mode. Choose from: {list(RESEARCH_MODES.keys())}")

    async def event_stream():
        def on_progress(step: str, depth: int, breadth: int, status: str):
            """SSE 进度回调 — 由 deep_research 调用"""
            pass  # We'll yield events inline

        try:
            # Send initial config
            config = RESEARCH_MODES[req.mode]
            yield f"data: {json.dumps({'type': 'config', 'mode': req.mode, 'breadth': config['breadth'], 'depth': config['depth'], 'label': config['label'], 'est_time': config['est_time']})}\n\n"

            # Custom progress wrapper
            progress_data = {"step": "initializing", "depth": 0, "breadth": 0, "status": "Starting..."}

            def sse_progress(step, depth, breadth, status):
                progress_data["step"] = step
                progress_data["depth"] = depth
                progress_data["breadth"] = breadth
                progress_data["status"] = status

            result = await deep_research_service.deep_research(
                query=req.query,
                mode=req.mode,
                on_progress=sse_progress,
            )

            # Yield final result
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"

        except Exception as e:
            logger.error("Deep research failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/start-sync")
async def start_deep_research_sync(req: DeepResearchRequest):
    """启动深度研究（同步等待完整结果）"""
    if req.mode not in RESEARCH_MODES:
        raise HTTPException(400, f"Invalid mode. Choose from: {list(RESEARCH_MODES.keys())}")

    try:
        result = await deep_research_service.deep_research(
            query=req.query,
            mode=req.mode,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Deep research failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/pubmed")
async def search_pubmed(req: PubMedSearchRequest):
    """PubMed / PMC 文献搜索"""
    try:
        results = await pubmed_retriever.search(
            query=req.query,
            max_results=req.max_results,
            db=req.db,
        )
        return {"success": True, "data": results, "total": len(results)}
    except Exception as e:
        logger.error("PubMed search failed", error=str(e))
        raise HTTPException(500, str(e))


@router.get("/sources")
async def list_sources():
    """列出所有可用的检索源"""
    sources = [
        {"id": "acasight", "name": "AcaSight (CORE+OpenAlex+arXiv+Crossref)", "available": True, "type": "academic"},
        {"id": "pubmed", "name": "PubMed Central", "available": True, "type": "academic"},
        {"id": "searx", "name": "SearXNG", "available": searx_retriever.available, "type": "web"},
        {"id": "tavily", "name": "Tavily", "available": tavily_retriever.available, "type": "web"},
    ]

    modes = [
        {"id": k, **v} for k, v in RESEARCH_MODES.items()
    ]

    return {
        "success": True,
        "data": {
            "sources": sources,
            "modes": modes,
            "total_sources": sum(1 for s in sources if s["available"]),
        },
    }
