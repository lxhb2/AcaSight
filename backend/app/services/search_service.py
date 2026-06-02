"""
文献搜索服务
聚合多个数据源：CORE, OpenAlex, Semantic Scholar, Crossref, Europe PMC, arXiv
"""

import asyncio
from typing import List, Dict, Optional
import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class LiteratureSearchService:
    """文献搜索服务"""
    
    def __init__(self):
        self.clients = {
            'core': CoreClient(),
            'openalex': OpenAlexClient(),
            'semanticscholar': SemanticScholarClient(),
            'crossref': CrossrefClient(),
            'europepmc': EuropePMCClient(),
            'arxiv': ArxivClient(),
        }
    
    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> Dict[str, List[Dict]]:
        """
        并行搜索多个数据源
        
        Args:
            query: 搜索关键词
            sources: 数据源列表，默认搜索所有
            limit: 每个数据源返回数量
            year_from: 起始年份
            year_to: 结束年份
        
        Returns:
            按数据源分组的结果
        """
        if sources is None:
            sources = list(self.clients.keys())
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for source in sources:
                if source in self.clients:
                    tasks.append(
                        self._search_source(
                            client, source, query, limit, year_from, year_to
                        )
                    )
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for source, response in zip(sources, responses):
                if isinstance(response, Exception):
                    logger.error(f"Search failed for {source}", error=str(response))
                    results[source] = {
                        'error': str(response),
                        'results': []
                    }
                else:
                    results[source] = response
        
        return results
    
    async def _search_source(
        self,
        client: httpx.AsyncClient,
        source: str,
        query: str,
        limit: int,
        year_from: Optional[int],
        year_to: Optional[int],
    ) -> Dict:
        """搜索单个数据源"""
        try:
            client_impl = self.clients[source]
            results = await client_impl.search(
                client, query, limit, year_from, year_to
            )
            return {
                'source': source,
                'results': results,
                'count': len(results)
            }
        except Exception as e:
            logger.error(f"Error searching {source}", error=str(e))
            raise
    
    async def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献详情"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 尝试多个数据源
            for source_name, client_impl in self.clients.items():
                try:
                    result = await client_impl.get_by_doi(client, doi)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"Failed to get DOI from {source_name}", error=str(e))
        
        return None


class OpenAlexClient:
    """OpenAlex API 客户端"""
    BASE_URL = "https://api.openalex.org"
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        params = {
            "search": query,
            "per-page": limit,
            "sort": "relevance_score:desc",
        }
        
        # 添加年份过滤
        if year_from or year_to:
            filter_parts = []
            if year_from:
                filter_parts.append(f"from_publication_date:{year_from}-01-01")
            if year_to:
                filter_parts.append(f"to_publication_date:{year_to}-12-31")
            params["filter"] = ",".join(filter_parts)
        
        response = await client.get(
            f"{self.BASE_URL}/works",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_work(w) for w in data.get('results', [])]
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        response = await client.get(
            f"{self.BASE_URL}/works/doi:{doi}"
        )
        if response.status_code == 200:
            return self._format_work(response.json())
        return None
    
    def _format_work(self, work: Dict) -> Dict:
        """格式化文献数据"""
        open_access = work.get('open_access', {})
        
        return {
            'id': work.get('id'),
            'title': work.get('display_name'),
            'authors': [
                a['author']['display_name']
                for a in work.get('authorships', [])
            ],
            'abstract': work.get('abstract'),
            'year': work.get('publication_year'),
            'doi': work.get('doi'),
            'pmid': work.get('ids', {}).get('pmid'),
            'journal': work.get('host_venue', {}).get('display_name'),
            'cited_by_count': work.get('cited_by_count'),
            'is_open_access': open_access.get('is_oa', False),
            'pdf_url': open_access.get('oa_url'),
            'source': 'openalex',
        }


class SemanticScholarClient:
    """Semantic Scholar API 客户端"""
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        params = {
            "query": query,
            "fields": "title,authors,year,citationCount,abstract,openAccessPdf,externalIds",
            "limit": limit,
        }
        
        if year_from:
            params["year"] = f"{year_from}-{year_to or ''}"
        
        response = await client.get(
            f"{self.BASE_URL}/paper/search",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_paper(p) for p in data.get('data', [])]
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        response = await client.get(
            f"{self.BASE_URL}/paper/DOI:{doi}",
            params={"fields": "title,authors,year,citationCount,abstract,openAccessPdf,externalIds"}
        )
        if response.status_code == 200:
            return self._format_paper(response.json())
        return None
    
    def _format_paper(self, paper: Dict) -> Dict:
        """格式化文献数据"""
        open_access = paper.get('openAccessPdf', {})
        external_ids = paper.get('externalIds', {})
        
        return {
            'id': paper.get('paperId'),
            'title': paper.get('title'),
            'authors': [a['name'] for a in paper.get('authors', [])],
            'abstract': paper.get('abstract'),
            'year': paper.get('year'),
            'doi': external_ids.get('DOI'),
            'pmid': external_ids.get('PubMed'),
            'arxiv_id': external_ids.get('ArXiv'),
            'journal': paper.get('venue'),
            'cited_by_count': paper.get('citationCount'),
            'is_open_access': bool(open_access.get('url')),
            'pdf_url': open_access.get('url'),
            'source': 'semanticscholar',
        }


