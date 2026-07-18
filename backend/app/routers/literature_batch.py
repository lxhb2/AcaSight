"""
批量文献处理路由

提供批量导入、分析、导出、统计接口。
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from pydantic import BaseModel
from dataclasses import asdict
import structlog

from app.services.literature_batch_service import literature_batch_service

logger = structlog.get_logger()
router = APIRouter()


# ==================== 请求模型 ====================

class BatchAnalyzeRequest(BaseModel):
    """批量分析请求"""
    paper_ids: List[int]
    dimensions: List[str] = []


class BatchExportRequest(BaseModel):
    """批量导出请求"""
    paper_ids: List[int]
    format: str = "bibtex"  # bibtex | ris | csv


# ==================== 导入接口 ====================

@router.post("/import")
async def import_literature(file: UploadFile = File(...)):
    """批量导入文献文件

    支持 BibTeX (.bib)、RIS (.ris)、CSV、EndNote XML 格式。
    自动检测格式并解析。
    """
    if not file.filename:
        raise HTTPException(400, "未提供文件名")

    try:
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8-sig', errors='replace')
    except Exception as e:
        raise HTTPException(400, f"文件读取失败: {str(e)}")

    try:
        entries = literature_batch_service.parse_file(file.filename, content)
    except Exception as e:
        logger.error("文献解析失败", filename=file.filename, error=str(e))
        raise HTTPException(400, f"文献解析失败: {str(e)}")

    # 尝试将解析结果导入到数据库
    imported = 0
    duplicates = 0
    saved_entries = []

    try:
        from app.database import get_session
        from app.models.paper import Paper
        from sqlalchemy import select

        async with get_session() as session:
            for entry in entries:
                # 检查是否重复（按 DOI 或标题）
                existing = None
                if entry.doi:
                    result = await session.execute(
                        select(Paper).where(Paper.doi == entry.doi)
                    )
                    existing = result.scalars().first()
                if not existing and entry.title:
                    result = await session.execute(
                        select(Paper).where(Paper.title == entry.title)
                    )
                    existing = result.scalars().first()

                if existing:
                    duplicates += 1
                    saved_entries.append({
                        **asdict(entry),
                        'status': 'duplicate',
                        'existing_id': existing.id,
                    })
                    continue

                # 创建新文献记录
                authors_list = [a.strip() for a in entry.authors.split(';') if a.strip()] if entry.authors else []
                paper = Paper(
                    title=entry.title,
                    authors=authors_list,
                    year=int(entry.year) if entry.year and entry.year.isdigit() else None,
                    journal=entry.journal or None,
                    doi=entry.doi or None,
                    abstract=entry.abstract or None,
                    extra_fields=entry.extra or {},
                )
                session.add(paper)
                imported += 1
                saved_entries.append({
                    **asdict(entry),
                    'status': 'imported',
                })

            await session.flush()
            # 获取新创建的 ID
            for e in saved_entries:
                if e.get('status') == 'imported':
                    # 重新查询获取 ID
                    result = await session.execute(
                        select(Paper).where(Paper.title == e['title']).order_by(Paper.id.desc())
                    )
                    p = result.scalars().first()
                    if p:
                        e['paper_id'] = p.id

    except Exception as e:
        logger.warning("数据库导入失败，仅返回解析结果", error=str(e))
        # 如果数据库不可用，仍然返回解析结果
        imported = len(entries)
        duplicates = 0
        saved_entries = [asdict(entry) | {'status': 'parsed'} for entry in entries]

    return {
        'imported': imported,
        'duplicates': duplicates,
        'entries': saved_entries,
        'total_parsed': len(entries),
    }


# ==================== 批量分析接口 ====================

@router.post("/analyze")
async def batch_analyze(req: BatchAnalyzeRequest):
    """批量分析文献

    对指定文献调用维度分析服务。
    """
    if not req.paper_ids:
        raise HTTPException(400, "请提供文献 ID 列表")

    results = []
    try:
        from app.database import get_session
        from app.models.paper import Paper
        from app.services.dimension_service import extract_dimensions
        from sqlalchemy import select

        async with get_session() as session:
            for pid in req.paper_ids:
                try:
                    result = await session.execute(
                        select(Paper).where(Paper.id == pid)
                    )
                    paper = result.scalars().first()
                    if not paper:
                        results.append({
                            'paper_id': pid,
                            'status': 'not_found',
                            'error': '文献不存在',
                        })
                        continue

                    # 调用维度分析
                    text = paper.abstract or ''
                    if req.dimensions:
                        dims = await extract_dimensions(text, req.dimensions)
                    else:
                        dims = await extract_dimensions(text)

                    results.append({
                        'paper_id': pid,
                        'status': 'analyzed',
                        'title': paper.title,
                        'dimensions': dims,
                    })
                except Exception as e:
                    results.append({
                        'paper_id': pid,
                        'status': 'error',
                        'error': str(e),
                    })
    except Exception as e:
        logger.error("批量分析服务异常", error=str(e))
        raise HTTPException(500, f"批量分析失败: {str(e)}")

    return {
        'results': results,
        'total': len(req.paper_ids),
        'success_count': sum(1 for r in results if r.get('status') == 'analyzed'),
    }


# ==================== 批量导出接口 ====================

@router.post("/export")
async def batch_export(req: BatchExportRequest):
    """批量导出文献

    支持 BibTeX、RIS、CSV 格式。
    """
    if not req.paper_ids:
        raise HTTPException(400, "请提供文献 ID 列表")

    if req.format not in ('bibtex', 'ris', 'csv'):
        raise HTTPException(400, "不支持的导出格式，可选: bibtex, ris, csv")

    papers = []
    try:
        from app.database import get_session
        from app.models.paper import Paper
        from sqlalchemy import select

        async with get_session() as session:
            for pid in req.paper_ids:
                result = await session.execute(
                    select(Paper).where(Paper.id == pid)
                )
                paper = result.scalars().first()
                if paper:
                    papers.append({
                        'title': paper.title,
                        'authors': '; '.join(paper.authors or []),
                        'year': str(paper.year) if paper.year else '',
                        'journal': paper.journal or '',
                        'doi': paper.doi or '',
                        'abstract': paper.abstract or '',
                        'keywords': paper.keywords or [],
                    })
    except Exception as e:
        logger.error("导出查询失败", error=str(e))
        raise HTTPException(500, f"导出查询失败: {str(e)}")

    if not papers:
        raise HTTPException(404, "未找到指定文献")

    try:
        content = literature_batch_service.export_papers(papers, req.format)
    except Exception as e:
        raise HTTPException(500, f"导出格式化失败: {str(e)}")

    # 确定文件扩展名和 MIME 类型
    ext_map = {
        'bibtex': ('bib', 'text/x-bibtex'),
        'ris': ('ris', 'application/x-research-info-systems'),
        'csv': ('csv', 'text/csv'),
    }
    ext, mime = ext_map.get(req.format, ('txt', 'text/plain'))

    return {
        'content': content,
        'format': req.format,
        'paper_count': len(papers),
        'filename': f'literature_export.{ext}',
        'mime_type': mime,
    }


# ==================== 统计接口 ====================

@router.get("/stats")
async def literature_stats():
    """获取文献统计信息

    返回按年份、期刊、关键词的分布统计。
    """
    papers = []
    try:
        from app.database import get_session
        from app.models.paper import Paper
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(select(Paper))
            all_papers = result.scalars().all()
            papers = [
                {
                    'title': p.title,
                    'authors': '; '.join(p.authors or []),
                    'year': str(p.year) if p.year else '',
                    'journal': p.journal or '',
                    'doi': p.doi or '',
                    'abstract': p.abstract or '',
                    'keywords': p.keywords or [],
                }
                for p in all_papers
            ]
    except Exception as e:
        logger.warning("统计查询失败，返回空结果", error=str(e))

    stats = literature_batch_service.compute_statistics(papers)
    return {'success': True, **stats}
