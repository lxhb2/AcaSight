"""
论文数据库 CRUD API — Chapter C

提供文献的增删改查、标签管理、搜索、统计等功能。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, or_, and_, cast, String
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List
import structlog

from app.database import get_db
from app.models.paper import Paper

logger = structlog.get_logger()
router = APIRouter()


# ==================== Schemas ====================

class PaperCreate(BaseModel):
    """创建文献"""
    title: str = Field(..., max_length=500)
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    semanticscholar_id: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    pdf_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    extra_fields: Optional[dict] = None
    citation_count: Optional[int] = 0
    reference_count: Optional[int] = 0


class PaperUpdate(BaseModel):
    """更新文献（所有字段可选）"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    semanticscholar_id: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    pdf_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    extra_fields: Optional[dict] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    is_favorite: Optional[int] = None
    read_status: Optional[str] = None
    rating: Optional[int] = None


class PaperBatchImport(BaseModel):
    """批量导入文献"""
    papers: List[PaperCreate]


class TagUpdate(BaseModel):
    """标签更新"""
    tags: List[str]


class ReadStatusUpdate(BaseModel):
    """阅读状态更新"""
    read_status: str  # unread / reading / read


class RatingUpdate(BaseModel):
    """评分更新"""
    rating: int = Field(..., ge=0, le=5)


# ==================== CRUD Endpoints ====================

