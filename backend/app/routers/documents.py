"""
文档管理 API — Phase 2 OnlyOffice 集成

提供文档 CRUD、OnlyOffice 编辑器集成、版本管理、模板等端点。
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List
from typing import Literal
import structlog

from app.database import get_db
from app.models.document import Document, DocumentVersion
from app.services.document_service import get_document_service
from app.services.onlyoffice_service import get_onlyoffice_service, ONLYOFFICE_URL
from app.services.convert_service import get_convert_service

logger = structlog.get_logger()
router = APIRouter()


# ==================== Schemas ====================

class DocumentCreate(BaseModel):
    """创建文档请求"""
    title: str = Field(..., max_length=500, description="文档标题")
    file_type: str = Field(..., pattern=r"^(docx|xlsx|pptx)$", description="文件类型")
    template_id: Optional[str] = Field(None, description="模板 ID，用于从模板创建")


class DocumentUpdate(BaseModel):
    """更新文档请求"""
    title: Optional[str] = Field(None, max_length=500, description="新标题")


class DocumentFromTemplate(BaseModel):
    """从模板创建文档请求"""
    template_id: str = Field(..., description="模板 ID")
    title: str = Field(..., max_length=500, description="文档标题")


class MdToDocRequest(BaseModel):
    """Markdown 转 Office 文档请求"""
    markdown: str = Field(..., min_length=1, description="Markdown 内容")
    title: str = Field(..., max_length=500, description="文档标题")
    file_type: Literal["docx", "pptx"] = Field("docx", description="目标文件类型")
    template_id: Optional[str] = Field(None, description="模板 ID")
    reference_docx: Optional[str] = Field(None, description="参考 docx 样式文件路径")


class DocToMdRequest(BaseModel):
    """Office 文档转 Markdown 请求"""
    doc_id: str = Field(..., description="文档 ID")


class InsertSectionRequest(BaseModel):
    """插入文档段落请求"""
    doc_id: str = Field(..., description="文档 ID")
    content: str = Field(..., min_length=1, description="要插入的内容")
    position: Literal["end", "cursor"] = Field("end", description="插入位置")


# ==================== CRUD Endpoints ====================

@router.post("")
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新文档"""
    doc_service = get_document_service()
    try:
        document = await doc_service.create_document(
            title=body.title,
            file_type=body.file_type,
            db=db,
            template_id=body.template_id,
        )
        return document.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_documents(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量上限"),
    file_type: Optional[str] = Query(None, description="按文件类型筛选 (docx/xlsx/pptx)"),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表"""
    doc_service = get_document_service()
    documents, total = await doc_service.list_documents(
        db=db, skip=skip, limit=limit, file_type=file_type,
    )
    return {
        "items": [d.to_dict() for d in documents],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/templates")
async def list_templates():
    """列出可用的文档模板"""
    doc_service = get_document_service()
    templates = doc_service.list_templates()
    return {"templates": templates}


@router.post("/from-template")
async def create_from_template(
    body: DocumentFromTemplate,
    db: AsyncSession = Depends(get_db),
):
    """从模板创建文档"""
    doc_service = get_document_service()
    # 从模板 ID 推断文件类型
    templates = doc_service.list_templates()
    template = next((t for t in templates if t["id"] == body.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"模板不存在: {body.template_id}")

    try:
        document = await doc_service.create_document(
            title=body.title,
            file_type=template["file_type"],
            db=db,
            template_id=body.template_id,
        )
        return document.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Bridge 端点：Markdown ↔ Office 双向转换 ====================

@router.post("/bridge/md-to-doc")
async def bridge_md_to_doc(
    body: MdToDocRequest,
    db: AsyncSession = Depends(get_db),
):
    """Markdown 内容转换为 Office 文档（AI Writing → Office 桥接）

    将 Markdown 内容通过 pypandoc 转换为 docx/pptx，
    创建新的文档记录并保存文件，返回含 OnlyOffice 编辑器配置的文档信息。
    """
    convert_svc = get_convert_service()
    if not convert_svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    # 1. 转换 Markdown → docx 字节
    try:
        docx_bytes = await convert_svc.md_to_docx(
            md_content=body.markdown,
            reference_docx=body.reference_docx,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Markdown 转换失败: {str(e)}")

    # 2. 创建文档记录
    doc_service = get_document_service()
    try:
        document = await doc_service.create_document(
            title=body.title,
            file_type=body.file_type,
            db=db,
            template_id=body.template_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. 用转换后的内容覆盖空白文件
    try:
        with open(document.file_path, "wb") as f:
            f.write(docx_bytes)
        # 更新文件大小
        document.size_bytes = len(docx_bytes)
        await db.flush()
        await db.refresh(document)
    except Exception as e:
        logger.error("写入转换文件失败", doc_id=document.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")

    # 4. 生成 OnlyOffice 编辑器配置
    oo_service = get_onlyoffice_service()
    editor_config = oo_service.generate_editor_config_for_document(
        doc_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        title=document.title,
        mode="edit",
    )

    result = document.to_dict()
    result["editor_config"] = editor_config
    result["editor_url"] = f"{ONLYOFFICE_URL}/web-apps/apps/api/documents/editor.html"
    result["onlyoffice_available"] = oo_service.available

    logger.info("Bridge: Markdown → Office 完成", doc_id=document.id, title=body.title)
    return result


@router.post("/bridge/doc-to-md")
async def bridge_doc_to_md(
    body: DocToMdRequest,
    db: AsyncSession = Depends(get_db),
):
    """从 Office 文档提取 Markdown（Office → AI Writing 桥接）

    读取文档文件，通过 pypandoc 转换为 Markdown 文本返回。
    """
    convert_svc = get_convert_service()
    if not convert_svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    # 获取文档记录
    doc_service = get_document_service()
    document = await doc_service.get_document(body.doc_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 读取文件
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="文档文件不存在")

    try:
        with open(document.file_path, "rb") as f:
            docx_bytes = f.read()
    except Exception as e:
        logger.error("读取文档文件失败", doc_id=body.doc_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

    # 转换
    try:
        md_content = await convert_svc.docx_to_md(docx_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"文档转换 Markdown 失败: {str(e)}")

    logger.info("Bridge: Office → Markdown 完成", doc_id=body.doc_id)
    return {"markdown": md_content, "title": document.title}


@router.post("/bridge/insert-section")
async def bridge_insert_section(
    body: InsertSectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """向 OnlyOffice 文档插入段落（AI Writing → Office 桥接）

    当前实现：将内容追加到文档的 Markdown 源并重新转换为 docx。
    未来将对接 OnlyOffice 连接器实现精确插入。
    """
    convert_svc = get_convert_service()
    if not convert_svc.available:
        raise HTTPException(status_code=503, detail="pypandoc 未安装，格式转换不可用")

    # 获取文档记录
    doc_service = get_document_service()
    document = await doc_service.get_document(body.doc_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="文档文件不存在")

    # 1. 读取现有文档并转为 Markdown
    try:
        with open(document.file_path, "rb") as f:
            existing_bytes = f.read()
        existing_md = await convert_svc.docx_to_md(existing_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"文档转 Markdown 失败: {str(e)}")

    # 2. 追加新内容
    updated_md = existing_md.rstrip() + "\n\n" + body.content + "\n"

    # 3. 重新转换为 docx
    try:
        new_docx_bytes = await convert_svc.md_to_docx(md_content=updated_md)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Markdown 转换 docx 失败: {str(e)}")

    # 4. 写回文件
    try:
        with open(document.file_path, "wb") as f:
            f.write(new_docx_bytes)
        document.size_bytes = len(new_docx_bytes)
        await db.flush()
        await db.refresh(document)
    except Exception as e:
        logger.error("写入更新文件失败", doc_id=body.doc_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")

    # 5. 保存版本
    try:
        await doc_service.save_document_version(
            doc_id=body.doc_id,
            file_path=document.file_path,
            db=db,
            change_summary="通过 Bridge 插入段落",
        )
    except Exception as e:
        logger.warning("保存版本失败", doc_id=body.doc_id, error=str(e))

    # 6. 生成编辑器配置
    oo_service = get_onlyoffice_service()
    editor_config = oo_service.generate_editor_config_for_document(
        doc_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        title=document.title,
        mode="edit",
    )

    result = document.to_dict()
    result["editor_config"] = editor_config
    result["editor_url"] = f"{ONLYOFFICE_URL}/web-apps/apps/api/documents/editor.html"
    result["onlyoffice_available"] = oo_service.available

    logger.info("Bridge: 插入段落完成", doc_id=body.doc_id, position=body.position)
    return result


# ==================== 文档详情端点 ====================

@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情（含 OnlyOffice 编辑器配置）"""
    doc_service = get_document_service()
    document = await doc_service.get_document(doc_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 生成 OnlyOffice 编辑器配置
    oo_service = get_onlyoffice_service()
    editor_config = oo_service.generate_editor_config_for_document(
        doc_id=doc_id,
        filename=document.filename,
        file_type=document.file_type,
        title=document.title,
        mode="edit",
    )

    result = document.to_dict()
    result["editor_config"] = editor_config
    result["editor_url"] = f"{ONLYOFFICE_URL}/web-apps/apps/api/documents/editor.html"
    result["onlyoffice_available"] = oo_service.available

    return result


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """下载文档文件（供 OnlyOffice 服务器访问）"""
    doc_service = get_document_service()
    document = await doc_service.get_document(doc_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="文档文件不存在")

    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media_type = media_types.get(document.file_type, "application/octet-stream")

    return FileResponse(
        path=document.file_path,
        media_type=media_type,
        filename=document.filename,
    )


@router.put("/{doc_id}")
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文档元数据"""
    doc_service = get_document_service()
    document = await doc_service.update_document(
        doc_id=doc_id,
        db=db,
        title=body.title,
    )
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document.to_dict()


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除文档"""
    doc_service = get_document_service()
    deleted = await doc_service.delete_document(doc_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"detail": "已删除", "id": doc_id}


@router.post("/{doc_id}/callback")
async def onlyoffice_callback(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """OnlyOffice 保存回调端点

    OnlyOffice Document Server 在文档保存时回调此端点。
    回调数据包含 status 和下载 URL。
    """
    oo_service = get_onlyoffice_service()

    # 读取回调数据
    data = await request.json()
    logger.info("OnlyOffice 回调接收", doc_id=doc_id, status=data.get("status"))

    # JWT 验证（如果配置了）
    if oo_service.available:
        token_header = request.headers.get(ONLYOFFICE_JWT_HEADER.lower(), "")
        if token_header:
            token = token_header.replace("Bearer ", "") if token_header.startswith("Bearer ") else token_header
            try:
                oo_service.verify_callback_token(token)
            except ValueError as e:
                logger.error("OnlyOffice 回调 JWT 验证失败", error=str(e))
                raise HTTPException(status_code=401, detail="JWT 验证失败")

    result = await oo_service.handle_callback(data, db)
    return result


@router.get("/{doc_id}/versions")
async def get_document_versions(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文档版本历史"""
    doc_service = get_document_service()
    document = await doc_service.get_document(doc_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    versions = await doc_service.get_document_versions(doc_id, db)
    return {
        "document_id": doc_id,
        "versions": [v.to_dict() for v in versions],
        "total": len(versions),
    }
