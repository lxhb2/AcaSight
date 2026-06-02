from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, cast, String, or_
from app.database import get_db
from app.models.paper import Paper
import logging
import httpx
import asyncio
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

# Semantic Scholar API（免费，限流 100 req/5min）
S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,citationCount,journal,abstract,externalIds,openAccessPdf"

# 简单内存缓存（避免重复请求触发限流）
_s2_cache: dict[str, dict] = {}


@router.get("/graph")
async def get_citation_graph(
    paper_id: int | None = None,
    depth: int = Query(2, ge=1, le=3),
    include_search: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).order_by(Paper.created_at.desc()).limit(200))
    papers = result.scalars().all()

    search_papers = []
    if include_search:
        search_papers = await _get_search_papers(db)

    all_papers = list(papers)
    existing_ids = {p.id for p in all_papers}
    for sp in search_papers:
        if sp.id not in existing_ids:
            all_papers.append(sp)
            existing_ids.add(sp.id)

    if not all_papers:
        return {"nodes": [], "links": []}

    nodes = []
    links = []
    paper_map = {}
    doi_map = {}

    for p in all_papers:
        is_online = _is_online_paper(p)
        node = {
            "id": f"paper-{p.id}",
            "label": p.title[:50] if p.title else "Untitled",
            "title": p.title,
            "year": p.year,
            "journal": p.journal,
            "citation_count": p.citation_count or 0,
            "authors": (p.authors or [])[:3],
            "doi": p.doi,
            "tags": p.tags or [],
            "is_favorite": p.is_favorite,
            "group": "online" if is_online else _assign_group(p),
            "source_type": "online" if is_online else "local",
        }
        nodes.append(node)
        paper_map[p.id] = node
        if p.doi:
            doi_map[p.doi] = p.id

    for p in all_papers:
        if p.doi and p.reference_count and p.reference_count > 0:
            refs = _extract_references(p)
            for ref_doi in refs:
                if ref_doi in doi_map and doi_map[ref_doi] != p.id:
                    links.append({
                        "source": f"paper-{p.id}",
                        "target": f"paper-{doi_map[ref_doi]}",
                        "type": "cites",
                    })

    if len(nodes) > 1 and len(links) == 0:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))):
                ni = nodes[i]
                nj = nodes[j]
                shared = set(ni.get("tags", []) or []) & set(nj.get("tags", []) or [])
                if shared:
                    links.append({
                        "source": ni["id"],
                        "target": nj["id"],
                        "type": "shared_tag",
                        "tags": list(shared),
                    })

    if paper_id and paper_id in paper_map:
        center_id = f"paper-{paper_id}"
        connected = set()
        for link in links:
            if link["source"] == center_id:
                connected.add(link["target"])
            if link["target"] == center_id:
                connected.add(link["source"])
        connected.add(center_id)
        nodes = [n for n in nodes if n["id"] in connected]
        links = [l for l in links if l["source"] in connected and l["target"] in connected]

    return {"nodes": nodes, "links": links}