@router.get("")
async def list_papers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    read_status: Optional[str] = Query(None, description="按阅读状态筛选"),
    is_favorite: Optional[int] = Query(None, description="按收藏筛选"),
    year_from: Optional[int] = Query(None, description="年份起始"),
    year_to: Optional[int] = Query(None, description="年份截止"),
    search: Optional[str] = Query(None, description="全文搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取文献列表（分页 + 筛选 + 搜索）"""
    query = select(Paper)

    # ── 筛选 ──
    if tag:
        query = query.where(cast(Paper.tags, String).like(f'%"{tag}"%'))
    if read_status:
        query = query.where(Paper.read_status == read_status)
    if is_favorite is not None:
        query = query.where(Paper.is_favorite == is_favorite)
    if year_from:
        query = query.where(Paper.year >= year_from)
    if year_to:
        query = query.where(Paper.year <= year_to)

    # ── 搜索 ──
    if search:
        search_term = f"%{search}%"
        authors_term = f'%{search}%'
        query = query.where(
            or_(
                Paper.title.ilike(search_term),
                Paper.abstract.ilike(search_term),
                Paper.journal.ilike(search_term),
                cast(Paper.authors, String).ilike(authors_term),
                cast(Paper.keywords, String).ilike(authors_term),
            )
        )

    # ── 排序 ──
    sort_col = getattr(Paper, sort_by, Paper.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # ── 计数 ──
    count_query = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # ── 分页 ──
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    papers = result.scalars().all()

    return {
        "items": [p.to_dict() for p in papers],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("")
async def create_paper(
    paper_data: PaperCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建文献"""
    paper = Paper(**paper_data.model_dump())
    db.add(paper)
    await db.flush()
    await db.refresh(paper)
    logger.info("Paper created", paper_id=paper.id, title=paper.title)
    return paper.to_dict()


@router.post("/batch")
async def batch_import(
    batch: PaperBatchImport,
    db: AsyncSession = Depends(get_db),
):
    """批量导入文献"""
    created = []
    for paper_data in batch.papers:
        paper = Paper(**paper_data.model_dump())
        db.add(paper)
        created.append(paper)
    await db.flush()
    for p in created:
        await db.refresh(p)
    logger.info("Batch import", count=len(created))
    return {"imported": len(created), "papers": [p.to_dict() for p in created]}


@router.get("/tags")
async def list_tags(
    db: AsyncSession = Depends(get_db),
):
    """获取所有标签及计数"""
    result = await db.execute(select(Paper.tags))
    all_tags = result.scalars().all()

    tag_counts: dict[str, int] = {}
    for tags_json in all_tags:
        if not tags_json:
            continue
        if isinstance(tags_json, list):
            for t in tags_json:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        elif isinstance(tags_json, str):
            tag_counts[tags_json] = tag_counts.get(tags_json, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
    return {"tags": [{"name": t, "count": c} for t, c in sorted_tags]}


@router.get("/stats")
async def paper_stats(
    db: AsyncSession = Depends(get_db),
):
    """文献库统计"""
    total = (await db.execute(select(sa_func.count(Paper.id)))).scalar() or 0
    favorites = (await db.execute(
        select(sa_func.count(Paper.id)).where(Paper.is_favorite == 1)
    )).scalar() or 0
    by_status = {}
    for status in ['unread', 'reading', 'read']:
        count = (await db.execute(
            select(sa_func.count(Paper.id)).where(Paper.read_status == status)
        )).scalar() or 0
        by_status[status] = count
    by_year = {}
    year_result = await db.execute(
        select(Paper.year, sa_func.count(Paper.id))
        .where(Paper.year.isnot(None))
        .group_by(Paper.year).order_by(Paper.year.desc())
    )
    for year, count in year_result:
        by_year[str(year)] = count

    return {
        "total": total,
        "favorites": favorites,
        "by_status": by_status,
        "by_year": by_year,
    }


@router.get("/search")
async def search_papers(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """全文搜索文献（标题/摘要/作者/DOI）"""
    search_term = f"%{q}%"
    query = select(Paper).where(
        or_(
            Paper.title.ilike(search_term),
            Paper.abstract.ilike(search_term),
            cast(Paper.authors, String).ilike(search_term),
            Paper.doi.ilike(search_term),
            Paper.journal.ilike(search_term),
            cast(Paper.keywords, String).ilike(search_term),
        )
    ).order_by(Paper.created_at.desc()).limit(limit)

    result = await db.execute(query)
    papers = result.scalars().all()
    return {"query": q, "results": [p.to_dict() for p in papers], "count": len(papers)}


@router.get("/{paper_id}")
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单个文献详情"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    return paper.to_dict()


@router.put("/{paper_id}")
async def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文献"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    update_data = paper_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(paper, key, value)

    await db.flush()
    await db.refresh(paper)
    logger.info("Paper updated", paper_id=paper.id)
    return paper.to_dict()


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除文献"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.delete(paper)
    logger.info("Paper deleted", paper_id=paper_id)
    return {"detail": "已删除", "id": paper_id}


# ==================== 标签管理 ====================

@router.put("/{paper_id}/tags")
async def update_tags(
    paper_id: int,
    tag_data: TagUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文献标签（替换）"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    paper.tags = tag_data.tags
    await db.flush()
    await db.refresh(paper)
    return paper.to_dict()


@router.post("/{paper_id}/tags/{tag_name}")
async def add_tag(
    paper_id: int,
    tag_name: str,
    db: AsyncSession = Depends(get_db),
):
    """添加单个标签"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    current_tags = list(paper.tags or [])
    if tag_name not in current_tags:
        current_tags.append(tag_name)
        paper.tags = current_tags
        await db.flush()
        await db.refresh(paper)
    return paper.to_dict()


@router.delete("/{paper_id}/tags/{tag_name}")
async def remove_tag(
    paper_id: int,
    tag_name: str,
    db: AsyncSession = Depends(get_db),
):
    """移除单个标签"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    current_tags = list(paper.tags or [])
    if tag_name in current_tags:
        current_tags.remove(tag_name)
        paper.tags = current_tags
        await db.flush()
        await db.refresh(paper)
    return paper.to_dict()


# =================── 阅读状态 & 评分 ====================

@router.put("/{paper_id}/read-status")
async def update_read_status(
    paper_id: int,
    status_data: ReadStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新阅读状态"""
    if status_data.read_status not in ('unread', 'reading', 'read'):
        raise HTTPException(status_code=400, detail="无效的阅读状态")

    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    paper.read_status = status_data.read_status
    await db.flush()
    await db.refresh(paper)
    return paper.to_dict()


@router.put("/{paper_id}/rating")
async def update_rating(
    paper_id: int,
    rating_data: RatingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新评分"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    paper.rating = rating_data.rating
    await db.flush()
    await db.refresh(paper)
    return paper.to_dict()


@router.put("/{paper_id}/favorite")
async def toggle_favorite(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """切换收藏状态"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    await db.refresh(paper)
    paper.is_favorite = 0 if paper.is_favorite else 1
    await db.flush()
    await db.refresh(paper)
    return paper.to_dict()
