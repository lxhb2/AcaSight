"""
全类型数据统一存储服务

扩展 PDFStorageService，支持：
1. 用户上传素材（图片/数据/报告）分类归档
2. 绘图成品+原始数据+编辑参数管理
3. 临时缓存+定时清理
"""

import os
import hashlib
import shutil
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import structlog

logger = structlog.get_logger()


class UnifiedStorageService:
    """全类型数据统一存储管理器"""

    CATEGORIES = ["images", "data", "reports", "charts", "chart_products", "chart_raw", "templates", "other", "pdf", "image", "svg", "doc"]

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "unified_storage")
        self.base_dir = os.path.abspath(base_dir)
        for cat in self.CATEGORIES:
            os.makedirs(os.path.join(self.base_dir, cat), exist_ok=True)
        logger.info("UnifiedStorageService init", base_dir=self.base_dir)

    def save_material(
        self,
        file_data: bytes,
        filename: str,
        category: str = "other",
        paper_id: int = None,
        metadata: dict = None,
    ) -> dict:
        """
        保存素材文件到统一存储

        Args:
            file_data: 文件二进制数据
            filename: 原始文件名
            category: 分类 (images/data/reports/charts/chart_products/chart_raw/templates/other)
            paper_id: 关联论文ID（可选）
            metadata: 额外元数据（可选）

        Returns:
            dict: {material_id, path, hash, size, category, ...}
        """
        if category not in self.CATEGORIES:
            category = "other"

        file_hash = hashlib.sha256(file_data).hexdigest()

        existing = self._find_by_hash(file_hash, category)
        if existing:
            logger.info("Material already exists", hash=file_hash[:12], category=category)
            return existing

        material_id = str(uuid.uuid4())[:8]
        ext = os.path.splitext(filename)[1] or ".bin"
        stored_name = f"{material_id}_{file_hash[:8]}{ext}"

        if paper_id:
            dir_path = os.path.join(self.base_dir, category, str(paper_id))
        else:
            dir_path = os.path.join(self.base_dir, category)
        os.makedirs(dir_path, exist_ok=True)

        full_path = os.path.join(dir_path, stored_name)
        with open(full_path, "wb") as f:
            f.write(file_data)

        if metadata:
            meta_path = full_path + ".meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

        result = {
            "material_id": material_id,
            "filename": filename,
            "path": full_path,
            "rel_path": os.path.relpath(full_path, self.base_dir),
            "hash": file_hash,
            "size": len(file_data),
            "category": category,
            "paper_id": paper_id,
            "created_at": datetime.now().isoformat(),
        }
        logger.info("Material saved", material_id=material_id, category=category, size=len(file_data))
        return result

    def list_materials(
        self,
        category: str = None,
        paper_id: int = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """列出素材文件"""
        results = []
        search_dir = self.base_dir

        if category and category in self.CATEGORIES:
            if paper_id:
                search_dir = os.path.join(self.base_dir, category, str(paper_id))
            else:
                search_dir = os.path.join(self.base_dir, category)

        if not os.path.isdir(search_dir):
            return results

        for root, _, files in os.walk(search_dir):
            for fn in files:
                if fn.endswith(".meta.json"):
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, self.base_dir)
                parts = rel.replace("\\", "/").split("/")
                cat = parts[0] if len(parts) > 0 else "other"

                meta = self._load_meta(full)
                results.append({
                    "filename": fn,
                    "path": full,
                    "rel_path": rel,
                    "category": cat,
                    "size": os.path.getsize(full),
                    "mtime": os.path.getmtime(full),
                    "metadata": meta,
                })

        results.sort(key=lambda x: -x.get("mtime", 0))
        return results[offset:offset + limit]

    def get_material(self, path: str) -> Optional[bytes]:
        """读取素材文件内容"""
        if not path or not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def delete_material(self, path: str) -> bool:
        """删除素材文件及其元数据"""
        if not path or not os.path.isfile(path):
            return False
        try:
            os.remove(path)
            meta_path = path + ".meta.json"
            if os.path.isfile(meta_path):
                os.remove(meta_path)
            logger.info("Material deleted", path=path)
            return True
        except Exception as e:
            logger.error("Material delete failed", error=str(e))
            return False

    def save_chart_product(
        self,
        image_data: bytes,
        filename: str,
        raw_data: bytes = None,
        edit_params: dict = None,
        paper_id: int = None,
    ) -> dict:
        """
        保存绘图成品 + 原始数据 + 编辑参数（三类数据分离存储）

        Returns:
            dict: {product, raw, params} 各自的存储信息
        """
        product_info = self.save_material(
            image_data, filename, "chart_products", paper_id,
            metadata={"type": "chart_product", "filename": filename},
        )

        raw_info = None
        if raw_data:
            raw_filename = os.path.splitext(filename)[0] + "_raw" + os.path.splitext(filename)[1]
            raw_info = self.save_material(
                raw_data, raw_filename, "chart_raw", paper_id,
                metadata={"type": "chart_raw", "product_id": product_info["material_id"]},
            )

        params_info = None
        if edit_params:
            params_filename = os.path.splitext(filename)[0] + "_params.json"
            params_data = json.dumps(edit_params, ensure_ascii=False, indent=2).encode("utf-8")
            params_info = self.save_material(
                params_data, params_filename, "charts", paper_id,
                metadata={"type": "chart_params", "product_id": product_info["material_id"]},
            )

        return {
            "product": product_info,
            "raw": raw_info,
            "params": params_info,
        }

    def get_stats(self) -> dict:
        """获取统一存储统计"""
        stats = {}
        total_size = 0
        total_files = 0
        for cat in self.CATEGORIES:
            cat_dir = os.path.join(self.base_dir, cat)
            cat_size = 0
            cat_files = 0
            if os.path.isdir(cat_dir):
                for root, _, files in os.walk(cat_dir):
                    for fn in files:
                        if fn.endswith(".meta.json"):
                            continue
                        fp = os.path.join(root, fn)
                        try:
                            cat_size += os.path.getsize(fp)
                            cat_files += 1
                        except:
                            pass
            stats[cat] = {"files": cat_files, "size_bytes": cat_size}
            total_size += cat_size
            total_files += cat_files
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "by_category": stats,
        }

    def _find_by_hash(self, file_hash: str, category: str) -> Optional[dict]:
        cat_dir = os.path.join(self.base_dir, category)
        if not os.path.isdir(cat_dir):
            return None
        for root, _, files in os.walk(cat_dir):
            for fn in files:
                if file_hash[:8] in fn and not fn.endswith(".meta.json"):
                    full = os.path.join(root, fn)
                    return {
                        "material_id": fn.split("_")[0] if "_" in fn else "",
                        "filename": fn,
                        "path": full,
                        "hash": file_hash,
                        "size": os.path.getsize(full),
                        "category": category,
                    }
        return None

    def _load_meta(self, file_path: str) -> Optional[dict]:
        meta_path = file_path + ".meta.json"
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return None


_unified_storage: Optional[UnifiedStorageService] = None


def get_unified_storage() -> UnifiedStorageService:
    global _unified_storage
    if _unified_storage is None:
        _unified_storage = UnifiedStorageService()
    return _unified_storage
