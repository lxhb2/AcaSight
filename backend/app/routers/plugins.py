"""
Plugin API 路由 — 方向Q.2 插件系统管理

端点:
- GET    /api/plugins/              — 列出已安装插件
- GET    /api/plugins/discover      — 发现可用插件
- POST   /api/plugins/load          — 加载插件
- POST   /api/plugins/{name}/enable — 启用插件
- POST   /api/plugins/{name}/disable — 禁用插件
- DELETE /api/plugins/{name}        — 卸载插件
- POST   /api/plugins/hook          — 触发钩子
- GET    /api/plugins/{name}/status — 插件状态
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.plugin_system import get_plugin_registry, PluginSandbox

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/plugins", tags=["插件系统"])


# ── 请求模型 ──

class PluginLoadRequest(BaseModel):
    """加载插件请求"""
    plugin_path: str = Field(..., description="插件目录路径")
    config: Optional[Dict[str, Any]] = Field(None, description="插件配置")


class PluginHookRequest(BaseModel):
    """钩子触发请求"""
    hook_name: str = Field(..., description="钩子名称")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="钩子参数")


# ── API 端点 ──

@router.get("/")
async def list_plugins():
    """列出所有已安装插件"""
    registry = get_plugin_registry()
    return {
        "success": True,
        "data": registry.list_plugins(),
    }


@router.get("/discover")
async def discover_plugins():
    """扫描插件目录，发现可用插件"""
    registry = get_plugin_registry()
    discovered = registry.scan_plugins_dir()
    return {
        "success": True,
        "data": {
            "plugins_dir": registry._plugins_dir,
            "discovered": discovered,
            "count": len(discovered),
        },
    }


@router.post("/load")
async def load_plugin(req: PluginLoadRequest):
    """加载插件"""
    registry = get_plugin_registry()
    
    try:
        instance = await registry.load_plugin(req.plugin_path, config=req.config)
        return {
            "success": instance.state.value in ("loaded", "enabled"),
            "data": registry.get_plugin_status(instance.manifest.name),
        }
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/{plugin_name}/enable")
async def enable_plugin(plugin_name: str):
    """启用插件"""
    registry = get_plugin_registry()
    success = await registry.enable_plugin(plugin_name)
    
    if not success:
        instance = registry._plugins.get(plugin_name)
        if not instance:
            raise HTTPException(404, f"Plugin not found: {plugin_name}")
        raise HTTPException(400, f"Cannot enable plugin: {instance.error}")
    
    return {"success": True, "data": registry.get_plugin_status(plugin_name)}


@router.post("/{plugin_name}/disable")
async def disable_plugin(plugin_name: str):
    """禁用插件"""
    registry = get_plugin_registry()
    success = await registry.disable_plugin(plugin_name)
    
    if not success:
        raise HTTPException(404, f"Plugin not found or not enabled: {plugin_name}")
    
    return {"success": True, "data": registry.get_plugin_status(plugin_name)}


@router.delete("/{plugin_name}")
async def unload_plugin(plugin_name: str):
    """卸载插件"""
    registry = get_plugin_registry()
    success = await registry.unload_plugin(plugin_name)
    
    if not success:
        raise HTTPException(404, f"Plugin not found: {plugin_name}")
    
    return {"success": True, "message": f"Plugin {plugin_name} unloaded"}


@router.post("/hook")
async def trigger_hook(req: PluginHookRequest):
    """触发钩子"""
    registry = get_plugin_registry()
    results = await registry.hook(req.hook_name, **req.kwargs)
    
    return {
        "success": True,
        "data": {
            "hook_name": req.hook_name,
            "handlers_called": len(results),
            "results": [
                {
                    "plugin": r.plugin_name,
                    "success": r.success,
                    "result": r.result,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        },
    }


@router.get("/{plugin_name}/status")
async def plugin_status(plugin_name: str):
    """获取插件状态"""
    registry = get_plugin_registry()
    status = registry.get_plugin_status(plugin_name)
    
    if not status:
        raise HTTPException(404, f"Plugin not found: {plugin_name}")
    
    return {"success": True, "data": status}
