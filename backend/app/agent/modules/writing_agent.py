"""
创作模块Agent — AI写作、研究方向、试验方案、降重润色、中断交互

核心能力：写作流推进 + 数据/插图章节自动中断 + 研究方向生成 + 试验方案设计 + 降重润色
"""

from app.agent.base_module import BaseModule, ModuleResult, ModuleStatus
from app.services.ai_service import ai_service
import structlog
import json

logger = structlog.get_logger()

DATA_SECTION_KEYWORDS = ["实验", "结果", "数据", "图表", "分析", "评价", "插图", "性能", "对比"]


class WritingAgent(BaseModule):
    def __init__(self):
        super().__init__(name="writing", description="创作模块Agent: 写作/研究方向/试验方案/降重/中断交互")

    async def execute(self, task: str, context: dict = None) -> ModuleResult:
        self._status = ModuleStatus.RUNNING
        ctx = context or {}

        try:
            task_lower = task.lower()
            if "研究方向" in task or "research_direction" in task_lower:
                result = await self._handle_research_direction(task, ctx)
            elif "试验方案" in task or "实验方案" in task or "experiment" in task_lower:
                result = await self._handle_experiment_design(task, ctx)
            elif "润色" in task or "polish" in task_lower or "降重" in task:
                result = await self._handle_polish(task, ctx)
            elif "大纲" in task or "outline" in task_lower:
                result = await self._handle_outline(task, ctx)
            elif "write_section" == task or "撰写" in task or "写作" in task or "章节" in task:
                result = await self._handle_write_section(task, ctx)
            else:
                result = await self._handle_general(task, ctx)

            if result.success and self._status != ModuleStatus.INTERRUPTED:
                self._status = ModuleStatus.COMPLETED
            self._last_result = result
            self._record_history(task, result)
            return result

        except Exception as e:
            self._status = ModuleStatus.FAILED
            result = ModuleResult(success=False, error=str(e))
            self._last_result = result
            self._record_history(task, result)
            logger.error("WritingAgent failed", error=str(e))
            return result

    async def resume(self, user_choice: dict = None) -> ModuleResult:
        base_result = await super().resume(user_choice)
        if not base_result.success:
            return base_result

        if user_choice:
            material_type = user_choice.get("type", "upload")
            material_info = user_choice.get("material", {})
            logger.info("WritingAgent resumed with material", material_type=material_type)

            if self._interrupt_info:
                section_title = self._interrupt_info.section_title
                section_index = self._interrupt_info.section_index
                ctx = {
                    "section_title": section_title,
                    "section_index": section_index,
                    "material_type": material_type,
                    "material_info": material_info,
                    "enable_interrupt": False,
                }
                result = await self._handle_write_section("write_section", ctx)
                self._status = ModuleStatus.COMPLETED
                self._last_result = result
                self._record_history("resume_write", result)
                return result

            return ModuleResult(success=True, data={"type": "material_confirmed", "material_type": material_type, "material": material_info})
        return ModuleResult(success=True, data={"type": "resumed_no_choice"})

    async def _handle_write_section(self, task: str, ctx: dict) -> ModuleResult:
        section_title = ctx.get("section_title", "")
        is_data_section = any(kw in section_title for kw in DATA_SECTION_KEYWORDS)

        if is_data_section and ctx.get("enable_interrupt", True):
            await self.interrupt(
                reason=f"章节「{section_title}」涉及数据/插图，需要用户确认素材来源",
                section_index=ctx.get("section_index", -1),
                section_title=section_title,
                required_type="data_or_figure",
                options=[
                    {"key": "upload", "label": "自主上传素材", "description": "上传实验图片、数据表格等"},
                    {"key": "chart", "label": "AI科研绘图", "description": "基于实验数据自动生成图表"},
                    {"key": "existing", "label": "已有成品图片", "description": "从存储模块选择已归档图片"},
                ],
            )
            return ModuleResult(
                success=True,
                interrupt_reason="data_section",
                interrupt_data={
                    "section_title": section_title,
                    "section_index": ctx.get("section_index", -1),
                    "options": ["upload", "chart", "existing"],
                },
            )

        outline = ctx.get("outline", [])
        section_index = ctx.get("section_index", 0)
        previous_content = ctx.get("previous_content", "")
        word_count = ctx.get("word_count", 1500)
        topic = ctx.get("topic", task)
        references = ctx.get("reference_dimensions", [])
        material_info = ctx.get("material_info")

        outline_text = "\n".join([f"{'#' * s.get('level', 1)} {s['title']}" for s in outline]) if outline else ""
        ref_text = ""
        if references:
            ref_text = "\n\n相关文献：\n" + "\n".join([
                f"- {r.get('paper_title', '')}: {r.get('content', '')[:200]}"
                for r in references[:5]
            ])
        mat_text = ""
        if material_info:
            mat_text = f"\n\n已确认素材：{material_info}"

        prompt = f"""请撰写以下论文章节：

**主题**：{topic}
{f'**提纲**：{outline_text}' if outline_text else ''}
**当前章节**：{section_title}
**目标字数**：{word_count}字
{f'上文：{previous_content[:500]}' if previous_content else ''}{ref_text}{mat_text}

要求：学术语言，逻辑严密，恰当引用文献。直接输出正文。"""

        messages = [
            {"role": "system", "content": "你是学术论文写作专家，擅长各学科论文撰写。"},
            {"role": "user", "content": prompt},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "section", "content": response, "section_index": section_index, "section_title": section_title})

    async def _handle_outline(self, task: str, ctx: dict) -> ModuleResult:
        topic = ctx.get("topic", task)
        paper_type = ctx.get("paper_type", "本科毕业论文")
        word_count = ctx.get("word_count", 8000)
        subject = ctx.get("subject", "")
        references = ctx.get("references", [])

        ref_text = ""
        if references:
            ref_text = "\n参考相关文献：\n" + "\n".join([
                f"- {r.get('title', '')} ({r.get('authors', '')}, {r.get('year', '')})"
                for r in references[:10]
            ])

        prompt = f"""请为以下论文主题生成详细的论文提纲：

**论文主题**：{topic}
**论文学科**：{subject or '通用'}
**论文类型**：{paper_type}
**目标字数**：{word_count}字
{ref_text}

请按以下 JSON 格式返回提纲（严格 JSON，不要额外解释）：
{{
  "title": "论文标题",
  "outline": [
    {{"level": 1, "title": "第一章 绪论", "sections": [
      {{"level": 2, "title": "1.1 研究背景", "estimated_words": 800, "description": "..."}}
    ]}}
  ],
  "keywords": ["关键词1", "关键词2"],
  "estimated_total_words": {word_count}
}}

要求：结构完整，层次清晰，符合中文学术论文规范，至少包含5个一级章节。"""

        messages = [
            {"role": "system", "content": "你是学术论文写作专家，精通各类论文结构。"},
            {"role": "user", "content": prompt},
        ]
        response = await ai_service.chat(messages, temperature=0.5)
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            parsed = json.loads(json_str.strip())
            return ModuleResult(success=True, data={"type": "outline", "outline": parsed})
        except Exception:
            return ModuleResult(success=True, data={"type": "outline", "raw": response})

    async def _handle_research_direction(self, task: str, ctx: dict) -> ModuleResult:
        topic = ctx.get("topic", task)
        subject = ctx.get("subject", "")
        background = ctx.get("background", "")
        count = ctx.get("count", 5)
        literature = ctx.get("existing_literature", [])

        lit_text = ""
        if literature:
            lit_text = "\n已有相关文献：\n" + "\n".join([
                f"- {r.get('title', '')} ({r.get('authors', '')}, {r.get('year', '')})"
                for r in literature[:10]
            ])

        prompt = f"""请基于以下信息，生成 {count} 个可行的研究方向：

**研究主题**：{topic}
**学科领域**：{subject or '通用'}
**研究背景**：{background or '暂无'}
{lit_text}

请按 JSON 格式返回，包含 title/description/novelty/feasibility/key_questions/suggested_methods/difficulty/related_fields。"""

        messages = [
            {"role": "system", "content": "你是资深学术研究规划专家，擅长发现研究空白和创新方向。"},
            {"role": "user", "content": prompt},
        ]
        response = await ai_service.chat(messages, temperature=0.7)
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            parsed = json.loads(json_str.strip())
            return ModuleResult(success=True, data={"type": "research_direction", "directions": parsed.get("directions", [])})
        except Exception:
            return ModuleResult(success=True, data={"type": "research_direction", "raw": response})

    async def _handle_experiment_design(self, task: str, ctx: dict) -> ModuleResult:
        topic = ctx.get("topic", task)
        research_question = ctx.get("research_question", "")
        methodology = ctx.get("methodology", "")
        variables = ctx.get("variables", [])

        vars_text = f"\n关键变量：{', '.join(variables)}" if variables else ""

        prompt = f"""请为以下研究设计详细的实验/试验方案：

**研究主题**：{topic}
**核心研究问题**：{research_question or '待明确'}
**研究方法倾向**：{methodology or '不限'}{vars_text}

请按 JSON 格式返回，包含 title/objective/hypothesis/design_type/variables/procedure/data_collection/analysis_plan/validity/ethics/timeline/risks/alternatives。"""

        messages = [
            {"role": "system", "content": "你是实验设计专家，精通各类学术实验方法论。"},
            {"role": "user", "content": prompt},
        ]
        response = await ai_service.chat(messages, temperature=0.5)
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            parsed = json.loads(json_str.strip())
            return ModuleResult(success=True, data={"type": "experiment_design", "design": parsed.get("experiment_design", {})})
        except Exception:
            return ModuleResult(success=True, data={"type": "experiment_design", "raw": response})

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

    async def _handle_general(self, task: str, ctx: dict) -> ModuleResult:
        messages = [
            {"role": "system", "content": "你是学术论文写作助手，擅长写作规划、结构设计和内容生成。"},
            {"role": "user", "content": task},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "general", "response": response})
