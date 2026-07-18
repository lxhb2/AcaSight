"""
实验笔记本路由 — Feature 6.6

提供实验的 CRUD、条目管理、关联链接管理等功能。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, and_
from pydantic import BaseModel, Field
from typing import Optional, List
import structlog

from app.database import get_db
from app.models.experiment import Experiment, ExperimentEntry, ExperimentLink

logger = structlog.get_logger()
router = APIRouter()


# ==================== Schemas ====================

class ExperimentCreate(BaseModel):
    """创建实验"""
    title: str = Field(..., max_length=500)
    description: Optional[str] = ''
    category: Optional[str] = ''
    status: Optional[str] = 'planning'
    metadata_json: Optional[dict] = None


class ExperimentUpdate(BaseModel):
    """更新实验"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    metadata_json: Optional[dict] = None


class EntryCreate(BaseModel):
    """创建实验条目"""
    entry_type: str = Field(..., pattern=r'^(text|data|table|image|procedure)$')
    content: Optional[dict] = None
    tags: Optional[List[str]] = None


class EntryUpdate(BaseModel):
    """更新实验条目"""
    entry_type: Optional[str] = None
    content: Optional[dict] = None
    tags: Optional[List[str]] = None


class LinkCreate(BaseModel):
    """创建关联链接"""
    linked_type: str = Field(..., pattern=r'^(literature|document|chart)$')
    linked_id: str
    note: Optional[str] = ''


# ==================== 实验 CRUD ====================

@router.post("/")
async def create_experiment(req: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    """创建实验"""
    exp = Experiment(
        title=req.title,
        description=req.description or '',
        category=req.category or '',
        status=req.status or 'planning',
        metadata_json=req.metadata_json or {},
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return {"success": True, "data": exp.to_dict()}


@router.get("/")
async def list_experiments(
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """列出实验（支持筛选和搜索）"""
    query = select(Experiment)

    # 筛选条件
    conditions = []
    if category:
        conditions.append(Experiment.category == category)
    if status:
        conditions.append(Experiment.status == status)
    if search:
        conditions.append(Experiment.title.ilike(f'%{search}%'))

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_q = select(sa_func.count()).select_from(Experiment)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # 排序和分页
    query = query.order_by(Experiment.updated_at.desc().nulls_last(), Experiment.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    experiments = result.scalars().all()

    return {
        "success": True,
        "data": [exp.to_dict() for exp in experiments],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{exp_id}")
async def get_experiment(exp_id: str, db: AsyncSession = Depends(get_db)):
    """获取实验详情（含条目）"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    # 获取条目
    entries_result = await db.execute(
        select(ExperimentEntry)
        .where(ExperimentEntry.experiment_id == exp_id)
        .order_by(ExperimentEntry.created_at.desc())
    )
    entries = [e.to_dict() for e in entries_result.scalars().all()]

    # 获取链接
    links_result = await db.execute(
        select(ExperimentLink)
        .where(ExperimentLink.experiment_id == exp_id)
        .order_by(ExperimentLink.created_at.desc())
    )
    links = [l.to_dict() for l in links_result.scalars().all()]

    data = exp.to_dict()
    data['entries'] = entries
    data['links'] = links

    return {"success": True, "data": data}


@router.put("/{exp_id}")
async def update_experiment(exp_id: str, req: ExperimentUpdate, db: AsyncSession = Depends(get_db)):
    """更新实验"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    # 验证 status 值
    valid_statuses = ['planning', 'running', 'completed', 'failed']
    if req.status and req.status not in valid_statuses:
        raise HTTPException(400, detail=f"无效状态，可选值: {', '.join(valid_statuses)}")

    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(exp, key, value)

    await db.flush()
    await db.refresh(exp)
    return {"success": True, "data": exp.to_dict()}


@router.delete("/{exp_id}")
async def delete_experiment(exp_id: str, db: AsyncSession = Depends(get_db)):
    """删除实验（级联删除条目和链接）"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    # 删除关联条目
    entries_result = await db.execute(
        select(ExperimentEntry).where(ExperimentEntry.experiment_id == exp_id)
    )
    for entry in entries_result.scalars().all():
        await db.delete(entry)

    # 删除关联链接
    links_result = await db.execute(
        select(ExperimentLink).where(ExperimentLink.experiment_id == exp_id)
    )
    for link in links_result.scalars().all():
        await db.delete(link)

    await db.delete(exp)
    return {"success": True, "message": "实验已删除"}


# ==================== 条目管理 ====================

@router.post("/{exp_id}/entries")
async def add_entry(exp_id: str, req: EntryCreate, db: AsyncSession = Depends(get_db)):
    """添加实验条目"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    entry = ExperimentEntry(
        experiment_id=exp_id,
        entry_type=req.entry_type,
        content=req.content or {},
        tags=req.tags or [],
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return {"success": True, "data": entry.to_dict()}


@router.put("/{exp_id}/entries/{entry_id}")
async def update_entry(exp_id: str, entry_id: str, req: EntryUpdate, db: AsyncSession = Depends(get_db)):
    """更新实验条目"""
    entry = await db.get(ExperimentEntry, entry_id)
    if not entry or entry.experiment_id != exp_id:
        raise HTTPException(404, detail="条目不存在")

    # 验证 entry_type
    valid_types = ['text', 'data', 'table', 'image', 'procedure']
    if req.entry_type and req.entry_type not in valid_types:
        raise HTTPException(400, detail=f"无效类型，可选值: {', '.join(valid_types)}")

    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()
    await db.refresh(entry)
    return {"success": True, "data": entry.to_dict()}


@router.delete("/{exp_id}/entries/{entry_id}")
async def delete_entry(exp_id: str, entry_id: str, db: AsyncSession = Depends(get_db)):
    """删除实验条目"""
    entry = await db.get(ExperimentEntry, entry_id)
    if not entry or entry.experiment_id != exp_id:
        raise HTTPException(404, detail="条目不存在")

    await db.delete(entry)
    return {"success": True, "message": "条目已删除"}


# ==================== 关联链接管理 ====================

@router.post("/{exp_id}/links")
async def add_link(exp_id: str, req: LinkCreate, db: AsyncSession = Depends(get_db)):
    """添加关联链接"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    link = ExperimentLink(
        experiment_id=exp_id,
        linked_type=req.linked_type,
        linked_id=req.linked_id,
        note=req.note or '',
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return {"success": True, "data": link.to_dict()}


@router.get("/{exp_id}/links")
async def get_links(exp_id: str, db: AsyncSession = Depends(get_db)):
    """获取实验的所有关联链接"""
    exp = await db.get(Experiment, exp_id)
    if not exp:
        raise HTTPException(404, detail="实验不存在")

    result = await db.execute(
        select(ExperimentLink)
        .where(ExperimentLink.experiment_id == exp_id)
        .order_by(ExperimentLink.created_at.desc())
    )
    links = [l.to_dict() for l in result.scalars().all()]

    # 按类型分组
    grouped = {
        "literature": [],
        "document": [],
        "chart": [],
    }
    for link in links:
        lt = link.get('linked_type', '')
        if lt in grouped:
            grouped[lt].append(link)

    return {"success": True, "data": {"all": links, "grouped": grouped}}


@router.delete("/{exp_id}/links/{link_id}")
async def delete_link(exp_id: str, link_id: str, db: AsyncSession = Depends(get_db)):
    """删除关联链接"""
    link = await db.get(ExperimentLink, link_id)
    if not link or link.experiment_id != exp_id:
        raise HTTPException(404, detail="链接不存在")

    await db.delete(link)
    return {"success": True, "message": "链接已删除"}
