"""
知识模块Agent — 论文搜索、上传文档、RAG拆分、图谱关联、精准引用

复用现有 search_service + dimension_service + knowledge_graph + rag_service
"""

from app.agent.base_module import BaseModule, ModuleResult, ModuleStatus
from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()


class KnowledgeAgent(BaseModule):
    def __init__(self):
        super().__init__(name="knowledge", description="知识模块Agent: 搜索/上传/RAG拆分/图谱/引用")

    async def execute(self, task: str, context: dict = None) -> ModuleResult:
        self._status = ModuleStatus.RUNNING
        ctx = context or {}

        try:
            task_lower = task.lower()
            if "搜索" in task or "search" in task_lower:
                result = await self._handle_search(task, ctx)
            elif "拆分" in task or "dimension" in task_lower or "提取" in task:
                result = await self._handle_dimension(task, ctx)
            elif "引用" in task or "cite" in task_lower or "匹配" in task:
                result = await self._handle_citation(task, ctx)
            elif "图谱" in task or "graph" in task_lower:
                result = await self._handle_graph(task, ctx)
            elif "rag" in task_lower or "问答" in task or "检索" in task:
                result = await self._handle_rag_query(task, ctx)
            elif "摘要" in task or "summarize" in task_lower:
                result = await self._handle_summarize(task, ctx)
            else:
                result = await self._handle_general(task, ctx)

            self._status = ModuleStatus.COMPLETED
            self._last_result = result
            self._record_history(task, result)
            return result

        except Exception as e:
            self._status = ModuleStatus.FAILED
            result = ModuleResult(success=False, error=str(e))
            self._last_result = result
            self._record_history(task, result)
            logger.error("KnowledgeAgent failed", error=str(e))
            return result

    async def _handle_search(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.search_service import search_service
        query = ctx.get("query", task)
        sources = ctx.get("sources")
        limit = ctx.get("limit", 15)
        try:
            results = await search_service.search(query, max_results=limit, sources=sources)
            formatted = []
            raw_items = results if isinstance(results, list) else results.get("results", [])
            for item in raw_items[:limit]:
                formatted.append({
                    "title": item.get("title", ""),
                    "authors": item.get("authors", ""),
                    "year": item.get("year", ""),
                    "doi": item.get("doi", ""),
                    "abstract": (item.get("abstract") or "")[:300],
                    "source": item.get("source", ""),
                })
            return ModuleResult(success=True, data={"type": "search", "query": query, "results": formatted, "count": len(formatted)})
        except Exception as e:
            return ModuleResult(success=False, error=f"搜索失败: {e}")

    async def _handle_dimension(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.dimension_service import extract_dimensions
        paper_id = ctx.get("paper_id")
        full_text = ctx.get("full_text", "")
        if not paper_id or not full_text:
            return ModuleResult(success=False, error="需要 paper_id 和 full_text")
        try:
            dimensions = await extract_dimensions(paper_id, full_text)
            return ModuleResult(success=True, data={"type": "dimensions", "paper_id": paper_id, "dimensions": dimensions})
        except Exception as e:
            return ModuleResult(success=False, error=f"维度拆分失败: {e}")

    async def _handle_citation(self, task: str, ctx: dict) -> ModuleResult:
        chapter = ctx.get("chapter", "")
        dimension = ctx.get("dimension", "research_methods")
        paper_ids = ctx.get("paper_ids", [])
        if not chapter:
            return ModuleResult(success=False, error="需要 chapter 参数")

        from app.services.dimension_service import extract_dimensions
        from app.database import get_db
        from app.models.paper_dimensions import PaperDimensions
        from sqlalchemy import select

        related = []
        if paper_ids:
            try:
                async for db in get_db():
                    for pid in paper_ids[:10]:
                        result = await db.execute(
                            select(PaperDimensions).where(PaperDimensions.paper_id == pid)
                        )
                        dim = result.scalar_one_or_none()
                        if dim:
                            content = getattr(dim, dimension, None)
                            if content:
                                related.append({"paper_id": pid, "dimension": dimension, "content": content[:500]})
                    break
            except Exception:
                pass

        ref_text = ""
        if related:
            ref_text = "\n\n相关文献维度数据：\n" + "\n".join([
                f"- Paper {r['paper_id']} ({r['dimension']}): {r['content'][:200]}"
                for r in related[:5]
            ])

        messages = [
            {"role": "system", "content": "你是学术引用匹配专家。根据章节内容，推荐最相关的文献引用。"},
            {"role": "user", "content": f"章节内容：{chapter[:3000]}\n推荐维度：{dimension}{ref_text}\n请推荐相关文献引用。"},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "citation", "recommendation": response, "related_count": len(related)})

    async def _handle_graph(self, task: str, ctx: dict) -> ModuleResult:
        try:
            from app.routers.knowledge_graph import get_graph_data
            return ModuleResult(success=True, data={"type": "graph", "message": "图谱数据请通过 /api/knowledge/graph 端点获取"})
        except Exception:
            return ModuleResult(success=True, data={"type": "graph", "message": "图谱端点可用"})

    async def _handle_rag_query(self, task: str, ctx: dict) -> ModuleResult:
        query = ctx.get("query", task)
        try:
            from app.services.rag_service import rag_service
            result = await rag_service.query(query)
            return ModuleResult(success=True, data={"type": "rag", "answer": result})
        except Exception as e:
            messages = [
                {"role": "system", "content": "你是学术知识助手（RAG服务暂不可用，使用通用模式）。"},
                {"role": "user", "content": query},
            ]
            response = await ai_service.chat(messages)
            return ModuleResult(success=True, data={"type": "rag_fallback", "answer": response, "fallback": True})

    async def _handle_summarize(self, task: str, ctx: dict) -> ModuleResult:
        text = ctx.get("text", "")
        if not text:
            return ModuleResult(success=False, error="需要 text 参数")
        messages = [
            {"role": "system", "content": "你是学术论文摘要专家。请生成结构化摘要，包含：研究背景、目的、方法、结果、结论。"},
            {"role": "user", "content": f"请摘要以下内容：\n{text[:6000]}"},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "summary", "content": response})

    async def _handle_general(self, task: str, ctx: dict) -> ModuleResult:
        messages = [
            {"role": "system", "content": "你是学术知识管理助手，擅长文献检索、知识组织和引用分析。"},
            {"role": "user", "content": task},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "general", "response": response})
