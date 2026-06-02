from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List

from app.services.data_preprocess_service import get_data_preprocess_service

router = APIRouter(tags=["data-preprocess"])


class ParseResponse(BaseModel):
    ok: bool
    instrument_type: str
    detected_type: str
    filename: str
    columns: List[dict]
    row_count: int
    data: List[dict] | str
    metadata: dict


class PreviewResponse(BaseModel):
    ok: bool
    instrument_type: str
    filename: str
    columns: List[dict]
    preview_rows: List[dict]
    metadata: dict


class InstrumentInfo(BaseModel):
    type: str
    name: str
    description: str
    extensions: List[str]


class InstrumentsResponse(BaseModel):
    instruments: List[InstrumentInfo]


class TextParseRequest(BaseModel):
    content: str
    filename: str
    instrument_type: str = "auto"
    export_format: str = "chart_data"


@router.post("/parse", response_model=ParseResponse)
async def parse_file(
    file: UploadFile = File(...),
    instrument_type: str = Form("auto"),
    export_format: str = Form("chart_data"),
):
    service = get_data_preprocess_service()
    try:
        raw_bytes = await file.read()
        result = service.parse(
            data=raw_bytes,
            filename=file.filename or "unknown",
            instrument_type=instrument_type,
            export_format=export_format,
        )
        return ParseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/preview", response_model=PreviewResponse)
async def preview_file(
    file: UploadFile = File(...),
    instrument_type: str = Form("auto"),
):
    service = get_data_preprocess_service()
    try:
        raw_bytes = await file.read()
        result = service.preview_bytes(
            data=raw_bytes,
            filename=file.filename or "unknown",
            instrument_type=instrument_type,
        )
        return PreviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/export")
async def export_file(
    file: UploadFile = File(...),
    instrument_type: str = Form("auto"),
    export_format: str = Form("csv"),
):
    service = get_data_preprocess_service()
    try:
        raw_bytes = await file.read()
        result = service.export(
            data=raw_bytes,
            filename=file.filename or "unknown",
            instrument_type=instrument_type,
            export_format=export_format,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    if export_format == "csv":
        content = result["content"]
        filename = result.get("filename", "export.csv")
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    if export_format == "json":
        import json as json_mod
        content = result["content"]
        if isinstance(content, str):
            content = content.encode("utf-8")
        elif not isinstance(content, bytes):
            content = json_mod.dumps(content).encode("utf-8")
        filename = result.get("filename", "export.json")
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    if export_format == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError:
            raise HTTPException(
                status_code=400,
                detail="XLSX export requires openpyxl to be installed",
            )
        wb = Workbook()
        ws = wb.active
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        if columns:
            ws.append([col.get("name", "") for col in columns])
        for row in rows:
            ws.append([row.get(col.get("name", ""), "") for col in columns])
        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        filename = result.get("filename", "export.xlsx")
        return Response(
            content=buffer.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {export_format}")


@router.get("/instruments", response_model=InstrumentsResponse)
async def list_instruments():
    service = get_data_preprocess_service()
    try:
        result = service.list_instruments()
        return InstrumentsResponse(instruments=[InstrumentInfo(**item) for item in result])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-parse", response_model=ParseResponse)
async def text_parse(request: TextParseRequest):
    service = get_data_preprocess_service()
    try:
        result = service.parse(
            data=request.content.encode("utf-8"),
            filename=request.filename,
            instrument_type=request.instrument_type,
            export_format=request.export_format,
        )
        return ParseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
