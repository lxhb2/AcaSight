"""
Agent Router — 学术 Agent API 端点（v2.0）

改进：
1. 支持多轮对话（conversation_id 持久化）
2. 支持技能包路由（bundle_name 参数）
3. 会话历史保存到数据库
4. 向量记忆检索（跨会话搜索）

POST /api/agent/task       — 执行 Agent 任务（SSE 流式返回）
GET  /api/agent/skills     — 列出可用技能
GET  /api/agent/bundles    — 列出技能包
POST /api/agent/direct     — 直接调用指定技能
POST /api/agent/memory     — 搜索 Agent 记忆
"""

import json
import os
import structlog
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

logger = structlog.get_logger()
router = APIRouter(prefix="/api/agent", tags=["agent"])

# 会话存储目录
SESSION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "agent_sessions"
)
os.makedirs(SESSION_DIR, exist_ok=True)


def _get_agent_core():
    from app.agent.core import agent_core
    agent_core._ensure_initialized()
    return agent_core


def _session_path(conversation_id: str) -> str:
    """获取会话文件路径"""
    return os.path.join(SESSION_DIR, f"{conversation_id}.json")


def _load_session(conversation_id: str) -> Dict:
    """加载会话历史"""
    path = _session_path(conversation_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load session {conversation_id}: {e}")
    return {"messages": [], "context": {}, "created_at": datetime.now().isoformat()}


def _save_session(conversation_id: str, session: Dict):
    """保存会话历史"""
    path = _session_path(conversation_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Failed to save session {conversation_id}: {e}")


# ==================== 请求/响应模型 ====================


class AgentTaskRequest(BaseModel):
    """Agent 任务请求"""
    task: str                               # 自然语言任务描述
    context: Optional[Dict[str, Any]] = None  # 上下文（pdf_id, selected_text, etc.）
    conversation_id: Optional[str] = None     # 对话 ID（用于多轮）
    bundle_name: Optional[str] = None          # 技能包名称（限定工具范围）


class DirectSkillRequest(BaseModel):
    """直接调用技能请求"""
    skill_name: str                           # 技能名称
    arguments: Dict[str, Any]                  # 技能参数


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str                                # 搜索关键词
    top_k: int = 5                            # 返回数量


# ==================== API 端点 ====================


@router.post("/task")
async def run_agent_task(request: AgentTaskRequest):
    """执行 Agent 任务（SSE 流式返回）
    
    返回事件流：
    - event: thinking    — Agent 思考过程
    - event: tool_call   — 工具调用
    - event: tool_result — 工具执行结果
    - event: answer      — 最终回答
    - event: error       — 错误
    - event: done        — 完成
    """
    async def event_stream():
        import uuid
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        session = _load_session(conversation_id)
        history = list(session.get("messages", []))
        
        merged_context = dict(session.get("context", {}))
        if request.context:
            merged_context.update(request.context)
        
        history.append({"role": "user", "content": request.task})
        
        try:
            core = _get_agent_core()
            if request.bundle_name:
                bundles = core.skill_registry.list_bundles()
                bundle_names = [b["name"] for b in bundles]
                if request.bundle_name not in bundle_names:
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': f'未知技能包: {request.bundle_name}'})}\n\n"
                    return
                merged_context["_bundle"] = request.bundle_name
                yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'content': f'使用技能包: {request.bundle_name}'})}\n\n"
            
            assistant_content = ""
            
            async for step in core.run(
                task=request.task,
                context=merged_context,
                conversation_history=history[:-1],
            ):
                event_type = step.get("type", "unknown")
                data = json.dumps(step, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data}\n\n"
                
                if event_type == "answer":
                    assistant_content = step.get("content", "")
                elif event_type == "error":
                    assistant_content = f"[错误] {step.get('content', '')}"
            
            if assistant_content:
                history.append({"role": "assistant", "content": assistant_content})
            
            session["messages"] = history[-20:]
            session["context"] = merged_context
            session["updated_at"] = datetime.now().isoformat()
            if not session.get("created_at"):
                session["created_at"] = datetime.now().isoformat()
            _save_session(conversation_id, session)
            
            yield f"event: meta\ndata: {json.dumps({'type': 'meta', 'conversation_id': conversation_id})}\n\n"
            yield "event: done\ndata: {}\n\n"
        
        except Exception as e:
            logger.error("agent task failed", error=str(e))
            error_data = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/skills")
