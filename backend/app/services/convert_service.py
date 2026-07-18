"""
格式转换服务 — Phase 2

基于 pypandoc 提供 Markdown ↔ docx、Markdown → PDF 等格式转换功能。
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

PANDOC_AVAILABLE = False

try:
    import pypandoc
    PANDOC_AVAILABLE = True
    logger.info("pypandoc loaded successfully")
except ImportError:
    logger.warning("pypandoc not available, format conversion will be limited")

# Pandoc 模板目录
PANDOC_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "pandoc_templates"
)


class ConvertService:
    """格式转换服务"""

    def __init__(self):
        self.available = PANDOC_AVAILABLE
        os.makedirs(PANDOC_TEMPLATE_DIR, exist_ok=True)

    async def md_to_docx(
        self,
        md_content: str,
        template_path: Optional[str] = None,
        reference_docx: Optional[str] = None,
    ) -> bytes:
        """Markdown 转 docx

        Args:
            md_content: Markdown 内容
            template_path: Pandoc 模板路径（可选）
            reference_docx: 参考 docx 样式文件路径（可选）

        Returns:
            docx 文件字节数据
        """
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法转换为 DOCX")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")
            output_path = os.path.join(tmpdir, "output.docx")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            args = [
                input_path,
                "-o", output_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--to", "docx",
                "--standalone",
            ]

            if template_path and os.path.exists(template_path):
                args.extend(["--template", template_path])

            if reference_docx and os.path.exists(reference_docx):
                args.extend(["--reference-doc", reference_docx])

            try:
                pypandoc.run_pandoc(args)
                with open(output_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error("Markdown → DOCX 转换失败", error=str(e))
                raise RuntimeError(f"DOCX 转换失败: {str(e)}")

    async def docx_to_md(self, docx_bytes: bytes) -> str:
        """docx 转 Markdown

        Args:
            docx_bytes: docx 文件字节数据

        Returns:
            Markdown 文本
        """
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法从 DOCX 转换")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.docx")

            with open(input_path, "wb") as f:
                f.write(docx_bytes)

            args = [
                input_path,
                "--from", "docx",
                "--to", "markdown",
                "--wrap=none",
            ]

            try:
                output = pypandoc.run_pandoc(args, capture_output=True)
                return output.decode("utf-8") if isinstance(output, bytes) else str(output)
            except Exception as e:
                logger.error("DOCX → Markdown 转换失败", error=str(e))
                raise RuntimeError(f"Markdown 转换失败: {str(e)}")

    async def md_to_pdf(
        self,
        md_content: str,
        template_path: Optional[str] = None,
    ) -> bytes:
        """Markdown 转 PDF（使用 XeLaTeX 引擎，支持中文）

        Args:
            md_content: Markdown 内容
            template_path: Pandoc 模板路径（可选）

        Returns:
            PDF 文件字节数据
        """
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法转换为 PDF")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")
            output_path = os.path.join(tmpdir, "output.pdf")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            args = [
                input_path,
                "-o", output_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--pdf-engine=xelatex",
                "-V", "CJKmainfont=SimSun",
                "--standalone",
            ]

            if template_path and os.path.exists(template_path):
                args.extend(["--template", template_path])

            try:
                pypandoc.run_pandoc(args)
                with open(output_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error("Markdown → PDF 转换失败", error=str(e))
                raise RuntimeError(f"PDF 转换失败（可能缺少 XeLaTeX）: {str(e)}")

    def list_templates(self) -> list[dict]:
        """列出可用的 Pandoc 模板

        Returns:
            模板列表
        """
        templates = []
        if not os.path.exists(PANDOC_TEMPLATE_DIR):
            return templates

        for fname in sorted(os.listdir(PANDOC_TEMPLATE_DIR)):
            fpath = os.path.join(PANDOC_TEMPLATE_DIR, fname)
            if os.path.isfile(fpath):
                name, ext = os.path.splitext(fname)
                templates.append({
                    "id": name,
                    "filename": fname,
                    "extension": ext.lstrip("."),
                    "size_bytes": os.path.getsize(fpath),
                })
        return templates


# 全局单例
_convert_service: Optional[ConvertService] = None


def get_convert_service() -> ConvertService:
    """获取格式转换服务单例"""
    global _convert_service
    if _convert_service is None:
        _convert_service = ConvertService()
    return _convert_service
