"""
Helsinki-NLP Opus-MT 翻译引擎

特性:
- 基于 Helsinki-NLP/opus-mt-en-zh 模型（学术级质量，OPUS 语料库训练）
- 100% 本地运行，无需网络
- HuggingFace transformers 标准接口
- 自动分块长文本翻译
- 支持多语言对扩展
- 延迟加载，按需初始化模型

参考:
- https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
- BabelDOC 的 BaseTranslator 架构
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 支持的语言对 → HuggingFace 模型映射
MODEL_MAP: Dict[str, str] = {
    "en-zh": "Helsinki-NLP/opus-mt-en-zh",
    "zh-en": "Helsinki-NLP/opus-mt-zh-en",
    "en-ja": "Helsinki-NLP/opus-mt-en-jap",  # ja → jap in older naming
    "ja-en": "Helsinki-NLP/opus-mt-jap-en",
    "en-de": "Helsinki-NLP/opus-mt-en-de",
    "de-en": "Helsinki-NLP/opus-mt-de-en",
    "en-fr": "Helsinki-NLP/opus-mt-en-fr",
    "fr-en": "Helsinki-NLP/opus-mt-fr-en",
    "en-es": "Helsinki-NLP/opus-mt-en-es",
    "es-en": "Helsinki-NLP/opus-mt-es-en",
    "en-ko": "Helsinki-NLP/opus-mt-en-ko",
    "ko-en": "Helsinki-NLP/opus-mt-ko-en",
    "en-ru": "Helsinki-NLP/opus-mt-en-ru",
    "ru-en": "Helsinki-NLP/opus-mt-ru-en",
}

# 语言代码简短映射
LANG_SHORT: Dict[str, str] = {
    "chinese": "zh", "english": "en", "japanese": "ja",
    "korean": "ko", "french": "fr", "german": "de",
    "spanish": "es", "portuguese": "pt", "russian": "ru",
    "zh-cn": "zh", "zh-tw": "zh", "en-us": "en", "en-gb": "en",
    "zh": "zh", "en": "en", "ja": "ja", "ko": "ko",
    "fr": "fr", "de": "de", "es": "es", "pt": "pt", "ru": "ru",
}

# 学术术语词典（后处理强化）
ACADEMIC_GLOSSARY_EN2ZH = {
    # AI/ML 领域
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
    "generative adversarial network": "生成对抗网络",
    "recurrent neural network": "循环神经网络",
    "long short-term memory": "长短期记忆",
    "backpropagation": "反向传播",
    "gradient descent": "梯度下降",
    "stochastic gradient descent": "随机梯度下降",
    "overfitting": "过拟合",
    "underfitting": "欠拟合",
    "regularization": "正则化",
    "batch normalization": "批归一化",
    "layer normalization": "层归一化",
    "activation function": "激活函数",
    "loss function": "损失函数",
    "cross-entropy": "交叉熵",
    "mean squared error": "均方误差",
    "hyperparameter": "超参数",
    "embedding": "嵌入",
    "tokenization": "分词",
    "encoder": "编码器",
    "decoder": "解码器",
    "self-attention": "自注意力",
    "multi-head attention": "多头注意力",
    "positional encoding": "位置编码",
    "feed-forward network": "前馈网络",
    "residual connection": "残差连接",
    "beam search": "束搜索",
    "perplexity": "困惑度",
    "BLEU score": "BLEU分数",
    "ROUGE score": "ROUGE分数",
    "F1 score": "F1分数",
    "end-to-end": "端到端",
    "zero-shot": "零样本",
    "few-shot": "少样本",
    "retrieval-augmented generation": "检索增强生成",
    "diffusion model": "扩散模型",
    "graph neural network": "图神经网络",
    "contrastive learning": "对比学习",
    "self-supervised learning": "自监督学习",
    "federated learning": "联邦学习",
    "data augmentation": "数据增强",
    "dimensionality reduction": "降维",
    "inference": "推理",
    "robustness": "鲁棒性",
    "generalization": "泛化能力",
    # 论文结构
    "abstract": "摘要",
    "introduction": "引言",
    "related work": "相关工作",
    "methodology": "方法",
    "experimental results": "实验结果",
    "discussion": "讨论",
    "conclusion": "结论",
    "references": "参考文献",
    "appendix": "附录",
    "acknowledgments": "致谢",
    # 统计/实验
    "p-value": "p值",
    "confidence interval": "置信区间",
    "null hypothesis": "零假设",
    "statistically significant": "统计显著",
    "correlation coefficient": "相关系数",
    "regression analysis": "回归分析",
    "root mean square error": "均方根误差",
    "area under the curve": "曲线下面积",
    "true positive": "真阳性",
    "false positive": "假阳性",
    "precision": "精确率",
    "recall": "召回率",
    # 化学/材料
    "X-ray diffraction": "X射线衍射",
    "scanning electron microscope": "扫描电子显微镜",
    "transmission electron microscopy": "透射电子显微镜",
    "Fourier transform infrared spectroscopy": "傅里叶变换红外光谱",
    "thermogravimetric analysis": "热重分析",
    "differential scanning calorimetry": "差示扫描量热法",
    "Brunauer-Emmett-Teller": "BET比表面积",
    # 通用学术
    "et al.": "等人",
    "i.e.": "即",
    "e.g.": "例如",
    "vs.": "对比",
    "corpus": "语料库",
    "benchmark": "基准测试",
    "baseline": "基线",
}

# 小写术语映射（用于不区分大小写的匹配）
_GLOSSARY_LOWER = {k.lower(): v for k, v in ACADEMIC_GLOSSARY_EN2ZH.items()}
_SORTED_TERMS = sorted(_GLOSSARY_LOWER.keys(), key=len, reverse=True)


def _apply_glossary(text: str) -> str:
    """应用学术术语词典后处理（保留原术语的大小写）"""
    result = text
    for term_lower in _SORTED_TERMS:
        pattern = re.compile(
            r'(?<![a-zA-Z])' + re.escape(term_lower) + r'(?![a-zA-Z])',
            re.IGNORECASE,
        )
        zh = _GLOSSARY_LOWER[term_lower]
        result = pattern.sub(zh, result)
    return result


def _detect_language(text: str) -> str:
    """检测文本主要语言（en/zh）"""
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    total = max(len(text.strip()), 1)
    return "zh" if (cjk / total) > 0.1 else "en"


def _normalize_lang(code: str) -> str:
    """标准化语言代码"""
    return LANG_SHORT.get(code.lower(), code)


def _chunk_text(text: str, max_chars: int = 512) -> List[str]:
    """将长文本按句子边界分块（Opus-MT 对短句质量更高）"""
    if len(text) <= max_chars:
        return [text]
    # 按句子分隔符切分
    sentences = re.split(r'(?<=[.!?。！？\n])\s*', text)
    chunks, cur = [], ""
    for s in sentences:
        if not s.strip():
            continue
        if len(cur) + len(s) <= max_chars:
            cur += (" " if cur else "") + s
        else:
            if cur:
                chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)
    return chunks or [text]


class OpusMTService:
    """Helsinki-NLP Opus-MT 翻译服务"""

    def __init__(self):
        self._models: Dict[str, object] = {}     # key: "en-zh" → pipeline
        self._tokenizers: Dict[str, object] = {}
        self._available = False
        self._init_error: Optional[str] = None
        self._try_init()

    def _try_init(self):
        """检测 transformers 是否可用"""
        try:
            import transformers
            self._available = True
            logger.info("OpusMT: transformers available, ready for lazy-loading models")
        except ImportError:
            self._available = False
            self._init_error = "transformers_not_installed"
            logger.warning("OpusMT: transformers not installed. Run: pip install transformers sentencepiece torch")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def status(self) -> Dict:
        return {
            "available": self._available,
            "error": self._init_error,
            "loaded_models": list(self._models.keys()),
            "supported_pairs": list(MODEL_MAP.keys()),
        }

    def _get_pair_key(self, source: str, target: str) -> str:
        return f"{source}-{target}"

    def _load_model(self, source: str, target: str) -> Tuple[Optional[object], Optional[object]]:
        """延迟加载指定的语言对模型"""
        pair = self._get_pair_key(source, target)
        if pair in self._models:
            return self._models[pair], self._tokenizers[pair]

        hf_model = MODEL_MAP.get(pair)
        if not hf_model:
            logger.warning(f"OpusMT: unsupported pair {pair}")
            return None, None

        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            import torch

            logger.info(f"OpusMT: loading {hf_model} ...")
            tokenizer = AutoTokenizer.from_pretrained(hf_model)
            model = AutoModelForSeq2SeqLM.from_pretrained(hf_model)

            # 使用 GPU 如果可用
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()

            self._models[pair] = (model, device)
            self._tokenizers[pair] = tokenizer
            logger.info(f"OpusMT: {hf_model} loaded on {device}")
            return (model, device), tokenizer
        except Exception as e:
            logger.error(f"OpusMT: failed to load {hf_model}: {e}")
            return None, None

    def _translate_sync(self, text: str, source: str, target: str) -> Optional[str]:
        """同步翻译单个文本块"""
        pair = self._get_pair_key(source, target)
        model_info = self._models.get(pair)
        tokenizer = self._tokenizers.get(pair)

        if model_info is None or tokenizer is None:
            result = self._load_model(source, target)
            if result[0] is None:
                return None
            model_info = self._models[pair]
            tokenizer = self._tokenizers[pair]

        try:
            import torch
            model, device = model_info

            # Opus-MT 需要添加目标语言前缀 token
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                )

            translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translation
        except Exception as e:
            logger.error(f"OpusMT translate failed: {e}")
            return None

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> Dict:
        """翻译文本（主入口）"""
        if not text or not text.strip():
            return {"translation": "", "source_lang": source_lang, "target_lang": target_lang,
                    "engine": "opus-mt", "error": "empty_text"}

        # 标准化语言代码
        source = _normalize_lang(source_lang)
        target = _normalize_lang(target_lang)

        # 自动检测源语言
        if source_lang == "auto":
            source = _detect_language(text)

        # 同语言不翻译
        if source == target:
            return {"translation": text, "source_lang": source, "target_lang": target,
                    "engine": "identity", "error": None}

        # 检查是否支持该语言对
        pair = self._get_pair_key(source, target)
        if pair not in MODEL_MAP:
            return {"translation": text, "source_lang": source, "target_lang": target,
                    "engine": "unsupported_pair", "error": f"pair {pair} not supported"}

        if not self._available:
            return {"translation": text, "source_lang": source, "target_lang": target,
                    "engine": "unavailable", "error": self._init_error}

        # 分块翻译
        chunks = _chunk_text(text)
        translated_parts = []
        all_ok = True

        for chunk in chunks:
            result = self._translate_sync(chunk, source, target)
            if result is not None:
                translated_parts.append(result)
            else:
                all_ok = False
                translated_parts.append(chunk)  # 保留原文

        translation = " ".join(translated_parts)

        # 学术术语词典后处理（仅 en→zh 时应用）
        if source == "en" and target == "zh":
            translation = _apply_glossary(translation)

        return {
            "translation": translation,
            "source_lang": source,
            "target_lang": target,
            "engine": "opus-mt",
            "chunks": len(chunks),
            "error": None if all_ok else "partial",
        }

    def translate_batch(self, texts: List[str], source_lang: str = "auto", target_lang: str = "zh") -> List[Dict]:
        """批量翻译"""
        return [self.translate(t, source_lang, target_lang) for t in texts]


# 全局单例
opus_mt_service = OpusMTService()
