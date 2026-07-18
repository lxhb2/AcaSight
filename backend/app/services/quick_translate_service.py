"""
[DEPRECATED] 轻量翻译服务 — 已迁移至 translation_service.py (Opus-MT)

此文件保留作为备份参考，不再被任何路由导入。
新的翻译架构:
- 主力: Helsinki-NLP/opus-mt-en-zh (本地学术翻译)
- 兜底: AI (LLM)
- 路由: app/routers/translate.py → translation_service.py

引擎策略（按优先级）:
1. translate 库 (MyMemory) — 主力引擎，免费，国内可用
2. Google Translate — 备用（国内可能被墙）
3. MyMemory (deep-translator) — 备用
4. AI (LLM) — 最终兜底，使用系统 AI 配置

特性:
- 引擎自动恢复：失败后延迟重试，不会永久禁用
- LRU 结果缓存
- 学术术语词典后处理
- 自动语言检测
"""

import hashlib
import re
import logging
import time
from typing import Dict, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

# 学术术语词典（用于后处理）
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
    "object detection": "目标检测",
    "named entity recognition": "命名实体识别",
    "sentiment analysis": "情感分析",
    "text summarization": "文本摘要",
    "machine translation": "机器翻译",
    "question answering": "问答系统",
    "reinforcement learning from human feedback": "基于人类反馈的强化学习",
    "inference": "推理",
    "robustness": "鲁棒性",
    "generalization": "泛化能力",
    "corpus": "语料库",
    "abstract": "摘要",
    "introduction": "引言",
    "related work": "相关工作",
    "methodology": "方法",
    "conclusion": "结论",
    "references": "参考文献",
    "appendix": "附录",
    "et al": "等人",
    "i.e.": "即",
    "e.g.": "例如",
    "vs.": "对比",
}


class TranslationCache:
    """LRU 翻译结果缓存"""
    def __init__(self, maxsize: int = 512):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize

    def _make_key(self, text: str, from_lang: str, to_lang: str) -> str:
        h = hashlib.md5(text.encode()).hexdigest()[:16]
        return f"{from_lang}:{to_lang}:{h}"

    def get(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        key = self._make_key(text, from_lang, to_lang)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, text: str, from_lang: str, to_lang: str, translation: str):
        key = self._make_key(text, from_lang, to_lang)
        self._cache[key] = translation
        while len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


def _normalize_lang(code: str, engine: str) -> str:
    """标准化语言代码为各引擎支持的格式"""
    if code == "zh":
        return "zh-CN" if engine in ("google", "mymemory") else "zh"
    if code == "en":
        return "en-GB" if engine == "mymemory" else "en"
    if code == "auto":
        return "auto" if engine == "google" else "en"
    return code


