"""
PubMed Central 检索器 — 从 gpt-researcher 移植并适配 AcaSight

支持:
- PMC 全文搜索 (esearch + efetch)
- PubMed 摘要搜索
- NCBI API Key 加速 (无 key 时自动降级限速)
- 异步 httpx 调用 (复用全局连接池)
"""

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx
import structlog

from app.services.ai_service import get_http_client

logger = structlog.get_logger()

# NCBI E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedRetriever:
    """PubMed / PMC 全文检索器"""

    def __init__(self):
        self.api_key = os.getenv("NCBI_API_KEY", "")
        if not self.api_key:
            logger.warning("NCBI_API_KEY not set — PubMed requests will be rate-limited (3/s → 10/s)")

    async def search(
        self,
        query: str,
        max_results: int = 10,
        db: str = "pmc",
        sort: str = "relevance",
    ) -> List[Dict[str, Any]]:
        """
        搜索 PubMed / PMC 文献。

        Args:
            query: 搜索查询词（支持 MeSH 术语、布尔运算符）
            max_results: 最大返回结果数
            db: 数据库选择 "pmc"（全文）或 "pubmed"（摘要）
            sort: 排序方式 relevance / pub_date

        Returns:
            文献列表，每项含 title, abstract, url, authors, year, doi, source
        """
        # Step 1: Search for article IDs
        article_ids = await self._search_ids(query, max_results, db, sort)
        if not article_ids:
            return []

        # Step 2: Fetch details for each article
        results = []
        client = await get_http_client()

        if not article_ids:
            logger.warning("PubMed: no article IDs returned")
            return []

        logger.info("PubMed fetching articles", ids=article_ids[:5], count=len(article_ids))

        # Batch fetch: NCBI supports comma-separated IDs
        id_str = ",".join(article_ids)
        fetch_params = {
            "db": "pmc" if db == "pmc" else "pubmed",
            "id": id_str,
            "rettype": "full" if db == "pmc" else "abstract",
            "retmode": "xml",
        }
        if self.api_key:
            fetch_params["api_key"] = self.api_key

        try:
            resp = await client.get(EFETCH_URL, params=fetch_params, timeout=30.0)
            resp.raise_for_status()
            logger.info("PubMed fetch response", length=len(resp.text), status=resp.status_code)
            articles = self._parse_fetch_xml(resp.text, db)
            logger.info("PubMed parsed articles", count=len(articles))
            results.extend(articles)
        except Exception as e:
            logger.error("PubMed fetch failed", error=str(e), error_type=type(e).__name__)
            # Fallback: fetch one by one
            for aid in article_ids:
                article = await self._fetch_single(aid, db, client)
                if article:
                    results.append(article)

        return results[:max_results]

    async def _search_ids(
        self, query: str, max_results: int, db: str, sort: str
    ) -> Optional[List[str]]:
        """Step 1: Use esearch to get article IDs"""
        search_term = query
        if db == "pubmed":
            # Filter for articles with full text links
            search_term = f"{query} AND (ffrft[filter] OR pmc[filter])"

        params = {
            "db": db,
            "term": search_term,
            "retmax": max_results,
            "sort": sort,
            "retmode": "json",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            client = await get_http_client()
            resp = await client.get(ESEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            logger.info("PubMed search completed", query=query[:50], results=len(id_list))
            return id_list
        except Exception as e:
            logger.error("PubMed search failed", error=str(e))
            return None

    async def _fetch_single(
        self, article_id: str, db: str, client: httpx.AsyncClient
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single article's details"""
        params = {
            "db": "pmc" if db in ("pmc", "pubmed") else db,
            "id": article_id,
            "rettype": "full" if db == "pmc" else "abstract",
            "retmode": "xml",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            resp = await client.get(EFETCH_URL, params=params)
            resp.raise_for_status()
            articles = self._parse_fetch_xml(resp.text, db)
            return articles[0] if articles else None
        except Exception:
            return None

    def _parse_fetch_xml(self, xml_text: str, db: str) -> List[Dict[str, Any]]:
        """Parse NCBI efetch XML response into structured articles"""
        articles = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.warning("Failed to parse PubMed XML")
            return articles

        # PMC articles
        for article_elem in root.findall(".//article"):
            title_elem = article_elem.find(".//article-title")
            title = self._get_text(title_elem) if title_elem is not None else ""

            # Abstract
            abstract_elem = article_elem.find(".//abstract")
            abstract = " ".join(abstract_elem.itertext()).strip() if abstract_elem is not None else ""

            # Body (PMC only)
            body_elem = article_elem.find(".//body")
            body = " ".join(body_elem.itertext()).strip()[:3000] if body_elem is not None else ""

            # Authors
            authors = []
            for contrib in article_elem.findall(".//contrib[@contrib-type='author']"):
                name = contrib.find(".//name")
                if name is not None:
                    surname = self._get_text(name.find("surname"))
                    given = self._get_text(name.find("given-names"))
                    if surname:
                        authors.append(f"{surname} {given}".strip())

            # Year
            year_elem = article_elem.find(".//pub-date/year")
            year = self._get_text(year_elem) if year_elem is not None else ""

            # DOI
            doi = ""
            for article_id in article_elem.findall(".//article-id"):
                if article_id.get("pub-id-type") == "doi":
                    doi = self._get_text(article_id)

            # PMC ID
            pmc_id = ""
            for article_id in article_elem.findall(".//article-id"):
                if article_id.get("pub-id-type") == "pmc":
                    pmc_id = self._get_text(article_id)

            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/" if pmc_id else ""

            content = f"Title: {title}\n\nAbstract: {abstract}"
            if body:
                content += f"\n\nBody excerpt: {body[:2000]}"

            articles.append({
                "title": title,
                "abstract": abstract,
                "url": url,
                "authors": authors[:5],
                "year": year,
                "doi": doi,
                "source": "PubMed Central" if db == "pmc" else "PubMed",
                "content": content,
            })

        # PubMed abstracts (non-PMC)
        if not articles:
            for pubmed_article in root.findall(".//PubmedArticle"):
                title_elem = pubmed_article.find(".//ArticleTitle")
                title = self._get_text(title_elem) if title_elem is not None else ""

                abstract_parts = []
                for abs_text in pubmed_article.findall(".//AbstractText"):
                    label = abs_text.get("Label", "")
                    text = self._get_text(abs_text)
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                abstract = " ".join(abstract_parts)

                authors = []
                for author in pubmed_article.findall(".//Author"):
                    lastname = self._get_text(author.find("LastName"))
                    forename = self._get_text(author.find("ForeName"))
                    if lastname:
                        authors.append(f"{lastname} {forename}".strip())

                year = ""
                pub_date = pubmed_article.find(".//PubDate")
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    if year_elem is not None:
                        year = self._get_text(year_elem)

                doi = ""
                for aid in pubmed_article.findall(".//ArticleId"):
                    if aid.get("IdType") == "doi":
                        doi = self._get_text(aid)

                pmid = self._get_text(pubmed_article.find(".//PMID"))
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                articles.append({
                    "title": title,
                    "abstract": abstract,
                    "url": url,
                    "authors": authors[:5],
                    "year": year,
                    "doi": doi,
                    "source": "PubMed",
                    "content": f"Title: {title}\n\nAbstract: {abstract}",
                })

        return articles

    @staticmethod
    def _get_text(elem) -> str:
        """Safely extract text from XML element"""
        if elem is None:
            return ""
        return (elem.text or "").strip()


# Singleton instance
pubmed_retriever = PubMedRetriever()
