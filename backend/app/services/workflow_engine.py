"""
工作流编排引擎 (WorkflowEngine)
基于文档 5.1-5.2 节实现

支持：
1. 多步骤工作流定义（DAG）
2. 步骤间数据流转（previous_step / global_state / static）
3. 条件执行（ON_SUCCESS / ON_FAILURE / ON_USER_CONFIRM）
4. 超时处理 + 失败分支
5. 预定义工作流模板
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import structlog

from app.services.agent_tools import registry
from app.services.global_state import get_global_state

logger = structlog.get_logger()

# ─── 枚举 ───

class StepCondition(str, Enum):
    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_USER_CONFIRM = "on_user_confirm"

class OperationMode(str, Enum):
    ASSIST = "assist"
    FULL_CONTROL = "full_control"

class ParamSource(str, Enum):
    USER_INPUT = "user_input"
    PREVIOUS_STEP = "previous_step"
    GLOBAL_STATE = "global_state"
    STATIC = "static"


# ─── 数据结构 ───

@dataclass
class WorkflowStep:
    step_id: str
    module: str                     # 模块名（对应 ToolRegistry module）
    operation: str                  # 操作名（对应 ToolRegistry tool name）
    description: str = ""
    mode: OperationMode = OperationMode.ASSIST
    params_source: ParamSource = ParamSource.USER_INPUT
    static_params: Dict[str, Any] = field(default_factory=dict)
    condition: StepCondition = StepCondition.ALWAYS
    next_steps: List[str] = field(default_factory=list)
    on_failure: Optional[str] = None
    on_success: Optional[str] = None
    timeout: int = 60               # 超时秒数
    skip_if_output_exists: bool = False  # 如果模块已有输出则跳过


@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_params_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowExecutionResult:
    workflow_id: str
    success: bool
    steps: Dict[str, Dict[str, Any]]  # step_id → {success, type, content, error}
    total_steps: int
    completed_steps: int
    duration_seconds: float
    error_step: Optional[str] = None


# ─── 引擎 ───

class WritingFlowStatus(str, Enum):
    CREATED = "created"
    OUTLINING = "outlining"
    OUTLINE_REVIEW = "outline_review"
    WRITING = "writing"
    INTERRUPTED = "interrupted"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WritingFlowState:
    session_id: str
    title: str
    status: WritingFlowStatus = WritingFlowStatus.CREATED
    outline: Optional[List[Dict[str, Any]]] = None
    current_section_index: int = 0
    sections_written: List[Dict[str, Any]] = field(default_factory=list)
    interrupt_info: Optional[Dict[str, Any]] = None
    data_mode: str = "knowledge_base"
    material_ids: List[str] = field(default_factory=list)
    reference_paper_ids: List[int] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


class WorkflowEngine:
    """
    工作流编排引擎
    
    用法：
        engine = WorkflowEngine()
        engine.define(paper_writing_workflow)
        result = await engine.execute("paper_writing", {"topic": "...", "style": "academic"})
    """
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._running: Dict[str, Dict[str, Any]] = {}
        self._writing_flows: Dict[str, WritingFlowState] = {}
        self._state = get_global_state()
    
    def define(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"[Workflow] Defined: {workflow.workflow_id}")
    
    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)
    
    def list_all(self) -> List[Dict]:
        return [
            {
                "id": wf.workflow_id,
                "name": wf.name,
                "description": wf.description,
                "steps": len(wf.steps),
                "tags": wf.tags,
            }
            for wf in self._workflows.values()
        ]
    
    async def execute(self,
                      workflow_id: str,
                      initial_params: Dict[str, Any],
                      mode: OperationMode = OperationMode.ASSIST,
                      on_confirm: Optional[Callable] = None,
                      ) -> WorkflowExecutionResult:
        """执行工作流"""
        
        wf = self._workflows.get(workflow_id)
        if not wf:
            return WorkflowExecutionResult(
                workflow_id=workflow_id, success=False,
                steps={}, total_steps=0, completed_steps=0,
                duration_seconds=0, error_step="workflow_not_found",
            )
        
        exec_id = f"{workflow_id}_{int(time.time())}"
        start_time = time.time()
        
        # 初始化运行状态
        self._running[exec_id] = {
            "workflow_id": workflow_id,
            "status": "running",
            "current_step": None,
            "step_results": {},
        }
        
        # 更新全局状态
        self._state.set_task(wf.name, "started")
        self._state.update({
            "workflow_id": workflow_id,
            "workflow_step": None,
        }, module="workflow_engine", operation="start_workflow")
        
        step_results: Dict[str, Dict] = {}
        visited = set()
        
        # 从第一个步骤开始
        current_id = wf.steps[0].step_id if wf.steps else None
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            self._running[exec_id]["current_step"] = current_id
            step = self._find_step(wf.steps, current_id)
            
            if not step:
                logger.warning(f"[Workflow] Step not found: {current_id}")
                break
            
            self._state.set("workflow_step", current_id, module="workflow_engine")
            
            # 检查跳过后件
            if step.skip_if_output_exists:
                cached = self._state.get_module_output(f"{step.module}.{step.operation}")
                if cached is not None:
                    step_results[current_id] = {
                        "success": True,
                        "type": "cached",
                        "content": cached,
                        "skipped": True,
                    }
                    current_id = self._next_step(step, was_success=True, results=step_results)
                    continue
            
            # 检查条件
            if not self._check_condition(step.condition, step_results):
                current_id = self._next_step(step, was_success=True, results=step_results)
                continue
            
            # 解析参数
            params = self._resolve_params(step, initial_params, step_results)
            
            # 执行步骤
            self._state.activate_module(step.module)
            
            try:
                result_data = await asyncio.wait_for(
                    registry.call(f"{step.module}_{step.operation}", params),
                    timeout=step.timeout,
                )
                
                # 缓存输出
                self._state.set_module_output(
                    f"{step.module}.{step.operation}",
                    result_data,
                    operation=step.operation,
                    ttl_seconds=3600,  # 1小时
                )
                
                step_result = {
                    "success": True,
                    "type": "result",
                    "content": result_data,
                }
                
                # 辅助模式 → 等待确认
                if step.mode == OperationMode.ASSIST and on_confirm:
                    confirmed = await on_confirm(step.step_id, result_data)
                    if confirmed:
                        step_results[current_id] = step_result
                    else:
                        step_result = {"success": False, "type": "cancelled", "content": None, "error": "用户取消"}
                        step_results[current_id] = step_result
                        if step.on_failure:
                            current_id = step.on_failure
                            continue
                        else:
                            break
                else:
                    step_results[current_id] = step_result
                
                current_id = self._next_step(step, was_success=True, results=step_results)
                
            except asyncio.TimeoutError:
                step_results[current_id] = {
                    "success": False, "type": "timeout",
                    "content": None, "error": f"步骤超时 ({step.timeout}s)",
                }
                current_id = step.on_failure if step.on_failure else None
                
            except Exception as e:
                logger.error(f"[Workflow] Step failed: {current_id} — {e}")
                step_results[current_id] = {
                    "success": False, "type": "error",
                    "content": None, "error": str(e),
                }
                current_id = step.on_failure if step.on_failure else None
            
            finally:
                self._state.deactivate_module(step.module)
        
        # 完成
        duration = time.time() - start_time
        all_ok = all(r.get("success", False) for r in step_results.values())
        
        self._running[exec_id]["status"] = "completed" if all_ok else "partial"
        self._state.clear_task()
        
        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            success=all_ok,
            steps=step_results,
            total_steps=len(wf.steps),
            completed_steps=len(step_results),
            duration_seconds=round(duration, 1),
            error_step=None if all_ok else [
                sid for sid, r in step_results.items()
                if not r.get("success", False)
            ][0] if step_results else None,
        )
    
    def get_progress(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流执行进度"""
        for exec_id, state in self._running.items():
            if state["workflow_id"] == workflow_id:
                wf = self._workflows.get(workflow_id)
                return {
                    "status": state["status"],
                    "current_step": state["current_step"],
                    "completed": len(state["step_results"]),
                    "total": len(wf.steps) if wf else 0,
                    "steps": {k: {"success": v.get("success")} for k, v in state["step_results"].items()},
                }
        return None
    
    # ─── 内部方法 ───
    
    def _find_step(self, steps: List[WorkflowStep], step_id: str) -> Optional[WorkflowStep]:
        for s in steps:
            if s.step_id == step_id:
                return s
        return None
    
    def _next_step(self, step: WorkflowStep, was_success: bool, results: Dict) -> Optional[str]:
        if was_success and step.on_success:
            return step.on_success
        if was_success and step.next_steps:
            return step.next_steps[0]
        if not was_success and step.on_failure:
            return step.on_failure
        return None
    
    def _resolve_params(self, step: WorkflowStep, initial: Dict, results: Dict) -> Dict:
        if step.params_source == ParamSource.USER_INPUT:
            return initial.copy()
        elif step.params_source == ParamSource.STATIC:
            return step.static_params.copy()
        elif step.params_source == ParamSource.GLOBAL_STATE:
            ctx = self._state.snapshot()
            return {
                "topic": ctx.get("shared_context", {}).get("writing_topic", ""),
                "paper_ids": ctx.get("shared_context", {}).get("current_paper_ids", []),
                **ctx.get("shared_context", {}),
            }
        elif step.params_source == ParamSource.PREVIOUS_STEP:
            last = list(results.values())[-1] if results else {}
            content = last.get("content", {})
            if isinstance(content, dict):
                return content
            return {"data": content}
        return initial.copy()
    
    def _check_condition(self, cond: StepCondition, results: Dict) -> bool:
        if cond == StepCondition.ALWAYS:
            return True
        if cond == StepCondition.ON_SUCCESS:
            if not results:
                return True
            last = list(results.values())[-1]
            return last.get("success", False)
        if cond == StepCondition.ON_FAILURE:
            if not results:
                return False
            last = list(results.values())[-1]
            return not last.get("success", True)
        if cond == StepCondition.ON_USER_CONFIRM:
            return True  # 由 execute 外层处理
        return True

    # ─── 写作流状态管理 ───

    def create_writing_flow(self, session_id: str, title: str,
                            data_mode: str = "knowledge_base",
                            material_ids: List[str] = None,
                            reference_paper_ids: List[int] = None) -> WritingFlowState:
        flow = WritingFlowState(
            session_id=session_id,
            title=title,
            data_mode=data_mode,
            material_ids=material_ids or [],
            reference_paper_ids=reference_paper_ids or [],
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._writing_flows[session_id] = flow
        logger.info("Writing flow created", session_id=session_id, title=title)
        return flow

    def get_writing_flow(self, session_id: str) -> Optional[WritingFlowState]:
        return self._writing_flows.get(session_id)

    def list_writing_flows(self) -> List[Dict[str, Any]]:
        return [
            {
                "session_id": f.session_id,
                "title": f.title,
                "status": f.status.value,
                "current_section_index": f.current_section_index,
                "sections_written": len(f.sections_written),
                "data_mode": f.data_mode,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
            }
            for f in self._writing_flows.values()
        ]

    def transition_writing_flow(self, session_id: str,
                                 new_status: WritingFlowStatus,
                                 **kwargs) -> Optional[WritingFlowState]:
        flow = self._writing_flows.get(session_id)
        if not flow:
            return None

        valid_transitions = {
            WritingFlowStatus.CREATED: [WritingFlowStatus.OUTLINING, WritingFlowStatus.FAILED],
            WritingFlowStatus.OUTLINING: [WritingFlowStatus.OUTLINE_REVIEW, WritingFlowStatus.FAILED],
            WritingFlowStatus.OUTLINE_REVIEW: [WritingFlowStatus.WRITING, WritingFlowStatus.OUTLINING, WritingFlowStatus.FAILED],
            WritingFlowStatus.WRITING: [WritingFlowStatus.INTERRUPTED, WritingFlowStatus.COMPLETED, WritingFlowStatus.FAILED],
            WritingFlowStatus.INTERRUPTED: [WritingFlowStatus.CONFIRMED, WritingFlowStatus.FAILED],
            WritingFlowStatus.CONFIRMED: [WritingFlowStatus.WRITING, WritingFlowStatus.COMPLETED, WritingFlowStatus.FAILED],
        }

        allowed = valid_transitions.get(flow.status, [])
        if new_status not in allowed and new_status != WritingFlowStatus.FAILED:
            logger.warning("Invalid transition", session_id=session_id,
                           from_status=flow.status.value, to_status=new_status.value)
            return None

        flow.status = new_status
        flow.updated_at = time.time()

        for key, value in kwargs.items():
            if hasattr(flow, key):
                setattr(flow, key, value)

        logger.info("Writing flow transitioned", session_id=session_id,
                     from_status=flow.status.value if flow.status != new_status else "?",
                     to_status=new_status.value)
        return flow

    async def execute_agent_chain(self, agent_name: str, task: str,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        from app.agent.modules import get_agent
        agent = get_agent(agent_name)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_name}' not found"}

        try:
            result = await agent.execute(task, context or {})
            if result.success and result.interrupt_reason:
                return {
                    "success": True,
                    "data": result.data,
                    "interrupted": True,
                    "interrupt_reason": result.interrupt_reason,
                    "interrupt_data": result.interrupt_data,
                }
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "interrupted": False,
            }
        except Exception as e:
            logger.error("Agent chain execution failed", agent=agent_name, error=str(e))
            return {"success": False, "error": str(e)}

    async def resume_agent(self, agent_name: str,
                            user_choice: Dict[str, Any] = None) -> Dict[str, Any]:
        from app.agent.modules import get_agent
        agent = get_agent(agent_name)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_name}' not found"}

        try:
            result = await agent.resume(user_choice)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
            }
        except Exception as e:
            logger.error("Agent resume failed", agent=agent_name, error=str(e))
            return {"success": False, "error": str(e)}

    async def run_writing_pipeline(self, session_id: str,
                                    outline: List[Dict[str, Any]],
                                    topic: str) -> Dict[str, Any]:
        flow = self._writing_flows.get(session_id)
        if not flow:
            return {"success": False, "error": "Writing flow not found"}

        self.transition_writing_flow(session_id, WritingFlowStatus.WRITING, outline=outline)

        results = []
        for idx, section in enumerate(outline):
            flow.current_section_index = idx
            section_title = section.get("title", f"Section {idx + 1}")

            is_data_section = any(kw in section_title for kw in
                                  ["实验", "结果", "数据", "图表", "分析", "评价", "插图", "性能", "对比"])

            if is_data_section and flow.status != WritingFlowStatus.CONFIRMED:
                self.transition_writing_flow(
                    session_id, WritingFlowStatus.INTERRUPTED,
                    interrupt_info={
                        "section_index": idx,
                        "section_title": section_title,
                        "reason": "该章节涉及数据/插图，请确认素材来源",
                        "options": [
                            {"key": "upload", "label": "自主上传素材"},
                            {"key": "chart", "label": "AI科研绘图"},
                            {"key": "existing", "label": "已有成品图片"},
                        ],
                    },
                )
                return {
                    "success": True,
                    "interrupted": True,
                    "section_index": idx,
                    "section_title": section_title,
                    "message": "写作流中断：等待用户确认素材来源",
                }

            agent_result = await self.execute_agent_chain(
                "writing",
                task="write_section",
                context={
                    "topic": topic,
                    "section_title": section_title,
                    "section_index": idx,
                    "outline": outline,
                    "data_mode": flow.data_mode,
                },
            )

            if not agent_result.get("success", False):
                self.transition_writing_flow(session_id, WritingFlowStatus.FAILED)
                return {"success": False, "error": agent_result.get("error", "Unknown"), "section_index": idx}

            if agent_result.get("interrupted"):
                self.transition_writing_flow(
                    session_id, WritingFlowStatus.INTERRUPTED,
                    interrupt_info=agent_result.get("interrupt_data", {}),
                )
                return {
                    "success": True,
                    "interrupted": True,
                    "section_index": idx,
                    "section_title": section_title,
                    "message": agent_result.get("interrupt_reason", ""),
                }

            results.append({
                "section_index": idx,
                "section_title": section_title,
                "content": agent_result.get("data", {}),
            })
            flow.sections_written.append(results[-1])

            if flow.status == WritingFlowStatus.CONFIRMED:
                self.transition_writing_flow(session_id, WritingFlowStatus.WRITING)

        self.transition_writing_flow(session_id, WritingFlowStatus.COMPLETED)
        return {
            "success": True,
            "completed": True,
            "sections": results,
            "total_sections": len(outline),
        }


# ─── 便捷访问 ───

_engine: Optional[WorkflowEngine] = None

def get_workflow_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine