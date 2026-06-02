from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.rag_service import get_rag_service
from app.services.vector_service import get_vector_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str
    dataset_ids: list[str] | None = None
    chat_id: str | None = None


class CleanupRequest(BaseModel):
    max_age_days: int = 90


class OrphanCleanupRequest(BaseModel):
    valid_paper_ids: list[int] = []


@router.get("/status")
async def rag_status():
    svc = get_rag_service()
    available = await svc.check_available()
    datasets = []
    if available:
        datasets = await svc.list_datasets()
    return {"available": available, "datasets": datasets}


@router.post("/query")
async def rag_query(req: RAGQueryRequest):
    svc = get_rag_service()
    result = await svc.query(
        question=req.question,
        dataset_ids=req.dataset_ids,
        chat_id=req.chat_id,
    )
    return result


@router.get("/vector-stats")
async def vector_stats():
    vs = get_vector_service()
    return vs.get_stats()


@router.post("/vector-cleanup-orphans")
async def vector_cleanup_orphans(req: OrphanCleanupRequest):
    vs = get_vector_service()
    return vs.cleanup_orphans(req.valid_paper_ids)


@router.post("/vector-cleanup-expired")
async def vector_cleanup_expired(req: CleanupRequest):
    vs = get_vector_service()
    return vs.cleanup_expired(req.max_age_days)


@router.delete("/vector-paper/{paper_id}")
async def vector_delete_paper(paper_id: int):
    vs = get_vector_service()
    ok = vs.delete_paper(paper_id)
    return {"ok": ok, "paper_id": paper_id}


@router.post("/vector-reset")
async def vector_reset():
    vs = get_vector_service()
    ok = vs.reset_all()
    return {"ok": ok}
