"""
智能写作助手端点 — 段落扩写/缩写/润色/翻译/降重
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai_service import AIService
import structlog

logger = structlog.get_logger()
router = APIRouter()

_ai = AIService()

# ─── 请求/响应模型 ───

class WritingRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待处理的文本")
    action: str = Field(..., description="操作类型: expand / shrink / polish / translate / rewrite")
    target_lang: Optional[str] = Field(default="en", description="翻译目标语言 (仅 translate 时有效)")
    context: Optional[str] = Field(default="", description="上下文信息（帮助 AI 理解写作场景）")
    model: Optional[str] = Field(default=None, description="指定模型（覆盖默认模型）")

class WritingResponse(BaseModel):
    result: str = ""
    action: str = ""
    word_count_before: int = 0
    word_count_after: int = 0

# ─── 系统提示词 ───

ACTION_PROMPTS = {
    "expand": """你是一位学术写作专家。请将用户给出的文本扩写，要求：
1. 保持原意不变，补充细节、论据和逻辑连接
2. 使用正式学术语言
3. 扩展后的文本应为原文的 2-3 倍长度
4. 补充的论据应合理、可信
5. 保持段落结构完整
直接输出扩写后的文本，不要加任何前言或解释。""",

    "shrink": """你是一位学术编辑。请将用户给出的文本缩写，要求：
1. 保留核心观点和关键信息
2. 删除冗余描述、重复论证
3. 缩写后文本约为原文的 1/3 长度
4. 保持逻辑完整、语言精炼
5. 不丢失任何重要信息
直接输出缩写后的文本，不要加任何前言或解释。""",

    "polish": """你是一位资深的学术论文润色编辑。请润色用户给出的文本，要求：
1. 将口语化表达转为正式学术语言
2. 改善句式结构，增强逻辑连贯性
3. 使用更准确的学术术语
4. 修正语法错误和表达不当
5. 保持原意不变，不添加新内容
直接输出润色后的文本，不要加任何前言或解释。""",

    "translate": """你是一位专业的学术翻译专家。请将用户给出的文本翻译为{target_lang}，要求：
1. 术语翻译准确，符合学科惯例
2. 保持学术语言风格
3. 长句适当拆分，确保译文流畅自然
4. 专有名词保留原文或按通行译法
5. 被动语态按目标语言习惯调整
直接输出翻译后的文本，不要加任何前言或解释。""",

    "rewrite": """你是一位学术写作专家。请对用户给出的文本进行降重改写，要求：
1. 完全改写句式结构和表达方式，但保持原意不变
2. 同义词替换、句式转换、主被动转换
3. 调整段落结构但不改变逻辑
4. 确保降重后文本与原文查重率低于 15%
5. 保持学术风格和专业性
直接输出改写后的文本，不要加任何前言或解释。""",
}

VALID_ACTIONS = set(ACTION_PROMPTS.keys())


@router.post("/process", response_model=WritingResponse)
async def process_writing(req: WritingRequest):
    """智能写作处理"""
    if req.action not in VALID_ACTIONS:
        raise HTTPException(400, f"不支持的操作类型: {req.action}，可选: {', '.join(sorted(VALID_ACTIONS))}")

    system_prompt = ACTION_PROMPTS[req.action]
    if req.action == "translate":
        lang_map = {"en": "英文", "zh": "中文", "ja": "日文", "de": "德文", "fr": "法文", "ko": "韩文"}
        target = lang_map.get(req.target_lang or "en", req.target_lang or "英文")
        system_prompt = system_prompt.format(target_lang=target)

    # 构建用户消息
    parts = []
    if req.context:
        parts.append(f"【写作背景】{req.context}")
    parts.append(f"【待处理文本】\n{req.text}")
    user_message = "\n\n".join(parts)

    try:
        text_parts: list[str] = []
        async for chunk in _ai.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            temperature=0.5,
            model=req.model,
        ):
            text_parts.append(chunk)

        result = "".join(text_parts).strip()

        # 简单字数统计（中英混合）
        wc_before = len(req.text.replace(" ", ""))
        wc_after = len(result.replace(" ", ""))

        return WritingResponse(
            result=result,
            action=req.action,
            word_count_before=wc_before,
            word_count_after=wc_after,
        )

    except Exception as e:
        logger.error("writing_process_failed", action=req.action, error=str(e))
        raise HTTPException(500, f"AI 处理失败: {str(e)}")
