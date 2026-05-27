"""
搜索路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

from app.services.search_service import LiteratureSearchService, CoreClient
from app.database import get_db

router = APIRouter()


@router.get("/")
async def search_papers(
    request: Request,
    q: str = Query(..., description="搜索关键词"),
    sources: Optional[List[str]] = Query(None, description="数据源列表"),
    limit: int = Query(20, ge=1, le=100, description="每源返回数量"),
    year_from: Optional[int] = Query(None, description="起始年份"),
    year_to: Optional[int] = Query(None, description="结束年份"),
):
    search_service: LiteratureSearchService = request.app.state.search_service
    
    results = await search_service.search(
        query=q,
        sources=sources,
        limit=limit,
        year_from=year_from,
        year_to=year_to,
    )
    
    return {
        "query": q,
        "sources": list(results.keys()),
        "results": results,
    }


@router.get("/doi/{doi:path}")
async def get_paper_by_doi(
    request: Request,
    doi: str,
):
    search_service: LiteratureSearchService = request.app.state.search_service
    result = await search_service.get_paper_by_doi(doi)
    if not result:
        return JSONResponse(status_code=404, content={"detail": "文献未找到"})
    return result


class CoreSearchRequest(BaseModel):
    q: str = Field(..., description="搜索关键词")
    title: Optional[str] = Field(None, description="标题筛选")
    authors: Optional[str] = Field(None, description="作者筛选")
    journal: Optional[str] = Field(None, description="期刊筛选")
    year_from: Optional[int] = Field(None, description="起始年份")
    year_to: Optional[int] = Field(None, description="结束年份")
    fulltext: Optional[str] = Field(None, description="全文搜索关键词")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


@router.post("/core")
async def core_search(req: CoreSearchRequest):
    """CORE API 高级搜索 - 全球开放获取论文"""
    core = CoreClient()
    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await core.search_advanced(
            client=client,
            query=req.q,
            title=req.title,
            authors=req.authors,
            journal=req.journal,
            year_from=req.year_from,
            year_to=req.year_to,
            fulltext=req.fulltext,
            limit=req.limit,
            offset=req.offset,
        )
    return result


@router.post("/core/discover")
async def core_discover(doi: Optional[str] = None, title: Optional[str] = None, year: Optional[int] = None):
    """发现论文全文链接"""
    core = CoreClient()
    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await core.discover_fulltext(client=client, doi=doi, title=title, year=year)
    if not result:
        return JSONResponse(status_code=404, content={"detail": "未找到全文链接"})
    return result


@router.get("/sources")
async def get_available_sources():
    return {
        "sources": [
            {
                "id": "core",
                "name": "CORE",
                "description": "全球开放获取论文聚合服务，收录3亿+论文全文",
                "url": "https://core.ac.uk",
            },
            {
                "id": "openalex",
                "name": "OpenAlex",
                "description": "完全开放的学术数据平台",
                "url": "https://openalex.org",
            },
            {
                "id": "semanticscholar",
                "name": "Semantic Scholar",
                "description": "AI 驱动的学术搜索引擎",
                "url": "https://www.semanticscholar.org",
            },
            {
                "id": "crossref",
                "name": "Crossref",
                "description": "DOI 官方注册机构",
                "url": "https://www.crossref.org",
            },
            {
                "id": "europepmc",
                "name": "Europe PMC",
                "description": "欧洲 PubMed Central",
                "url": "https://europepmc.org",
            },
            {
                "id": "arxiv",
                "name": "arXiv",
                "description": "预印本论文库",
                "url": "https://arxiv.org",
            },
        ]
    }