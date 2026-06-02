"""
PDF 处理服务 - 融合 PaperPal + pdf-research-assistant
文本提取、合并/拆分、旋转、水印、图片提取、OCR、结构化解析
"""

import os
import io
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter


class PDFService:
    """PDF 综合处理服务"""

    # ==================== 文本提取 ====================

    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        """提取 PDF 全文文本"""
        doc = fitz.open(file_path)
        result = {
            "filename": os.path.basename(file_path),
            "pages": len(doc),
            "metadata": dict(doc.metadata),
            "text": "",
            "pages_text": [],
            "file_size": os.path.getsize(file_path),
        }
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            result["pages_text"].append({"page": page_num + 1, "text": text})
            result["text"] += f"\n--- 第 {page_num + 1} 页 ---\n{text}"
        doc.close()
        return result

    @staticmethod
    def extract_text_from_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
        """从字节数据提取文本"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        result = {
            "pages": len(doc),
            "metadata": dict(doc.metadata),
            "text": "",
            "pages_text": [],
        }
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            result["pages_text"].append({"page": page_num + 1, "text": text})
            result["text"] += f"\n--- 第 {page_num + 1} 页 ---\n{text}"
        doc.close()
        return result

    @staticmethod
    def extract_page(file_path: str, page_num: int) -> Dict[str, Any]:
        """提取单页内容和元数据"""
        doc = fitz.open(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            raise ValueError(f"页码 {page_num + 1} 超出范围 (1-{len(doc)})")
        page = doc[page_num]
        text = page.get_text()
        images = page.get_images()
        result = {
            "page": page_num + 1,
            "text": text,
            "width": page.rect.width,
            "height": page.rect.height,
            "image_count": len(images),
            "rotation": page.rotation,
        }
        doc.close()
        return result

    # ==================== PDF 操作 ====================

    @staticmethod
    def merge_pdfs(file_paths: List[str], output_path: str) -> str:
        """合并多个 PDF"""
        writer = PdfWriter()
        for fp in file_paths:
            reader = PdfReader(fp)
            for page in reader.pages:
                writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path

    @staticmethod
    def split_pdf(file_path: str, output_dir: str, pages_per_file: int = 1) -> List[str]:
        """拆分 PDF"""
        reader = PdfReader(file_path)
        total = len(reader.pages)
        outputs = []
        os.makedirs(output_dir, exist_ok=True)
        for start in range(0, total, pages_per_file):
            writer = PdfWriter()
            end = min(start + pages_per_file, total)
            for i in range(start, end):
                writer.add_page(reader.pages[i])
            path = os.path.join(output_dir, f"pages_{start + 1}-{end}.pdf")
            with open(path, "wb") as f:
                writer.write(f)
            outputs.append(path)
        return outputs

    @staticmethod
    def rotate_pages(file_path: str, output_path: str, rotation: int = 90) -> str:
        """旋转 PDF 页面"""
        reader = PdfReader(file_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(rotation)
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path

    @staticmethod
    def add_watermark(file_path: str, output_path: str, text: str, opacity: float = 0.3) -> str:
        """添加文字水印"""
        doc = fitz.open(file_path)
        for page in doc:
            center = fitz.Point(page.rect.width / 2, page.rect.height / 2)
            page.insert_text(center, text, fontsize=50, color=(0.5, 0.5, 0.5), opacity=opacity)
        doc.save(output_path)
        doc.close()
        return output_path

    @staticmethod
    def extract_images(file_path: str, output_dir: str) -> List[Dict]:
        """提取 PDF 内嵌图片"""
        doc = fitz.open(file_path)
        results = []
        os.makedirs(output_dir, exist_ok=True)
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_idx, img in enumerate(page.get_images(), 1):
                xref = img[0]
                base = doc.extract_image(xref)
                ext = base["ext"]
                name = f"page{page_num + 1}_img{img_idx}.{ext}"
                path = os.path.join(output_dir, name)
                with open(path, "wb") as f:
                    f.write(base["image"])
                results.append({
                    "page": page_num + 1,
                    "index": img_idx,
                    "format": ext,
                    "width": base["width"],
                    "height": base["height"],
                    "path": path,
                })
        doc.close()
        return results

    # ==================== 结构解析（目录、引用） ====================

    @staticmethod
    def get_toc(file_path: str) -> List[Dict]:
        """提取 PDF 目录（书签）"""
        doc = fitz.open(file_path)
        toc = doc.get_toc()
        doc.close()
        result = []
        for item in toc:
            level, title, page_num = item
            result.append({"level": level, "title": title, "page": page_num})
        return result

    @staticmethod
    def get_info(file_path: str) -> Dict[str, Any]:
        """获取 PDF 元信息"""
        doc = fitz.open(file_path)
        info = {
            "filename": os.path.basename(file_path),
            "pages": len(doc),
            "metadata": dict(doc.metadata),
            "file_size": os.path.getsize(file_path),
            "toc": doc.get_toc(),
            "is_encrypted": doc.is_encrypted,
            "needs_pass": doc.needs_pass if hasattr(doc, "needs_pass") else False,
        }
        doc.close()
        return info

    # ==================== 渲染预览 ====================

    @staticmethod
    def render_page_image(file_path: str, page_num: int, zoom: float = 1.5) -> bytes:
        """将指定页面渲染为 PNG 图片字节"""
        doc = fitz.open(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            raise ValueError(f"页码 {page_num + 1} 超出范围")
        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes

    @staticmethod
    def get_thumbnails(file_path: str, zoom: float = 0.3) -> List[bytes]:
        """获取所有页面的缩略图"""
        doc = fitz.open(file_path)
        thumbs = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            thumbs.append(pix.tobytes("png"))
        doc.close()
        return thumbs

    # ==================== 文本搜索与定位 ====================

    @staticmethod
    def search_text(file_path: str, query: str) -> List[Dict]:
        """在 PDF 中搜索文本并返回位置信息"""
        doc = fitz.open(file_path)
        results = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            areas = page.search_for(query)
            for area in areas:
                results.append({
                    "page": page_num + 1,
                    "x": area.x0,
                    "y": area.y0,
                    "width": area.width,
                    "height": area.height,
                })
        doc.close()
        return results

    # ==================== AI 精读 ====================

    @staticmethod
    def extract_for_reading(file_path: str, max_chars: int = 8000) -> Dict[str, Any]:
        """提取用于 AI 精读的内容（标题 + 摘要 + 正文前段）"""
        doc = fitz.open(file_path)
        title = doc.metadata.get("title", os.path.basename(file_path))

        # 收集前几页文本作为精读内容
        chunks = []
        total = 0
        for page in doc:
            text = page.get_text()
            if total + len(text) <= max_chars:
                chunks.append(text)
                total += len(text)
            else:
                remaining = max_chars - total
                if remaining > 0:
                    chunks.append(text[:remaining])
                break

        reading_text = "\n\n".join(chunks)
        page_count = len(doc)
        doc.close()

        return {
            "title": title,
            "page_count": page_count,
            "text": reading_text,
            "truncated": total > max_chars,
        }

    # ==================== 文件哈希 ====================

    @staticmethod
    def file_hash(file_path: str) -> str:
        """计算文件 MD5"""
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


# 全局实例
pdf_service = PDFService()