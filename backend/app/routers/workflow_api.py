"""
工作流与状态管理 API
暴露：工作流列表/执行/进度 · 全局状态查询 · 意图解析 · 模式切换
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import structlog

from app.services.agent_tools import registry
from app.services.global_state import get_global_state
from app.services.workflow_engine import get_workflow_engine, OperationMode, WritingFlowStatus
from app.services.workflow_templates import register_all_workflows
from app.services.intent_parser import IntentParser

logger = structlog.get_logger()
router = APIRouter()

# 启动时注册预定义工作流
try:
    register_all_workflows()
    logger.info("[Workflow] Predefined workflows registered")
except Exception as e:
    logger.warning(f"[Workflow] Failed to register workflows: {e}")


# ─── 请求模型 ───

class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str
    params: Dict[str, Any] = {}
    mode: str = "assist"  # assist | full_control


class ParseIntentRequest(BaseModel):
    input: str
    use_llm: bool = False


class UpdateStateRequest(BaseModel):
    updates: Dict[str, Any]
    module: str = "api"
    operation: str = "update"


class SetModeRequest(BaseModel):
    mode: str  # assist | full_control


# ─── 工作流端点 ───

@router.get("/workflows")
async def list_workflows():
    """列出所有预定义工作流"""
    engine = get_workflow_engine()
    return {"success": True, "workflows": engine.list_all()}


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """获取工作流定义"""
    engine = get_workflow_engine()
    wf = engine.get(workflow_id)
    if not wf:
        raise HTTPException(404, f"工作流 '{workflow_id}' 不存在")
    return {
        "success": True,
        "workflow": {
            "id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "steps": [
                {
                    "id": s.step_id,
                    "module": s.module,
                    "operation": s.operation,
                    "description": s.description,
                    "mode": s.mode.value,
                    "timeout": s.timeout,
                }
                for s in wf.steps
            ],
            "tags": wf.tags,
        }
    }


@router.post("/workflows/execute")
async def execute_workflow(req: ExecuteWorkflowRequest):
    """执行工作流"""
    engine = get_workflow_engine()
    mode = OperationMode.ASSIST if req.mode == "assist" else OperationMode.FULL_CONTROL
    
    result = await engine.execute(
        workflow_id=req.workflow_id,
        initial_params=req.params,
        mode=mode,
    )
    
    return {
        "success": result.success,
        "workflow_id": result.workflow_id,
        "total_steps": result.total_steps,
        "completed_steps": result.completed_steps,
        "duration_seconds": result.duration_seconds,
        "steps": result.steps,
        "error_step": result.error_step,
    }


@router.get("/workflows/{workflow_id}/progress")
async def get_workflow_progress(workflow_id: str):
    """获取工作流执行进度"""
    engine = get_workflow_engine()
    progress = engine.get_progress(workflow_id)
    if not progress:
        raise HTTPException(404, f"工作流 '{workflow_id}' 未在运行")
    return {"success": True, **progress}


# ─── 状态管理端点 ───

@router.get("/state")
async def get_state():
    """获取当前全局状态快照"""
    state = get_global_state()
    return {
        "success": True,
        "state": state.snapshot(),
        "summary": state.generate_context_summary(),
        "mode": state.get("mode"),
        "active_modules": state.get("active_modules"),
    }


@router.post("/state/update")
async def update_state(req: UpdateStateRequest):
    """更新全局状态"""
    state = get_global_state()
    state.update(req.updates, module=req.module, operation=req.operation)
    return {"success": True, "updated_keys": list(req.updates.keys())}


@router.post("/state/mode")
async def set_mode(req: SetModeRequest):
    """切换操作模式: assist（辅助） / full_control（全权）"""
    if req.mode not in ("assist", "full_control"):
        raise HTTPException(400, "mode 必须为 assist 或 full_control")
    state = get_global_state()
    state.set_mode(req.mode)
    return {
        "success": True,
        "mode": req.mode,
        "description": "辅助模式：给建议等待确认" if req.mode == "assist" else "全权模式：自动执行",
    }


@router.get("/state/context")
async def get_context():
    """获取共享上下文"""
    state = get_global_state()
    return {"success": True, "context": state.get("shared_context")}


@router.post("/state/context")
async def set_context(data: Dict[str, Any]):
    """设置共享上下文"""
    state = get_global_state()
    for key, value in data.items():
        state.set_context(key, value)
    return {"success": True}


# ─── 意图解析端点 ───

_parser = IntentParser()

@router.post("/intent/parse")
async def parse_intent(req: ParseIntentRequest):
    """解析用户输入意图"""
    if req.use_llm:
        intent = _parser.parse_with_llm(req.input)
    else:
        intent = _parser.parse(req.input)
    
    return {
        "success": True,
        "intent": {
            "task_type": intent.task_type.value,
            "module": intent.module,
            "operation": intent.operation,
            "params": intent.params,
            "confidence": intent.confidence,
            "workflow_id": intent.workflow_id,
            "requires_confirmation": intent.requires_confirmation,
            "suggested_mode": intent.suggested_mode,
        },
    }


@router.get("/intent/capabilities")
async def list_intent_capabilities():
    """列出意图解析器能识别的所有任务类型"""
    return {"success": True, "capabilities": _parser.get_capabilities()}


# ─── 上下文摘要端 ───

@router.get("/summary")
async def get_system_summary():
    """Agent 系统全局摘要"""
    state = get_global_state()
    return {
        "success": True,
        "mode": state.get("mode"),
        "context_summary": state.generate_context_summary(),
        "tools_total": len(registry.list_all()),
        "workflows_total": len(get_workflow_engine().list_all()),
        "active_modules": state.get("active_modules"),
        "current_task": state.get("current_task"),
        "task_stage": state.get("task_stage"),
    }


# ─── 写作流管理端点 ───

class CreateWritingFlowRequest(BaseModel):
    session_id: str
    title: str
    data_mode: str = "knowledge_base"
    material_ids: List[str] = []
    reference_paper_ids: List[int] = []


class TransitionFlowRequest(BaseModel):
    new_status: str
    outline: Optional[List[Dict[str, Any]]] = None
    interrupt_info: Optional[Dict[str, Any]] = None


class RunPipelineRequest(BaseModel):
    outline: List[Dict[str, Any]]
    topic: str


class AgentChainRequest(BaseModel):
    agent_name: str
    task: str
    context: Dict[str, Any] = {}


class AgentResumeRequest(BaseModel):
    agent_name: str
    user_choice: Dict[str, Any] = {}


@router.get("/writing-flows")
async def list_writing_flows():
    """列出所有写作流"""
    engine = get_workflow_engine()
    return {"success": True, "flows": engine.list_writing_flows()}


@router.post("/writing-flows/create")
async def create_writing_flow(req: CreateWritingFlowRequest):
    """创建写作流"""
    engine = get_workflow_engine()
    flow = engine.create_writing_flow(
        session_id=req.session_id,
        title=req.title,
        data_mode=req.data_mode,
        material_ids=req.material_ids,
        reference_paper_ids=req.reference_paper_ids,
    )
    return {
        "success": True,
        "flow": {
            "session_id": flow.session_id,
            "title": flow.title,
            "status": flow.status.value,
            "data_mode": flow.data_mode,
        },
    }


@router.get("/writing-flows/{session_id}")
async def get_writing_flow(session_id: str):
    """获取写作流状态"""
    engine = get_workflow_engine()
    flow = engine.get_writing_flow(session_id)
    if not flow:
        raise HTTPException(404, f"写作流 '{session_id}' 不存在")
    return {
        "success": True,
        "flow": {
            "session_id": flow.session_id,
            "title": flow.title,
            "status": flow.status.value,
            "outline": flow.outline,
            "current_section_index": flow.current_section_index,
            "sections_written": flow.sections_written,
            "interrupt_info": flow.interrupt_info,
            "data_mode": flow.data_mode,
            "material_ids": flow.material_ids,
            "reference_paper_ids": flow.reference_paper_ids,
            "created_at": flow.created_at,
            "updated_at": flow.updated_at,
        },
    }


@router.post("/writing-flows/{session_id}/transition")
async def transition_writing_flow(session_id: str, req: TransitionFlowRequest):
    """转换写作流状态"""
    engine = get_workflow_engine()
    try:
        new_status = WritingFlowStatus(req.new_status)
    except ValueError:
        raise HTTPException(400, f"无效状态 '{req.new_status}'，有效值: {[s.value for s in WritingFlowStatus]}")

    kwargs = {}
    if req.outline is not None:
        kwargs["outline"] = req.outline
    if req.interrupt_info is not None:
        kwargs["interrupt_info"] = req.interrupt_info

    flow = engine.transition_writing_flow(session_id, new_status, **kwargs)
    if not flow:
        raise HTTPException(400, f"状态转换失败：'{session_id}' 不存在或转换不合法")
    return {
        "success": True,
        "session_id": flow.session_id,
        "status": flow.status.value,
    }


@router.post("/writing-flows/{session_id}/pipeline")
async def run_writing_pipeline(session_id: str, req: RunPipelineRequest):
    """执行写作流管道（自动遍历大纲，中断时返回）"""
    engine = get_workflow_engine()
    result = await engine.run_writing_pipeline(
        session_id=session_id,
        outline=req.outline,
        topic=req.topic,
    )
    return {"success": result.get("success", False), **result}


@router.post("/agent-chain/execute")
async def execute_agent_chain(req: AgentChainRequest):
    """通过引擎执行指定Agent任务"""
    engine = get_workflow_engine()
    result = await engine.execute_agent_chain(
        agent_name=req.agent_name,
        task=req.task,
        context=req.context,
    )
    return {"success": result.get("success", False), **result}


@router.post("/agent-chain/resume")
async def resume_agent_chain(req: AgentResumeRequest):
    """恢复被中断的Agent"""
    engine = get_workflow_engine()
    result = await engine.resume_agent(
        agent_name=req.agent_name,
        user_choice=req.user_choice,
    )
    return {"success": result.get("success", False), **result}