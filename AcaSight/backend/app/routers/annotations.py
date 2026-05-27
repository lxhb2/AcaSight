"""
批注路由器 — Chapter D.2

PDF 批注 CRUD + 按 PDF/页面查询。
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.annotation import Annotation

router = APIRouter()


# ==================== Schemas ====================

class AnnotationCreate(BaseModel):
    """创建批注"""
    pdf_hash: str
    paper_id: Optional[int] = None
    annotation_type: str = 'highlight'  # highlight / underline / note / strikethrough
    page: int
    rect: List[float]                    # [x0, y0, x1, y1]
    selected_text: Optional[str] = None
    note: Optional[str] = None
    color: str = '#FFEB3B'


class AnnotationUpdate(BaseModel):
    """更新批注"""
    annotation_type: Optional[str] = None
    rect: Optional[List[float]] = None
    selected_text: Optional[str] = None
    note: Optional[str] = None
    color: Optional[str] = None


# ==================== CRUD ====================

@router.get("")
async def list_annotations(
    pdf_hash: Optional[str] = Query(None, description="按 PDF 哈希筛选"),
    paper_id: Optional[int] = Query(None, description="按文献 ID 筛选"),
    page: Optional[int] = Query(None, description="按页码筛选"),
    annotation_type: Optional[str] = Query(None, description="按批注类型筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取批注列表（按 PDF / 文献 / 页码筛选）"""
    stmt = select(Annotation).order_by(Annotation.page, Annotation.created_at)

    if pdf_hash:
        stmt = stmt.where(Annotation.pdf_hash == pdf_hash)
    if paper_id:
        stmt = stmt.where(Annotation.paper_id == paper_id)
    if page is not None:
        stmt = stmt.where(Annotation.page == page)
    if annotation_type:
        stmt = stmt.where(Annotation.annotation_type == annotation_type)

    result = await db.execute(stmt)
    annotations = result.scalars().all()
    return [a.to_dict() for a in annotations]


@router.post("")
async def create_annotation(
    data: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建批注"""
    # 验证 annotation_type
    valid_types = {'highlight', 'underline', 'note', 'strikethrough'}
    if data.annotation_type not in valid_types:
        raise HTTPException(400, f"无效批注类型: {data.annotation_type}，可选: {valid_types}")

    # 验证 rect
    if not data.rect or len(data.rect) != 4:
        raise HTTPException(400, "rect 必须为 [x0, y0, x1, y1] 格式")

    annotation = Annotation(
        pdf_hash=data.pdf_hash,
        paper_id=data.paper_id,
        annotation_type=data.annotation_type,
        page=data.page,
        rect=data.rect,
        selected_text=data.selected_text,
        note=data.note,
        color=data.color,
    )
    db.add(annotation)
    await db.flush()
    await db.refresh(annotation)
    return annotation.to_dict()


@router.get("/{annotation_id}")
async def get_annotation(
    annotation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单个批注"""
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(404, "批注不存在")
    return annotation.to_dict()


@router.put("/{annotation_id}")
async def update_annotation(
    annotation_id: int,
    data: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新批注"""
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(404, "批注不存在")

    await db.refresh(annotation)

    if data.annotation_type is not None:
        annotation.annotation_type = data.annotation_type
    if data.rect is not None:
        annotation.rect = data.rect
    if data.selected_text is not None:
        annotation.selected_text = data.selected_text
    if data.note is not None:
        annotation.note = data.note
    if data.color is not None:
        annotation.color = data.color

    await db.flush()
    await db.refresh(annotation)
    return annotation.to_dict()


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除批注"""
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(404, "批注不存在")

    await db.delete(annotation)
    await db.flush()
    return {"detail": "已删除", "id": annotation_id}


# ==================== 批量操作 ====================

@router.get("/stats/{pdf_hash}")
async def annotation_stats(
    pdf_hash: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定 PDF 的批注统计"""
    # 总数
    total_result = await db.execute(
        select(sqlfunc.count(Annotation.id)).where(Annotation.pdf_hash == pdf_hash)
    )
    total = total_result.scalar() or 0

    # 按类型统计
    type_result = await db.execute(
        select(Annotation.annotation_type, sqlfunc.count(Annotation.id))
        .where(Annotation.pdf_hash == pdf_hash)
        .group_by(Annotation.annotation_type)
    )
    by_type = {row[0]: row[1] for row in type_result}

    # 按页码统计
    page_result = await db.execute(
        select(Annotation.page, sqlfunc.count(Annotation.id))
        .where(Annotation.pdf_hash == pdf_hash)
        .group_by(Annotation.page)
    )
    by_page = {row[0]: row[1] for row in page_result}

    return {
        "pdf_hash": pdf_hash,
        "total": total,
        "by_type": by_type,
        "by_page": by_page,
    }
