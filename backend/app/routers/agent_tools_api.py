"""
Agent 工具增强端点
为 Agent 对话添加 function calling 能力
调用 ai_service.chat_with_tools()，自动注入 ToolRegistry 中的工具定义
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import structlog

from app.services.ai_service import AIService
from app.services.agent_tools import registry, get_registry

logger = structlog.get_logger()
router = APIRouter()

# ─── 请求模型 ───

class ToolChatRequest(BaseModel):
    """工具增强对话请求"""
    messages: List[Dict[str, Any]]          # 对话历史
    tools: Optional[List[Dict]] = None   # 覆盖工具列表（不传则使用全量）
    module: Optional[str] = None           # 限定模块（literature/writing/charts/knowledge/agent）
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.3
    max_tokens: Optional[int] = 4096
    conversation_id: Optional[str] = None   # 用于保存会话


# ─── 端点 ───

@router.post("/tool-chat")
async def tool_enhanced_chat(req: ToolChatRequest):
    """
    工具增强对话
    
    自动注入 ToolRegistry 中的工具定义，支持 function calling。
    支持两种模式：
    1. 不传 tools → 使用 ToolRegistry 全量（或指定 module 过滤）
    2. 传 tools → 使用传入的工具定义（前端自定义）
    
    SSE 返回格式：
    data: {"type":"text", "content":"..."}        ← 文本流
    data: {"type":"tool_call", "name":"...", "arguments":{...}}  ← 工具调用
    data: {"type":"tool_result", "content":"..."}     ← 工具执行结果
    data: {"type":"done"}                          ← 结束
    """
    
    # 1. 确定工具定义
    if req.tools is not None:
        tools_def = req.tools
    elif req.module:
        tools_def = registry.list_by_module_schemas(req.module)
    else:
        tools_def = registry.list_all_schemas()
    
    if not tools_def:
        raise HTTPException(400, "没有可用的工具定义，请先注册工具")
    
    # 2. 格式转换为 OpenAI function calling 格式
    openai_tools = [
        {"type": "function", "function": t}
        for t in tools_def
    ]
    
    # 3. 调用 AI 服务（带工具）
    async def event_generator():
        try:
            # 第一次调用：可能返回工具调用
            result = await ai_service.chat_with_tools(
                messages=req.messages,
                tools=openai_tools,
                provider=req.provider,
                model=req.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
            
            # result: {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}
            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            
            # 如果有工具调用 → 执行 → 继续对话
            if tool_calls:
                yield _sse(f"{{'type':'tool_call', 'calls':{json.dumps(tool_calls, ensure_ascii=False)}}}")
                
                # 执行每个工具调用
                new_messages = list(req.messages)
                
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("arguments", {})
                    
                    yield _sse(json.dumps({
                        "type": "tool_exec",
                        "name": tool_name,
                        "arguments": tool_args,
                    }, ensure_ascii=False))
                    
                    # 执行工具
                    try:
                        tool_result = await registry.call(tool_name, tool_args)
                        tool_result_str = json.dumps(tool_result, ensure_ascii=False, default=str)
                    except Exception as e:
                        tool_result_str = json.dumps({
                            "error": str(e),
                            "success": False,
                        }, ensure_ascii=False)
                    
                    yield _sse(json.dumps({
                        "type": "tool_result",
                        "name": tool_name,
                        "result": tool_result_str,
                    }, ensure_ascii=False))
                    
                    # 追加到消息历史
                    new_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_{tool_name}",
                            "type": "function",
                            "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                        }],
                    })
                    new_messages.append({
                        "role": "tool",
                        "tool_call_id": f"call_{tool_name}",
                        "content": tool_result_str,
                    })
                
                # 工具执行完毕后，让 AI 生成最终回复
                yield _sse(json.dumps({"type": "text_start"}, ensure_ascii=False))
                final_result = await ai_service.chat_with_tools(
                    messages=new_messages,
                    tools=openai_tools,
                    provider=req.provider,
                    model=req.model,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                )
                final_content = final_result.get("content", "")
                # 流式输出最终回复
                # 简单分块
                chunk_size = 20
                for i in range(0, len(final_content), chunk_size):
                    yield _sse(json.dumps({
                        "type": "text",
                        "content": final_content[i:i+chunk_size],
                    }, ensure_ascii=False))
                
            else:
                # 无工具调用 → 直接流式输出
                yield _sse(json.dumps({"type": "text_start"}, ensure_ascii=False))
                chunk_size = 20
                for i in range(0, len(content), chunk_size):
                    yield _sse(json.dumps({
                        "type": "text",
                        "content": content[i:i+chunk_size],
                    }, ensure_ascii=False))
            
            yield _sse(json.dumps({"type": "done"}, ensure_ascii=False))
            
            # 保存会话
            if req.conversation_id:
                from app.agent.router import _save_session
                new_messages = list(req.messages)
                final_content = content or " ".join([m.get("content","") for m in new_messages if m.get("role")=="assistant"])
                new_messages.append({"role": "assistant", "content": final_content})
                _save_session(req.conversation_id, {
                    "messages": new_messages[-50:],  # 保留最近 50 条
                    "updated_at": __import__('datetime').datetime.now().isoformat(),
                })
            
        except Exception as e:
            logger.error("tool_chat failed", error=str(e))
            yield _sse(json.dumps({
                "type": "error",
                "message": str(e),
            }, ensure_ascii=False))
            yield _sse(json.dumps({"type": "done"}, ensure_ascii=False))
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tool-chat/tools")
async def list_available_tools(module: Optional[str] = None):
    """列出可用于工具对话的工具（供前端选择）"""
    if module:
        tools = registry.list_by_module_schemas(module)
    else:
        tools = registry.list_all_schemas()
    return {
        "success": True,
        "total": len(tools),
        "tools": tools,
        "modules": {
            m: len(ns) for m, ns in registry._modules.items()
        } if hasattr(registry, '_modules') else {},
    }


@router.post("/tool-chat/execute")
async def execute_tool_directly(request: dict):
    """
    直接执行工具（不经过 AI，前端手动触发）
    
    请求：{"tool_name": "literature_search", "arguments": {"query": "催化剂"}}
    """
    tool_name = request.get("tool_name", "")
    arguments = request.get("arguments", {})
    if not tool_name:
        raise HTTPException(400, "tool_name 不能为空")
    try:
        result = await registry.call(tool_name, arguments)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"工具执行失败: {str(e)}")


# ─── 辅助函数 ───

def _sse(data: str) -> str:
    """格式化 SSE 数据"""
    return f"data: {data}\n\n"
