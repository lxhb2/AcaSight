"""
DBLP 会议论文检索服务 — 借鉴 PaperHunter

通过 DBLP 公开 API 检索会议论文，支持:
- 按会议+年份+关键词检索
- 按作者检索
- 按标题精确检索
- 结果可直接导入论文库
"""

import re
import httpx
import structlog
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = structlog.get_logger()

DBLP_API_BASE = "https://dblp.org/search/publ/api"

MAJOR_CONFERENCES = {
    "ai": ["aaai", "ijcai", "nips", "icml", "iclr"],
    "cv": ["cvpr", "iccv", "eccv"],
    "nlp": ["acl", "emnlp", "naacl", "coling"],
    "systems": ["asplos", "isca", "micro", "osdi", "sosp", "eurosys", "nsdi", "sosp"],
    "security": ["ccs", "uss", "ndss", "sp"],
    "db": ["sigmod", "vldb", "icde", "kdd"],
    "se": ["icse", "fse", "ase", "msr"],
    "network": ["sigcomm", "infocom", "mobicom"],
    "hci": ["chi", "cscw", "uist"],
    "graphics": ["siggraph", "eg", "pg"],
}


@dataclass
class DBLPPaper:
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""
    doi: str = ""
    url: str = ""
    type: str = ""
    key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
            "type": self.type,
            "key": self.key,
        }


class DBLPService:
    """DBLP 论文检索服务"""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def search(
        self,
        query: str,
        limit: int = 30,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venue: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {
            "q": query,
            "format": "json",
            "h": min(limit, 100),
            "f": 0,
        }

        try:
            resp = await self._client.get(DBLP_API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("DBLP search failed", query=query, error=str(e))
            return {"results": [], "total": 0, "query": query, "error": str(e)}

        hits = data.get("result", {}).get("hits", {})
        total = int(hits.get("@total", 0))
        papers = []

        for hit in hits.get("hit", []):
            info = hit.get("info", {})
            paper = DBLPPaper(
                title=info.get("title", ""),
                authors=self._parse_authors(info.get("authors", {})),
                year=int(info.get("year", 0)),
                venue=info.get("venue", ""),
                doi=info.get("doi", ""),
                url=info.get("url", ""),
                type=info.get("type", ""),
                key=info.get("key", ""),
            )

            if year_from and paper.year < year_from:
                continue
            if year_to and paper.year > year_to:
                continue
            if venue and venue.lower() not in paper.venue.lower():
                continue

            papers.append(paper.to_dict())

        return {
            "results": papers,
            "total": total,
            "returned": len(papers),
            "query": query,
        }

    async def search_by_author(
        self,
        author: str,
        limit: int = 30,
    ) -> Dict[str, Any]:
        return await self.search(f"author:{author}", limit=limit)

    async def search_by_venue(
        self,
        venue: str,
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        query_parts = [venue]
        if year:
            query_parts.append(str(year))
        if keyword:
            query_parts.append(keyword)
        query = " ".join(query_parts)
        return await self.search(query, limit=limit, venue=venue)

    async def get_conference_papers(
        self,
        conference: str,
        year: int,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        query = f"{conference} {year}"
        if keyword:
            query += f" {keyword}"
        return await self.search(query, limit=limit)

    def get_supported_conferences(self) -> Dict[str, List[str]]:
        return dict(MAJOR_CONFERENCES)

    def _parse_authors(self, authors_data: Any) -> List[str]:
        if isinstance(authors_data, dict):
            author = authors_data.get("author", [])
            if isinstance(author, list):
                return [a.get("text", str(a)) if isinstance(a, dict) else str(a) for a in author]
            elif isinstance(author, dict):
                return [author.get("text", str(author))]
            elif isinstance(author, str):
                return [author]
        elif isinstance(authors_data, list):
            return [a.get("text", str(a)) if isinstance(a, dict) else str(a) for a in authors_data]
        return []

    async def close(self):
        await self._client.aclose()


_dblp_service: Optional[DBLPService] = None


def get_dblp_service() -> DBLPService:
    global _dblp_service
    if _dblp_service is None:
        _dblp_service = DBLPService()
    return _dblp_service
