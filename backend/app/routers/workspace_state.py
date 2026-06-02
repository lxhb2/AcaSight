"""
工作区状态 API 路由 (方向T.1)

端点:
- POST /api/workspace-state/save          — 保存工作区状态
- POST /api/workspace-state/restore        — 恢复工作区状态
- GET  /api/workspace-state/list           — 列出所有工作区
- DELETE /api/workspace-state/{workspace_id} — 删除工作区
- GET  /api/workspace-state/{workspace_id}/snapshots — 获取快照列表
- POST /api/workspace-state/export          — 导出工作区
- POST /api/workspace-state/import          — 导入工作区
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.workspace_state import get_workspace_state_service

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/workspace-state", tags=["工作区状态"])


# ── 请求模型 ──

class WorkspaceSaveRequest(BaseModel):
    workspace_id: str = Field(..., description="工作区ID")
    state: Dict[str, Any] = Field(..., description="工作区状态数据")
    name: Optional[str] = Field(None, description="工作区名称")
    tags: Optional[List[str]] = Field(None, description="标签")


class WorkspaceRestoreRequest(BaseModel):
    workspace_id: str = Field(..., description="工作区ID")
    snapshot_timestamp: Optional[float] = Field(None, description="快照时间戳(None=最新)")


class WorkspaceExportRequest(BaseModel):
    workspace_id: str = Field(..., description="工作区ID")
    include_snapshots: bool = Field(False, description="是否包含历史快照")


class WorkspaceImportRequest(BaseModel):
    workspace_id: str = Field(..., description="目标工作区ID")
    data: Dict[str, Any] = Field(..., description="导入数据")
    overwrite: bool = Field(False, description="是否覆盖已有数据")


# ── API 端点 ──

@router.post("/save")
async def save_workspace(req: WorkspaceSaveRequest):
    """保存工作区状态"""
    service = get_workspace_state_service()
    result = service.save(
        workspace_id=req.workspace_id,
        state=req.state,
        name=req.name,
        tags=req.tags,
    )
    return {"success": True, "data": result}


@router.post("/restore")
async def restore_workspace(req: WorkspaceRestoreRequest):
    """恢复工作区状态"""
    service = get_workspace_state_service()
    result = service.restore(
        workspace_id=req.workspace_id,
        snapshot_timestamp=req.snapshot_timestamp,
    )
    if result is None:
        raise HTTPException(404, f"Workspace not found: {req.workspace_id}")
    return {"success": True, "data": result}


@router.get("/list")
async def list_workspaces(tag: Optional[str] = None):
    """列出所有工作区"""
    service = get_workspace_state_service()
    workspaces = service.list_workspaces(tag=tag)
    return {"success": True, "data": workspaces}


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """删除工作区"""
    service = get_workspace_state_service()
    success = service.delete(workspace_id)
    if not success:
        raise HTTPException(404, f"Workspace not found: {workspace_id}")
    return {"success": True, "message": f"Workspace {workspace_id} deleted"}


@router.get("/{workspace_id}/snapshots")
async def get_snapshots(workspace_id: str):
    """获取工作区快照列表"""
    service = get_workspace_state_service()
    snapshots = service.get_snapshots(workspace_id)
    return {"success": True, "data": snapshots}


@router.post("/export")
async def export_workspace(req: WorkspaceExportRequest):
    """导出工作区数据"""
    service = get_workspace_state_service()
    
    # 恢复最新状态
    state = service.restore(req.workspace_id)
    if state is None:
        raise HTTPException(404, f"Workspace not found: {req.workspace_id}")
    
    export_data = {
        "workspace_id": req.workspace_id,
        "exported_at": __import__("time").time(),
        "state": state,
    }
    
    if req.include_snapshots:
        snapshots = service.get_snapshots(req.workspace_id)
        export_data["snapshot_count"] = len(snapshots)
    
    return {"success": True, "data": export_data}


@router.post("/import")
async def import_workspace(req: WorkspaceImportRequest):
    """导入工作区数据"""
    service = get_workspace_state_service()
    
    # 检查是否已有同名工作区
    existing = service.restore(req.workspace_id)
    if existing and not req.overwrite:
        raise HTTPException(409, f"Workspace already exists: {req.workspace_id}")
    
    # 提取状态数据
    state_data = req.data.get("state", req.data)
    
    result = service.save(
        workspace_id=req.workspace_id,
        state=state_data.get("state", state_data),
        name=req.data.get("name"),
    )
    return {"success": True, "data": result}
