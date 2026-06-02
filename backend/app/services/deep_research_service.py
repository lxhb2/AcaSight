"""
Deep Research 服务 — 从 gpt-researcher 移植并适配 AcaSight

核心功能:
- 子问题分解（LLM 生成搜索子查询 + 研究目标）
- 递归深度搜索（breadth × depth 迭代）
- 多检索器并行聚合（PubMed + SearX + Tavily + CORE + OpenAlex）
- 学习提取 + 后续问题生成
- SSE 流式进度推送

设计原则:
- 不依赖 gpt-researcher 框架，纯自研适配层
- 复用 AcaSight 的 ai_service (task_type="deep_research")
- 复用全局 httpx 连接池
- 三种模式: quick(1×3), deep(2×4), comprehensive(3×5)
"""

import asyncio
import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import structlog

from app.services.ai_service import ai_service
from app.services.retriever_pubmed import pubmed_retriever
from app.services.retriever_searx_tavily import searx_retriever, tavily_retriever
from app.services.search_service import search_service

logger = structlog.get_logger()


# ============== 辅助函数 ==============

async def _ai_chat(messages, task_type="deep_research", temperature=0.4, max_tokens=None) -> str:
    """调用 ai_service.chat() 并收集完整响应"""
    result = ""
    async for chunk in ai_service.chat(
        messages=messages,
        task_type=task_type,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        result += chunk
    return result

# ============== 常量 ==============

RESEARCH_MODES = {
    "quick": {"breadth": 3, "depth": 1, "concurrency": 2, "max_learnings": 5, "label": "快速研究", "est_time": "3-5 min"},
    "deep": {"breadth": 4, "depth": 2, "concurrency": 2, "max_learnings": 8, "label": "深度研究", "est_time": "10-15 min"},
    "comprehensive": {"breadth": 5, "depth": 3, "concurrency": 3, "max_learnings": 12, "label": "综合研究", "est_time": "20-30 min"},
}

MAX_CONTEXT_WORDS = 25000


# ============== 辅助函数 ==============

def parse_search_queries(response: str, num_queries: int) -> List[Dict[str, str]]:
    """从 LLM 响应中解析搜索子查询"""
    queries: List[Dict[str, str]] = []

    # Try JSON first
    try:
        # Extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
        if json_match:
            parsed = json.loads(json_match.group(1).strip())
        else:
            parsed = json.loads(response.strip())

        if isinstance(parsed, dict):
            items = parsed.get("queries") or parsed.get("searchQueries") or parsed.get("items") or []
        elif isinstance(parsed, list):
            items = parsed
        else:
            items = []

        for item in items:
            if isinstance(item, dict) and item.get("query"):
                queries.append({
                    "query": item["query"].strip(),
                    "researchGoal": item.get("researchGoal", item.get("research_goal", "")).strip(),
                })
        if queries:
            return queries[:num_queries]
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: parse line by line
    current_query = {}
    for line in response.splitlines():
        line = line.strip()
        q_match = re.match(r'^(?:[-*]|\d+[.)])?\s*Query:\s*(.+)$', line, re.IGNORECASE)
        g_match = re.match(r'^(?:[-*]|\d+[.)])?\s*(?:Goal|Research Goal):\s*(.+)$', line, re.IGNORECASE)

        if q_match:
            if current_query.get("query") and current_query.get("researchGoal"):
                queries.append(current_query)
            current_query = {"query": q_match.group(1).strip()}
        elif g_match and current_query.get("query"):
            current_query["researchGoal"] = g_match.group(1).strip()

    if current_query.get("query") and current_query.get("researchGoal"):
        queries.append(current_query)

    return queries[:num_queries]


def parse_research_results(response: str, num_learnings: int) -> Dict[str, Any]:
    """从 LLM 响应中解析研究结果（学习 + 后续问题）"""
    learnings: List[Dict[str, str]] = []
    follow_up: List[str] = []
    citations: Dict[str, str] = {}

    try:
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
        if json_match:
            parsed = json.loads(json_match.group(1).strip())
        else:
            parsed = json.loads(response.strip())

        if isinstance(parsed, dict):
            for item in parsed.get("learnings", []):
                if isinstance(item, dict):
                    insight = item.get("insight") or item.get("learning") or ""
                    source = item.get("sourceUrl") or item.get("citation") or ""
                    if insight:
                        learnings.append({"insight": insight.strip(), "source": source.strip()})
                        if source:
                            citations[insight.strip()] = source.strip()
                elif str(item).strip():
                    learnings.append({"insight": str(item).strip(), "source": ""})

            for item in parsed.get("followUpQuestions", parsed.get("questions", [])):
                if str(item).strip():
                    follow_up.append(str(item).strip())

            if learnings or follow_up:
                return {"learnings": learnings[:num_learnings], "followUpQuestions": follow_up[:num_learnings], "citations": citations}
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: parse line by line
    for line in response.replace("```json", "").replace("```", "").splitlines():
        line = line.strip()
        if not line:
            continue
        learning_match = re.match(r'^(?:[-*]|\d+[.)])?\s*Learning(?:\s*\[([^\]]+)\])?:\s*(.+)$', line, re.IGNORECASE)
        question_match = re.match(r'^(?:[-*]|\d+[.)])?\s*(?:Question:\s*)?(.+\?)$', line, re.IGNORECASE)

        if learning_match:
            citation = (learning_match.group(1) or "").strip()
            insight = learning_match.group(2).strip()
            if insight:
                learnings.append({"insight": insight, "source": citation})
                if citation:
                    citations[insight] = citation
        elif question_match:
            follow_up.append(question_match.group(1).strip())

    return {"learnings": learnings[:num_learnings], "followUpQuestions": follow_up[:num_learnings], "citations": citations}


def count_words(text) -> int:
    if isinstance(text, list):
        text = " ".join(str(item) for item in text)
    return len(str(text).split())


def trim_context(context_list: List[str], max_words: int = MAX_CONTEXT_WORDS) -> List[str]:
    """Trim context to stay within word limit, keeping most recent items"""
    total = 0
    trimmed = []
    for item in reversed(context_list):
        words = count_words(item)
        if total + words <= max_words:
            trimmed.insert(0, item)
            total += words
        else:
            break
    return trimmed


# ============== 主服务类 ==============

class DeepResearchService:
    """Deep Research 多步骤研究服务"""

    async def generate_search_queries(self, query: str, num_queries: int = 3) -> List[Dict[str, str]]:
        """LLM 生成搜索子查询"""
        messages = [
            {
                "role": "system",
                "content": "You are an expert researcher generating search queries. Return valid JSON only. Do not include markdown, code fences, bullets, numbering, or prose.",
            },
            {
                "role": "user",
                "content": (
                    f"Given the following research question, generate {num_queries} unique search queries to research the topic thoroughly. "
                    "For each query, provide a research goal.\n\n"
                    'Return ONLY a JSON array: [{"query": "<search query>", "researchGoal": "<research goal>"}]\n\n'
                    f"Research question: {query}"
                ),
            },
        ]

        response = await _ai_chat(messages, task_type="deep_research", temperature=0.4)
        return parse_search_queries(response, num_queries)

    async def process_research_results(
        self, query: str, context: str, num_learnings: int = 5
    ) -> Dict[str, Any]:
        """从搜索结果中提取学习和后续问题"""
        messages = [
            {
                "role": "system",
                "content": "You are an expert researcher analyzing search results. Return valid JSON only.",
            },
            {
                "role": "user",
                "content": (
                    f"Given the following research results for the query '{query}', extract key learnings and suggest "
                    "follow-up questions. For each learning, include a citation to the source URL if available.\n\n"
                    'Return ONLY a JSON object: {"learnings": [{"insight": "<insight>", "sourceUrl": "<url or empty>"}], '
                    '"followUpQuestions": ["<question 1>", "<question 2>"]}\n\n'
                    f"Research results:\n{context[:8000]}"
                ),
            },
        ]

        response = await _ai_chat(messages, task_type="deep_research", temperature=0.4)
        return parse_research_results(response, num_learnings)

    async def _search_all_sources(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """多检索器并行搜索"""
        all_results = []
        tasks = []

        # AcaSight 内置搜索 (CORE + OpenAlex + Semantic Scholar + Crossref + arXiv + Unpaywall)
        tasks.append(self._search_acasight(query, max_results))

        # PubMed Central
        tasks.append(self._search_pubmed(query, max_results))

        # SearXNG (if configured)
        if searx_retriever.available:
            tasks.append(self._search_searx(query, max_results))

        # Tavily (if configured)
        if tavily_retriever.available:
            tasks.append(self._search_tavily(query, max_results))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, list):
                all_results.extend(r)
            elif isinstance(r, Exception):
                logger.warning("Search source failed", error=str(r))

        return all_results

    async def _search_acasight(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            from app.services.ai_service import get_http_client
            client = await get_http_client()
            results = await search_service.search(client, query, limit=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", r.get("doi", "")),
                    "content": r.get("abstract", r.get("snippet", "")),
                    "authors": r.get("authors", []),
                    "year": r.get("year", ""),
                    "citation_count": r.get("citation_count", 0),
                    "source": r.get("source", "AcaSight"),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("AcaSight search failed", error=str(e))
            return []

    async def _search_pubmed(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            return await pubmed_retriever.search(query, max_results=max_results)
        except Exception as e:
            logger.warning("PubMed search failed", error=str(e))
            return []

    async def _search_searx(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            return await searx_retriever.search(query, max_results=max_results, categories="science")
        except Exception as e:
            logger.warning("SearX search failed", error=str(e))
            return []

    async def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            return await tavily_retriever.search(query, max_results=max_results, topic="research")
        except Exception as e:
            logger.warning("Tavily search failed", error=str(e))
            return []

    async def deep_research(
        self,
        query: str,
        mode: str = "deep",
        on_progress=None,
    ) -> Dict[str, Any]:
        """
        执行 Deep Research。

        Args:
            query: 研究问题
            mode: "quick" / "deep" / "comprehensive"
            on_progress: SSE 进度回调 (step, depth, breadth, status)

        Returns:
            {
                "summary": str,
                "papers": [...],
                "insights": [...],
                "gaps": [...],
                "citations": {...},
                "context": str,
                "metadata": {...}
            }
        """
        config = RESEARCH_MODES.get(mode, RESEARCH_MODES["deep"])
        breadth = config["breadth"]
        depth = config["depth"]
        max_learnings = config["max_learnings"]

        start_time = time.time()

        if on_progress:
            on_progress("initializing", 0, 0, "Starting deep research...")

        # Step 1: Generate sub-queries
        if on_progress:
            on_progress("planning", 0, 0, "Generating research plan...")

        serp_queries = await self.generate_search_queries(query, num_queries=breadth)
        logger.info("Deep research plan generated", queries=len(serp_queries))

        # Step 2: Iterative search + extract
        all_learnings: List[Dict[str, str]] = []
        all_papers: List[Dict[str, Any]] = []
        all_citations: Dict[str, str] = {}
        all_context: List[str] = []
        visited_queries: Set[str] = set()

        for d in range(depth):
            if on_progress:
                on_progress("searching", d + 1, 0, f"Depth {d+1}/{depth}: Searching...")

            queries_to_process = serp_queries if d == 0 else [
                {"query": f"{query} {insight['insight'][:100]}", "researchGoal": insight["insight"]}
                for insight in all_learnings[-breadth:]
                if insight["insight"] not in visited_queries
            ][:breadth]

            for b_idx, sq in enumerate(queries_to_process):
                q_key = sq["query"][:100]
                if q_key in visited_queries:
                    continue
                visited_queries.add(q_key)

                if on_progress:
                    on_progress("searching", d + 1, b_idx + 1, f"Searching: {q_key[:60]}...")

                # Multi-source search
                results = await self._search_all_sources(sq["query"], max_results=5)

                # Collect papers
                for r in results:
                    if r.get("title") and r not in all_papers:
                        paper = {
                            "title": r.get("title", ""),
                            "authors": r.get("authors", []),
                            "year": r.get("year", ""),
                            "url": r.get("url", ""),
                            "doi": r.get("doi", ""),
                            "citation_count": r.get("citation_count", 0),
                            "key_finding": r.get("content", "")[:200],
                            "source": r.get("source", ""),
                            "relevance": round(r.get("score", 0.5), 2),
                        }
                        all_papers.append(paper)

                # Build context from results
                context_text = "\n\n".join(
                    f"Source: {r.get('source', 'Unknown')}\nTitle: {r.get('title', '')}\n{r.get('content', '')[:1000]}"
                    for r in results
                )
                all_context.append(context_text)

                # Extract learnings
                if on_progress:
                    on_progress("analyzing", d + 1, b_idx + 1, f"Analyzing results...")

                research_output = await self.process_research_results(sq["query"], context_text, max_learnings)
                for learning in research_output.get("learnings", []):
                    if learning["insight"] not in [l["insight"] for l in all_learnings]:
                        all_learnings.append(learning)
                    if learning.get("source"):
                        all_citations[learning["insight"]] = learning["source"]

        # Step 3: Synthesize
        if on_progress:
            on_progress("synthesizing", depth, breadth, "Synthesizing findings...")

        summary = await self._synthesize(query, all_learnings, all_papers)
        gaps = await self._identify_gaps(query, all_learnings)

        elapsed = round(time.time() - start_time, 1)

        # Step 4: Build result
        result = {
            "summary": summary,
            "papers": all_papers[:20],
            "insights": [
                {"title": f"Insight {i+1}", "description": l["insight"], "relatedPapers": [l["source"]] if l.get("source") else []}
                for i, l in enumerate(all_learnings[:max_learnings])
            ],
            "gaps": gaps,
            "citations": all_citations,
            "context": "\n\n".join(trim_context(all_context)),
            "metadata": {
                "mode": mode,
                "breadth": breadth,
                "depth": depth,
                "total_queries": len(visited_queries),
                "total_papers": len(all_papers),
                "total_insights": len(all_learnings),
                "elapsed_seconds": elapsed,
                "sources_used": ["AcaSight", "PubMed Central"] + (["SearXNG"] if searx_retriever.available else []) + (["Tavily"] if tavily_retriever.available else []),
            },
        }

        if on_progress:
            on_progress("completed", depth, breadth, "Research completed!")

        return result

    async def _synthesize(self, query: str, learnings: List[Dict[str, str]], papers: List[Dict[str, Any]]) -> str:
        """综合学习内容生成摘要"""
        learning_text = "\n".join(f"- {l['insight']}" for l in learnings[:10])
        paper_count = len(papers)

        messages = [
            {
                "role": "system",
                "content": "You are an expert research synthesizer. Write a clear, structured research summary.",
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {query}\n\n"
                    f"Based on {paper_count} papers and the following key findings:\n{learning_text}\n\n"
                    "Write a comprehensive research summary (3-5 paragraphs) covering:\n"
                    "1. Main findings and consensus\n"
                    "2. Key methodologies used\n"
                    "3. Important gaps or contradictions\n"
                    "4. Practical implications"
                ),
            },
        ]

        return await _ai_chat(messages, task_type="deep_research", temperature=0.3)

    async def _identify_gaps(self, query: str, learnings: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """识别研究空白"""
        learning_text = "\n".join(f"- {l['insight']}" for l in learnings[:8])

        messages = [
            {
                "role": "system",
                "content": "You are an expert at identifying research gaps. Return valid JSON only.",
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {query}\n\nKnown findings:\n{learning_text}\n\n"
                    "Identify 3-5 significant research gaps or unanswered questions.\n\n"
                    'Return ONLY a JSON array: [{"area": "<gap area>", "description": "<description>", "potentialQuestions": ["<q1>", "<q2>"]}]'
                ),
            },
        ]

        response = await _ai_chat(messages, task_type="deep_research", temperature=0.4)

        try:
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
            text = json_match.group(1).strip() if json_match else response.strip()
            gaps = json.loads(text)
            if isinstance(gaps, list):
                return gaps[:5]
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback
        return [{"area": "General", "description": "Further research needed on the specific topic areas identified.", "potentialQuestions": [query]}]


# Singleton
deep_research_service = DeepResearchService()
