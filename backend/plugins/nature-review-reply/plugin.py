"""
Nature Review Reply Plugin
Nature审稿回复插件 — 生成结构化审稿回复，逐条回应审稿人意见
"""

from typing import Any

from app.services.plugin_system import AcaSightPlugin


class NatureReviewReplyPlugin(AcaSightPlugin):
    """Nature审稿回复插件"""

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_write", self._on_post_write)
        self._reply_tone = config.get("reply_tone", "respectful")

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
        """post_write 钩子: 提供审稿回复模板"""
        doc_type = kwargs.get("doc_type", "")
        if doc_type != "review_reply":
            return {"applied": False, "reason": "not_review_reply_document"}

        review_comments = kwargs.get("review_comments", [])
        if not review_comments:
            return {"applied": False, "reason": "no_review_comments"}

        structured = self.structure_point_by_point(review_comments)
        return {"applied": True, "template": structured, "tone": self._reply_tone}

    def generate_review_reply(self, review_comments: list, paper_content: str) -> dict:
        """
        生成结构化逐条审稿回复

        对每条审稿意见生成: 原始意见 → 回复策略 → 具体回复 → 修改说明
        """
        structured = self.structure_point_by_point(review_comments)
        replies = []

        for item in structured.get("items", []):
            comment = item.get("comment", "")
            reviewer = item.get("reviewer", "Reviewer")
            point = item.get("point", 1)

            suggestions = self.suggest_revisions(comment, paper_content)

            reply = {
                "reviewer": reviewer,
                "point": point,
                "original_comment": comment,
                "reply_strategy": suggestions.get("strategy", "address_directly"),
                "reply_text": suggestions.get("draft_reply", ""),
                "suggested_revisions": suggestions.get("revisions", []),
                "confidence": suggestions.get("confidence", "medium"),
            }
            replies.append(reply)

        return {
            "total_comments": len(replies),
            "replies": replies,
            "tone": self._reply_tone,
            "summary": {
                "addressed": sum(1 for r in replies if r["reply_strategy"] == "address_directly"),
                "partially_addressed": sum(1 for r in replies if r["reply_strategy"] == "partial_revision"),
                "deferred": sum(1 for r in replies if r["reply_strategy"] == "defer_with_explanation"),
            },
        }

    def structure_point_by_point(self, comments: list) -> dict:
        """
        将审稿意见结构化为 Reviewer/Point/Response 格式

        输入: 原始审稿意见列表
        输出: 按审稿人分组的结构化意见
        """
        items = []
        reviewer_map = {}

        for idx, comment in enumerate(comments):
            if isinstance(comment, dict):
                reviewer = comment.get("reviewer", "Reviewer 1")
                text = comment.get("comment", "")
            else:
                reviewer = "Reviewer 1"
                text = str(comment)

            if reviewer not in reviewer_map:
                reviewer_map[reviewer] = 0
            reviewer_map[reviewer] += 1
            point = reviewer_map[reviewer]

            items.append(
                {
                    "reviewer": reviewer,
                    "point": point,
                    "comment": text,
                    "category": self._categorize_comment(text),
                }
            )

        reviewers = []
        for name, count in reviewer_map.items():
            reviewers.append({"name": name, "comment_count": count})

        return {"items": items, "reviewers": reviewers, "total_points": len(items)}

    def suggest_revisions(self, comment: str, paper_content: str) -> dict:
        """
        针对单条审稿意见建议具体修改

        分析意见类型并给出修改策略和草稿回复
        """
        category = self._categorize_comment(comment)

        strategy_map = {
            "methodology": "address_directly",
            "data_analysis": "address_directly",
            "literature": "partial_revision",
            "clarity": "address_directly",
            "formatting": "address_directly",
            "scope": "defer_with_explanation",
            "additional_experiment": "partial_revision",
        }

        strategy = strategy_map.get(category, "address_directly")

        reply_templates = {
            "methodology": f"We thank the reviewer for this insightful comment. We have revised the methodology section to address this concern. Specifically, ",
            "data_analysis": f"We appreciate the reviewer's careful evaluation. We have re-analyzed the data as suggested and updated the results accordingly. ",
            "literature": f"We thank the reviewer for pointing out these relevant references. We have incorporated them into the revised manuscript. ",
            "clarity": f"We agree with the reviewer that this section could be clearer. We have rewritten the relevant passage to improve clarity. ",
            "formatting": f"We have corrected the formatting issues as requested. ",
            "scope": f"We appreciate this suggestion, which extends beyond the current scope. We have added a discussion of this point in the Limitations section. ",
            "additional_experiment": f"We acknowledge the value of this suggestion. Due to resource constraints, we have addressed this by ",
        }

        draft_reply = reply_templates.get(category, "We thank the reviewer for this comment. ")

        revisions = []
        if category in ("methodology", "data_analysis"):
            revisions.append({"type": "content_update", "section": "Methods", "action": "revise"})
            revisions.append({"type": "content_update", "section": "Results", "action": "update"})
        elif category == "literature":
            revisions.append({"type": "reference_add", "section": "Introduction", "action": "add_citations"})
        elif category == "clarity":
            revisions.append({"type": "rewriting", "section": "as_needed", "action": "clarify"})
        elif category == "additional_experiment":
            revisions.append({"type": "content_add", "section": "Supplementary", "action": "add_analysis"})

        return {
            "category": category,
            "strategy": strategy,
            "draft_reply": draft_reply,
            "revisions": revisions,
            "confidence": "high" if category in ("methodology", "clarity", "formatting") else "medium",
        }

    def _categorize_comment(self, text: str) -> str:
        """将审稿意见分类"""
        text_lower = text.lower()

        methodology_keywords = ["method", "approach", "procedure", "protocol", "experimental design", "algorithm"]
        data_keywords = ["data", "analysis", "statistic", "result", "figure", "table", "measurement"]
        literature_keywords = ["reference", "citation", "literature", "prior work", "related work", "previous study"]
        clarity_keywords = ["clarify", "clear", "confusing", "ambiguous", "explain", "unclear", "readability"]
        format_keywords = ["format", "typo", "grammar", "spelling", "style", "font", "layout"]
        scope_keywords = ["scope", "beyond", "limitation", "extend", "future work", "out of scope"]
        experiment_keywords = [
            "additional experiment",
            "further experiment",
            "more experiment",
            "control",
            "validation",
            "benchmark",
        ]

        categories = [
            ("additional_experiment", experiment_keywords),
            ("methodology", methodology_keywords),
            ("data_analysis", data_keywords),
            ("literature", literature_keywords),
            ("clarity", clarity_keywords),
            ("formatting", format_keywords),
            ("scope", scope_keywords),
        ]

        for cat, keywords in categories:
            if any(kw in text_lower for kw in keywords):
                return cat

        return "general"


__acasight_plugin__ = NatureReviewReplyPlugin()
