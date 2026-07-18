"""
格式保留翻译器 — 保护公式、代码等特殊内容

特性:
- 使用占位符保护 LaTeX 公式（$$...$$ / $...$）
- 保护代码块（```...``` / `...`）
- 保护 URL
- 翻译后还原占位符
- 智能学术术语替换（避开保护区域）
"""

import re
from typing import Dict

import logging

logger = logging.getLogger(__name__)

# 学术术语词典
ACADEMIC_GLOSSARY_EN2ZH = {
    "deep learning": "深度学习",
    "machine learning": "机器学习",
    "neural network": "神经网络",
    "convolutional neural network": "卷积神经网络",
    "transformer": "Transformer",
    "attention mechanism": "注意力机制",
    "reinforcement learning": "强化学习",
    "transfer learning": "迁移学习",
    "large language model": "大语言模型",
    "pre-trained model": "预训练模型",
    "fine-tuning": "微调",
    "natural language processing": "自然语言处理",
    "computer vision": "计算机视觉",
    "knowledge graph": "知识图谱",
    "ablation study": "消融实验",
    "state-of-the-art": "当前最优",
    "cross-validation": "交叉验证",
    "standard deviation": "标准差",
    "standard error": "标准误",
    "principal component analysis": "主成分分析",
    "p-value": "p值",
    "confidence interval": "置信区间",
    "precision": "精确率",
    "recall": "召回率",
    "F1 score": "F1分数",
    "abstract": "摘要",
    "introduction": "引言",
    "related work": "相关工作",
    "methodology": "方法",
    "experimental results": "实验结果",
    "discussion": "讨论",
    "conclusion": "结论",
    "references": "参考文献",
    "corpus": "语料库",
    "benchmark": "基准测试",
    "baseline": "基线",
    "end-to-end": "端到端",
    "zero-shot": "零样本",
    "few-shot": "少样本",
    "inference": "推理",
    "robustness": "鲁棒性",
    "generalization": "泛化能力",
    "embedding": "嵌入",
    "regularization": "正则化",
    "overfitting": "过拟合",
    "underfitting": "欠拟合",
    "beam search": "束搜索",
    "perplexity": "困惑度",
    "et al.": "等人",
    "i.e.": "即",
    "e.g.": "例如",
    "vs.": "对比",
    "diffusion model": "扩散模型",
    "contrastive learning": "对比学习",
    "self-supervised learning": "自监督学习",
    "generative adversarial network": "生成对抗网络",
}


class FormatPreservingTranslator:
    """格式保留翻译器"""

    PLACEHOLDER_TEMPLATE = "<<<{id}>>>"

    def __init__(self, inner_translator):
        self.inner = inner_translator
        self.placeholders: Dict[str, dict] = {}
        self.placeholder_id = 0
        self.academic_glossary = ACADEMIC_GLOSSARY_EN2ZH

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """格式保留翻译"""
        self.placeholders = {}
        self.placeholder_id = 0

        # 1. 提取并保护特殊内容
        protected_text = self._extract_special_content(text)

        # 2. 翻译
        try:
            result = await self.inner.translate(protected_text, from_lang, to_lang)
            translated = result.text if hasattr(result, "text") else str(result)
        except Exception as e:
            logger.warning(f"Format preserving inner translate failed: {e}")
            return text

        # 3. 还原占位符
        result_text = self._restore_placeholders(translated)

        # 4. 应用学术术语（避开保护区域）
        if from_lang == "en" and to_lang == "zh":
            result_text = self._apply_glossary_smart(result_text)

        return result_text

    def _extract_special_content(self, text: str) -> str:
        """提取并保护特殊内容"""
        result = text

        # 保护 LaTeX 公式 $$...$$
        result = re.sub(
            r"\$\$(.*?)\$\$",
            lambda m: self._create_placeholder(m.group(0), "formula_display"),
            result,
            flags=re.DOTALL,
        )

        # 保护行内公式 $...$（不匹配 $$）
        result = re.sub(
            r"(?<!\$)\$(?!\$)(.*?)\$",
            lambda m: self._create_placeholder(m.group(0), "formula_inline"),
            result,
        )

        # 保护代码块 ```...```
        result = re.sub(
            r"```[\s\S]*?```",
            lambda m: self._create_placeholder(m.group(0), "code_block"),
            result,
        )

        # 保护行内代码 `...`
        result = re.sub(
            r"`([^`]+)`",
            lambda m: self._create_placeholder(m.group(0), "code_inline"),
            result,
        )

        # 保护 URL
        result = re.sub(
            r'https?://[^\s<>"\']+',
            lambda m: self._create_placeholder(m.group(0), "url"),
            result,
        )

        return result

    def _create_placeholder(self, content: str, content_type: str) -> str:
        self.placeholder_id += 1
        placeholder = self.PLACEHOLDER_TEMPLATE.format(id=self.placeholder_id)
        self.placeholders[placeholder] = {"content": content, "type": content_type}
        return placeholder

    def _restore_placeholders(self, text: str) -> str:
        result = text
        for placeholder, info in self.placeholders.items():
            result = result.replace(placeholder, info["content"])
        return result

    def _apply_glossary_smart(self, text: str) -> str:
        """智能应用术语词典，避开保护区域"""
        # 识别保护区域（已还原的内容）
        protected_ranges = []
        for match in re.finditer(
            r"(\$\$.*?\$\$|\$.*?\$|`[^`]+`|```[\s\S]*?```)", text
        ):
            protected_ranges.append((match.start(), match.end()))

        # 按长度排序术语，先替换长的
        sorted_terms = sorted(self.academic_glossary.keys(), key=len, reverse=True)

        result = text
        for term in sorted_terms:
            pattern = re.compile(
                r"(?<![a-zA-Z])" + re.escape(term) + r"(?![a-zA-Z])", re.IGNORECASE
            )

            def replace_if_safe(match):
                start, end = match.span()
                # 检查是否在保护区域内
                for p_start, p_end in protected_ranges:
                    if start >= p_start and end <= p_end:
                        return match.group(0)  # 不替换
                return self.academic_glossary[term]

            result = pattern.sub(replace_if_safe, result)

        return result