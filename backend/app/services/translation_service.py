"""
翻译服务 — STranslate 风格内嵌引擎 (零模型, 零 API Key)

v2.0 升级:
- 多引擎并发调用（asyncio.as_completed 取最快结果）
- SQLite 持久化缓存（进程重启不丢失）
- 漏桶速率限制（防止 API 限流）
- 格式保留翻译（保护公式、代码、URL）
- 流式翻译（SSE）
- 向后兼容: 原有接口签名不变

引擎策略:
1. Google (googlet.deno.dev)     — 主力引擎，Deno 代理免翻
2. Microsoft (Edge TTS API)      — 内嵌免 Key
3. MyMemory                       — 免费全开
4. AI (LLM)                       — 最终兜底
"""

import logging
import re
import asyncio
from typing import Optional

from app.services.translation_engine import ConcurrentTranslationService
from app.services.format_preserving_translator import FormatPreservingTranslator

logger = logging.getLogger(__name__)


def _detect_language(text: str) -> str:
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    return "zh" if (cjk / max(len(text.strip()), 1)) > 0.1 else "en"


# ── 统一翻译服务 ────────────────────────────────────────────────────

class TranslationService:
    """STranslate 风格多引擎翻译: Google | Microsoft | MyMemory | AI 并发"""

    def __init__(self):
        self._concurrent = ConcurrentTranslationService()
        self._formatter = FormatPreservingTranslator(self._concurrent)

    def translate(self, text, from_lang="auto", to_lang="zh"):
        """同步翻译（兼容旧接口）"""
        if not text or not text.strip():
            return {"translation": "", "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "none", "error": "empty_text"}
        if from_lang == "auto":
            from_lang = _detect_language(text)
        if from_lang == to_lang:
            return {"translation": text, "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "identity", "error": None}

        try:
            result = asyncio.run(self._translate_impl(text, from_lang, to_lang))
            return result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {"translation": text, "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "none", "error": str(e)}

    async def translate_async(self, text, from_lang="auto", to_lang="zh"):
        """异步翻译"""
        if not text or not text.strip():
            return {"translation": "", "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "none", "error": "empty_text"}
        if from_lang == "auto":
            from_lang = _detect_language(text)
        if from_lang == to_lang:
            return {"translation": text, "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "identity", "error": None}

        try:
            return await self._translate_impl(text, from_lang, to_lang)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {"translation": text, "from_lang": from_lang, "to_lang": to_lang,
                    "engine": "none", "error": str(e)}

    async def _translate_impl(self, text, from_lang, to_lang):
        """内部实现 — 并发引擎 + 格式保留 + AI 兜底"""
        # 格式保留翻译（并发引擎取最快结果）
        try:
            translated = await self._formatter.translate(text, from_lang, to_lang)
            if translated and translated != text:
                return {"translation": translated, "from_lang": from_lang,
                        "to_lang": to_lang, "engine": "concurrent", "error": None}
        except Exception as e:
            logger.warning(f"Concurrent translation failed: {e}")

        # AI 兜底
        try:
            from app.services.ai_service import AIService
            ai = AIService()
            sys = "You are a professional academic translator. Output ONLY the translation, no explanations."
            parts = []
            async for chunk in ai.chat(
                messages=[{"role": "system", "content": sys},
                          {"role": "user", "content": text}],
                temperature=0.1, max_tokens=2048, task_type="translate",
                use_cache=False,
            ):
                parts.append(chunk)
            result = "".join(parts).strip()
            if result and result != text:
                logger.info(f"AI ✓: {text[:30]}...")
                return {"translation": result, "from_lang": from_lang,
                        "to_lang": to_lang, "engine": "ai", "error": None}
        except Exception as e:
            logger.error(f"AI fallback: {e}")

        return {"translation": text, "from_lang": from_lang, "to_lang": to_lang,
                "engine": "none", "error": "all_failed"}

    @property
    def status(self):
        return {
            "engines": {"google": True, "microsoft": True, "mymemory": True, "ai": True},
            "cache": {"size": 0, "hits": 0, "misses": 0, "hit_rate": "0%"},
            "chain": ["google", "microsoft", "mymemory", "ai"],
            "mode": "concurrent",
        }


translation_service = TranslationService()