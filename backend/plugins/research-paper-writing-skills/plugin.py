"""
Plugin: Research Paper Writing Skills
计算机类论文逻辑检查插件 — 检查论文的逻辑链条、结论支撑、实验设计完整性
"""

from app.services.plugin_system import AcaSightPlugin


class ResearchPaperWritingSkillsPlugin(AcaSightPlugin):
    """计算机类论文逻辑检查插件"""

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_write", self.post_write)
        self._strict_mode = config.get("strict_mode", False)

    async def on_enable(self) -> None:
        """启用"""
        pass

    async def on_disable(self) -> None:
        """禁用"""
        pass

    async def on_unload(self) -> None:
        """卸载"""
        pass

    async def check_paper_logic(self, paper_content: str, section: str = "full") -> dict:
        """
        检查论文逻辑链条

        分析论文各部分之间的逻辑关系，检测:
        1. 研究问题 → 方法 的逻辑一致性
        2. 方法 → 结果 的因果链
        3. 结果 → 结论 的推导合理性
        4. 各章节之间的衔接连贯性

        Args:
            paper_content: 论文全文或章节内容
            section: 检查范围 ("full", "introduction", "methodology", "results", "discussion")

        Returns:
            dict: 逻辑检查结果，包含问题列表和改进建议
        """
        issues = []
        suggestions = []

        if not paper_content or not paper_content.strip():
            return {
                "passed": False,
                "section": section,
                "issues": [{"type": "empty_content", "severity": "error", "message": "论文内容为空"}],
                "suggestions": [],
            }

        logic_markers = {
            "introduction": ["problem", "challenge", "gap", "motivation", "objective"],
            "methodology": ["propose", "design", "approach", "algorithm", "framework", "model"],
            "results": ["experiment", "evaluation", "performance", "accuracy", "comparison"],
            "discussion": ["finding", "implication", "limitation", "future", "conclusion"],
        }

        content_lower = paper_content.lower()

        if section == "full":
            for sec, markers in logic_markers.items():
                found = [m for m in markers if m in content_lower]
                if not found:
                    issues.append({
                        "type": "missing_logic_component",
                        "severity": "warning",
                        "section": sec,
                        "message": f"未检测到 {sec} 部分的关键逻辑标记: {markers}",
                    })
                    suggestions.append({
                        "section": sec,
                        "suggestion": f"建议在 {sec} 部分补充相关逻辑表述，如: {', '.join(markers[:3])}",
                    })
        else:
            markers = logic_markers.get(section, [])
            found = [m for m in markers if m in content_lower]
            if not found and markers:
                issues.append({
                    "type": "weak_logic_chain",
                    "severity": "warning",
                    "section": section,
                    "message": f"{section} 部分逻辑链条薄弱，缺少关键标记",
                })
                suggestions.append({
                    "section": section,
                    "suggestion": f"建议加强逻辑表述: {', '.join(markers[:3])}",
                })

        transition_words = ["however", "therefore", "furthermore", "consequently", "thus", "moreover"]
        transitions_found = [t for t in transition_words if t in content_lower]
        if len(transitions_found) < 2 and section in ("full", "discussion"):
            issues.append({
                "type": "weak_transitions",
                "severity": "info",
                "section": section,
                "message": "段落间过渡词较少，逻辑衔接可能不够流畅",
            })
            suggestions.append({
                "section": section,
                "suggestion": "建议增加逻辑过渡词以增强论证连贯性",
            })

        return {
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "section": section,
            "issues": issues,
            "suggestions": suggestions,
            "logic_score": max(0, 100 - len(issues) * 15),
        }

    async def check_conclusion_support(self, conclusions: list, evidence: list) -> dict:
        """
        检查结论是否有充分证据支撑

        逐条验证每个结论是否有对应的实验数据、统计分析或文献支撑

        Args:
            conclusions: 结论列表，每条为字符串
            evidence: 证据列表，每条为 dict {"type": "experiment|statistic|citation", "content": str, "supports": int}

        Returns:
            dict: 结论支撑检查结果
        """
        if not conclusions:
            return {
                "passed": False,
                "issues": [{"type": "no_conclusions", "severity": "error", "message": "未提供结论列表"}],
                "support_map": [],
            }

        if not evidence:
            return {
                "passed": False,
                "issues": [{"type": "no_evidence", "severity": "error", "message": "未提供证据列表"}],
                "support_map": [],
            }

        support_map = []
        unsupported = []

        for idx, conclusion in enumerate(conclusions):
            supporting = [e for e in evidence if e.get("supports") == idx]
            evidence_types = [e.get("type", "unknown") for e in supporting]

            has_experiment = "experiment" in evidence_types
            has_statistic = "statistic" in evidence_types
            has_citation = "citation" in evidence_types

            entry = {
                "conclusion_index": idx,
                "conclusion": conclusion[:80] if len(conclusion) > 80 else conclusion,
                "evidence_count": len(supporting),
                "evidence_types": evidence_types,
                "has_experiment": has_experiment,
                "has_statistic": has_statistic,
                "has_citation": has_citation,
            }

            if not supporting:
                unsupported.append(idx)
                entry["status"] = "unsupported"
            elif has_experiment and has_statistic:
                entry["status"] = "well_supported"
            elif has_experiment or has_statistic:
                entry["status"] = "partially_supported"
            else:
                entry["status"] = "weakly_supported"

            support_map.append(entry)

        issues = []
        for idx in unsupported:
            issues.append({
                "type": "unsupported_conclusion",
                "severity": "error",
                "conclusion_index": idx,
                "message": f"结论 #{idx + 1} 缺乏证据支撑",
            })

        weakly = [e for e in support_map if e["status"] == "weakly_supported"]
        for entry in weakly:
            issues.append({
                "type": "weakly_supported_conclusion",
                "severity": "warning",
                "conclusion_index": entry["conclusion_index"],
                "message": f"结论 #{entry['conclusion_index'] + 1} 仅有文献支撑，缺少实验或统计数据",
            })

        return {
            "passed": len(unsupported) == 0,
            "total_conclusions": len(conclusions),
            "unsupported_count": len(unsupported),
            "weakly_supported_count": len(weakly),
            "support_map": support_map,
            "issues": issues,
            "support_score": max(0, 100 - len(unsupported) * 25 - len(weakly) * 10),
        }

    async def check_experiment_design(self, experiment_desc: str, research_questions: list) -> dict:
        """
        检查实验设计完整性

        验证实验设计是否覆盖所有研究问题，是否包含必要的实验要素

        Args:
            experiment_desc: 实验设计描述
            research_questions: 研究问题列表

        Returns:
            dict: 实验设计检查结果
        """
        if not experiment_desc or not experiment_desc.strip():
            return {
                "passed": False,
                "issues": [{"type": "empty_experiment", "severity": "error", "message": "实验设计描述为空"}],
                "completeness": {},
            }

        required_components = {
            "dataset": ["dataset", "benchmark", "corpus", "data"],
            "baseline": ["baseline", "comparison", "compare", "against"],
            "metric": ["metric", "measure", "evaluation", "accuracy", "f1", "precision", "recall"],
            "setup": ["setup", "environment", "hardware", "gpu", "cpu", "implementation"],
            "parameter": ["parameter", "hyperparameter", "configuration", "setting"],
            "reproducibility": ["seed", "random", "reproducib", "code", "available"],
        }

        desc_lower = experiment_desc.lower()
        completeness = {}
        missing = []

        for component, keywords in required_components.items():
            found = [k for k in keywords if k in desc_lower]
            completeness[component] = {
                "present": len(found) > 0,
                "matched_keywords": found,
            }
            if not found:
                missing.append(component)

        issues = []
        for comp in missing:
            severity = "error" if comp in ("dataset", "metric") else "warning"
            issues.append({
                "type": "missing_component",
                "severity": severity,
                "component": comp,
                "message": f"实验设计缺少 {comp} 相关描述",
            })

        if research_questions:
            covered = []
            uncovered = []
            for rq in research_questions:
                rq_keywords = [w.lower() for w in rq.split() if len(w) > 3]
                if any(kw in desc_lower for kw in rq_keywords):
                    covered.append(rq)
                else:
                    uncovered.append(rq)

            if uncovered:
                issues.append({
                    "type": "uncovered_research_question",
                    "severity": "warning",
                    "message": f"有 {len(uncovered)} 个研究问题未被实验设计覆盖",
                    "uncovered_questions": uncovered,
                })
        else:
            covered = []
            uncovered = []

        total_components = len(required_components)
        present_count = sum(1 for v in completeness.values() if v["present"])

        return {
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "completeness": completeness,
            "missing_components": missing,
            "coverage_ratio": f"{present_count}/{total_components}",
            "research_questions_covered": len(covered),
            "research_questions_total": len(research_questions) if research_questions else 0,
            "issues": issues,
            "design_score": max(0, int(100 * present_count / total_components) - len(uncovered) * 10),
        }

    async def post_write(self, content: str, section: str = "full", **kwargs) -> dict:
        """
        post_write 钩子: 写作后自动检查论文逻辑

        Args:
            content: 写入的论文内容
            section: 写入的章节

        Returns:
            dict: 逻辑检查结果
        """
        result = await self.check_paper_logic(content, section=section)
        return {
            "hook": "post_write",
            "auto_logic_check": result,
        }


__acasight_plugin__ = ResearchPaperWritingSkillsPlugin()