@router.get("/references/{doi:path}")
async def get_reference_graph(
    doi: str,
    max_depth: int = Query(1, ge=1, le=2, description="最大展开深度"),
    max_nodes: int = Query(100, ge=10, le=300, description="最大节点数"),
):
    """Chapter D: 获取论文引用/被引关系图谱（对接 Semantic Scholar API）
    
    以指定 DOI 为中心，获取引用文献和被引文献，构建力导向图数据。
    支持最多 300 个节点，性能友好。
    """
    # 清理 DOI（可能包含前缀或 URL 编码）
    clean_doi = doi.strip()
    if clean_doi.lower().startswith("http"):
        clean_doi = clean_doi.split("doi.org/")[-1]
    
    try:
        # 1. 获取中心论文信息 + 引用/被引列表
        center_paper = await _fetch_s2_paper(clean_doi)
        if not center_paper:
            return {"error": "未找到该 DOI 对应的论文", "nodes": [], "links": []}
        
        refs = center_paper.get("references", [])
        cits = center_paper.get("citations", [])
        
        # 2. 构建节点和边
        nodes = [_paper_to_node(center_paper, group="center")]
        seen_ids = {center_paper.get("paperId")}
        links = []
        
        # 引用文献（当前论文引用了它们）
        for ref in refs[:max_nodes - 1]:
            pid = ref.get("paperId")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            nodes.append(_paper_to_node(ref, group="reference"))
            links.append({
                "source": f"paper-{center_paper.get('paperId')}",
                "target": f"paper-{pid}",
                "type": "references",
            })
        
        # 被引文献（引用了当前论文）
        for cit in cits[:max_nodes - len(nodes)]:
            pid = cit.get("paperId")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            nodes.append(_paper_to_node(cit, group="citation"))
            links.append({
                "source": f"paper-{pid}",
                "target": f"paper-{center_paper.get('paperId')}",
                "type": "cites",
            })
        
        # 3. 深度 2：展开引用文献的引用（可选）
        if max_depth >= 2 and len(nodes) < max_nodes:
            for ref_node in nodes[1:]:  # 跳过中心节点
                if len(nodes) >= max_nodes:
                    break
                ref_dois = (ref_node.get("doi") or [])
                if not ref_dois:
                    continue
                try:
                    ref_paper = await _fetch_s2_paper_cached(
                        ref_dois[0] if isinstance(ref_dois, list) else ref_dois,
                        fields="references.title,references.authors,references.year,references.citationCount"
                    )
                    if ref_paper:
                        for r in (ref_paper.get("references") or [])[:5]:
                            rpid = r.get("paperId")
                            if not rpid or rpid in seen_ids or len(nodes) >= max_nodes:
                                continue
                            seen_ids.add(rpid)
                            nodes.append(_paper_to_node(r, group="indirect"))
                            links.append({
                                "source": ref_node["id"],
                                "target": f"paper-{rpid}",
                                "type": "references",
                            })
                except Exception:
                    pass
        
        return {"nodes": nodes[:max_nodes], "links": links, "center_doi": clean_doi}
    
    except Exception as e:
        logger.error(f"Reference graph failed for DOI {doi}: {e}")
        return {"error": str(e), "nodes": [], "links": []}


@router.get("/graph/stats")
async def get_graph_stats(
    include_search: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(sa_func.count(Paper.id)))
    with_doi = await db.scalar(select(sa_func.count(Paper.id)).where(Paper.doi.isnot(None)))
    with_tags = await db.scalar(
        select(sa_func.count(Paper.id)).where(cast(Paper.tags, String) != "[]")
    )
    online_count = 0
    if include_search:
        online_count = await db.scalar(
            select(sa_func.count(Paper.id)).where(
                or_(
                    Paper.pdf_path.like("http%"),
                    Paper.pdf_path.like("https%"),
                )
            )
        )
    return {
        "total_papers": total or 0,
        "with_doi": with_doi or 0,
        "with_tags": with_tags or 0,
        "online_papers": online_count or 0,
    }


