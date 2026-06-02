"""
精准引用匹配器 — 写作时按章节关键词匹配文献维度数据
Phase 7, 方向A A.4 — DEVLOG-031

功能:
  - 章节标题/关键词 → 匹配11维度数据
  - 返回相关文献段落 + 引用格式
  - SSE流中插入引用推荐事件
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import Paper
from app.models.paper_dimensions import PaperDimensions

logger = logging.getLogger(__name__)

# 11维度 → 关键词映射
DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "research_problem": ["问题", "背景", "动机", "problem", "background", "motivation", "challenge", "issue"],
    "methodology": ["方法", "模型", "算法", "method", "model", "algorithm", "approach", "framework", "technique"],
    "dataset": ["数据集", "数据源", "样本", "dataset", "data", "corpus", "benchmark", "sample"],
    "experimental_design": ["实验设计", "实验设置", "experimental", "setup", "protocol", "procedure"],
    "results": ["结果", "发现", "results", "findings", "outcome", "performance"],
    "analysis": ["分析", "讨论", "analysis", "discussion", "interpretation", "comparison"],
    "limitations": ["局限", "不足", "limitation", "weakness", "constraint", "future work"],
    "conclusions": ["结论", "总结", "conclusion", "summary", "contribution", "takeaway"],
    "related_work": ["相关工作", "文献综述", "related", "survey", "literature", "previous", "prior"],
    "novelty": ["创新", "新颖", "novel", "innovation", "contribution", "unique", "first"],
    "reproducibility": ["复现", "开源", "代码", "reproduce", "open-source", "code", "available"],
}

# 章节类型 → 最相关维度映射
SECTION_DIMENSION_MAP: Dict[str, List[str]] = {
    "introduction": ["research_problem", "novelty", "related_work"],
    "background": ["related_work", "research_problem", "methodology"],
    "related_work": ["related_work", "methodology", "novelty"],
    "literature_review": ["related_work", "research_problem", "methodology"],
    "methodology": ["methodology", "dataset", "experimental_design", "reproducibility"],
    "method": ["methodology", "dataset", "experimental_design"],
    "experiment": ["experimental_design", "dataset", "methodology"],
    "experiment_design": ["experimental_design", "dataset", "methodology"],
    "results": ["results", "analysis", "dataset"],
    "discussion": ["analysis", "limitations", "results", "conclusions"],
    "conclusion": ["conclusions", "limitations", "novelty"],
    "future_work": ["limitations", "conclusions", "novelty"],
}


def _extract_section_type(section_title: str) -> str:
    """从章节标题推断章节类型"""
    title_lower = section_title.lower()
    for section_type in SECTION_DIMENSION_MAP:
        if section_type in title_lower:
            return section_type
    # 英文常见标题
    for key in ["intro", "background", "survey", "approach", "setup", "finding", "limit", "conclud", "future"]:
        if key in title_lower:
            for st in SECTION_DIMENSION_MAP:
                if key in st:
                    return st
    return ""


def _extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """从文本中提取关键词（简单分词+去停用词）"""
    # 中英文混合分词
    # 英文词
    en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    # 中文词（2-4字）
    cn_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    
    # 停用词
    en_stop = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "this", "that", "with", "from", "they", "been", "have", "will", "what", "when", "which", "their", "about", "would", "could", "should", "these", "those", "other", "than", "then", "also", "more", "some", "such", "only", "into", "over", "most", "very", "much", "many", "well", "using", "based", "each", "where", "while", "how", "both", "between"}
    cn_stop = {"基于", "通过", "进行", "提出", "本文", "研究", "分析", "方法", "结果", "表明", "可以", "利用", "实现", "一种", "以及", "对于", "根据", "首先", "然后", "最后", "同时", "并且", "因此", "所以", "由于", "但是", "然而"}
    
    filtered = []
    seen = set()
    for w in en_words:
        if w not in en_stop and w not in seen and len(w) >= 3:
            seen.add(w)
            filtered.append(w)
    for w in cn_words:
        if w not in cn_stop and w not in seen:
            seen.add(w)
            filtered.append(w)
    
    return filtered[:max_keywords]


def _compute_relevance_score(
    section_type: str,
    section_keywords: List[str],
    dimension_key: str,
    dimension_content: str,
) -> float:
    """计算章节与维度数据的匹配度"""
    score = 0.0
    
    # 维度类型匹配（权重 40%）
    relevant_dims = SECTION_DIMENSION_MAP.get(section_type, [])
    if dimension_key in relevant_dims:
        score += 0.4 * (1.0 / (relevant_dims.index(dimension_key) + 1))
    
    # 关键词匹配（权重 40%）
    content_lower = dimension_content.lower()
    keyword_hits = sum(1 for kw in section_keywords if kw.lower() in content_lower)
    if section_keywords:
        score += 0.4 * (keyword_hits / max(len(section_keywords), 1))
    
    # 内容丰富度（权重 20%）
    content_len = len(dimension_content.strip())
    if content_len > 500:
        score += 0.2
    elif content_len > 200:
        score += 0.1
    
    return round(score, 4)


class CitationMatcherService:
    """精准引用匹配服务"""

    async def match_citations_for_section(
        self,
        section_title: str,
        section_content: str,
        reference_paper_ids: Optional[List[int]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        为章节匹配最相关的引用
        
        Args:
            section_title: 章节标题
            section_content: 章节已有内容（可为空）
            reference_paper_ids: 限定匹配的文献ID列表（None=全部）
            top_k: 返回前K个匹配
        
        Returns:
            [
                {
                    "paper_id": 1,
                    "title": "...",
                    "authors": "...",
                    "year": 2024,
                    "doi": "...",
                    "dimension_key": "methodology",
                    "dimension_label": "研究方法",
                    "matched_content": "...",
                    "relevance_score": 0.85,
                    "citation_format": "[1] Author et al. (2024) ...",
                },
                ...
            ]
        """
        section_type = _extract_section_type(section_title)
        keywords = _extract_keywords(f"{section_title} {section_content}")
        
        async for db in get_db():
            # 查询文献
            query = select(Paper)
            if reference_paper_ids:
                query = query.where(Paper.id.in_(reference_paper_ids))
            query = query.order_by(Paper.citation_count.desc().nullslast()).limit(100)
            result = await db.execute(query)
            papers = result.scalars().all()
            
            if not papers:
                return []
            
            # 查询维度数据
            paper_ids = [p.id for p in papers]
            dim_query = select(PaperDimensions).where(PaperDimensions.paper_id.in_(paper_ids))
            dim_result = await db.execute(dim_query)
            dimensions = dim_result.scalars().all()
            
            # 构建 paper_id → dimensions 映射
            dim_map: Dict[int, List[PaperDimensions]] = {}
            for d in dimensions:
                dim_map.setdefault(d.paper_id, []).append(d)
            
            # 计算匹配分数
            candidates: List[Tuple[float, Dict[str, Any]]] = []
            
            for paper in papers:
                paper_dims = dim_map.get(paper.id, [])
                for dim in paper_dims:
                    content = dim.content or ""
                    if len(content.strip()) < 20:
                        continue
                    
                    score = _compute_relevance_score(
                        section_type=section_type,
                        section_keywords=keywords,
                        dimension_key=dim.dimension_key,
                        dimension_content=content,
                    )
                    
                    if score < 0.05:
                        continue
                    
                    # 生成引用格式
                    authors_str = ""
                    if paper.authors:
                        if isinstance(paper.authors, list):
                            authors_str = paper.authors[0] if paper.authors else ""
                            if len(paper.authors) > 1:
                                authors_str += " et al."
                        else:
                            authors_str = str(paper.authors)[:50]
                    
                    year_str = f" ({paper.year})" if paper.year else ""
                    citation_format = f"[{paper.id}] {authors_str}{year_str}. {paper.title or 'Untitled'}."
                    if paper.journal:
                        citation_format += f" {paper.journal}."
                    
                    match = {
                        "paper_id": paper.id,
                        "title": paper.title,
                        "authors": paper.authors,
                        "year": paper.year,
                        "doi": paper.doi,
                        "dimension_key": dim.dimension_key,
                        "dimension_label": dim.dimension_label or dim.dimension_key,
                        "matched_content": content[:500],
                        "relevance_score": score,
                        "citation_format": citation_format,
                    }
                    candidates.append((score, match))
            
            # 按分数排序
            candidates.sort(key=lambda x: x[0], reverse=True)
            return [c[1] for c in candidates[:top_k]]

    async def match_for_outline(
        self,
        outline: List[Dict[str, Any]],
        reference_paper_ids: Optional[List[int]] = None,
        top_k_per_section: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        为大纲的每个章节匹配引用
        
        Args:
            outline: [{level: 1, title: "...", description: "..."}, ...]
            reference_paper_ids: 限定匹配的文献ID列表
            top_k_per_section: 每节最大返回数
        
        Returns:
            {"1 Introduction": [...matches], "2 Methodology": [...matches], ...}
        """
        results = {}
        for section in outline:
            title = section.get("title", "")
            description = section.get("description", "")
            matches = await self.match_citations_for_section(
                section_title=title,
                section_content=description,
                reference_paper_ids=reference_paper_ids,
                top_k=top_k_per_section,
            )
            results[title] = matches
        return results


# 全局单例
_citation_matcher: Optional[CitationMatcherService] = None


def get_citation_matcher() -> CitationMatcherService:
    """获取引用匹配服务单例"""
    global _citation_matcher
    if _citation_matcher is None:
        _citation_matcher = CitationMatcherService()
    return _citation_matcher