class CrossrefClient:
    """Crossref API 客户端"""
    BASE_URL = "https://api.crossref.org"
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        params = {
            "query": query,
            "rows": limit,
            "sort": "relevance",
            "order": "desc",
        }
        
        if year_from:
            params["filter"] = f"from-pub-date:{year_from}"
        if year_to:
            filter_str = params.get("filter", "")
            if filter_str:
                filter_str += ","
            filter_str += f"until-pub-date:{year_to}"
            params["filter"] = filter_str
        
        response = await client.get(
            f"{self.BASE_URL}/works",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_work(w) for w in data.get('message', {}).get('items', [])]
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        response = await client.get(
            f"{self.BASE_URL}/works/{doi}"
        )
        if response.status_code == 200:
            return self._format_work(response.json().get('message', {}))
        return None
    
    def _format_work(self, work: Dict) -> Dict:
        """格式化文献数据"""
        return {
            'id': work.get('DOI'),
            'title': work.get('title', [''])[0] if work.get('title') else '',
            'authors': [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in work.get('author', [])
            ],
            'abstract': work.get('abstract'),
            'year': work.get('published-print', {}).get('date-parts', [[None]])[0][0],
            'doi': work.get('DOI'),
            'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
            'cited_by_count': work.get('is-referenced-by-count'),
            'is_open_access': work.get('open-access', {}).get('bool', False),
            'source': 'crossref',
        }


class EuropePMCClient:
    """Europe PMC API 客户端"""
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        # 构建查询
        search_query = query
        if year_from:
            search_query += f" AND (YEAR:{year_from}-{year_to or ''})"
        
        params = {
            "query": search_query,
            "pageSize": limit,
            "format": "json",
            "sort": "relevance",
        }
        
        response = await client.get(
            f"{self.BASE_URL}/search",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_result(r) for r in data.get('resultList', {}).get('result', [])]
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        response = await client.get(
            f"{self.BASE_URL}/search",
            params={"query": f"DOI:{doi}", "format": "json", "pageSize": 1}
        )
        if response.status_code == 200:
            results = response.json().get('resultList', {}).get('result', [])
            if results:
                return self._format_result(results[0])
        return None
    
    def _format_result(self, result: Dict) -> Dict:
        """格式化文献数据"""
        return {
            'id': result.get('id'),
            'title': result.get('title'),
            'authors': result.get('authorString', '').split(', '),
            'abstract': result.get('abstractText'),
            'year': result.get('pubYear'),
            'doi': result.get('doi'),
            'pmid': result.get('pmid'),
            'pmcid': result.get('pmcid'),
            'journal': result.get('journalTitle'),
            'cited_by_count': result.get('citedByCount'),
            'is_open_access': result.get('isOpenAccess') == 'Y',
            'pdf_url': result.get('fullTextUrlList', {}).get('fullTextUrl', [{}])[0].get('url'),
            'source': 'europepmc',
        }


class ArxivClient:
    """arXiv API 客户端"""
    BASE_URL = "http://export.arxiv.org/api/query"
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        search_query = f"all:{query}"
        
        # 添加年份过滤
        if year_from:
            search_query += f" AND submittedDate:[{year_from}0101 TO {year_to or '9999'}1231]"
        
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        
        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        # 解析 Atom XML
        return self._parse_atom(response.text)
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        params = {
            "search_query": f"doi:{doi}",
            "max_results": 1,
        }
        
        response = await client.get(self.BASE_URL, params=params)
        if response.status_code == 200:
            results = self._parse_atom(response.text)
            return results[0] if results else None
        return None
    
    def _parse_atom(self, xml_text: str) -> List[Dict]:
        """解析 Atom XML"""
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(xml_text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        results = []
        for entry in root.findall('atom:entry', ns):
            # 提取 arXiv ID
            id_elem = entry.find('atom:id', ns)
            arxiv_id = id_elem.text.split('/')[-1] if id_elem is not None else ''
            
            # 提取作者
            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns)
                if name is not None:
                    authors.append(name.text)
            
            # 提取类别
            categories = []
            for cat in entry.findall('atom:category', ns):
                term = cat.get('term')
                if term:
                    categories.append(term)
            
            results.append({
                'id': arxiv_id,
                'title': entry.findtext('atom:title', '', ns).replace('\n', ' ').strip(),
                'authors': authors,
                'abstract': entry.findtext('atom:summary', '', ns).replace('\n', ' ').strip(),
                'year': entry.findtext('atom:published', '', ns)[:4],
                'doi': None,
                'arxiv_id': arxiv_id,
                'journal': 'arXiv',
                'cited_by_count': None,
                'is_open_access': True,
                'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                'categories': categories,
                'source': 'arxiv',
            })
        
        return results


