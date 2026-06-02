"""
Retry Utils — 照搬 Hermes Agent retry_utils.py 的核心逻辑
提供 jittered backoff 和 provider 降级策略。

来源：hermes-agent-main/agent/retry_utils.py
"""

import random
import asyncio
import structlog

logger = structlog.get_logger()


def jittered_backoff(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """指数退避 + 抖动
    
    Args:
        attempt: 当前重试次数 (0-based)
        base: 基础等待时间（秒），每次翻倍
        cap: 最大等待时间上限（秒）
    
    Returns:
        建议等待时间（秒）
    
    示例：
        attempt 0 → ~1.0s
        attempt 1 → ~2.0s  
        attempt 2 → ~4.0s
        attempt 3 → ~8.0s (继续增长直到 cap)
    """
    sleep = min(cap, base * (2 ** attempt))
    # 添加 ±20% 随机抖动，避免 thundering herd
    jitter = sleep * 0.2 * (0.5 - random.random())
    return max(0.1, sleep + jitter)


async def retry_with_backoff(
    fn,
    *args,
    max_retries: int = 3,
    retryable_errors: tuple = (Exception,),
    base_delay: float = 1.0,
    **kwargs,
):
    """带退避的重试执行
    
    Args:
        fn: 要执行的异步函数
        max_retries: 最大重试次数
        retryable_errors: 可重试的异常类型
        base_delay: 基础延迟
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_errors as e:
            last_error = e
            if attempt < max_retries:
                delay = jittered_backoff(attempt, base=base_delay)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} retries exhausted: {e}")
    
    raise last_error


def classify_api_error(error: Exception, status_code: int = None) -> str:
    """分类 API 错误类型，用于决策重试策略
    
    Returns:
        'rate_limit' — 429 / rate limit → 应等待后重试
        'context_overflow' — 上下文过长 → 应压缩后重试
        'auth_error' — 401/403 → 不应重试（除非换 provider）
        'server_error' — 5xx → 可重试（临时的）
        'timeout' — 超时 → 可重试
        'unknown' — 无法分类
    """
    error_msg = str(error).lower()
    
    # Rate limit
    if status_code == 429 or any(kw in error_msg for kw in [
        'rate limit', 'rate_limit', 'too many requests', 'quota',
        'ratelimit', 'throttle',
    ]):
        return 'rate_limit'
    
    # Context overflow
    if any(kw in error_msg for kw in [
        'context length', 'context_length', 'context window',
        'maximum context', 'max_tokens', 'token limit',
        'reduce the length', 'too long', 'input length',
    ]):
        return 'context_overflow'
    
    # Auth errors
    if status_code in (401, 403) or any(kw in error_msg for kw in [
        'unauthorized', 'forbidden', 'invalid api key',
        'authentication', 'auth', 'access denied',
    ]):
        return 'auth_error'
    
    # Server errors
    if status_code and status_code >= 500:
        return 'server_error'
    
    # Timeout
    if any(kw in error_msg for kw in [
        'timeout', 'timed out', 'connection', 'network',
    ]):
        return 'timeout'
    
    return 'unknown'
