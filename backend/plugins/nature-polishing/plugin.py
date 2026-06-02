"""
Plugin: Nature Polishing
自然科学论文润色插件 — 符合Nature语言风格，提升学术表达质量
"""

from app.services.plugin_system import AcaSightPlugin


class NaturePolishingPlugin(AcaSightPlugin):
    """自然科学论文润色插件"""

    PASSIVE_PATTERNS = [
        "was performed", "was conducted", "were observed", "was carried out",
        "was investigated", "were analyzed", "was evaluated", "were examined",
        "was determined", "were measured",
    ]

    WORDY_EXPRESSIONS = {
        "utilize": "use",
        "utilizes": "uses",
        "utilized": "used",
        "in order to": "to",
        "due to the fact that": "because",
        "a large number of": "many",
        "a significant number of": "many",
        "in the event that": "if",
        "at the present time": "now",
        "for the purpose of": "to",
        "in the vicinity of": "near",
        "it is worth noting that": "notably",
        "it should be noted that": "notably",
        "has the ability to": "can",
        "is capable of": "can",
        "on the basis of": "based on",
        "with regard to": "regarding",
        "in terms of": "for",
        "a considerable amount of": "much",
        "prior to": "before",
        "subsequent to": "after",
    }

    NATURE_STYLE_RULES = {
        "active_voice": "Nature prefers active voice (e.g., 'We performed' not 'was performed')",
        "conciseness": "Eliminate wordy expressions; every word should earn its place",
        "precision": "Use precise terms; avoid vague quantifiers (e.g., 'some', 'various')",
        "directness": "State findings directly; avoid hedging unless necessary",
    }

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_write", self.post_write)
        self._auto_polish = config.get("auto_polish", True)
        self._polish_level = config.get("polish_level", "standard")

    async def on_enable(self) -> None:
        """启用"""
        pass

    async def on_disable(self) -> None:
        """禁用"""
        pass

    async def on_unload(self) -> None:
        """卸载"""
        pass

    async def polish_nature_style(self, text: str, section: str = "body") -> dict:
        """
        润色为Nature语言风格

        核心风格要求:
        1. 主动语态优先
        2. 简洁表达
        3. 精确用词
        4. 直接陈述

        Args:
            text: 待润色文本
            section: 文本所属章节 ("abstract", "introduction", "body", "methods", "results", "discussion")

        Returns:
            dict: 润色结果，包含修改建议和润色后文本
        """
        if not text or not text.strip():
            return {
                "success": False,
                "issues": [{"type": "empty_text", "severity": "error", "message": "待润色文本为空"}],
            }

        polished = text
        changes = []

        for wordy, concise in self.WORDY_EXPRESSIONS.items():
            if wordy in polished.lower():
                original_text = polished
                polished_lower = polished.lower()
                start = 0
                while True:
                    idx = polished_lower.find(wordy, start)
                    if idx == -1:
                        break
                    original_word = polished[idx:idx + len(wordy)]
                    if original_word[0].isupper():
                        replacement = concise[0].upper() + concise[1:]
                    else:
                        replacement = concise
                    polished = polished[:idx] + replacement + polished[idx + len(wordy):]
                    polished_lower = polished.lower()
                    changes.append({
                        "type": "wordy_expression",
                        "original": original_word,
                        "replacement": replacement,
                        "rule": "conciseness",
                    })
                    start = idx + len(replacement)

        text_lower = polished.lower()
        passive_found = [p for p in self.PASSIVE_PATTERNS if p in text_lower]
        for passive in passive_found:
            idx = text_lower.find(passive)
            context_start = max(0, idx - 30)
            context_end = min(len(polished), idx + len(passive) + 30)
            context = polished[context_start:context_end]
            changes.append({
                "type": "passive_voice",
                "original": passive,
                "suggestion": f"Consider active voice, e.g., 'We {passive.replace('was ', '').replace('were ', '')}'",
                "context": context,
                "rule": "active_voice",
            })

        vague_quantifiers = ["some", "various", "several", "a lot of", "quite", "rather", "somewhat"]
        for vq in vague_quantifiers:
            if vq in text_lower:
                changes.append({
                    "type": "vague_quantifier",
                    "original": vq,
                    "suggestion": "Replace with a specific number or remove",
                    "rule": "precision",
                })

        if section == "abstract":
            word_count = len(polished.split())
            if word_count > 150:
                changes.append({
                    "type": "word_limit",
                    "original": f"{word_count} words",
                    "suggestion": "Reduce to 150 words or fewer for Nature abstract",
                    "rule": "conciseness",
                })

        return {
            "success": True,
            "polished_text": polished,
            "changes": changes,
            "change_count": len(changes),
            "section": section,
        }

    async def check_language_quality(self, text: str) -> dict:
        """
        检查语言质量

        检查维度:
        1. 语法正确性 (基础检查)
        2. 表达清晰度
        3. 简洁度
        4. 一致性

        Args:
            text: 待检查文本

        Returns:
            dict: 语言质量检查结果
        """
        if not text or not text.strip():
            return {
                "passed": False,
                "issues": [{"type": "empty_text", "severity": "error", "message": "待检查文本为空"}],
                "scores": {},
            }

        issues = []
        text_lower = text.lower()
        sentences = [s.strip() for s in text.split(".") if s.strip()]

        grammar_issues = []
        double_words = []
        words = text.split()
        for i in range(len(words) - 1):
            if words[i].lower() == words[i + 1].lower() and words[i].lower() not in ("that", "had"):
                double_words.append((words[i], i))
        for word, pos in double_words:
            grammar_issues.append({
                "type": "repeated_word",
                "word": word,
                "position": pos,
                "message": f"疑似重复词: '{word} {word}'",
            })

        clarity_issues = []
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        for s in long_sentences:
            clarity_issues.append({
                "type": "long_sentence",
                "word_count": len(s.split()),
                "message": f"句子过长 ({len(s.split())} 词)，建议拆分",
                "preview": s[:80] + "..." if len(s) > 80 else s,
            })

        conciseness_issues = []
        for wordy, concise in self.WORDY_EXPRESSIONS.items():
            if wordy in text_lower:
                conciseness_issues.append({
                    "type": "wordy_expression",
                    "original": wordy,
                    "suggested": concise,
                    "message": f"冗余表达: '{wordy}' → '{concise}'",
                })

        consistency_issues = []
        ize_words = [w for w in words if w.lower().endswith("ize") and w.lower() not in ("size", "prize")]
        ise_words = [w for w in words if w.lower().endswith("ise") and w.lower() not in ("raise", "arise", "comprise")]
        if ize_words and ise_words:
            consistency_issues.append({
                "type": "spelling_inconsistency",
                "message": "混合使用 -ize 和 -ise 拼写，Nature建议统一使用 -ize (美式)",
                "ize_examples": ize_words[:3],
                "ise_examples": ise_words[:3],
            })

        all_issues = grammar_issues + clarity_issues + conciseness_issues + consistency_issues
        for issue in all_issues:
            if issue["type"] in ("repeated_word",):
                issues.append({**issue, "severity": "error", "category": "grammar"})
            elif issue["type"] in ("long_sentence",):
                issues.append({**issue, "severity": "warning", "category": "clarity"})
            elif issue["type"] in ("wordy_expression",):
                issues.append({**issue, "severity": "warning", "category": "conciseness"})
            elif issue["type"] in ("spelling_inconsistency",):
                issues.append({**issue, "severity": "info", "category": "consistency"})

        grammar_score = max(0, 100 - len(grammar_issues) * 20)
        clarity_score = max(0, 100 - len(clarity_issues) * 10)
        conciseness_score = max(0, 100 - len(conciseness_issues) * 5)
        consistency_score = max(0, 100 - len(consistency_issues) * 15)
        overall = int(0.3 * grammar_score + 0.3 * clarity_score + 0.25 * conciseness_score + 0.15 * consistency_score)

        return {
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "scores": {
                "grammar": grammar_score,
                "clarity": clarity_score,
                "conciseness": conciseness_score,
                "consistency": consistency_score,
                "overall": overall,
            },
            "issues": issues,
            "issue_counts": {
                "grammar": len(grammar_issues),
                "clarity": len(clarity_issues),
                "conciseness": len(conciseness_issues),
                "consistency": len(consistency_issues),
            },
        }

    async def suggest_improvements(self, text: str, section: str = "body") -> dict:
        """
        提出具体改进建议

        基于Nature风格指南，针对文本提出可操作的改进建议

        Args:
            text: 待改进文本
            section: 文本所属章节

        Returns:
            dict: 改进建议列表
        """
        if not text or not text.strip():
            return {
                "suggestions": [],
                "message": "文本为空，无法提供改进建议",
            }

        suggestions = []
        text_lower = text.lower()
        sentences = [s.strip() for s in text.split(".") if s.strip()]

        passive_count = sum(1 for p in self.PASSIVE_PATTERNS if p in text_lower)
        if passive_count > 0:
            suggestions.append({
                "category": "active_voice",
                "priority": "high",
                "rule": self.NATURE_STYLE_RULES["active_voice"],
                "count": passive_count,
                "action": f"将 {passive_count} 处被动语态改为主动语态",
                "example": "'was performed' → 'We performed'",
            })

        wordy_count = sum(1 for w in self.WORDY_EXPRESSIONS if w in text_lower)
        if wordy_count > 0:
            suggestions.append({
                "category": "conciseness",
                "priority": "high",
                "rule": self.NATURE_STYLE_RULES["conciseness"],
                "count": wordy_count,
                "action": f"替换 {wordy_count} 处冗余表达",
                "example": "'in order to' → 'to'",
            })

        long_sentences = [s for s in sentences if len(s.split()) > 35]
        if long_sentences:
            suggestions.append({
                "category": "clarity",
                "priority": "medium",
                "rule": self.NATURE_STYLE_RULES["directness"],
                "count": len(long_sentences),
                "action": f"拆分 {len(long_sentences)} 个过长句子 (>35词)",
                "example": "将复合句拆分为2-3个简洁短句",
            })

        vague_words = ["some", "various", "several", "a lot of", "quite", "rather"]
        vague_found = [v for v in vague_words if v in text_lower]
        if vague_found:
            suggestions.append({
                "category": "precision",
                "priority": "medium",
                "rule": self.NATURE_STYLE_RULES["precision"],
                "count": len(vague_found),
                "action": f"替换 {len(vague_found)} 个模糊量词为具体数值",
                "example": "'several methods' → 'three methods'",
                "found": vague_found,
            })

        hedge_words = ["may", "might", "could potentially", "it is possible that", "it seems that"]
        hedge_found = [h for h in hedge_words if h in text_lower]
        if len(hedge_found) > 2:
            suggestions.append({
                "category": "directness",
                "priority": "low",
                "rule": self.NATURE_STYLE_RULES["directness"],
                "count": len(hedge_found),
                "action": f"减少 {len(hedge_found)} 处不必要的模糊表述",
                "example": "'it seems that' → 直接陈述发现",
            })

        if section == "abstract":
            word_count = len(text.split())
            if word_count > 150:
                suggestions.append({
                    "category": "word_limit",
                    "priority": "high",
                    "rule": "Nature abstracts must not exceed 150 words",
                    "count": 1,
                    "action": f"将摘要从 {word_count} 词缩减至150词以内",
                    "example": "删除背景细节，保留核心发现",
                })

        return {
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "section": section,
        }

    async def post_write(self, content: str, section: str = "body", **kwargs) -> dict:
        """
        post_write 钩子: 写作后自动润色

        Args:
            content: 写入的内容
            section: 写入的章节

        Returns:
            dict: 自动润色结果
        """
        if not self._auto_polish:
            return {
                "hook": "post_write",
                "auto_polish": False,
                "message": "自动润色已禁用",
            }

        polish_result = await self.polish_nature_style(content, section=section)
        quality_result = await self.check_language_quality(content)
        suggestion_result = await self.suggest_improvements(content, section=section)

        return {
            "hook": "post_write",
            "auto_polish": True,
            "polish": polish_result,
            "quality": quality_result,
            "suggestions": suggestion_result,
        }


__acasight_plugin__ = NaturePolishingPlugin()
