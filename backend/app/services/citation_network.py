"""
引用网络数据服务 — 对接 Semantic Scholar API 获取引用/被引关系
Phase 7, 方向A A.1 — DEVLOG-031

功能:
  - 单篇论文引用/被引获取
  - 批量引用网络构建（支持深度展开）
  - 内存缓存 + 限流控制
  - 缓存持久化至 data/citation_cache.json
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Semantic Scholar API 配置
S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS_PAPER = "title,authors,year,citationCount,referenceCount,journal,abstract,externalIds,openAccessPdf,fieldsOfStudy"
S2_FIELDS_REFS = "title,authors,year,citationCount,referenceCount,journal,externalIds,fieldsOfStudy"

# 限流: 100 req / 5 min → 保守 1 req / 3s
_MIN_INTERVAL = 3.0
_last_request_time = 0.0
_request_lock = asyncio.Lock()

# 内存缓存
_memory_cache: Dict[str, Dict[str, Any]] = {}

# 持久化缓存路径
_CACHE_DIR = Path("data")
_CACHE_FILE = _CACHE_DIR / "citation_cache.json"


def _load_persistent_cache() -> Dict[str, Any]:
    """从磁盘加载缓存"""
    try:
        if _CACHE_FILE.exists():
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load citation cache: {e}")
    return {}


def _save_persistent_cache(cache: Dict[str, Any]) -> None:
    """持久化缓存到磁盘"""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
    except Exception as e:
        logger.warning(f"Failed to save citation cache: {e}")


async def _rate_limit() -> None:
    """Semantic Scholar 限流控制"""
    global _last_request_time
    async with _request_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_INTERVAL:
            await asyncio.sleep(_MIN_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


def _clean_doi(doi: str) -> str:
    """清理 DOI 格式"""
    clean = doi.strip()
    if clean.lower().startswith("http"):
        clean = clean.split("doi.org/")[-1]
    return clean


class CitationNetworkService:
    """引用网络数据获取服务"""

    def __init__(self):
        self._disk_cache = _load_persistent_cache()

    async def fetch_paper(self, doi: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取单篇论文详情（含引用/被引列表ID）
        
        返回格式:
        {
            "paperId": "xxx",
            "doi": "10.xxx/xxx",
            "title": "...",
            "authors": [{"name": "..."}],
            "year": 2024,
            "citationCount": 42,
            "referenceCount": 30,
            "journal": {"name": "..."},
            "abstract": "...",
            "references": [{"paperId": "xxx", "doi": "..."}],
            "citations": [{"paperId": "xxx", "doi": "..."}],
            "fieldsOfStudy": ["Computer Science"],
        }
        """
        clean = _clean_doi(doi)
        cache_key = f"paper:{clean}"

        # 内存缓存
        if use_cache and cache_key in _memory_cache:
            return _memory_cache[cache_key]
        # 磁盘缓存
        if use_cache and cache_key in self._disk_cache:
            _memory_cache[cache_key] = self._disk_cache[cache_key]
            return self._disk_cache[cache_key]

        await _rate_limit()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{S2_BASE}/paper/DOI:{clean}"
                params = {
                    "fields": f"{S2_FIELDS_PAPER},references.paperId,references.doi,references.title,references.year,references.citationCount,citations.paperId,citations.doi,citations.title,citations.year,citations.citationCount"
                }
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    logger.info(f"S2 paper not found: DOI:{clean}")
                    return None
                resp.raise_for_status()
                data = resp.json()

            # 缓存
            _memory_cache[cache_key] = data
            self._disk_cache[cache_key] = data
            # 每 50 次请求持久化一次
            if len(_memory_cache) % 50 == 0:
                _save_persistent_cache(self._disk_cache)

            return data

        except httpx.HTTPStatusError as e:
            logger.warning(f"S2 API error for DOI:{clean}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"S2 fetch failed for DOI:{clean}: {e}")
            return None

    async def fetch_citation_network(
        self,
        doi: str,
        max_depth: int = 1,
        max_nodes: int = 100,
        direction: str = "both",
    ) -> Dict[str, Any]:
        """
        构建以指定 DOI 为中心的引用网络
        
        Args:
            doi: 中心论文 DOI
            max_depth: 展开深度 (1-2)
            max_nodes: 最大节点数 (10-300)
            direction: "references" | "citations" | "both"
        
        Returns:
        {
            "center_doi": "10.xxx/xxx",
            "nodes": [...],
            "links": [...],
            "stats": {"total_nodes": N, "total_links": M, "by_group": {...}}
        }
        """
        clean = _clean_doi(doi)
        center = await self.fetch_paper(clean)
        if not center:
            return {"center_doi": clean, "nodes": [], "links": [], "stats": {"total_nodes": 0, "total_links": 0}}

        center_id = center.get("paperId", clean)
        nodes = [self._paper_to_node(center, group="center")]
        seen_ids = {center_id}
        links = []

        # 一级展开：引用文献
        if direction in ("references", "both"):
            refs = center.get("references") or []
            for ref in refs[:max_nodes]:
                pid = ref.get("paperId")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                nodes.append(self._paper_to_node(ref, group="reference"))
                links.append({
                    "source": f"paper-{center_id}",
                    "target": f"paper-{pid}",
                    "type": "references",
                })

        # 一级展开：被引文献
        if direction in ("citations", "both"):
            cits = center.get("citations") or []
            remaining = max_nodes - len(nodes)
            for cit in cits[:remaining]:
                pid = cit.get("paperId")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                nodes.append(self._paper_to_node(cit, group="citation"))
                links.append({
                    "source": f"paper-{pid}",
                    "target": f"paper-{center_id}",
                    "type": "cites",
                })

        # 二级展开（仅引用方向，限制每节点最多展开5个）
        if max_depth >= 2 and len(nodes) < max_nodes:
            ref_nodes = [n for n in nodes if n.get("group") == "reference"]
            for ref_node in ref_nodes:
                if len(nodes) >= max_nodes:
                    break
                ref_doi_list = ref_node.get("doi")
                ref_doi_val = ref_doi_list[0] if isinstance(ref_doi_list, list) else ref_doi_list
                if not ref_doi_val:
                    continue
                try:
                    ref_paper = await self.fetch_paper(ref_doi_val)
                    if not ref_paper:
                        continue
                    sub_refs = ref_paper.get("references") or []
                    for sr in sub_refs[:5]:
                        if len(nodes) >= max_nodes:
                            break
                        spid = sr.get("paperId")
                        if not spid or spid in seen_ids:
                            continue
                        seen_ids.add(spid)
                        nodes.append(self._paper_to_node(sr, group="indirect"))
                        links.append({
                            "source": ref_node["id"],
                            "target": f"paper-{spid}",
                            "type": "references",
                        })
                except Exception:
                    pass

        # 统计
        by_group: Dict[str, int] = {}
        for n in nodes:
            g = n.get("group", "unknown")
            by_group[g] = by_group.get(g, 0) + 1

        # 持久化
        _save_persistent_cache(self._disk_cache)

        return {
            "center_doi": clean,
            "nodes": nodes[:max_nodes],
            "links": links,
            "stats": {
                "total_nodes": min(len(nodes), max_nodes),
                "total_links": len(links),
                "by_group": by_group,
            },
        }

    async def batch_fetch_citations(
        self,
        dois: List[str],
        max_per_paper: int = 20,
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多篇论文的引用信息
        
        Returns:
        {
            "10.xxx/a": {"citation_count": 42, "top_citations": [...]},
            "10.xxx/b": {"citation_count": 10, "top_citations": [...]},
        }
        """
        results = {}
        for doi in dois:
            paper = await self.fetch_paper(doi)
            if paper:
                cits = paper.get("citations") or []
                results[doi] = {
                    "doi": doi,
                    "title": paper.get("title"),
                    "citation_count": paper.get("citationCount", 0),
                    "reference_count": paper.get("referenceCount", 0),
                    "top_citations": [
                        {
                            "paperId": c.get("paperId"),
                            "title": c.get("title"),
                            "year": c.get("year"),
                            "citationCount": c.get("citationCount"),
                        }
                        for c in sorted(cits, key=lambda x: x.get("citationCount") or 0, reverse=True)[:max_per_paper]
                    ],
                }
            else:
                results[doi] = {"doi": doi, "error": "not_found"}
        return results

    @staticmethod
    def _paper_to_node(paper: Dict[str, Any], group: str = "unknown") -> Dict[str, Any]:
        """将 S2 论文数据转换为图节点"""
        pid = paper.get("paperId", "")
        authors = paper.get("authors") or []
        journal = paper.get("journal") or {}
        doi_val = paper.get("externalIds", {}).get("DOI") or paper.get("doi") or ""

        return {
            "id": f"paper-{pid}",
            "paperId": pid,
            "doi": doi_val,
            "title": paper.get("title", "Untitled"),
            "label": (paper.get("title") or "Untitled")[:50],
            "year": paper.get("year"),
            "citationCount": paper.get("citationCount", 0),
            "referenceCount": paper.get("referenceCount", 0),
            "authors": [a.get("name", "") for a in authors[:5]],
            "journal": journal.get("name") if isinstance(journal, dict) else str(journal),
            "fieldsOfStudy": paper.get("fieldsOfStudy") or [],
            "group": group,
        }


# 全局单例
_citation_network_service: Optional[CitationNetworkService] = None


def get_citation_network_service() -> CitationNetworkService:
    """获取引用网络服务单例"""
    global _citation_network_service
    if _citation_network_service is None:
        _citation_network_service = CitationNetworkService()
    return _citation_network_service