async def _get_search_papers(db: AsyncSession) -> list[Paper]:
    result = await db.execute(
        select(Paper).where(
            or_(
                Paper.pdf_path.like("http%"),
                Paper.pdf_path.like("https%"),
            )
        ).order_by(Paper.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())


def _is_online_paper(paper: Paper) -> bool:
    if paper.pdf_path and (paper.pdf_path.startswith("http://") or paper.pdf_path.startswith("https://")):
        return True
    return False


def _assign_group(paper: Paper) -> str:
    tags = paper.tags or []
    if not tags:
        return "other"
    return str(tags[0])


def _extract_references(paper: Paper) -> list[str]:
    dois = []
    if paper.extra_fields and isinstance(paper.extra_fields, dict):
        refs = paper.extra_fields.get("references", [])
        for ref in refs:
            if isinstance(ref, dict) and ref.get("doi"):
                dois.append(ref["doi"])
            elif isinstance(ref, str) and ref.startswith("10."):
                dois.append(ref)
    return dois


# ==================== Semantic Scholar API 客户端 ====================

async def _fetch_s2_paper(doi: str, fields: str = "") -> Optional[dict]:
    """获取论文详细信息 + 引用/被引列表"""
    cache_key = f"{doi}:{fields}" if fields else doi
    if cache_key in _s2_cache:
        return _s2_cache[cache_key]
    
    f = fields or f"references.title,references.authors,references.year,references.citationCount,references.journal,references.abstract,citations.title,citations.authors,citations.year,citations.citationCount,citations.journal,citations.abstract,{S2_FIELDS}"
    url = f"{S2_BASE}/paper/DOI:{doi}?fields={f}"
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                _s2_cache[cache_key] = data
                return data
            elif resp.status_code == 429:
                logger.warning(f"Semantic Scholar rate limited for DOI: {doi}")
                await asyncio.sleep(2)
                return await _fetch_s2_paper(doi, fields)  # retry once
            elif resp.status_code == 404:
                return None
            logger.warning(f"S2 API {resp.status_code} for DOI: {doi}")
            return None
    except Exception as e:
        logger.error(f"S2 fetch failed: {e}")
        return None


async def _fetch_s2_paper_cached(doi: str, fields: str = "") -> Optional[dict]:
    """同上但使用已缓存的值"""
    cache_key = f"{doi}:{fields}" if fields else doi
    if cache_key in _s2_cache:
        return _s2_cache[cache_key]
    return await _fetch_s2_paper(doi, fields)


def _paper_to_node(paper: dict, group: str = "other") -> dict:
    """将 Semantic Scholar 论文数据转为图谱节点"""
    title = (paper.get("title") or "Untitled").strip()
    authors_raw = paper.get("authors") or []
    authors = [a.get("name", "") for a in authors_raw] if isinstance(authors_raw, list) else []
    pid = paper.get("paperId", "")
    external_ids = paper.get("externalIds") or {}
    doi_val = external_ids.get("DOI", "")
    
    return {
        "id": f"paper-{pid}",
        "paperId": pid,
        "label": title[:50],
        "title": title,
        "year": paper.get("year"),
        "journal": (paper.get("journal") or {}).get("name") if isinstance(paper.get("journal"), dict) else paper.get("journal"),
        "citation_count": paper.get("citationCount", 0) or 0,
        "authors": authors[:3],
        "doi": doi_val,
        "tags": [],
        "is_favorite": False,
        "group": group,
        "source_type": "online",
    }


# ==================== Phase 7: 引用网络端点 (方向A A.2) ====================

from app.services.citation_network import get_citation_network_service


@router.get("/citations/{doi:path}")
async def get_citation_network(
    doi: str,
    max_depth: int = Query(1, ge=1, le=2, description="展开深度"),
    max_nodes: int = Query(100, ge=10, le=300, description="最大节点数"),
    direction: str = Query("both", description="方向: references/citations/both"),
):
    """Phase 7 A.2: 获取引用关系网络（使用 CitationNetworkService）
    
    以指定 DOI 为中心，获取引用/被引关系，构建力导向图数据。
    使用独立的 citation_network.py 服务，支持持久化缓存和限流控制。
    """
    service = get_citation_network_service()
    result = await service.fetch_citation_network(
        doi=doi,
        max_depth=max_depth,
        max_nodes=max_nodes,
        direction=direction,
    )
    return result


@router.post("/citations/batch")
async def batch_fetch_citations(
    dois: List[str] = Query(..., description="DOI 列表"),
    max_per_paper: int = Query(20, ge=1, le=50, description="每篇最大返回引用数"),
):
    """Phase 7 A.2: 批量获取多篇论文的引用信息"""
    service = get_citation_network_service()
    results = await service.batch_fetch_citations(dois=dois, max_per_paper=max_per_paper)
    return {"success": True, "results": results}


# ==================== Phase 7: 精准引用匹配端点 (方向A A.4) ====================

from pydantic import BaseModel as PdModel
from app.services.citation_matcher import get_citation_matcher


class SectionMatchRequest(PdModel):
    """章节引用匹配请求"""
    section_title: str
    section_content: str = ""
    reference_paper_ids: Optional[List[int]] = None
    top_k: int = 5


class OutlineMatchRequest(PdModel):
    """大纲引用匹配请求"""
    outline: List[Dict[str, Any]]
    reference_paper_ids: Optional[List[int]] = None
    top_k_per_section: int = 3


@router.post("/match/section")
async def match_citations_for_section(req: SectionMatchRequest):
    """Phase 7 A.4: 为章节匹配最相关的引用"""
    matcher = get_citation_matcher()
    matches = await matcher.match_citations_for_section(
        section_title=req.section_title,
        section_content=req.section_content,
        reference_paper_ids=req.reference_paper_ids,
        top_k=req.top_k,
    )
    return {"success": True, "section_title": req.section_title, "matches": matches}


@router.post("/match/outline")
async def match_citations_for_outline(req: OutlineMatchRequest):
    """Phase 7 A.4: 为大纲每个章节匹配引用"""
    matcher = get_citation_matcher()
    results = await matcher.match_for_outline(
        outline=req.outline,
        reference_paper_ids=req.reference_paper_ids,
        top_k_per_section=req.top_k_per_section,
    )
    return {"success": True, "matches": results}