async def list_skills(category: Optional[str] = None, bundle: Optional[str] = None):
    """列出所有可用技能
    
    - category: 按分类筛选（可选）
    - bundle: 按技能包筛选（可选）
    """
    core = _get_agent_core()
    
    if bundle:
        bundles = core.skill_registry.list_bundles()
        for b in bundles:
            if b["name"] == bundle:
                return {"total": len(b["skills"]), "skills": b["skills"]}
        return {"total": 0, "skills": [], "error": f"未知技能包: {bundle}"}
    
    skills = core.skill_registry.list_skills(category=category)
    categories = {}
    for s in skills:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)
    
    return {
        "total": len(skills),
        "categories": categories,
        "skills": skills,
    }


@router.get("/bundles")
async def list_bundles():
    """列出所有技能包"""
    core = _get_agent_core()
    bundles = core.skill_registry.list_bundles()
    return {
        "total": len(bundles),
        "bundles": bundles,
    }


@router.post("/direct")
async def direct_skill_call(request: DirectSkillRequest):
    """直接调用指定技能（跳过推理循环）"""
    result = await _get_agent_core().skill_registry.execute(
        request.skill_name, request.arguments
    )
    return {"skill": request.skill_name, "result": result}


@router.post("/memory")
async def search_memory(request: MemorySearchRequest):
    """搜索 Agent 记忆（跨会话向量检索）
    
    使用 Qdrant 搜索已保存的 Agent 会话历史。
    """
    try:
        from app.services.vector_service import vector_service
        results = await vector_service.search(
            request.query,
            filter={"source": "agent_memory"},
            top_k=request.top_k,
        )
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.warning(f"Memory search unavailable: {e}")
        return {
            "query": request.query,
            "count": 0,
            "results": [],
            "note": f"向量记忆检索不可用: {str(e)}。请确保 Qdrant 服务运行中。",
        }


@router.get("/sessions")
async def list_sessions():
    """列出所有 Agent 会话"""
    if not os.path.exists(SESSION_DIR):
        return {"total": 0, "sessions": []}
    
    sessions = []
    for fname in os.listdir(SESSION_DIR):
        if fname.endswith(".json"):
            path = os.path.join(SESSION_DIR, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                messages = data.get("messages", [])
                first_user = ""
                for m in messages:
                    if m.get("role") == "user":
                        first_user = m.get("content", "")[:60]
                        break
                sessions.append({
                    "conversation_id": fname[:-5],
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(messages),
                    "preview": first_user,
                })
            except (json.JSONDecodeError, IOError):
                continue
    
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return {"total": len(sessions), "sessions": sessions}


@router.get("/sessions/{conversation_id}")
async def get_session(conversation_id: str):
    """获取单个会话详情"""
    session = _load_session(conversation_id)
    if not session.get("messages") and not session.get("created_at"):
        return {"error": "会话不存在", "conversation_id": conversation_id}
    return {
        "conversation_id": conversation_id,
        "messages": session.get("messages", []),
        "context": session.get("context", {}),
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", ""),
    }


@router.delete("/sessions/{conversation_id}")
async def delete_session(conversation_id: str):
    """删除会话"""
    path = _session_path(conversation_id)
    if os.path.exists(path):
        os.remove(path)
        return {"detail": "会话已删除", "conversation_id": conversation_id}
    return {"error": "会话不存在", "conversation_id": conversation_id}
