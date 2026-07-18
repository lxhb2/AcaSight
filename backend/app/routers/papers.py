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
from app.models.paper_dimensions import PaperDimensions
from app.services.dimension_service import extract_dimensions

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
    """创建文献（维度拆分改为异步后台执行，避免阻塞）"""
    from app.services.paper_code_service import generate_paper_code
    paper = Paper(**paper_data.model_dump())

    paper.paper_code = await generate_paper_code(
        title=paper.title, authors=paper.authors, year=paper.year,
        abstract=paper.abstract or "", keywords=paper.keywords,
        db_session=db,
    )

    db.add(paper)
    await db.flush()
    await db.refresh(paper)

    # 维度拆分改为异步后台执行，不阻塞创建请求
    import asyncio
    async def _background_dimension_extract(paper_id: int, pdf_path: str | None, abstract: str | None):
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as bg_db:
                full_text = abstract or ""
                if pdf_path:
                    try:
                        from app.services.pdf_service import pdf_service
                        text_result = await pdf_service.extract_text(pdf_path)
                        full_text = text_result.get("text", full_text)
                    except Exception as e:
                        logger.warning("Background PDF text extraction failed", paper_id=paper_id, error=str(e))
                if full_text and len(full_text.strip()) >= 50:
                    try:
                        await extract_dimensions(paper_id, full_text, bg_db, pdf_path=pdf_path)
                        logger.info("Background dimension extraction completed", paper_id=paper_id)
                    except Exception as e:
                        logger.warning("Background dimension extraction failed", paper_id=paper_id, error=str(e))
        except Exception as e:
            logger.warning("Background task failed", paper_id=paper_id, error=str(e))

    asyncio.create_task(_background_dimension_extract(paper.id, paper.pdf_path, paper.abstract))

    logger.info("Paper created", paper_id=paper.id, title=paper.title)
    return paper.to_dict()


@router.post("/batch")
async def batch_import(
    batch: PaperBatchImport,
    db: AsyncSession = Depends(get_db),
):
    """批量导入文献（自动执行11维度拆分）"""
    from app.services.paper_code_service import generate_paper_code
    created = []
    for paper_data in batch.papers:
        paper = Paper(**paper_data.model_dump())

        paper.paper_code = await generate_paper_code(
            title=paper.title, authors=paper.authors, year=paper.year,
            abstract=paper.abstract or "", keywords=paper.keywords,
            db_session=db,
        )

        db.add(paper)
        created.append(paper)
    await db.flush()
    for p in created:
        await db.refresh(p)

    for p in created:
        full_text = p.abstract or ""
        if p.pdf_path:
            try:
                from app.services.pdf_service import pdf_service
                text_result = await pdf_service.extract_text(p.pdf_path)
                full_text = text_result.get("text", full_text)
            except Exception as e:
                logger.warning("PDF text extraction failed", paper_id=p.id, error=str(e))
        if full_text and len(full_text.strip()) >= 50:
            try:
                await extract_dimensions(p.id, full_text, db, pdf_path=p.pdf_path)
            except Exception as e:
                logger.warning("Auto dimension extraction failed", paper_id=p.id, error=str(e))

    logger.info("Batch import with auto-split", count=len(created))
    return {"imported": len(created), "papers": [p.to_dict() for p in created]}


class BatchSplitRequest(BaseModel):
    paper_ids: List[int]


@router.post("/batch-split")
async def batch_split_dimensions(
    req: BatchSplitRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量对文献执行11维度拆分（补拆分/重新拆分）"""
    results = []
    for pid in req.paper_ids:
        result = await db.execute(select(Paper).where(Paper.id == pid))
        paper = result.scalar_one_or_none()
        if not paper:
            results.append({"paper_id": pid, "status": "not_found"})
            continue

        full_text = paper.abstract or ""
        if paper.pdf_path:
            try:
                from app.services.pdf_service import pdf_service
                text_result = await pdf_service.extract_text(paper.pdf_path)
                full_text = text_result.get("text", full_text)
            except Exception as e:
                logger.warning("PDF extraction failed", paper_id=pid, error=str(e))

        if not full_text or len(full_text.strip()) < 50:
            results.append({"paper_id": pid, "status": "text_too_short"})
            continue

        try:
            dims = await extract_dimensions(pid, full_text, db, pdf_path=paper.pdf_path)
            filled = sum(1 for v in dims.values() if v)
            results.append({"paper_id": pid, "status": "ok", "filled": filled})
        except Exception as e:
            results.append({"paper_id": pid, "status": "error", "error": str(e)})

    return {"results": results, "total": len(req.paper_ids)}


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


@router.get("/by_doi/{doi:path}")
async def get_paper_by_doi(
    doi: str,
    db: AsyncSession = Depends(get_db),
):
    """Chapter D: 按 DOI 查找文献（图谱节点→详情跳转）"""
    # 清理 DOI 前缀
    clean_doi = doi.strip()
    if clean_doi.lower().startswith("http"):
        clean_doi = clean_doi.split("doi.org/")[-1]

    # 精确匹配 + URL 编码差异
    result = await db.execute(
        select(Paper).where(
            or_(
                Paper.doi == clean_doi,
                Paper.doi.ilike(f"%{clean_doi}%"),
            )
        ).limit(1)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail=f"未找到 DOI 为 {clean_doi} 的文献")
    return paper.to_dict()


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


# ==================== 11维度结构化拆分 ====================

class DimensionQuery(BaseModel):
    dimensions: Optional[List[str]] = None


@router.get("/{paper_id}/dimensions")
async def get_dimensions(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取文献的11维度拆分数据"""
    result = await db.execute(
        select(PaperDimensions).where(PaperDimensions.paper_id == paper_id)
    )
    dims = result.scalar_one_or_none()
    if not dims:
        raise HTTPException(status_code=404, detail="该文献尚未进行维度拆分")
    return dims.to_dict()


@router.post("/{paper_id}/dimensions")
async def create_dimensions(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """对文献执行AI 11维度拆分（自动提取全文并拆分，直接存库）"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    full_text = paper.abstract or ""
    if paper.pdf_path:
        try:
            from app.services.pdf_service import pdf_service
            import tempfile
            import os
            pdf_path = paper.pdf_path
            # 如果是 URL，先下载到临时文件
            if pdf_path.startswith(("http://", "https://")):
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(pdf_path, follow_redirects=True)
                        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                                tmp.write(resp.content)
                                pdf_path = tmp.name
                except Exception as e:
                    logger.warning("Failed to download PDF from URL, using abstract", paper_id=paper_id, url=pdf_path, error=str(e))
            text_result = await pdf_service.extract_text(pdf_path)
            full_text = text_result.get("text", full_text)
            # 清理临时文件
            if pdf_path != paper.pdf_path and os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("PDF text extraction failed, using abstract", paper_id=paper_id, error=str(e))

    if not full_text or len(full_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="文献内容不足，无法拆分")

    dimensions = await extract_dimensions(paper_id, full_text, db, pdf_path=paper.pdf_path)
    return {"paper_id": paper_id, "dimensions": dimensions}


@router.post("/{paper_id}/dimensions/preview")
async def preview_dimensions(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """对文献执行AI 11维度拆分（仅预览，不存库）"""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    full_text = paper.abstract or ""
    if paper.pdf_path:
        try:
            from app.services.pdf_service import pdf_service
            import tempfile
            import os
            pdf_path = paper.pdf_path
            # 如果是 URL，先下载到临时文件
            if pdf_path.startswith(("http://", "https://")):
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(pdf_path, follow_redirects=True)
                        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                                tmp.write(resp.content)
                                pdf_path = tmp.name
                except Exception as e:
                    logger.warning("Failed to download PDF from URL, using abstract", paper_id=paper_id, url=pdf_path, error=str(e))
            text_result = await pdf_service.extract_text(pdf_path)
            full_text = text_result.get("text", full_text)
            # 清理临时文件
            if pdf_path != paper.pdf_path and os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("PDF text extraction failed, using abstract", paper_id=paper_id, error=str(e))

    if not full_text or len(full_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="文献内容不足，无法拆分")

    dimensions = await extract_dimensions(paper_id, full_text, db_session=None, pdf_path=paper.pdf_path)
    return {"paper_id": paper_id, "dimensions": dimensions, "preview": True}


class DimensionsConfirm(BaseModel):
    dimensions: dict


@router.post("/{paper_id}/dimensions/confirm")
async def confirm_dimensions(
    paper_id: int,
    body: DimensionsConfirm,
    db: AsyncSession = Depends(get_db),
):
    """确认保存预览的维度拆分数据到数据库"""
    from app.services.dimension_service import _save_dimensions
    record = await _save_dimensions(paper_id, body.dimensions, db)
    return {"paper_id": paper_id, "dimensions": record.to_dict(), "saved": True}


@router.delete("/{paper_id}/dimensions")
async def delete_dimensions(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除文献的维度拆分数据"""
    result = await db.execute(
        select(PaperDimensions).where(PaperDimensions.paper_id == paper_id)
    )
    dims = result.scalar_one_or_none()
    if not dims:
        raise HTTPException(status_code=404, detail="维度数据不存在")
    await db.delete(dims)
    logger.info("Dimensions deleted", paper_id=paper_id)
    return {"detail": "已删除", "paper_id": paper_id}


@router.get("/{paper_id}/dimensions/{dimension_key}")
async def get_single_dimension(
    paper_id: int,
    dimension_key: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文献的某个维度数据"""
    if dimension_key not in PaperDimensions.DIMENSION_KEYS:
        valid = ", ".join(PaperDimensions.DIMENSION_KEYS)
        raise HTTPException(status_code=400, detail=f"无效维度名，可选: {valid}")

    result = await db.execute(
        select(PaperDimensions).where(PaperDimensions.paper_id == paper_id)
    )
    dims = result.scalar_one_or_none()
    if not dims:
        raise HTTPException(status_code=404, detail="该文献尚未进行维度拆分")

    return {
        "paper_id": paper_id,
        "dimension": dimension_key,
        "label": PaperDimensions.DIMENSION_LABELS.get(dimension_key, dimension_key),
        "content": getattr(dims, dimension_key, None),
    }


@router.get("/dimensions/search")
async def search_by_dimension(
    dimension: str = Query(..., description="维度名"),
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """按维度搜索文献（精准引用匹配）"""
    if dimension not in PaperDimensions.DIMENSION_KEYS:
        valid = ", ".join(PaperDimensions.DIMENSION_KEYS)
        raise HTTPException(status_code=400, detail=f"无效维度名，可选: {valid}")

    col = getattr(PaperDimensions, dimension, None)
    if col is None:
        raise HTTPException(status_code=400, detail="维度字段不存在")

    query = select(PaperDimensions).where(col.ilike(f"%{q}%")).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "dimension": dimension,
        "query": q,
        "results": [
            {
                "paper_id": r.paper_id,
                "content": getattr(r, dimension, None),
            }
            for r in records
        ],
        "count": len(records),
    }
