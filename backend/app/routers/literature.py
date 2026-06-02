"""
文献结构化检索与管理路由
集成 literature_service，提供 RAG 拆分、结构化查询、临时缓存接口
"""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
import asyncio

from app.services.literature_service import (
    init_db, save_structured_paper, get_structured_paper,
    search_structured_papers, query_paper_field, query_by_dimension,
    delete_structured_paper, get_paper_statistics, list_sources,
    decompose_paper, cache_search_results, get_cached_results, cleanup_temp_cache,
    StructuredPaper, STRUCTURED_FIELDS,
)

router = APIRouter()

# 初始化数据库
init_db()


# ==================== 请求模型 ====================

class DecomposeRequest(BaseModel):
    paper_id: str
    title: str
    full_text: str
    authors: str = ""
    year: int = 0
    journal: str = ""
    doi: str = ""
    source: str = "local"


class QueryDimensionRequest(BaseModel):
    dimension: str
    keywords: str = ""
    limit: int = 10


class CacheResultsRequest(BaseModel):
    query: str
    results: List[dict]


class ExportCitationRequest(BaseModel):
    paper_id: str
    style: str = "gbt7714"


# ==================== 数据库初始化检查 ====================

@router.get("/init-status")
async def init_status():
    """检查文献数据库初始化状态"""
    from app.services.literature_service import DB_PATH
    import os
    return {
        "initialized": os.path.exists(DB_PATH),
        "db_path": DB_PATH,
    }


# ==================== 结构化文献 CRUD ====================

@router.post("/decompose")
async def decompose_literature(req: DecomposeRequest):
    """使用 AI 拆分文献为 11 个结构化字段"""
    try:
        paper = await decompose_paper(
            paper_id=req.paper_id,
            title=req.title,
            full_text=req.full_text,
            authors=req.authors,
            year=req.year,
            journal=req.journal,
            doi=req.doi,
            source=req.source,
        )
        return {"success": True, "paper": paper.__dict__}
    except Exception as e:
        raise HTTPException(500, f"文献拆分失败: {str(e)}")


@router.get("/paper/{paper_id}")
async def get_paper(paper_id: str):
    """获取单篇结构化文献"""
    paper = get_structured_paper(paper_id)
    if not paper:
        raise HTTPException(404, "文献不存在")
    return {"success": True, "paper": paper}


@router.get("/search")
async def search_papers(
    query: str = Query("", description="搜索关键词"),
    source: str = Query("", description="来源过滤：local/database/api"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """搜索结构化文献"""
    result = search_structured_papers(query, source, limit=limit, offset=offset)
    return {"success": True, **result}


@router.get("/query-dimension")
async def query_dimension(
    dimension: str = Query(..., description="维度字段名"),
    keywords: str = Query("", description="关键词过滤"),
    limit: int = Query(10, ge=1, le=50),
):
    """按维度查询文献（用于写作时快速找引用）"""
    if dimension not in STRUCTURED_FIELDS:
        raise HTTPException(400, f"无效维度，可选: {STRUCTURED_FIELDS}")
    results = query_by_dimension(dimension, keywords, limit)
    return {"success": True, "dimension": dimension, "results": results}


@router.get("/field/{paper_id}/{field}")
async def get_paper_field(paper_id: str, field: str):
    """获取文献指定字段内容（用于引用插入）"""
    if field not in STRUCTURED_FIELDS:
        raise HTTPException(400, f"无效字段，可选: {STRUCTURED_FIELDS}")
    content = query_paper_field(paper_id, field)
    return {"success": True, "paper_id": paper_id, "field": field, "content": content}


@router.delete("/paper/{paper_id}")
async def delete_paper(paper_id: str):
    """删除结构化文献"""
    ok = delete_structured_paper(paper_id)
    return {"success": ok, "deleted": paper_id}


# ==================== 统计与来源 ====================

@router.get("/statistics")
async def get_statistics():
    """获取文献库统计信息"""
    return {"success": True, **get_paper_statistics()}


@router.get("/sources")
async def get_sources():
    """获取各来源文献数量"""
    return {"success": True, "sources": list_sources()}


# ==================== 临时缓存管理 ====================

@router.post("/cache-results")
async def cache_results(req: CacheResultsRequest):
    """缓存网络检索结果（30分钟过期）"""
    cache_id = cache_search_results(req.query, req.results)
    return {"success": True, "cache_id": cache_id, "ttl_minutes": 30}


@router.get("/cached-results/{cache_id}")
async def get_cached(cache_id: str):
    """获取缓存的检索结果"""
    results = get_cached_results(cache_id)
    if results is None:
        raise HTTPException(404, "缓存已过期或不存在")
    return {"success": True, "results": results}


@router.post("/cleanup-cache")
async def cleanup_cache():
    """清理过期缓存"""
    cleanup_temp_cache()
    return {"success": True, "message": "过期缓存已清理"}


# ==================== 引用导出 ====================

@router.post("/export-citation")
async def export_citation(req: ExportCitationRequest):
    """导出文献引用格式（GB/T 7714）"""
    from app.services.literature_service import export_paper_citation
    citation = export_paper_citation(req.paper_id, req.style)
    if not citation:
        raise HTTPException(404, "文献不存在")
    return {"success": True, "citation": citation, "style": req.style}


# ==================== 批量操作 ====================

class BatchDecomposeRequest(BaseModel):
    papers: List[DecomposeRequest]


@router.post("/batch-decompose")
async def batch_decompose(req: BatchDecomposeRequest):
    """批量拆分文献（异步）"""
    results = []
    for p in req.papers:
        try:
            paper = await decompose_paper(
                paper_id=p.paper_id,
                title=p.title,
                full_text=p.full_text,
                authors=p.authors,
                year=p.year,
                journal=p.journal,
                doi=p.doi,
                source=p.source,
            )
            results.append({"success": True, "paper": paper.__dict__})
        except Exception as e:
            results.append({"success": False, "paper_id": p.paper_id, "error": str(e)})
    return {"success": True, "results": results, "total": len(results)}
