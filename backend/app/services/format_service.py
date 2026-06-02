import logging
import tempfile
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PANDOC_AVAILABLE = False

try:
    import pypandoc
    PANDOC_AVAILABLE = True
    logger.info("pypandoc loaded successfully")
except ImportError:
    logger.warning("pypandoc not available, format export will be limited")


class FormatService:
    def __init__(self):
        self.available = PANDOC_AVAILABLE

    async def markdown_to_docx(
        self,
        markdown: str,
        title: str = "document",
        reference_docx: Optional[str] = None,
        bibliography: Optional[str] = None,
        csl_style: Optional[str] = None,
    ) -> bytes:
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法导出 DOCX")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")
            output_path = os.path.join(tmpdir, "output.docx")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            args = [
                input_path,
                "-o", output_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--to", "docx",
                "--standalone",
            ]

            if reference_docx and os.path.exists(reference_docx):
                args.extend(["--reference-doc", reference_docx])

            if bibliography and os.path.exists(bibliography):
                args.extend(["--bibliography", bibliography])

            if csl_style:
                csl_path = self._resolve_csl(csl_style)
                if csl_path:
                    args.extend(["--csl", csl_path])

            if bibliography or csl_style:
                args.append("--citeproc")

            try:
                pypandoc.run_pandoc(args)
                with open(output_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Pandoc DOCX conversion failed: {e}")
                raise RuntimeError(f"DOCX 导出失败: {str(e)}")

    async def markdown_to_latex(
        self,
        markdown: str,
        title: str = "document",
        bibliography: Optional[str] = None,
        csl_style: Optional[str] = None,
    ) -> str:
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法导出 LaTeX")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            args = [
                input_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--to", "latex",
                "--standalone",
            ]

            if bibliography and os.path.exists(bibliography):
                args.extend(["--bibliography", bibliography])

            if csl_style:
                csl_path = self._resolve_csl(csl_style)
                if csl_path:
                    args.extend(["--csl", csl_path])

            if bibliography or csl_style:
                args.append("--citeproc")

            try:
                output = pypandoc.run_pandoc(args, capture_output=True)
                return output.decode("utf-8") if isinstance(output, bytes) else str(output)
            except Exception as e:
                logger.error(f"Pandoc LaTeX conversion failed: {e}")
                raise RuntimeError(f"LaTeX 导出失败: {str(e)}")

    async def markdown_to_pdf(
        self,
        markdown: str,
        title: str = "document",
        bibliography: Optional[str] = None,
        csl_style: Optional[str] = None,
    ) -> bytes:
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法导出 PDF")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")
            output_path = os.path.join(tmpdir, "output.pdf")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            args = [
                input_path,
                "-o", output_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--pdf-engine=xelatex",
                "-V", "CJKmainfont=SimSun",
                "--standalone",
            ]

            if bibliography and os.path.exists(bibliography):
                args.extend(["--bibliography", bibliography])

            if csl_style:
                csl_path = self._resolve_csl(csl_style)
                if csl_path:
                    args.extend(["--csl", csl_path])

            if bibliography or csl_style:
                args.append("--citeproc")

            try:
                pypandoc.run_pandoc(args)
                with open(output_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Pandoc PDF conversion failed: {e}")
                raise RuntimeError(f"PDF 导出失败（可能缺少 XeLaTeX）: {str(e)}")

    async def markdown_to_html(
        self,
        markdown: str,
        title: str = "document",
        bibliography: Optional[str] = None,
        csl_style: Optional[str] = None,
    ) -> str:
        if not self.available:
            raise RuntimeError("pypandoc 未安装，无法导出 HTML")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.md")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            args = [
                input_path,
                "--from", "markdown+tex_math_dollars+raw_html",
                "--to", "html5",
                "--standalone",
                "--mathjax",
                "-V", f"title={title}",
            ]

            if bibliography and os.path.exists(bibliography):
                args.extend(["--bibliography", bibliography])

            if csl_style:
                csl_path = self._resolve_csl(csl_style)
                if csl_path:
                    args.extend(["--csl", csl_path])

            if bibliography or csl_style:
                args.append("--citeproc")

            try:
                output = pypandoc.run_pandoc(args, capture_output=True)
                return output.decode("utf-8") if isinstance(output, bytes) else str(output)
            except Exception as e:
                logger.error(f"Pandoc HTML conversion failed: {e}")
                raise RuntimeError(f"HTML 导出失败: {str(e)}")

    def generate_bib_from_papers(self, papers: list[dict]) -> str:
        """从论文数据生成 BibTeX 文件内容"""
        entries = []
        for i, p in enumerate(papers):
            entry_type = "article"
            title = p.get("title", f"Untitled_{i}")
            authors = p.get("authors", "Unknown")
            year = p.get("year", "")
            doi = p.get("doi", "")
            journal = p.get("journal", "")
            volume = p.get("volume", "")
            pages = p.get("pages", "")
            abstract = p.get("abstract", "")

            key = f"ref{i+1}"
            if doi:
                key = doi.replace("/", "_").replace(".", "_")[:30]
            elif authors and year:
                first_author = authors.split(",")[0].split(" and ")[0].strip().split()[-1]
                key = f"{first_author}{year}"

            lines = [f"@{entry_type}{{{key},"]
            lines.append(f"  title = {{{title}}},")
            lines.append(f"  author = {{{authors}}},")
            if year:
                lines.append(f"  year = {{{year}}},")
            if journal:
                lines.append(f"  journal = {{{journal}}},")
            if volume:
                lines.append(f"  volume = {{{volume}}},")
            if pages:
                lines.append(f"  pages = {{{pages}}},")
            if doi:
                lines.append(f"  doi = {{{doi}}},")
            lines.append("}")
            entries.append("\n".join(lines))

        return "\n\n".join(entries)

    def _resolve_csl(self, style_name: str) -> Optional[str]:
        csl_dir = Path(__file__).resolve().parent.parent / "csl_styles"
        csl_file = csl_dir / f"{style_name}.csl"
        if csl_file.exists():
            return str(csl_file)

        well_known = {
            "apa": "https://www.zotero.org/styles/apa",
            "ieee": "https://www.zotero.org/styles/ieee",
            "chicago": "https://www.zotero.org/styles/chicago-author-date",
            "mla": "https://www.zotero.org/styles/modern-language-association",
            "nature": "https://www.zotero.org/styles/nature",
            "science": "https://www.zotero.org/styles/science",
            "gb-t-7714-2015-numeric": "https://www.zotero.org/styles/gb-t-7714-2015-numeric",
            "gb-t-7714-2015-author-date": "https://www.zotero.org/styles/gb-t-7714-2015-author-date",
            "gb-t-7714-2005-numeric": "https://www.zotero.org/styles/gb-t-7714-2005-numeric",
            "chinese-gb7714-2015": "https://www.zotero.org/styles/china-national-standard-gb-t-7714-2015-numeric",
        }
        if style_name.lower() in well_known:
            return well_known[style_name.lower()]

        return None

    def list_csl_styles(self) -> list[dict]:
        return [
            {"id": "gb-t-7714-2015-numeric", "name": "GB/T 7714-2015 顺序编码制（中国国标）"},
            {"id": "gb-t-7714-2015-author-date", "name": "GB/T 7714-2015 著者-出版年制（中国国标）"},
            {"id": "chinese-gb7714-2015", "name": "GB/T 7714-2015 数字编码（中文标准）"},
            {"id": "apa", "name": "APA (American Psychological Association)"},
            {"id": "ieee", "name": "IEEE"},
            {"id": "chicago", "name": "Chicago Author-Date"},
            {"id": "mla", "name": "MLA (Modern Language Association)"},
            {"id": "nature", "name": "Nature"},
            {"id": "science", "name": "Science"},
        ]


_format_service: Optional[FormatService] = None


def get_format_service() -> FormatService:
    global _format_service
    if _format_service is None:
        _format_service = FormatService()
    return _format_service
