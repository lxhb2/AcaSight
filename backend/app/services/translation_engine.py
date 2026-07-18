"""
并发翻译引擎 — STranslate 风格多引擎并发

特性:
- 抽象基类 BaseTranslationEngine
- 并发调用 Google / Microsoft / MyMemory
- asyncio.as_completed 取最快结果
- 集成 RateLimiter + TranslationCache
- 全部失败时返回原文
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

import httpx

from app.services.rate_limiter import RateLimiter
from app.services.translation_cache import TranslationCache

logger = logging.getLogger(__name__)


class TranslationResult:
    def __init__(self, text: str, engine: str, from_lang: str, to_lang: str):
        self.text = text
        self.engine = engine
        self.from_lang = from_lang
        self.to_lang = to_lang


class BaseTranslationEngine(ABC):
    name: str = "base"

    def __init__(self, rate_limiter: RateLimiter, cache: TranslationCache):
        self.rate_limiter = rate_limiter
        self.cache = cache

    async def translate(
        self, text: str, from_lang: str, to_lang: str
    ) -> Optional[TranslationResult]:
        # 检查缓存
        cached = self.cache.get(text)
        if cached:
            return TranslationResult(cached, "cache", from_lang, to_lang)

        # 速率限制
        self.rate_limiter.wait()

        # 执行翻译
        result = await self._do_translate(text, from_lang, to_lang)
        if result:
            self.cache.set(text, result)
        return TranslationResult(result, self.name, from_lang, to_lang) if result else None

    @abstractmethod
    async def _do_translate(
        self, text: str, from_lang: str, to_lang: str
    ) -> Optional[str]:
        pass


class GoogleEngine(BaseTranslationEngine):
    name = "google"

    def __init__(self):
        super().__init__(RateLimiter(5), TranslationCache("google"))

    async def _do_translate(
        self, text: str, from_lang: str, to_lang: str
    ) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://googlet.deno.dev/translate",
                    json={
                        "text": text,
                        "source_lang": self._normalize_lang(from_lang),
                        "target_lang": self._normalize_lang(to_lang),
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("data", "")
                    if result and result.strip() and result != text:
                        logger.info(f"Google ✓: {text[:30]}...")
                        return result
            return None
        except Exception as e:
            logger.warning(f"Google error: {e}")
            return None

    def _normalize_lang(self, code: str) -> str:
        mapping = {"zh": "zh-CN", "en": "en", "auto": "auto"}
        return mapping.get(code, code)


class MicrosoftEngine(BaseTranslationEngine):
    name = "microsoft"

    def __init__(self):
        super().__init__(RateLimiter(5), TranslationCache("microsoft"))

    async def _do_translate(
        self, text: str, from_lang: str, to_lang: str
    ) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "api-version": "3.0",
                    "from": self._normalize_lang(from_lang) if from_lang != "auto" else "",
                    "to": self._normalize_lang(to_lang),
                }
                resp = await client.get(
                    "https://api-edge.cognitive.microsofttranslator.com/translate",
                    params=params,
                    headers={"Content-Type": "application/json"},
                    json=[{"Text": text}],
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = data[0]["translations"][0]["text"]
                    if result and result != text:
                        logger.info(f"Microsoft ✓: {text[:30]}...")
                        return result
            return None
        except Exception as e:
            logger.warning(f"Microsoft error: {e}")
            return None

    def _normalize_lang(self, code: str) -> str:
        mapping = {"zh": "zh-Hans", "en": "en", "auto": ""}
        return mapping.get(code, code)


class MyMemoryEngine(BaseTranslationEngine):
    name = "mymemory"

    def __init__(self):
        super().__init__(RateLimiter(10), TranslationCache("mymemory"))

    async def _do_translate(
        self, text: str, from_lang: str, to_lang: str
    ) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.mymemory.translated.net/get",
                    params={
                        "q": text,
                        "langpair": f"{self._normalize_lang(from_lang)}|{self._normalize_lang(to_lang)}",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("responseData", {}).get("translatedText", "")
                    match = data.get("responseData", {}).get("match", 0)
                    if result and result.strip() and result != text:
                        logger.info(f"MyMemory ✓ (match={match}): {text[:30]}...")
                        return result
            return None
        except Exception as e:
            logger.warning(f"MyMemory error: {e}")
            return None

    def _normalize_lang(self, code: str) -> str:
        mapping = {"zh": "zh-CN", "en": "en-GB", "auto": "en"}
        return mapping.get(code, code)


class ConcurrentTranslationService:
    """并发翻译服务 — 多引擎竞争，取最快结果"""

    def __init__(self):
        self.engines = [
            GoogleEngine(),
            MicrosoftEngine(),
            MyMemoryEngine(),
        ]

    async def translate(
        self, text: str, from_lang: str = "auto", to_lang: str = "zh"
    ) -> TranslationResult:
        """并发翻译，返回最快结果（全部失败返回原文）"""
        if from_lang == "auto":
            from_lang = self._detect_language(text)

        # 创建并发任务
        tasks = [
            engine.translate(text, from_lang, to_lang) for engine in self.engines
        ]

        # 取第一个成功结果
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result and result.text:
                    return result
            except Exception:
                continue

        # 全部失败，返回原文
        return TranslationResult(text, "none", from_lang, to_lang)

    async def translate_stream(
        self, text: str, from_lang: str = "auto", to_lang: str = "zh"
    ) -> AsyncGenerator[dict, None]:
        """流式翻译 — 实时返回结果（SSE 格式）"""
        if from_lang == "auto":
            from_lang = self._detect_language(text)

        # 先检查缓存
        for engine in self.engines:
            cached = engine.cache.get(text)
            if cached:
                yield {"type": "chunk", "text": cached}
                yield {"type": "complete", "text": cached, "engine": "cache"}
                return

        # 并发请求，谁先返回就推送
        tasks = {
            asyncio.create_task(engine.translate(text, from_lang, to_lang)): engine
            for engine in self.engines
        }

        done, pending = await asyncio.wait(
            tasks.keys(), return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            try:
                result = await task
                if result and result.text:
                    # 取消其他任务
                    for t in pending:
                        t.cancel()
                    yield {
                        "type": "complete",
                        "text": result.text,
                        "engine": result.engine,
                    }
                    return
            except Exception:
                continue

        # 等待剩余任务
        for task in asyncio.as_completed(pending):
            try:
                result = await task
                if result and result.text:
                    yield {
                        "type": "complete",
                        "text": result.text,
                        "engine": result.engine,
                    }
                    return
            except Exception:
                continue

        yield {"type": "error", "error": "All engines failed"}

    def _detect_language(self, text: str) -> str:
        import re

        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        return "zh" if (cjk / max(len(text.strip()), 1)) > 0.1 else "en"