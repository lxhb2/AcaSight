"""
版本历史 + 写作模板 API 路由 (方向U.1+U.3)

版本历史端点:
- POST /api/version-history/save          — 保存版本
- GET  /api/version-history/{document_id} — 获取最新版本
- GET  /api/version-history/{document_id}/list — 版本列表
- POST /api/version-history/compare       — 对比版本
- POST /api/version-history/restore       — 恢复版本

写作模板端点:
- GET  /api/writing-templates/list        — 模板列表
- GET  /api/writing-templates/{id}        — 获取模板
- POST /api/writing-templates/create      — 创建模板
- PUT  /api/writing-templates/{id}        — 更新模板
- DELETE /api/writing-templates/{id}       — 删除模板
- GET  /api/writing-templates/categories  — 分类列表
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.version_history import get_version_history_service
from app.services.writing_template_service import get_writing_template_service

import structlog

logger = structlog.get_logger()

# ── 版本历史路由 ──

vh_router = APIRouter(prefix="/version-history", tags=["版本历史"])


class VersionSaveRequest(BaseModel):
    document_id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")
    note: Optional[str] = Field(None, description="版本备注")
    author: Optional[str] = Field(None, description="作者")


class VersionCompareRequest(BaseModel):
    document_id: str = Field(..., description="文档ID")
    version_a: str = Field(..., description="版本A ID")
    version_b: str = Field(..., description="版本B ID")


class VersionRestoreRequest(BaseModel):
    document_id: str = Field(..., description="文档ID")
    version_id: str = Field(..., description="要恢复的版本ID")
    note: Optional[str] = Field(None, description="恢复备注")


@vh_router.post("/save")
async def save_version(req: VersionSaveRequest):
    service = get_version_history_service()
    result = service.save_version(
        document_id=req.document_id,
        content=req.content,
        note=req.note,
        author=req.author,
    )
    return {"success": True, "data": result}


@vh_router.get("/{document_id}")
async def get_latest_version(document_id: str):
    service = get_version_history_service()
    result = service.get_version(document_id)
    if result is None:
        raise HTTPException(404, f"No versions found for document: {document_id}")
    return {"success": True, "data": result}


@vh_router.get("/{document_id}/list")
async def list_versions(document_id: str):
    service = get_version_history_service()
    versions = service.list_versions(document_id)
    return {"success": True, "data": versions}


@vh_router.get("/{document_id}/{version_id}")
async def get_version(document_id: str, version_id: str):
    service = get_version_history_service()
    result = service.get_version(document_id, version_id)
    if result is None:
        raise HTTPException(404, f"Version not found: {document_id}/{version_id}")
    return {"success": True, "data": result}


@vh_router.post("/compare")
async def compare_versions(req: VersionCompareRequest):
    service = get_version_history_service()
    result = service.compare_versions(req.document_id, req.version_a, req.version_b)
    if result is None:
        raise HTTPException(404, "One or both versions not found")
    return {"success": True, "data": result}


@vh_router.post("/restore")
async def restore_version(req: VersionRestoreRequest):
    service = get_version_history_service()
    result = service.restore_version(req.document_id, req.version_id, note=req.note)
    if result is None:
        raise HTTPException(404, f"Version not found: {req.version_id}")
    return {"success": True, "data": result}


# ── 写作模板路由 ──

wt_router = APIRouter(prefix="/writing-templates", tags=["写作模板"])


class TemplateCreateRequest(BaseModel):
    id: Optional[str] = Field(None, description="模板ID (自动生成)")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field("", description="描述")
    category: Optional[str] = Field("custom", description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    sections: Optional[List[Dict]] = Field(None, description="章节列表")
    style: Optional[Dict[str, Any]] = Field(None, description="样式配置")


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    sections: Optional[List[Dict]] = None
    style: Optional[Dict[str, Any]] = None


@wt_router.get("/list")
async def list_templates(category: Optional[str] = None, tag: Optional[str] = None, search: Optional[str] = None):
    service = get_writing_template_service()
    templates = service.list_templates(category=category, tag=tag, search=search)
    return {"success": True, "data": templates}


@wt_router.get("/categories")
async def get_categories():
    service = get_writing_template_service()
    categories = service.get_categories()
    return {"success": True, "data": categories}


@wt_router.get("/{template_id}")
async def get_template(template_id: str):
    service = get_writing_template_service()
    template = service.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    return {"success": True, "data": template}


@wt_router.post("/create")
async def create_template(req: TemplateCreateRequest):
    service = get_writing_template_service()
    template_data = req.dict(exclude_none=True)
    result = service.create_template(template_data)
    return {"success": True, "data": result}


@wt_router.put("/{template_id}")
async def update_template(template_id: str, req: TemplateUpdateRequest):
    service = get_writing_template_service()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    result = service.update_template(template_id, updates)
    if result is None:
        raise HTTPException(404, f"Custom template not found: {template_id}")
    return {"success": True, "data": result}


@wt_router.delete("/{template_id}")
async def delete_template(template_id: str):
    service = get_writing_template_service()
    success = service.delete_template(template_id)
    if not success:
        raise HTTPException(404, f"Custom template not found: {template_id}")
    return {"success": True, "message": f"Template {template_id} deleted"}
