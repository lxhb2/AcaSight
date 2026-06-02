"""
DBLP 会议论文检索 API — 借鉴 PaperHunter

提供 DBLP 在线检索 + 一键导入论文库功能
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import structlog

from app.services.dblp_service import get_dblp_service
from app.database import get_db
from app.models.paper import Paper

logger = structlog.get_logger()
router = APIRouter()


class DBLPImportRequest(BaseModel):
    papers: List[dict]


@router.get("/search")
async def search_dblp(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(30, ge=1, le=100, description="结果数量"),
    year_from: Optional[int] = Query(None, description="起始年份"),
    year_to: Optional[int] = Query(None, description="截止年份"),
    venue: Optional[str] = Query(None, description="会议/期刊名"),
):
    svc = get_dblp_service()
    return await svc.search(q, limit, year_from, year_to, venue)


@router.get("/search-by-author")
async def search_by_author(
    author: str = Query(..., min_length=1, description="作者名"),
    limit: int = Query(30, ge=1, le=100),
):
    svc = get_dblp_service()
    return await svc.search_by_author(author, limit)


@router.get("/conference")
async def conference_papers(
    conference: str = Query(..., min_length=1, description="会议缩写"),
    year: int = Query(..., description="年份"),
    keyword: Optional[str] = Query(None, description="关键词筛选"),
    limit: int = Query(50, ge=1, le=100),
):
    svc = get_dblp_service()
    return await svc.get_conference_papers(conference, year, keyword, limit)


@router.get("/conferences")
async def list_conferences():
    svc = get_dblp_service()
    return {"conferences": svc.get_supported_conferences()}


@router.post("/import")
async def import_from_dblp(
    req: DBLPImportRequest,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    imported = 0
    skipped = 0
    for paper_data in req.papers:
        doi = paper_data.get("doi", "")
        if doi:
            existing = await db.execute(
                select(Paper).where(Paper.doi == doi).limit(1)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

        paper = Paper(
            title=paper_data.get("title", ""),
            authors=paper_data.get("authors", []),
            year=paper_data.get("year"),
            doi=doi or None,
            journal=paper_data.get("venue", ""),
            extra_fields={
                "source": "dblp",
                "dblp_key": paper_data.get("key", ""),
                "dblp_url": paper_data.get("url", ""),
                "type": paper_data.get("type", ""),
            },
        )
        db.add(paper)
        imported += 1

    await db.flush()
    logger.info("DBLP import", imported=imported, skipped=skipped)
    return {"imported": imported, "skipped": skipped}
