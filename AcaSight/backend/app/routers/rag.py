from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.rag_service import get_rag_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str
    dataset_ids: list[str] | None = None
    chat_id: str | None = None


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
