"""
OnlyOffice 集成服务 — Phase 2

提供 OnlyOffice 编辑器配置生成、JWT 签名、回调处理等功能。
当 OnlyOffice 不可用时，优雅降级返回错误信息。
"""

import os
import json
import time
import uuid
from typing import Optional
from urllib.parse import urljoin

import structlog

logger = structlog.get_logger()

# 环境变量配置
ONLYOFFICE_URL = os.environ.get("ONLYOFFICE_URL", "http://localhost:8080")
ONLYOFFICE_JWT_SECRET = os.environ.get("ONLYOFFICE_JWT_SECRET", "")
ONLYOFFICE_JWT_HEADER = os.environ.get("ONLYOFFICE_JWT_HEADER", "Authorization")
# 回调基础 URL（后端自身的外部可达地址）
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")

# 文件类型到 OnlyOffice 文档类型的映射
FILE_TYPE_MAP = {
    "docx": "word",
    "xlsx": "cell",
    "pptx": "slide",
}

# OnlyOffice 回调状态码
CALLBACK_STATUS_SAVE = 2
CALLBACK_STATUS_FORCE_SAVE = 6


class OnlyOfficeService:
    """OnlyOffice 集成服务"""

    @property
    def available(self) -> bool:
        """检查 OnlyOffice 是否可用（JWT 密钥已配置）"""
        return bool(ONLYOFFICE_JWT_SECRET)

    def generate_editor_config(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        mode: str = "edit",
    ) -> dict:
        """生成 OnlyOffice 编辑器配置

        Args:
            doc_id: 文档 ID
            user_id: 用户 ID（可选）
            mode: 编辑模式 (edit/view)

        Returns:
            OnlyOffice 编辑器配置字典，包含 JWT token
        """
        # 获取文档信息
        from app.services.document_service import get_document_service
        doc_service = get_document_service()

        # 需要从数据库获取文档信息，这里先构建基础配置
        # 实际文档信息在路由层获取后传入
        document_key = f"{doc_id}_{int(time.time())}"

        config = {
            "document": {
                "fileType": "docx",  # 默认，路由层会覆盖
                "key": document_key,
                "title": "document.docx",
                "url": self.build_download_url(doc_id),
            },
            "documentType": "word",
            "editorConfig": {
                "mode": mode,
                "callbackUrl": self.build_callback_url(doc_id),
                "lang": "zh-CN",
                "customization": {
                    "autosave": True,
                    "forcesave": True,
                    "chat": False,
                    "compactHeader": True,
                    "compactToolbar": True,
                    "toolbarNoTabs": False,
                },
            },
        }

        if user_id:
            config["editorConfig"]["user"] = {
                "id": user_id,
                "name": f"User {user_id}",
            }

        # JWT 签名
        if ONLYOFFICE_JWT_SECRET:
            token = self._sign_token(config)
            config["token"] = token

        return config

    def generate_editor_config_for_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        title: str,
        user_id: Optional[str] = None,
        mode: str = "edit",
    ) -> dict:
        """根据完整文档信息生成 OnlyOffice 编辑器配置

        Args:
            doc_id: 文档 ID
            filename: 文件名
            file_type: 文件类型 (docx/xlsx/pptx)
            title: 文档标题
            user_id: 用户 ID
            mode: 编辑模式

        Returns:
            OnlyOffice 编辑器配置字典
        """
        document_key = f"{doc_id}_{int(time.time())}"
        document_type = FILE_TYPE_MAP.get(file_type, "word")

        config = {
            "document": {
                "fileType": file_type,
                "key": document_key,
                "title": filename,
                "url": self.build_download_url(doc_id),
            },
            "documentType": document_type,
            "editorConfig": {
                "mode": mode,
                "callbackUrl": self.build_callback_url(doc_id),
                "lang": "zh-CN",
                "customization": {
                    "autosave": True,
                    "forcesave": True,
                    "chat": False,
                    "compactHeader": True,
                    "compactToolbar": True,
                    "toolbarNoTabs": False,
                },
            },
        }

        if user_id:
            config["editorConfig"]["user"] = {
                "id": str(user_id),
                "name": f"User {user_id}",
            }

        # JWT 签名
        if ONLYOFFICE_JWT_SECRET:
            token = self._sign_token(config)
            config["token"] = token

        return config

    def verify_callback_token(self, token: str) -> dict:
        """验证 OnlyOffice 回调 JWT token

        Args:
            token: JWT token 字符串

        Returns:
            解码后的 payload 字典

        Raises:
            ValueError: token 无效或验证失败
        """
        if not ONLYOFFICE_JWT_SECRET:
            # 未配置 JWT 密钥时，跳过验证
            logger.warning("OnlyOffice JWT 密钥未配置，跳过回调验证")
            return {}

        try:
            from jose import jwt
            payload = jwt.decode(
                token,
                ONLYOFFICE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except Exception as e:
            logger.error("OnlyOffice 回调 JWT 验证失败", error=str(e))
            raise ValueError(f"JWT 验证失败: {str(e)}")

    async def handle_callback(self, data: dict, db) -> dict:
        """处理 OnlyOffice 保存/状态回调

        OnlyOffice 回调数据格式:
        - status 0: 无错误
        - status 1: 正在编辑
        - status 2: 文档已保存（需要下载）
        - status 3: 保存错误
        - status 4: 文档关闭，无修改
        - status 6: 正在编辑但强制保存

        Args:
            data: OnlyOffice 回调数据
            db: 数据库会话

        Returns:
            处理结果字典
        """
        status = data.get("status")
        doc_key = data.get("key", "")

        # 从 key 中提取 doc_id（格式: {doc_id}_{timestamp}）
        doc_id = doc_key.rsplit("_", 1)[0] if "_" in doc_key else doc_key

        logger.info("OnlyOffice 回调", status=status, doc_id=doc_id, key=doc_key)

        if status in (CALLBACK_STATUS_SAVE, CALLBACK_STATUS_FORCE_SAVE):
            # 文档已保存，需要下载新版本
            download_url = data.get("url")
            if not download_url:
                logger.error("OnlyOffice 回调缺少下载 URL", doc_id=doc_id)
                return {"error": 0}

            try:
                file_path = await self._download_document(doc_id, download_url)
                # 保存新版本
                from app.services.document_service import get_document_service
                doc_service = get_document_service()
                change_summary = "OnlyOffice 自动保存" if status == CALLBACK_STATUS_FORCE_SAVE else "OnlyOffice 保存"
                await doc_service.save_document_version(doc_id, file_path, db, change_summary=change_summary)
                logger.info("OnlyOffice 文档版本已保存", doc_id=doc_id, status=status)
            except Exception as e:
                logger.error("OnlyOffice 回调处理失败", doc_id=doc_id, error=str(e))

        # OnlyOffice 要求回调返回 {"error": 0} 表示成功
        return {"error": 0}

    def build_download_url(self, doc_id: str) -> str:
        """构建文档下载 URL（供 OnlyOffice 服务器访问）

        Args:
            doc_id: 文档 ID

        Returns:
            下载 URL
        """
        return f"{SERVER_BASE_URL}/api/documents/{doc_id}/download"

    def build_callback_url(self, doc_id: str) -> str:
        """构建回调 URL（供 OnlyOffice 服务器回调）

        Args:
            doc_id: 文档 ID

        Returns:
            回调 URL
        """
        return f"{SERVER_BASE_URL}/api/documents/{doc_id}/callback"

    def _sign_token(self, payload: dict) -> str:
        """对配置进行 JWT 签名

        Args:
            payload: 要签名的数据

        Returns:
            JWT token 字符串
        """
        try:
            from jose import jwt
            return jwt.encode(payload, ONLYOFFICE_JWT_SECRET, algorithm="HS256")
        except Exception as e:
            logger.error("JWT 签名失败", error=str(e))
            raise RuntimeError(f"JWT 签名失败: {str(e)}")

    async def _download_document(self, doc_id: str, download_url: str) -> str:
        """从 OnlyOffice 服务器下载文档

        Args:
            doc_id: 文档 ID
            download_url: OnlyOffice 提供的下载 URL

        Returns:
            下载后的本地文件路径
        """
        import aiohttp
        from app.services.document_service import DOCUMENT_STORAGE_ROOT

        doc_dir = os.path.join(DOCUMENT_STORAGE_ROOT, doc_id)
        os.makedirs(doc_dir, exist_ok=True)

        # 临时文件名
        temp_filename = f"onlyoffice_save_{int(time.time())}.tmp"
        temp_path = os.path.join(doc_dir, temp_filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"下载文档失败: HTTP {response.status}")
                with open(temp_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        return temp_path


# 全局单例
_onlyoffice_service: Optional[OnlyOfficeService] = None


def get_onlyoffice_service() -> OnlyOfficeService:
    """获取 OnlyOffice 服务单例"""
    global _onlyoffice_service
    if _onlyoffice_service is None:
        _onlyoffice_service = OnlyOfficeService()
    return _onlyoffice_service
