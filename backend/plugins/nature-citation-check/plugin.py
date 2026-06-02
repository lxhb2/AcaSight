"""
Nature Citation Check Plugin
Nature引用检查插件 — 检查引用格式、完整性、自引比例，确保符合Nature引用规范
"""

import re
from typing import Any

from app.services.plugin_system import AcaSightPlugin


class NatureCitationCheckPlugin(AcaSightPlugin):
    """Nature引用检查插件"""

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_write", self._on_post_write)
        self._max_self_citation_ratio = config.get("max_self_citation_ratio", 0.20)

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
        """post_write 钩子: 自动检查引用"""
        format_result = self.check_citation_format(content)
        refs = kwargs.get("references", [])
        completeness_result = self.check_citation_completeness(refs) if refs else {"complete": True, "issues": []}
        author = kwargs.get("author_name", "")
        self_citation_result = (
            self.check_self_citation_ratio(author, refs) if author and refs else {"ratio": 0.0, "warning": False}
        )
        return {
            "citation_format": format_result,
            "citation_completeness": completeness_result,
            "self_citation": self_citation_result,
        }

    def check_citation_format(self, text: str, style: str = "nature") -> dict:
        """
        检查Nature引用格式 (编号式、顺序引用)

        Nature要求:
        1. 引用使用上标编号 [1], [2] 等
        2. 按出现顺序编号
        3. 编号连续无跳号
        """
        issues = []

        citation_pattern = re.compile(r"\[(\d+)\]")
        found = citation_pattern.findall(text)

        if not found:
            issues.append("no_citations_found")
            return {"style": style, "valid": False, "issues": issues}

        numbers = [int(n) for n in found]

        if style == "nature":
            sorted_unique = sorted(set(numbers))
            expected = list(range(1, len(sorted_unique) + 1))
            if sorted_unique != expected:
                gaps = set(expected) - set(sorted_unique)
                issues.append(f"non_sequential_numbers: missing {sorted(gaps)}")

            for i, n in enumerate(numbers[:-1]):
                if numbers[i + 1] < n:
                    issues.append(f"out_of_order: [{n}] appears before [{numbers[i + 1]}]")
                    break

            author_year_pattern = re.compile(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)")
            if author_year_pattern.search(text):
                issues.append("author_year_format_found: Nature requires numbered citations")

        return {"style": style, "valid": len(issues) == 0, "issues": issues, "citation_count": len(set(numbers))}

    def check_citation_completeness(self, references: list) -> dict:
        """
        检查引用完整性: 所有引用编号是否有对应的参考文献条目
        """
        issues = []
        ref_numbers = set()
        for ref in references:
            if isinstance(ref, dict):
                num = ref.get("number")
                if num is not None:
                    ref_numbers.add(int(num))
            elif isinstance(ref, (int, str)):
                try:
                    ref_numbers.add(int(ref))
                except (ValueError, TypeError):
                    pass

        if not ref_numbers:
            issues.append("no_numbered_references")
            return {"complete": False, "issues": issues}

        expected = set(range(1, max(ref_numbers) + 1))
        missing = expected - ref_numbers
        if missing:
            issues.append(f"missing_references: {sorted(missing)}")

        for ref in references:
            if isinstance(ref, dict):
                required_fields = ["authors", "title", "journal", "year"]
                missing_fields = [f for f in required_fields if not ref.get(f)]
                if missing_fields:
                    issues.append(f"incomplete_reference_{ref.get('number', '?')}: missing {missing_fields}")

        return {"complete": len(issues) == 0, "issues": issues, "reference_count": len(ref_numbers)}

    def check_self_citation_ratio(self, author_name: str, references: list) -> dict:
        """
        检查自引比例 (超过阈值则警告)

        Nature建议自引比例不超过20%
        """
        if not references:
            return {"ratio": 0.0, "warning": False, "self_citations": 0, "total": 0}

        self_count = 0
        author_last = author_name.strip().lower().split()[-1] if author_name else ""

        for ref in references:
            if isinstance(ref, dict):
                authors_str = ref.get("authors", "")
                if author_last and author_last in authors_str.lower():
                    self_count += 1

        total = len(references)
        ratio = self_count / total if total > 0 else 0.0
        warning = ratio > self._max_self_citation_ratio

        return {
            "ratio": round(ratio, 3),
            "warning": warning,
            "self_citations": self_count,
            "total": total,
            "threshold": self._max_self_citation_ratio,
        }


__acasight_plugin__ = NatureCitationCheckPlugin()
