"""
输出模块Agent — Markdown编辑、Word导出、格式转换、润色、BibTeX生成

复用现有 format_service + template_service
"""

from app.agent.base_module import BaseModule, ModuleResult, ModuleStatus
from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()


class OutputAgent(BaseModule):
    def __init__(self):
        super().__init__(name="output", description="输出模块Agent: MD编辑/Word导出/格式转换/润色/BibTeX")

    async def execute(self, task: str, context: dict = None) -> ModuleResult:
        self._status = ModuleStatus.RUNNING
        ctx = context or {}

        try:
            task_lower = task.lower()
            if "导出" in task or "export" in task_lower or "word" in task_lower:
                result = await self._handle_export(task, ctx)
            elif "格式" in task or "format" in task_lower:
                result = await self._handle_format(task, ctx)
            elif "润色" in task or "polish" in task_lower:
                result = await self._handle_polish(task, ctx)
            elif "bibtex" in task_lower or "bib" in task_lower:
                result = await self._handle_bibtex(task, ctx)
            elif "样式" in task or "style" in task_lower or "csl" in task_lower:
                result = await self._handle_styles(task, ctx)
            else:
                result = await self._handle_general(task, ctx)

            self._status = ModuleStatus.COMPLETED
            self._last_result = result
            self._record_history(task, result)
            return result

        except Exception as e:
            self._status = ModuleStatus.FAILED
            result = ModuleResult(success=False, error=str(e))
            self._last_result = result
            self._record_history(task, result)
            logger.error("OutputAgent failed", error=str(e))
            return result

    async def _handle_export(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.format_service import format_service
        fmt = ctx.get("format", "docx")
        markdown = ctx.get("markdown", "")
        title = ctx.get("title", "document")
        csl_style = ctx.get("csl_style")
        bibliography = ctx.get("bibliography")

        if not markdown:
            return ModuleResult(success=False, error="需要 markdown 内容")

        try:
            if fmt == "docx":
                output_path = await format_service.markdown_to_docx(
                    markdown=markdown, title=title,
                    csl_style=csl_style, bibliography=bibliography,
                )
                return ModuleResult(success=True, data={"type": "export", "format": "docx", "path": str(output_path)})
            elif fmt == "latex":
                output_path = await format_service.markdown_to_latex(
                    markdown=markdown, title=title,
                    csl_style=csl_style, bibliography=bibliography,
                )
                return ModuleResult(success=True, data={"type": "export", "format": "latex", "path": str(output_path)})
            elif fmt == "pdf":
                output_path = await format_service.markdown_to_pdf(
                    markdown=markdown, title=title,
                    csl_style=csl_style, bibliography=bibliography,
                )
                return ModuleResult(success=True, data={"type": "export", "format": "pdf", "path": str(output_path)})
            elif fmt == "html":
                html = format_service.markdown_to_html(markdown=markdown, title=title)
                return ModuleResult(success=True, data={"type": "export", "format": "html", "content": html})
            else:
                return ModuleResult(success=False, error=f"不支持的格式: {fmt}")
        except Exception as e:
            return ModuleResult(success=False, error=f"导出失败: {e}")

    async def _handle_format(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.format_service import format_service
        available = ["docx", "latex", "pdf", "html"] if format_service.available else []
        return ModuleResult(success=True, data={
            "type": "format_info",
            "available_formats": available,
            "pandoc_available": format_service.available,
        })

    async def _handle_polish(self, task: str, ctx: dict) -> ModuleResult:
        text = ctx.get("text", "")
        mode = ctx.get("mode", "polish")
        if not text:
            return ModuleResult(success=False, error="需要 text 参数")

        mode_prompts = {
            "polish": "请润色以下学术文本，保持原意，使语言更流畅、更学术化：",
            "academic": "请将以下文本改写为更正式、更学术的表达：",
            "shorten": "请精简以下文本，删除冗余，保留核心观点：",
            "expand": "请扩写以下文本，增加学术细节和论证：",
            "paraphrase": "请用不同表达方式改写以下文本，保持原意不变（用于降重）：",
        }
        prompt = mode_prompts.get(mode, mode_prompts["polish"])

        messages = [
            {"role": "system", "content": "你是学术文本润色专家，按Nature标准润色。"},
            {"role": "user", "content": f"{prompt}\n\n原文：\n{text}"},
        ]
        response = await ai_service.chat(messages, temperature=0.4)
        return ModuleResult(success=True, data={"type": "polish", "content": response, "mode": mode})

    async def _handle_bibtex(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.format_service import format_service
        papers = ctx.get("papers", [])
        if not papers:
            return ModuleResult(success=False, error="需要 papers 数据")

        try:
            bib_content = format_service.generate_bib_from_papers(papers)
            return ModuleResult(success=True, data={"type": "bibtex", "content": bib_content, "count": len(papers)})
        except Exception as e:
            return ModuleResult(success=False, error=f"BibTeX生成失败: {e}")

    async def _handle_styles(self, task: str, ctx: dict) -> ModuleResult:
        from app.services.format_service import format_service
        styles = format_service.list_csl_styles()
        return ModuleResult(success=True, data={"type": "styles", "styles": styles, "pandoc_available": format_service.available})

    async def _handle_general(self, task: str, ctx: dict) -> ModuleResult:
        messages = [
            {"role": "system", "content": "你是学术文档输出助手，擅长格式转换、引用规范和文档排版。"},
            {"role": "user", "content": task},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "general", "response": response})