class CoreClient:
    """CORE API v3 客户端 - 全球开放获取论文聚合服务"""
    BASE_URL = "https://api.core.ac.uk/v3"
    
    def __init__(self):
        self.api_key = getattr(settings, 'CORE_API_KEY', '') or 'kSbRLqWtrlBE4uaNsQMjpAO2gD8nz569'
    
    async def search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 20,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict]:
        """搜索文献"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        q_parts = [query]
        if year_from or year_to:
            yf = year_from or 1900
            yt = year_to or 2099
            q_parts.append(f"yearPublished>={yf} AND yearPublished<={yt}")
        
        params = {
            "q": " AND ".join(q_parts) if len(q_parts) > 1 else query,
            "limit": min(limit, 100),
            "offset": 0,
            "sort": "relevance",
        }
        
        response = await client.get(
            f"{self.BASE_URL}/search/works",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_work(w) for w in data.get('results', [])]
    
    async def get_by_doi(self, client: httpx.AsyncClient, doi: str) -> Optional[Dict]:
        """通过 DOI 获取文献"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = await client.get(
            f"{self.BASE_URL}/search/works",
            headers=headers,
            params={"q": f"doi:\"{doi}\"", "limit": 1},
        )
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                return self._format_work(results[0])
        return None
    
    async def search_advanced(
        self,
        client: httpx.AsyncClient,
        query: str,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        journal: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        fulltext: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """高级搜索 - 使用 POST 聚合接口"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        q_parts = []
        if query:
            q_parts.append(query)
        if title:
            q_parts.append(f"title:\"{title}\"")
        if authors:
            q_parts.append(f"authors:\"{authors}\"")
        if journal:
            q_parts.append(f"journal:\"{journal}\"")
        if year_from or year_to:
            yf = year_from or 1900
            yt = year_to or 2099
            q_parts.append(f"yearPublished>={yf} AND yearPublished<={yt}")
        
        body = {
            "q": " AND ".join(q_parts) if q_parts else "*",
            "limit": min(limit, 100),
            "offset": offset,
            "sort": "relevance",
        }
        
        if fulltext:
            body["q"] += f" AND fullText:\"{fulltext}\""
        
        response = await client.post(
            f"{self.BASE_URL}/search/works",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "totalHits": data.get("totalHits", 0),
            "results": [self._format_work(w) for w in data.get('results', [])],
        }
    
    async def discover_fulltext(
        self,
        client: httpx.AsyncClient,
        doi: Optional[str] = None,
        title: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[Dict]:
        """发现全文链接"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {}
        if doi:
            body["doi"] = doi
        if title:
            body["title"] = title
        if year:
            body["year"] = year
        
        response = await client.post(
            f"{self.BASE_URL}/discover",
            headers=headers,
            json=body,
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _format_work(self, work: Dict) -> Dict:
        """格式化文献数据"""
        authors_list = []
        for a in work.get('authors', []):
            if isinstance(a, dict):
                authors_list.append(a.get('name', ''))
            elif isinstance(a, str):
                authors_list.append(a)
        
        download_url = work.get('downloadUrl') or work.get('sourceFulltextUrl') or ''
        
        return {
            'id': work.get('id'),
            'title': work.get('title', ''),
            'authors': authors_list,
            'abstract': work.get('abstract', ''),
            'year': work.get('yearPublished'),
            'doi': work.get('doi'),
            'journal': work.get('journal', '') or (work.get('publisher', '') if work.get('publisher') else ''),
            'cited_by_count': work.get('citationCount', 0),
            'is_open_access': bool(download_url),
            'pdf_url': download_url,
            'source_fulltext_url': work.get('sourceFulltextUrl', ''),
            'repositories': [r.get('name', '') for r in work.get('repositories', []) if isinstance(r, dict)],
            'language': work.get('language', ''),
            'source': 'core',
        }


# ==================== 全局实例 ====================

# 模块级实例 — 方便 from ... import search_service
search_service = LiteratureSearchService()
