"""
Agent 工具调度 API
提供工具列表查询、工具执行、任务编排接口
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import traceback

from app.services.agent_tools import registry, get_orchestrator, ToolCall

router = APIRouter()

# 确保工具已注册（导入触发注册）
try:
    from app.services.tool_definitions import init_agent_tools
except ImportError:
    pass


# ─── 请求模型 ───

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class TaskExecuteRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = {}


class SearchReferencesRequest(BaseModel):
    topic: str
    section: str = ""
    dimension: str = "current_status"
    limit: int = 5


# ─── API 端点 ───

@router.get("/tools")
async def list_tools(module: str = ""):
    """列出所有可用的 Agent 工具"""
    if module:
        tools = registry.list_by_module_schemas(module)
    else:
        tools = registry.list_all_schemas()
    return {
        "success": True,
        "total": len(tools),
        "tools": tools,
        "modules": {
            "literature": ["search", "decompose", "dimension_query", "get_field", "export_citation"],
            "writing": ["generate_outline", "generate_section", "polish"],
            "charts": ["auto_generate", "list_templates"],
            "agent": ["summarize", "chat"],
            "knowledge": ["query_graph"],
        }
    }


@router.get("/tools/summary")
async def tools_summary():
    """工具注册表摘要"""
    return {"success": True, **registry.summary()}


@router.post("/tools/call")
async def call_tool(req: ToolCallRequest):
    """直接调用指定工具"""
    try:
        result = await registry.call(req.tool_name, req.arguments)
        return {"success": True, "tool": req.tool_name, "result": result}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"工具执行失败: {str(e)}")


@router.post("/execute")
async def execute_task(req: TaskExecuteRequest):
    """执行高层任务（Agent 编排器自动拆解）"""
    orchestrator = get_orchestrator()
    result = await orchestrator.execute_task(req.task, req.context)
    return result


@router.post("/search-references")
async def search_references_for_writing(req: SearchReferencesRequest):
    """
    为写作章节搜索相关参考文献
    自动调用: literature_search → literature_dimension_query
    返回: {references: [...], suggested_citations: [...]}
    """
    from app.services.literature_service import search_structured_papers, query_by_dimension
    
    # 1. 全文搜索
    search_result = search_structured_papers(req.topic, limit=min(req.limit, 10), offset=0)
    papers = search_result.get("results", []) if isinstance(search_result, dict) else []
    
    # 2. 按维度搜索（补充）
    dim_results = query_by_dimension(req.dimension, req.section, min(req.limit, 5))
    
    # 3. 合并去重
    seen_ids = set()
    all_refs = []
    for p in papers:
        if p.get("id") not in seen_ids:
            all_refs.append(p)
            seen_ids.add(p.get("id"))
    for p in dim_results:
        if p.get("id") not in seen_ids:
            all_refs.append(p)
            seen_ids.add(p.get("id"))
    
    # 4. 生成引用建议
    suggested_citations = [
        {
            "paper_id": p.get("id", ""),
            "citation": f"{p.get('authors', '')}. {p.get('title', '')}. {p.get('journal', '')}, {p.get('year', '')}.",
            "relevance_for": {
                "background": bool(p.get("background")),
                "method": bool(p.get("method")),
                "results": bool(p.get("results")),
                "conclusion": bool(p.get("conclusion")),
            }
        } for p in all_refs[:8] if p.get("title")
    ]
    
    return {
        "success": True,
        "topic": req.topic,
        "dimension": req.dimension,
        "references": all_refs,
        "suggested_citations": suggested_citations,
        "total": len(all_refs),
    }


@router.get("/context")
async def get_agent_context():
    """获取 Agent 当前全局上下文（文献库统计、工具列表、写作状态等）"""
    from app.services.literature_service import get_paper_statistics
    
    stats = get_paper_statistics()
    tools_summary = registry.summary()
    
    return {
        "success": True,
        "literature_stats": stats,
        "tools_available": tools_summary["total_tools"],
        "modules": tools_summary["modules"],
        "status": "ready",
    }


# ==================== 六大模块Agent调度 (方向三 3.2-3.3) ====================

class ModuleExecuteRequest(BaseModel):
    module: str
    task: str
    context: Optional[Dict[str, Any]] = {}


class ModuleResumeRequest(BaseModel):
    module: str
    user_choice: Optional[Dict[str, Any]] = None


@router.get("/modules")
async def list_modules():
    """列出所有模块Agent及其状态"""
    from app.agent.modules import list_agents
    agents = list_agents()
    return {"success": True, "modules": agents, "count": len(agents)}


@router.get("/skills")
async def list_skills():
    """列出所有可用技能"""
    tools = registry.list_all()
    skills = []
    for t in tools:
        skills.append({
            "name": t.name,
            "category": t.module,
            "description": t.description,
            "parameters": t.parameters,
            "tags": t.tags,
        })
    return {"success": True, "skills": skills, "count": len(skills)}


@router.get("/modules/{module_name}")
async def get_module_status(module_name: str):
    """获取指定模块Agent的状态"""
    from app.agent.modules import get_agent
    agent = get_agent(module_name)
    if not agent:
        raise HTTPException(404, f"模块 '{module_name}' 不存在，可选: knowledge, writing, output, chart, storage")
    return {"success": True, **agent.get_status()}


@router.post("/modules/execute")
async def module_execute(req: ModuleExecuteRequest):
    """通过模块Agent执行任务"""
    from app.agent.modules import get_agent
    agent = get_agent(req.module)
    if not agent:
        raise HTTPException(404, f"模块 '{req.module}' 不存在，可选: knowledge, writing, output, chart, storage")
    result = await agent.execute(req.task, req.context)
    return {"success": result.success, "module": req.module, "data": result.data, "error": result.error, "interrupt_reason": result.interrupt_reason, "interrupt_data": result.interrupt_data}


@router.post("/modules/resume")
async def module_resume(req: ModuleResumeRequest):
    """恢复被中断的模块Agent"""
    from app.agent.modules import get_agent
    agent = get_agent(req.module)
    if not agent:
        raise HTTPException(404, f"模块 '{req.module}' 不存在")
    result = await agent.resume(req.user_choice)
    return {"success": result.success, "module": req.module, "data": result.data, "error": result.error}