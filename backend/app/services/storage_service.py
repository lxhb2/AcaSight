"""
PDF 存储服务 - Layer 0 核心
管理本地 PDF 仓库、文件去重、路径组织
"""

import os
import hashlib
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import structlog

logger = structlog.get_logger()


class PDFStorageService:
    """本地 PDF 仓库管理器"""

    def __init__(self, base_dir: str = None):
        # 默认存储目录: backend/data/pdfs/
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pdfs")
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info("PDFStorageService init", base_dir=self.base_dir)

    # --------------------------------------------------
    # 文件存储
    # --------------------------------------------------

    def save_pdf(self, source_path: str, paper_id: int = None,
                overwrite: bool = False) -> Tuple[bool, str, str]:
        """
        保存 PDF 到本地仓库
        返回: (成功?, 仓库路径, 文件哈希)
        """
        if not os.path.isfile(source_path):
            return False, "", ""

        # 计算文件哈希（用于去重）
        file_hash = self._calc_hash(source_path)
        if not file_hash:
            return False, "", ""

        # 去重检查
        existing = self._find_by_hash(file_hash)
        if existing and not overwrite:
            logger.info("PDF already exists (by hash)", hash=file_hash[:12])
            return True, existing, file_hash

        # 组织路径: data/pdfs/ab/cd/abcdef...pdf
        rel_path = self._hash_to_path(file_hash)
        full_path = os.path.join(self.base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 复制文件
        try:
            shutil.copy2(source_path, full_path)
            logger.info("PDF saved", src=source_path, dst=rel_path, hash=file_hash[:12])
            return True, full_path, file_hash
        except Exception as e:
            logger.error("PDF save failed", error=str(e))
            return False, "", file_hash

    def save_pdf_bytes(self, data: bytes, filename: str, paper_id: int = None) -> Tuple[bool, str, str]:
        """从字节流保存 PDF（用于上传场景）"""
        import tempfile
        tmp_path = os.path.join(self.base_dir, "..", "_tmp", filename)
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(data)
        ok, path, h = self.save_pdf(tmp_path, paper_id)
        try:
            os.remove(tmp_path)
        except:
            pass
        return ok, path, h

    def delete_pdf(self, file_path: str) -> bool:
        """删除 PDF 文件（仅删除仓库中的文件）"""
        if not file_path or not os.path.isfile(file_path):
            return False
        try:
            os.remove(file_path)
            logger.info("PDF deleted", path=file_path)
            return True
        except Exception as e:
            logger.error("PDF delete failed", error=str(e))
            return False

    def get_pdf(self, file_path: str) -> Optional[bytes]:
        """读取 PDF 文件内容"""
        if not file_path or not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error("PDF read failed", error=str(e))
            return None

    def list_pdfs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出仓库中的 PDF 文件"""
        results = []
        for root, _, files in os.walk(self.base_dir):
            for fn in files:
                if not fn.lower().endswith(".pdf"):
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, self.base_dir)
                results.append({
                    "path": full,
                    "rel_path": rel,
                    "size": os.path.getsize(full),
                    "mtime": os.path.getmtime(full),
                })
        return results[offset:offset + limit]

    def get_stats(self) -> Dict:
        """获取仓库统计信息"""
        total = 0
        total_size = 0
        for root, _, files in os.walk(self.base_dir):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    total += 1
                    try:
                        total_size += os.path.getsize(os.path.join(root, fn))
                    except:
                        pass
        return {
            "total_pdfs": total,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "base_dir": self.base_dir,
        }

    # --------------------------------------------------
    # 内部方法
    # --------------------------------------------------

    def _calc_hash(self, file_path: str, algo: str = "sha256") -> str:
        """计算文件哈希"""
        try:
            h = hashlib.new(algo)
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            logger.error("Hash calc failed", path=file_path, error=str(e))
            return ""

    def _hash_to_path(self, file_hash: str) -> str:
        """将哈希值转换为分层路径: ab/cd/abcdef...pdf"""
        prefix = os.path.join(file_hash[0:2], file_hash[2:4])
        filename = file_hash + ".pdf"
        return os.path.join(prefix, filename)

    def _find_by_hash(self, file_hash: str) -> Optional[str]:
        """根据哈希查找已有文件"""
        target = self._hash_to_path(file_hash)
        full = os.path.join(self.base_dir, target)
        return full if os.path.isfile(full) else None


# 全局实例
_storage_service: Optional[PDFStorageService] = None


def get_storage_service() -> PDFStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = PDFStorageService()
    return _storage_service