class QuickTranslateService:
    """轻量翻译服务 — 多引擎自动降级 + AI 兜底"""

    def __init__(self):
        self._cache = TranslationCache()
        self._engine_fail_time: Dict[str, float] = {}
        self._engine_retry_delay = 300  # 5 分钟后重试失败的引擎

    def _is_engine_disabled(self, name: str) -> bool:
        fail_time = self._engine_fail_time.get(name, 0)
        if fail_time == 0:
            return False
        if time.time() - fail_time > self._engine_retry_delay:
            self._engine_fail_time[name] = 0
            logger.info(f"Engine {name} auto-recovered after {self._engine_retry_delay}s")
            return False
        return True

    def _disable_engine(self, name: str):
        self._engine_fail_time[name] = time.time()
        logger.warning(f"Engine {name} disabled, will retry in {self._engine_retry_delay}s")

    def _apply_glossary(self, text: str) -> str:
        """应用学术术语词典后处理"""
        terms = sorted(ACADEMIC_GLOSSARY_EN2ZH.keys(), key=len, reverse=True)
        for term in terms:
            pattern = re.compile(
                r'(?<![a-zA-Z])' + re.escape(term) + r'(?![a-zA-Z])',
                re.IGNORECASE
            )
            text = pattern.sub(ACADEMIC_GLOSSARY_EN2ZH[term], text)
        text = re.sub(r'\b(for|and|the|of|in|on|at|to|with|by|from|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|shall|should|can|could|may|might|must|a|an)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _detect_language(self, text: str) -> str:
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        total = len(text.strip())
        return "en" if total == 0 else ("zh" if (cjk / total) > 0.1 else "en")

    def _translate_translate_lib(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """translate 库 (MyMemory) — 主力引擎"""
        if self._is_engine_disabled("translate_lib"):
            return None
        try:
            from translate import Translator
            source = _normalize_lang(from_lang, "mymemory")
            target = _normalize_lang(to_lang, "mymemory")
            translator = Translator(from_lang=source, to_lang=target)
            result = translator.translate(text)
            if result and result.strip() and result != text:
                logger.info(f"translate_lib success: {text[:30]}... -> {result[:30]}...")
                return result
            return None
        except Exception as e:
            logger.warning(f"translate_lib failed: {e}")
            self._disable_engine("translate_lib")
            return None

    def _translate_google(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """Google Translate 引擎"""
        if self._is_engine_disabled("google"):
            return None
        try:
            from deep_translator import GoogleTranslator
            source = _normalize_lang(from_lang, "google")
            target = _normalize_lang(to_lang, "google")
            result = GoogleTranslator(source=source, target=target).translate(text)
            if result and result.strip() and result != text:
                logger.info(f"Google Translate success: {text[:30]}... -> {result[:30]}...")
                return result
            return None
        except Exception as e:
            logger.warning(f"Google Translate failed: {e}")
            self._disable_engine("google")
            return None

    def _translate_mymemory(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """MyMemory 翻译引擎 (deep-translator)"""
        if self._is_engine_disabled("mymemory"):
            return None
        try:
            from deep_translator import MyMemoryTranslator
            source = _normalize_lang(from_lang, "mymemory")
            target = _normalize_lang(to_lang, "mymemory")
            result = MyMemoryTranslator(source=source, target=target).translate(text)
            if result and result.strip() and result != text and "MYMEMORY" not in result.upper():
                logger.info(f"MyMemory success: {text[:30]}... -> {result[:30]}...")
                return result
            return None
        except Exception as e:
            logger.warning(f"MyMemory Translate failed: {e}")
            self._disable_engine("mymemory")
            return None

    def _translate_ai(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """AI (LLM) 翻译 — 最终兜底"""
        try:
            import asyncio
            from app.services.ai_service import AIService

            ai = AIService()

            if from_lang == "en" and to_lang == "zh":
                system_prompt = "You are a professional academic translator. Translate the given English text to Chinese. Keep technical terms in English. Output only the translation, no explanations."
            else:
                system_prompt = f"You are a professional translator. Translate to {to_lang}. Output only the translation, no explanations."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ]

            async def _collect() -> str:
                result_parts = []
                async for chunk in ai.chat(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048,
                    task_type="translate",
                    use_cache=False,
                ):
                    result_parts.append(chunk)
                return "".join(result_parts)

            translation = asyncio.run(_collect())
            if translation and translation.strip():
                logger.info(f"AI translation success: {text[:30]}... -> {translation[:50]}...")
                return translation.strip()

            logger.warning("AI translation returned empty result")
            return None
        except Exception as e:
            logger.warning(f"AI translation failed: {e}")
            return None

    def translate(
        self,
        text: str,
        from_lang: str = "auto",
        to_lang: str = "zh",
    ) -> Dict:
        if not text or not text.strip():
            return {
                "translation": "",
                "from_lang": from_lang,
                "to_lang": to_lang,
                "engine": "none",
                "error": "empty_text",
            }

        if from_lang == "auto":
            from_lang = self._detect_language(text)

        if from_lang == to_lang:
            return {
                "translation": text,
                "from_lang": from_lang,
                "to_lang": to_lang,
                "engine": "identity",
                "error": None,
            }

        cached = self._cache.get(text, from_lang, to_lang)
        if cached is not None:
            return {
                "translation": cached,
                "from_lang": from_lang,
                "to_lang": to_lang,
                "engine": "cache",
                "error": None,
            }

        # 引擎降级链：translate_lib → Google → MyMemory → AI
        engines = [
            ("translate_lib", self._translate_translate_lib),
            ("google", self._translate_google),
            ("mymemory", self._translate_mymemory),
            ("ai", self._translate_ai),
        ]

        result = None
        used_engine = "none"
        error = None

        for engine_name, engine_fn in engines:
            try:
                result = engine_fn(text, from_lang, to_lang)
                if result:
                    used_engine = engine_name
                    logger.info(f"Translation engine used: {engine_name}")
                    break
            except Exception as e:
                logger.warning(f"Engine {engine_name} error: {e}")
                continue

        if result is None:
            error = "all_engines_failed"
            result = text
        else:
            if from_lang == "en" and to_lang == "zh":
                result = self._apply_glossary(result)

        self._cache.set(text, from_lang, to_lang, result)

        return {
            "translation": result,
            "from_lang": from_lang,
            "to_lang": to_lang,
            "engine": used_engine,
            "error": error,
        }

    @property
    def status(self) -> Dict:
        engines = {}
        for name in ("translate_lib", "google", "mymemory"):
            engines[name] = not self._is_engine_disabled(name)
        engines["ai"] = True
        return {
            "engines": engines,
            "cache_size": len(self._cache._cache),
        }


quick_translate_service = QuickTranslateService()