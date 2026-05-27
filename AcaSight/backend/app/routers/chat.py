"""
AI 对话路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json

from app.services.ai_service import AIService
from app.database import get_db

router = APIRouter()


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage]
    provider: Optional[str] = None
    model: Optional[str] = None
    conversation_id: Optional[str] = None
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None


@router.post("/", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
):
    """
    AI 对话
    
    支持多模型，非流式输出
    """
    ai_service: AIService = request.app.state.ai_service
    
    conversation_id = chat_request.conversation_id
    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())
    session_key = f"session:{conversation_id}"

    try:
        messages = [m.model_dump() for m in chat_request.messages]
        
        # 尝试配置的 provider，失败时自动回退到其他可用 provider
        providers_to_try = []
        preferred = chat_request.provider or "default"
        
        if preferred != "default":
            providers_to_try.append(preferred)
        
        # 获取所有可用 provider
        try:
            from app.services.ai_service import ai_service as _ai_svc
            pconf = _ai_svc.get_available_providers()
            # pconf 是 List[Dict]，每个含 name/enabled/available
            enabled = [p['name'] for p in pconf if p.get('enabled') or p.get('available')]
            
            if preferred == "default":
                providers_to_try = enabled or ["ollama"]
            else:
                # 优先 preferred，再 fallback 其他
                others = [p for p in enabled if p != preferred]
                providers_to_try = [preferred] + others
        except Exception:
            providers_to_try = [preferred if preferred != "default" else "ollama"]
        
        last_error = None
        response = ""
        
        for provider in providers_to_try:
            try:
                response = ""
                async for chunk in ai_service.chat(
                    messages=messages,
                    provider=provider,
                    model=chat_request.model,
                    stream=False,
                    temperature=chat_request.temperature,
                    max_tokens=chat_request.max_tokens,
                ):
                    response += chunk
                
                if response.strip():
                    return ChatResponse(
                        content=response,
                        provider=provider,
                        model=chat_request.model or "default",
                    )
            except Exception as e:
                last_error = e
                continue
        
        # 所有 provider 都失败
        error_msg = str(last_error) if last_error else "所有 AI 服务均不可用"
        raise HTTPException(
            status_code=503,
            detail=f"AI 服务暂不可用: {error_msg}。请前往设置页面配置可用的 AI 提供商（如 SiliconFlow / OpenAI），或启动本地 Ollama。"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
):
    """
    AI 对话 - 流式输出
    
    支持 SSE (Server-Sent Events) 流式输出
    """
    ai_service: AIService = request.app.state.ai_service
    
    async def generate():
        try:
            messages = [m.model_dump() for m in chat_request.messages]
            
            async for chunk in ai_service.chat(
                messages=messages,
                provider=chat_request.provider,
                model=chat_request.model,
                stream=True,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens,
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@router.post("/summary")
async def generate_summary(
    request: Request,
    text: str,
    max_length: int = 500,
):
    """
    生成摘要
    """
    ai_service: AIService = request.app.state.ai_service
    
    try:
        summary = await ai_service.generate_summary(text, max_length)
        return {"summary": summary}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate")
async def translate(
    request: Request,
    text: str,
    target_language: str = "zh",
):
    """
    翻译文本
    """
    ai_service: AIService = request.app.state.ai_service
    
    try:
        translation = await ai_service.translate(text, target_language)
        return {"translation": translation}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research-gaps")
async def find_research_gaps(
    request: Request,
    papers: List[dict],
):
    """
    发现研究空白
    """
    ai_service: AIService = request.app.state.ai_service
    
    try:
        gaps = await ai_service.find_research_gaps(papers)
        return {"research_gaps": gaps}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_providers(request: Request):
    """
    获取可用的 AI 提供商
    """
    ai_service: AIService = request.app.state.ai_service
    
    return {
        "providers": ai_service.get_available_providers()
    }
