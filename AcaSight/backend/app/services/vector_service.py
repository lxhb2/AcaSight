"""
ChromaDB 向量存储服务 - Layer 0 RAG 前置任务
"""

import os
from typing import Optional, List, Dict, Any
import structlog

logger = structlog.get_logger()

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed - vector storage disabled")


class VectorService:
    """ChromaDB 向量存储 & 语义检索"""

    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")
        self.persist_dir = os.path.abspath(persist_dir)
        self._client = None
        self._collection = None
        self._embed_fn = None
        self.available = CHROMADB_AVAILABLE

    def _ensure_client(self):
        if not CHROMADB_AVAILABLE:
            return False
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                self._collection = self._client.get_or_create_collection(
                    name="papers",
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("ChromaDB initialized", path=self.persist_dir)
            except Exception as e:
                logger.error("ChromaDB init failed", error=str(e))
                self._client = None
                return False
        return True

    # --------------------------------------------------
    # 文档索引
    # --------------------------------------------------

    def index_paper(self, paper_id: int, text: str, metadata: Dict[str, Any] = None) -> bool:
        """索引单篇论文文本"""
        if not self._ensure_client():
            return False
        if not text or len(text.strip()) < 50:
            logger.warning("Text too short for indexing", paper_id=paper_id)
            return False

        # 分块：按段落切，每块最多 1000 字符
        chunks = self._chunk_text(text, max_chars=1000, overlap=200)

        try:
            ids = [f"p{paper_id}_c{i}" for i in range(len(chunks))]
            metadatas = [(metadata or {}) for _ in chunks]
            metadatas = [{**m, "paper_id": paper_id, "chunk_index": i}
                         for i, m in enumerate(metadatas)]

            self._collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
            )
            logger.info("Paper indexed", paper_id=paper_id, chunks=len(chunks))
            return True
        except Exception as e:
            logger.error("Index failed", paper_id=paper_id, error=str(e))
            return False

    def index_papers_batch(self, papers: List[Dict[str, Any]]) -> int:
        """批量索引论文 - paper = {id, text, metadata}"""
        if not self._ensure_client():
            return 0

        all_ids, all_docs, all_metas = [], [], []
        count = 0

        for paper in papers:
            pid = paper.get("id", 0)
            text = paper.get("text", "")
            meta = paper.get("metadata", {})
            if not text or len(text.strip()) < 50:
                continue
            chunks = self._chunk_text(text, max_chars=1000, overlap=200)
            for i, chunk in enumerate(chunks):
                all_ids.append(f"p{pid}_c{i}")
                all_docs.append(chunk)
                all_metas.append({**meta, "paper_id": pid, "chunk_index": i})
            count += 1

        if not all_ids:
            return 0

        try:
            self._collection.upsert(ids=all_ids, documents=all_docs, metadatas=all_metas)
            logger.info("Batch indexed", papers=count, chunks=len(all_ids))
            return count
        except Exception as e:
            logger.error("Batch index failed", error=str(e))
            return 0

    # --------------------------------------------------
    # 语义检索
    # --------------------------------------------------

    def search(self, query: str, top_k: int = 5,
               paper_ids: List[int] = None) -> List[Dict[str, Any]]:
        """语义检索"""
        if not self._ensure_client():
            return []

        try:
            where = None
            if paper_ids:
                where = {"paper_id": {"$in": paper_ids}}

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
            )

            hits = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    hits.append({
                        "id": doc_id,
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })
            return hits
        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            return []

    # --------------------------------------------------
    # 管理
    # --------------------------------------------------

    def delete_paper(self, paper_id: int) -> bool:
        """删除论文的所有向量"""
        if not self._ensure_client():
            return False
        try:
            results = self._collection.get(where={"paper_id": paper_id})
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
            logger.info("Paper vectors deleted", paper_id=paper_id)
            return True
        except Exception as e:
            logger.error("Delete vectors failed", paper_id=paper_id, error=str(e))
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计"""
        if not self._ensure_client():
            return {"available": False}
        try:
            count = self._collection.count()
            return {
                "available": True,
                "total_chunks": count,
                "collection_name": "papers",
                "persist_dir": self.persist_dir,
            }
        except:
            return {"available": True, "error": "stats failed"}

    # --------------------------------------------------
    # 内部
    # --------------------------------------------------

    def _chunk_text(self, text: str, max_chars: int = 1000, overlap: int = 200) -> List[str]:
        """语义分块"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) <= max_chars:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                    # 重叠：保留最后 overlap 字符
                    overlap_text = current[-overlap:] if len(current) > overlap else ""
                    current = overlap_text + "\n\n" + para
                else:
                    # 单段超过 max_chars，强行切
                    for i in range(0, len(para), max_chars - overlap):
                        chunks.append(para[i:i + max_chars])
                    current = ""
        if current:
            chunks.append(current)
        return chunks or [text]

    # --------------------------------------------------
    # 异步兼容接口（Agent 系统需要 await）
    # --------------------------------------------------

    async def asearch(
        self, query: str, top_k: int = 5,
        paper_ids: List[int] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """异步语义检索 — Agent 系统兼容接口
        
        支持两种过滤方式:
        - paper_ids: 按论文 ID 列表过滤
        - filter: 通用过滤条件 dict（兼容不同向量库）
        """
        import asyncio
        return await asyncio.to_thread(
            self._search_impl, query, top_k, paper_ids, filter
        )
    
    def _search_impl(
        self, query: str, top_k: int = 5,
        paper_ids: List[int] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """内部检索实现（同步，供 asearch 调用）"""
        if not self._ensure_client():
            return []
        
        # 从 filter 中提取 paper_id（兼容 Agent 传参风格）
        if filter and not paper_ids:
            pdf_id = filter.get("pdf_id") or filter.get("paper_id")
            if pdf_id:
                paper_ids = [int(pdf_id)] if isinstance(pdf_id, (int, str)) else pdf_id
        
        # 从 filter 中提取 source 过滤
        source = filter.get("source") if filter else None
        
        try:
            where = None
            if paper_ids:
                where = {"paper_id": {"$in": paper_ids}}
            
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
            )
            
            hits = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    score = float(results["distances"][0][i]) if results["distances"] else 0
                    
                    # source 过滤
                    if source and meta.get("source") != source:
                        continue
                    
                    hits.append({
                        "id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": meta,
                        "score": score,
                        "distance": score,
                    })
            return hits
        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            return []

    # --------------------------------------------------
    # Agent 记忆存储
    # --------------------------------------------------

    async def store_memory(
        self, text: str, metadata: Dict[str, Any] = None,
        collection: str = "agent_memory",
    ) -> bool:
        """存储 Agent 对话记忆"""
        if not self._ensure_client():
            return False
        
        try:
            from datetime import datetime
            mem_id = f"mem_{datetime.now().timestamp()}"
            
            # 使用独立 collection 存储 agent 记忆
            mem_collection = self._client.get_or_create_collection(
                name=collection,
                metadata={"hnsw:space": "cosine"},
            )
            
            mem_meta = dict(metadata or {})
            if "source" not in mem_meta:
                mem_meta["source"] = "agent_memory"
            
            mem_collection.add(
                ids=[mem_id],
                documents=[text],
                metadatas=[mem_meta],
            )
            return True
        except Exception as e:
            logger.error("Memory store failed", error=str(e))
            return False


# ==================== 全局实例 ====================

_vector_service: Optional[VectorService] = None


def get_vector_service() -> VectorService:
    """获取 VectorService 单例"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service


# 模块级实例 — 方便 from ... import vector_service
vector_service = get_vector_service()