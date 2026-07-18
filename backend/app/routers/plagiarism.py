"""
论文查重路由

提供文本/文件查重、历史记录查询接口。
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from dataclasses import asdict
import structlog

from app.services.plagiarism_service import plagiarism_service

logger = structlog.get_logger()
router = APIRouter()


# ==================== 请求模型 ====================

class CheckRequest(BaseModel):
    """文本查重请求"""
    text: str
    paper_ids: Optional[List[int]] = None
    check_type: str = "local"  # local | external


# ==================== 查重接口 ====================

@router.post("/check")
async def check_text(req: CheckRequest):
    """检查文本相似度

    - local: 与本地数据库中的文献比对
    - external: 预留外部 API 接口
    """
    if not req.text or not req.text.strip():
        raise HTTPException(400, "请提供待检查文本")

    reference_texts = []

    if req.check_type == "local":
        # 从本地数据库获取参考文本
        reference_texts = await _get_local_references(req.paper_ids)
    elif req.check_type == "external":
        # 外部查重：预留接口
        return {
            'similarity_score': 0.0,
            'matches': [],
            'message': '外部查重服务暂未接入，请使用本地查重',
            'checked_at': '',
            'text_length': len(req.text),
            'reference_count': 0,
        }
    else:
        raise HTTPException(400, "不支持的查重类型，可选: local, external")

    result = plagiarism_service.check_similarity(req.text, reference_texts)
    return asdict(result)


@router.post("/check-file")
async def check_file(file: UploadFile = File(...)):
    """检查文档文件的相似度

    支持 .txt / .md / .docx 格式。
    """
    if not file.filename:
        raise HTTPException(400, "未提供文件名")

    # 检查文件格式
    lower_name = file.filename.lower()
    if not lower_name.endswith(('.txt', '.md', '.docx')):
        raise HTTPException(400, "仅支持 .txt / .md / .docx 格式")

    try:
        content_bytes = await file.read()
        text = plagiarism_service.extract_text_from_file(content_bytes, file.filename)
    except Exception as e:
        raise HTTPException(400, f"文件读取失败: {str(e)}")

    if not text.strip():
        raise HTTPException(400, "文件内容为空")

    # 获取本地参考文本
    reference_texts = await _get_local_references()

    result = plagiarism_service.check_similarity(text, reference_texts)
    return asdict(result)


# ==================== 历史记录接口 ====================

@router.get("/history")
async def get_history(limit: int = 20):
    """获取查重历史记录"""
    history = plagiarism_service.get_history(limit=limit)
    return {
        'success': True,
        'history': history,
        'count': len(history),
    }


# ==================== 内部辅助函数 ====================

async def _get_local_references(paper_ids: Optional[List[int]] = None) -> List[dict]:
    """从本地数据库获取参考文本"""
    references = []
    try:
        from app.database import get_session
        from app.models.paper import Paper
        from sqlalchemy import select

        async with get_session() as session:
            if paper_ids:
                result = await session.execute(
                    select(Paper).where(Paper.id.in_(paper_ids))
                )
            else:
                # 限制最多查询 100 篇作为参考
                result = await session.execute(
                    select(Paper).limit(100)
                )
            papers = result.scalars().all()

            for p in papers:
                content = p.abstract or ''
                if not content:
                    continue
                references.append({
                    'title': p.title,
                    'authors': '; '.join(p.authors or []),
                    'content': content,
                })
    except Exception as e:
        logger.warning("获取本地参考文本失败", error=str(e))

    return references
