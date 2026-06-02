"""
Nature Paper2PPT Plugin
Nature论文转PPT插件 — 将Nature论文转换为学术报告PPT，保留关键图表和数据
"""

from typing import Any

from app.services.plugin_system import AcaSightPlugin


class NaturePaper2PPTPlugin(AcaSightPlugin):
    """Nature论文转PPT插件"""

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_write", self._on_post_write)
        self._default_slide_count = config.get("default_slide_count", 15)
        self._include_notes = config.get("include_notes", True)

    async def on_enable(self) -> None:
        """启用"""
        pass

    async def on_disable(self) -> None:
        """禁用"""
        pass

    async def on_unload(self) -> None:
        """卸载"""
        pass

    async def _on_post_write(self, content: str, **kwargs) -> dict:
        """post_write 钩子: 论文完成后提供PPT转换建议"""
        doc_type = kwargs.get("doc_type", "")
        if doc_type != "paper":
            return {"applied": False, "reason": "not_paper_document"}

        paper_data = kwargs.get("paper_data")
        if not paper_data:
            return {"applied": False, "reason": "no_paper_data"}

        key_slides = self.extract_key_slides(paper_data)
        return {
            "applied": True,
            "suggestion": "paper_to_ppt_available",
            "key_slides_count": len(key_slides.get("slides", [])),
            "default_slide_count": self._default_slide_count,
        }

    def convert_paper_to_ppt(self, paper_data: dict, slide_count: int = 15) -> dict:
        """
        将论文转换为PPT结构

        根据论文内容生成幻灯片序列，包含标题、要点、图表引用
        """
        if slide_count <= 0:
            slide_count = self._default_slide_count

        key_slides = self.extract_key_slides(paper_data)
        slides = key_slides.get("slides", [])

        allocated = self._allocate_slides(slide_count, len(slides))

        final_slides = []
        for i, slide in enumerate(slides):
            budget = allocated.get(slide.get("section", ""), 1)

            main_slide = {
                "slide_number": len(final_slides) + 1,
                "section": slide.get("section", ""),
                "title": slide.get("title", ""),
                "bullet_points": slide.get("key_points", [])[:6],
                "figures": slide.get("figures", []),
                "tables": slide.get("tables", []),
                "layout": self._suggest_layout(slide),
            }

            if self._include_notes:
                main_slide["notes"] = self.generate_slide_notes(main_slide)

            final_slides.append(main_slide)

            if budget > 1 and len(slide.get("key_points", [])) > 6:
                extra_points = slide["key_points"][6:]
                extra_slide = {
                    "slide_number": len(final_slides) + 1,
                    "section": slide.get("section", "") + " (cont.)",
                    "title": slide.get("title", "") + " (continued)",
                    "bullet_points": extra_points[:6],
                    "figures": [],
                    "tables": [],
                    "layout": "content",
                }
                if self._include_notes:
                    extra_slide["notes"] = self.generate_slide_notes(extra_slide)
                final_slides.append(extra_slide)

        return {
            "total_slides": len(final_slides),
            "slides": final_slides,
            "paper_title": paper_data.get("title", ""),
            "authors": paper_data.get("authors", ""),
        }

    def extract_key_slides(self, paper_data: dict) -> dict:
        """
        提取关键幻灯片: 标题/引言/方法/结果/结论

        从论文数据中提取各部分的核心内容
        """
        slides = []

        title_slide = {
            "section": "title",
            "title": paper_data.get("title", "Untitled"),
            "key_points": [
                f"Authors: {paper_data.get('authors', 'N/A')}",
                f"Affiliation: {paper_data.get('affiliation', 'N/A')}",
            ],
            "figures": [],
            "tables": [],
        }
        slides.append(title_slide)

        intro = paper_data.get("introduction", {})
        if isinstance(intro, dict) and intro:
            intro_slide = {
                "section": "introduction",
                "title": intro.get("heading", "Introduction"),
                "key_points": intro.get("key_points", [])[:6],
                "figures": intro.get("figures", []),
                "tables": [],
            }
            slides.append(intro_slide)

        methods = paper_data.get("methods", {})
        if isinstance(methods, dict) and methods:
            methods_slide = {
                "section": "methods",
                "title": methods.get("heading", "Methods"),
                "key_points": methods.get("key_points", [])[:6],
                "figures": methods.get("figures", []),
                "tables": methods.get("tables", []),
            }
            slides.append(methods_slide)

        results = paper_data.get("results", {})
        if isinstance(results, dict) and results:
            results_slide = {
                "section": "results",
                "title": results.get("heading", "Results"),
                "key_points": results.get("key_points", [])[:6],
                "figures": results.get("figures", []),
                "tables": results.get("tables", []),
            }
            slides.append(results_slide)

        discussion = paper_data.get("discussion", {})
        if isinstance(discussion, dict) and discussion:
            discussion_slide = {
                "section": "discussion",
                "title": discussion.get("heading", "Discussion"),
                "key_points": discussion.get("key_points", [])[:6],
                "figures": discussion.get("figures", []),
                "tables": [],
            }
            slides.append(discussion_slide)

        conclusion = paper_data.get("conclusion", {})
        if isinstance(conclusion, dict) and conclusion:
            conclusion_slide = {
                "section": "conclusion",
                "title": conclusion.get("heading", "Conclusion"),
                "key_points": conclusion.get("key_points", [])[:6],
                "figures": [],
                "tables": [],
            }
            slides.append(conclusion_slide)

        return {"slides": slides, "total_sections": len(slides)}

    def generate_slide_notes(self, slide_data: dict) -> str:
        """
        为每张幻灯片生成演讲者备注

        根据幻灯片内容生成辅助讲解的文字
        """
        section = slide_data.get("section", "")
        title = slide_data.get("title", "")
        bullets = slide_data.get("bullet_points", [])
        figures = slide_data.get("figures", [])

        notes_parts = []

        if section == "title":
            notes_parts.append("Introduce yourself and co-authors.")
            notes_parts.append("Briefly state the main contribution of this work.")
        elif section == "introduction":
            notes_parts.append("Provide background context for the research question.")
            notes_parts.append("Highlight the gap in current knowledge this paper addresses.")
            if bullets:
                notes_parts.append(f"Key motivation: {bullets[0] if bullets else ''}")
        elif section == "methods":
            notes_parts.append("Walk through the experimental design step by step.")
            notes_parts.append("Emphasize novel techniques or modifications.")
        elif section == "results":
            notes_parts.append("Present findings in logical order.")
            if figures:
                notes_parts.append(f"Refer to {', '.join(figures)} when discussing visual data.")
            notes_parts.append("Highlight statistical significance where applicable.")
        elif section == "discussion":
            notes_parts.append("Interpret results in context of existing literature.")
            notes_parts.append("Address limitations and alternative explanations.")
        elif section == "conclusion":
            notes_parts.append("Summarize key takeaways concisely.")
            notes_parts.append("Mention future directions or implications.")

        if bullets:
            notes_parts.append(f"Talking points: {'; '.join(str(b) for b in bullets[:3])}")

        return "\n".join(notes_parts)

    def _allocate_slides(self, total: int, section_count: int) -> dict:
        """按比例分配各部分的幻灯片数"""
        if section_count == 0:
            return {}

        weights = {
            "title": 1,
            "introduction": 2,
            "methods": 3,
            "results": 4,
            "discussion": 2,
            "conclusion": 1,
        }

        total_weight = sum(weights.get(s, 1) for s in ["title", "introduction", "methods", "results", "discussion", "conclusion"][:section_count])
        allocated = {}
        remaining = total

        sections = ["title", "introduction", "methods", "results", "discussion", "conclusion"][:section_count]
        for section in sections:
            w = weights.get(section, 1)
            count = max(1, round(total * w / total_weight))
            allocated[section] = count
            remaining -= count

        if remaining > 0 and sections:
            max_section = max(sections, key=lambda s: weights.get(s, 1))
            allocated[max_section] += remaining

        return allocated

    def _suggest_layout(self, slide: dict) -> str:
        """根据内容建议幻灯片布局"""
        figures = slide.get("figures", [])
        tables = slide.get("tables", [])
        section = slide.get("section", "")

        if section == "title":
            return "title_slide"
        if figures and tables:
            return "two_column"
        if figures:
            return "image_left_text_right" if len(figures) == 1 else "image_grid"
        if tables:
            return "table_focus"
        return "content"


__acasight_plugin__ = NaturePaper2PPTPlugin()
