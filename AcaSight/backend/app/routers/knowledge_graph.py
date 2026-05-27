from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, cast, String, or_
from app.database import get_db
from app.models.paper import Paper
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


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
