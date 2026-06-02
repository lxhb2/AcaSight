"""
Plugin: Nature Writing
自然科学论文写作插件 — 遵循Nature写作规范，生成结构化科学论文
"""

from app.services.plugin_system import AcaSightPlugin


class NatureWritingPlugin(AcaSightPlugin):
    """自然科学论文写作插件"""

    NATURE_ABSTRACT_WORD_LIMIT = 150
    NATURE_SECTIONS = ["abstract", "introduction", "methods", "results", "discussion", "references"]

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("pre_write", self.pre_write)
        self.register_hook("post_write", self.post_write)
        self._word_limit_override = config.get("abstract_word_limit", self.NATURE_ABSTRACT_WORD_LIMIT)

    async def on_enable(self) -> None:
        """启用"""
        pass

    async def on_disable(self) -> None:
        """禁用"""
        pass

    async def on_unload(self) -> None:
        """卸载"""
        pass

    async def write_nature_abstract(self, research_summary: dict, word_limit: int = 150) -> dict:
        """
        生成Nature格式摘要

        Nature摘要要求:
        1. 不超过150词 (默认)
        2. 包含: 基本背景 → 研究问题 → 关键方法 → 主要发现 → 意义
        3. 避免专业术语，面向广泛读者

        Args:
            research_summary: dict 包含 background, problem, method, finding, significance
            word_limit: 词数上限

        Returns:
            dict: 摘要生成结果及合规检查
        """
        effective_limit = min(word_limit, self._word_limit_override)

        required_keys = ["background", "problem", "method", "finding", "significance"]
        missing_keys = [k for k in required_keys if k not in research_summary or not research_summary[k]]
        if missing_keys:
            return {
                "success": False,
                "issues": [{"type": "missing_field", "field": k} for k in missing_keys],
                "message": f"research_summary 缺少必要字段: {', '.join(missing_keys)}",
            }

        abstract_parts = [
            research_summary["background"],
            research_summary["problem"],
            research_summary["method"],
            research_summary["finding"],
            research_summary["significance"],
        ]

        abstract_text = " ".join(part.strip() for part in abstract_parts if part.strip())
        word_count = len(abstract_text.split())

        compliance = {
            "word_count": word_count,
            "word_limit": effective_limit,
            "within_limit": word_count <= effective_limit,
            "has_background": bool(research_summary.get("background")),
            "has_problem": bool(research_summary.get("problem")),
            "has_method": bool(research_summary.get("method")),
            "has_finding": bool(research_summary.get("finding")),
            "has_significance": bool(research_summary.get("significance")),
        }

        issues = []
        if word_count > effective_limit:
            issues.append({
                "type": "word_limit_exceeded",
                "severity": "error",
                "message": f"摘要词数 {word_count} 超过限制 {effective_limit}",
                "excess": word_count - effective_limit,
            })

        return {
            "success": True,
            "abstract": abstract_text,
            "word_count": word_count,
            "compliance": compliance,
            "issues": issues,
        }

    async def write_nature_introduction(self, background: str, gap: str, objective: str) -> dict:
        """
        生成Nature格式引言

        Nature引言结构:
        1. 宽泛背景 → 引入领域
        2. 研究空白 → 指出未解决的问题
        3. 研究目标 → 本文要解决什么

        Args:
            background: 研究背景
            gap: 研究空白/现有问题
            objective: 研究目标

        Returns:
            dict: 引言生成结果
        """
        issues = []

        if not background or not background.strip():
            issues.append({"type": "missing_background", "severity": "error", "message": "缺少研究背景"})
        if not gap or not gap.strip():
            issues.append({"type": "missing_gap", "severity": "error", "message": "缺少研究空白描述"})
        if not objective or not objective.strip():
            issues.append({"type": "missing_objective", "severity": "error", "message": "缺少研究目标"})

        if issues:
            return {"success": False, "issues": issues}

        introduction_parts = []
        if background:
            introduction_parts.append(background.strip())
        if gap:
            gap_text = gap.strip()
            gap_starters = ["however", "but", "yet", "despite", "although", "nevertheless"]
            gap_lower = gap_text.lower()
            if not any(gap_lower.startswith(s) for s in gap_starters):
                introduction_parts.append("However, " + gap_text[0].lower() + gap_text[1:])
            else:
                introduction_parts.append(gap_text)
        if objective:
            obj_text = objective.strip()
            introduction_parts.append("Here, " + obj_text[0].lower() + obj_text[1:])

        introduction_text = " ".join(introduction_parts)

        structure_check = {
            "has_background": bool(background and background.strip()),
            "has_gap": bool(gap and gap.strip()),
            "has_objective": bool(objective and objective.strip()),
            "follows_funnel_structure": bool(background and gap and objective),
        }

        return {
            "success": True,
            "introduction": introduction_text,
            "structure": structure_check,
            "issues": [],
        }

    async def write_nature_methods(self, methods_data: dict) -> dict:
        """
        生成Nature格式方法部分

        Nature方法要求:
        1. 详细且可复现
        2. 包含: 材料/数据、实验步骤、参数设置、统计分析
        3. 足够详细以供同行复现

        Args:
            methods_data: dict 包含 materials, procedures, parameters, statistical_analysis

        Returns:
            dict: 方法部分生成结果
        """
        required_sections = {
            "materials": "材料/数据来源",
            "procedures": "实验步骤",
            "parameters": "参数设置",
            "statistical_analysis": "统计分析",
        }

        present = {}
        missing = []
        issues = []

        for key, label in required_sections.items():
            value = methods_data.get(key)
            is_present = bool(value and (value if isinstance(value, str) else str(value).strip()))
            present[key] = is_present
            if not is_present:
                missing.append(key)
                issues.append({
                    "type": "missing_method_section",
                    "severity": "warning" if key in ("parameters", "statistical_analysis") else "error",
                    "section": key,
                    "message": f"方法部分缺少 {label} ({key})",
                })

        methods_parts = []
        for key in required_sections:
            value = methods_data.get(key)
            if value:
                if isinstance(value, str):
                    methods_parts.append(value.strip())
                elif isinstance(value, list):
                    methods_parts.append(" ".join(str(v) for v in value))
                else:
                    methods_parts.append(str(value))

        methods_text = "\n\n".join(methods_parts)

        reproducibility_markers = ["replicate", "sample size", "n =", "p <", "confidence", "error bar"]
        text_lower = methods_text.lower()
        found_markers = [m for m in reproducibility_markers if m in text_lower]

        if not found_markers:
            issues.append({
                "type": "low_reproducibility",
                "severity": "info",
                "message": "未检测到可复现性标记 (如样本量、p值、置信区间等)",
            })

        return {
            "success": len([i for i in issues if i["severity"] == "error"]) == 0,
            "methods": methods_text,
            "present_sections": present,
            "missing_sections": missing,
            "reproducibility_markers_found": found_markers,
            "issues": issues,
        }

    async def write_nature_results(self, results_data: dict) -> dict:
        """
        生成Nature格式结果部分

        Nature结果要求:
        1. 简洁，以图表为核心
        2. 只报告结果，不做解释
        3. 引用图表 (Figure/Extended Data Figure)

        Args:
            results_data: dict 包含 findings (list of dict), figures (list of dict)

        Returns:
            dict: 结果部分生成结果
        """
        findings = results_data.get("findings", [])
        figures = results_data.get("figures", [])

        issues = []

        if not findings:
            issues.append({"type": "no_findings", "severity": "error", "message": "未提供研究发现"})

        results_parts = []
        figure_refs_in_text = set()

        for finding in findings:
            text = finding.get("text", "")
            ref = finding.get("figure_ref", "")
            if text:
                if ref:
                    results_parts.append(f"{text.strip()} ({ref})")
                    figure_refs_in_text.add(ref)
                else:
                    results_parts.append(text.strip())

        available_figures = {f.get("ref", "") for f in figures if f.get("ref")}
        unreferenced = available_figures - figure_refs_in_text
        if unreferenced:
            issues.append({
                "type": "unreferenced_figure",
                "severity": "warning",
                "message": f"以下图表未被结果文本引用: {', '.join(unreferenced)}",
            })

        missing_refs = figure_refs_in_text - available_figures
        if missing_refs:
            issues.append({
                "type": "missing_figure",
                "severity": "error",
                "message": f"结果引用了不存在的图表: {', '.join(missing_refs)}",
            })

        interpretive_words = ["suggests", "implies", "indicates that", "means that", "because"]
        full_text = " ".join(results_parts).lower()
        found_interpretive = [w for w in interpretive_words if w in full_text]
        if found_interpretive:
            issues.append({
                "type": "interpretive_language",
                "severity": "info",
                "message": f"结果部分包含解释性语言 (应留至讨论部分): {', '.join(found_interpretive)}",
            })

        results_text = "\n\n".join(results_parts)

        return {
            "success": len([i for i in issues if i["severity"] == "error"]) == 0,
            "results": results_text,
            "findings_count": len(findings),
            "figures_count": len(figures),
            "figure_coverage": len(figure_refs_in_text),
            "issues": issues,
        }

    async def pre_write(self, section: str = "full", **kwargs) -> dict:
        """
        pre_write 钩子: 提供Nature写作模板

        Args:
            section: 目标章节

        Returns:
            dict: Nature写作模板和指导
        """
        templates = {
            "abstract": {
                "structure": ["Background (1-2 sentences)", "Problem (1 sentence)", "Method (1-2 sentences)", "Key finding (1-2 sentences)", "Significance (1 sentence)"],
                "word_limit": self._word_limit_override,
                "tips": ["Use active voice", "Avoid jargon", "Be concise"],
            },
            "introduction": {
                "structure": ["Broad context", "Specific gap", "Research objective"],
                "tips": ["Follow funnel structure", "End with clear objective", "Cite key references"],
            },
            "methods": {
                "structure": ["Materials/Data", "Procedures", "Parameters", "Statistical analysis"],
                "tips": ["Be reproducible", "Include sample sizes", "Report all parameters"],
            },
            "results": {
                "structure": ["Finding + figure reference", "Finding + figure reference", "..."],
                "tips": ["Be concise", "Reference all figures", "No interpretation"],
            },
            "full": {
                "structure": self.NATURE_SECTIONS,
                "tips": ["Follow Nature format strictly", "Active voice preferred", "Concise and precise"],
            },
        }

        template = templates.get(section, templates["full"])

        return {
            "hook": "pre_write",
            "section": section,
            "nature_template": template,
        }

    async def post_write(self, content: str, section: str = "full", **kwargs) -> dict:
        """
        post_write 钩子: 验证Nature写作规范

        Args:
            content: 写入的内容
            section: 写入的章节

        Returns:
            dict: Nature规范验证结果
        """
        violations = []

        if not content or not content.strip():
            return {
                "hook": "post_write",
                "compliant": False,
                "violations": [{"type": "empty_content", "severity": "error", "message": "内容为空"}],
            }

        content_lower = content.lower()

        passive_markers = ["was performed", "was conducted", "were observed", "was carried out", "it was found"]
        passive_found = [m for m in passive_markers if m in content_lower]
        if len(passive_found) > 3:
            violations.append({
                "type": "excessive_passive_voice",
                "severity": "warning",
                "message": f"检测到较多被动语态 ({len(passive_found)} 处)，Nature建议使用主动语态",
                "examples": passive_found[:3],
            })

        if section in ("abstract", "full"):
            word_count = len(content.split())
            if word_count > self._word_limit_override:
                violations.append({
                    "type": "abstract_word_limit",
                    "severity": "error",
                    "message": f"摘要词数 {word_count} 超过Nature限制 {self._word_limit_override}",
                })

        jargon_phrases = ["utilize", "in order to", "due to the fact that", "a large number of", "in the event that"]
        jargon_found = [j for j in jargon_phrases if j in content_lower]
        if jargon_found:
            violations.append({
                "type": "wordy_expressions",
                "severity": "info",
                "message": f"检测到冗余表达: {', '.join(jargon_found)}",
                "suggestions": {
                    "utilize": "use",
                    "in order to": "to",
                    "due to the fact that": "because",
                    "a large number of": "many",
                    "in the event that": "if",
                },
            })

        return {
            "hook": "post_write",
            "section": section,
            "compliant": len([v for v in violations if v["severity"] == "error"]) == 0,
            "violations": violations,
        }


__acasight_plugin__ = NatureWritingPlugin()
