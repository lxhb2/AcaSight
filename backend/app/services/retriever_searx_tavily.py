"""
SearXNG 检索器 — 从 gpt-researcher 移植并适配 AcaSight

支持:
- SearXNG 自建实例 API 搜索
- 隐私优先的元搜索引擎
- 自定义实例 URL (SEARX_URL 环境变量)
- 异步 httpx 调用
"""

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import structlog

from app.services.ai_service import get_http_client

logger = structlog.get_logger()


class SearXRetriever:
    """SearXNG 元搜索引擎检索器"""

    def __init__(self):
        self.base_url = os.getenv("SEARX_URL", "")
        if not self.base_url:
            logger.info("SEARX_URL not set — SearX retriever disabled")
        else:
            if not self.base_url.endswith("/"):
                self.base_url += "/"
            logger.info("SearXNG configured", url=self.base_url)

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        categories: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        搜索 SearXNG 实例。

        Args:
            query: 搜索查询词
            max_results: 最大返回结果数
            categories: 搜索类别 (general/science/images 等), None=全部
            language: 搜索语言

        Returns:
            搜索结果列表
        """
        if not self.available:
            logger.warning("SearXNG not configured, skipping")
            return []

        search_url = urljoin(self.base_url, "search")
        params = {
            "q": query,
            "format": "json",
            "language": language,
        }
        if categories:
            params["categories"] = categories

        try:
            client = await get_http_client()
            resp = await client.get(
                search_url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "engine": item.get("engine", ""),
                    "score": item.get("score", 0),
                    "category": item.get("category", ""),
                    "source": "SearXNG",
                })

            logger.info("SearX search completed", query=query[:50], results=len(results))
            return results

        except Exception as e:
            logger.error("SearX search failed", error=str(e))
            return []


class TavilyRetriever:
    """Tavily API 检索器 — AI 驱动的搜索 API"""

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com/search"
        if not self.api_key:
            logger.info("TAVILY_API_KEY not set — Tavily retriever disabled")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        topic: str = "general",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索 Tavily API。

        Args:
            query: 搜索查询词
            max_results: 最大返回结果数
            search_depth: "basic" 或 "advanced"
            topic: "general" 或 "news" 或 "research"
            include_domains: 限定域名列表
            exclude_domains: 排除域名列表

        Returns:
            搜索结果列表
        """
        if not self.available:
            logger.warning("Tavily not configured, skipping")
            return []

        payload = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_answer": True,
            "include_raw_content": False,
            "api_key": self.api_key,
        }

        try:
            client = await get_http_client()
            resp = await client.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                    "source": "Tavily",
                })

            # Include AI-generated answer if available
            answer = data.get("answer", "")
            if answer:
                results.insert(0, {
                    "title": "AI Summary",
                    "url": "",
                    "content": answer,
                    "score": 1.0,
                    "source": "Tavily AI",
                })

            logger.info("Tavily search completed", query=query[:50], results=len(results))
            return results

        except Exception as e:
            logger.error("Tavily search failed", error=str(e))
            return []


# Singleton instances
searx_retriever = SearXRetriever()
tavily_retriever = TavilyRetriever()
