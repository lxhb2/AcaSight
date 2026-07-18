"""
翻译路由 — STranslate 风格内嵌引擎 v2.0

端点:
- GET  /translate/status       → 引擎状态
- POST /translate/text         → 翻译文本
- POST /translate/quick        → 快速翻译 (同 /text)
- POST /translate/long         → 长文本翻译
- POST /translate/batch        → 批量翻译
- POST /translate/stream       → 流式翻译 (SSE) [新增]
"""

import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from app.services.translation_service import translation_service
from app.services.translation_engine import ConcurrentTranslationService
from app.services.babeldoc_service import babeldoc_service

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "zh"


class BatchTranslateRequest(BaseModel):
    texts: List[str]
    source_lang: str = "auto"
    target_lang: str = "zh"


@router.get("/status")
async def get_status():
    return {"status": "ok", "data": translation_service.status}


@router.post("/text")
async def translate_text(req: TranslateRequest):
    try:
        result = translation_service.translate(req.text, req.source_lang, req.target_lang)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_translate(req: TranslateRequest):
    try:
        result = translation_service.translate(req.text, req.source_lang, req.target_lang)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/long")
async def translate_long(req: TranslateRequest):
    try:
        result = await translation_service.translate_async(req.text, req.source_lang, req.target_lang)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def translate_batch(req: BatchTranslateRequest):
    try:
        service = ConcurrentTranslationService()
        tasks = [
            service.translate(text, req.source_lang, req.target_lang)
            for text in req.texts
        ]
        results = await asyncio.gather(*tasks)
        return {
            "status": "ok",
            "data": [
                {
                    "translation": r.text,
                    "engine": r.engine,
                    "from_lang": r.from_lang,
                    "to_lang": r.to_lang,
                }
                for r in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def translate_stream(req: TranslateRequest):
    """流式翻译 — SSE 端点"""
    service = ConcurrentTranslationService()

    async def event_generator():
        try:
            async for event in service.translate_stream(
                req.text, req.source_lang, req.target_lang
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── BabelDOC PDF 翻译 ───────────────────────────────────────────────

class BabelDOCTranslateRequest(BaseModel):
    pdf_path: str
    lang_in: str = "en"
    lang_out: str = "zh"
    no_dual: bool = False
    no_mono: bool = True
    use_alternating_pages_dual: bool = False
    pages: Optional[str] = None
    openai_model: str = "gpt-4o-mini"


@router.get("/babeldoc/status")
async def babeldoc_status():
    return {"status": "ok", "data": babeldoc_service.status}


@router.post("/babeldoc/translate")
async def babeldoc_translate(req: BabelDOCTranslateRequest):
    if not babeldoc_service.available:
        raise HTTPException(status_code=400, detail="BabelDOC is not available")
    try:
        task_id = babeldoc_service.start_translation(
            pdf_path=req.pdf_path, lang_in=req.lang_in, lang_out=req.lang_out,
            no_dual=req.no_dual, no_mono=req.no_mono,
            use_alternating_pages_dual=req.use_alternating_pages_dual,
            pages=req.pages, openai_model=req.openai_model,
        )
        return {"status": "ok", "data": {"task_id": task_id}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/babeldoc/task/{task_id}")
async def babeldoc_task_status(task_id: str):
    task = babeldoc_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "data": task.to_dict()}


@router.get("/babeldoc/tasks")
async def babeldoc_list_tasks():
    return {"status": "ok", "data": babeldoc_service.list_tasks()}


@router.get("/babeldoc/result/{task_id}/{pdf_type}")
async def babeldoc_get_result(task_id: str, pdf_type: str):
    if pdf_type not in ("mono", "dual"):
        raise HTTPException(status_code=400, detail="pdf_type must be 'mono' or 'dual'")
    task = babeldoc_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    file_path = babeldoc_service.get_translated_pdf_path(task_id, pdf_type)
    if file_path is None:
        raise HTTPException(status_code=404, detail=f"{pdf_type} PDF not found")
    return FileResponse(path=file_path, media_type="application/pdf",
                        filename=f"{task_id}_{pdf_type}.pdf")


@router.delete("/babeldoc/task/{task_id}")
async def babeldoc_delete_task(task_id: str):
    try:
        babeldoc_service.cleanup_task(task_id)
        return {"status": "ok", "message": f"Task {task_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))