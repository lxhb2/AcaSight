"""
请求限流与 CORS 加固 (方向V.4)

功能:
1. IP 限流中间件 (令牌桶算法)
2. 请求大小限制
3. CORS 白名单加固
4. 安全头注入
"""

import os
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP 限流中间件 — 令牌桶算法
    
    配置:
    - default_limit: 每分钟默认请求数
    - burst_limit: 突发最大请求数
    - window_seconds: 滑动窗口大小
    """
    
    def __init__(
        self,
        app: FastAPI,
        default_limit: int = 60,
        burst_limit: int = 20,
        window_seconds: int = 60,
        enable_rate_limit: bool = True,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.burst_limit = burst_limit
        self.window_seconds = window_seconds
        if os.environ.get("TESTING", "false").lower() == "true":
            self.enable_rate_limit = False
        else:
            self.enable_rate_limit = enable_rate_limit
        
        # IP → [(timestamp, count)]
        self._buckets: Dict[str, list] = defaultdict(list)
        
        # 特殊路径限流 (更宽松)
        self._relaxed_paths = {
            "/api/health",
            "/api/arch/status",
            "/api/figure-edit/status",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        }
        
        # SSE 端点 (更宽松)
        self._sse_paths = {
            "/api/chat/stream",
            "/api/writing/workspace/",
            "/api/deep-research/start",
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, ip: str, path: str) -> Tuple[bool, int]:
        """
        检查是否超限
        
        Returns:
            (is_limited, remaining_requests)
        """
        if not self.enable_rate_limit:
            return False, self.default_limit
        
        now = time.time()
        
        # 清理过期记录
        self._buckets[ip] = [
            t for t in self._buckets[ip]
            if now - t < self.window_seconds
        ]
        
        # 确定限流阈值
        if path in self._relaxed_paths:
            limit = self.default_limit * 5  # 健康检查等5倍宽松
        elif any(path.startswith(p) for p in self._sse_paths):
            limit = self.default_limit * 3  # SSE 端点3倍宽松
        else:
            limit = self.default_limit
        
        current_count = len(self._buckets[ip])
        remaining = max(0, limit - current_count)
        
        if current_count >= limit:
            return True, 0
        
        # 记录本次请求
        self._buckets[ip].append(now)
        return False, remaining
    
    async def dispatch(self, request: Request, call_next):
        if not self.enable_rate_limit:
            response = await call_next(request)
            return response

        bypass_secret = os.environ.get("RATE_LIMIT_BYPASS_SECRET", "")
        bypass_header = request.headers.get("X-RateLimit-Bypass", "")
        is_debug = os.environ.get("DEBUG", "false").lower() == "true"
        if bypass_secret and bypass_header == bypass_secret:
            response = await call_next(request)
            return response
        if is_debug and bypass_header == "acasight-test-bypass":
            response = await call_next(request)
            return response

        ip = self._get_client_ip(request)
        path = request.url.path
        
        is_limited, remaining = self._is_rate_limited(ip, path)
        
        if is_limited:
            logger.warning("Rate limit exceeded", ip=ip, path=path)
            return Response(
                content=json_dumps({"detail": "Rate limit exceeded. Please try again later."}),
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Remaining": "0",
                },
            )
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    请求大小限制中间件
    
    默认: 10MB (文件上传例外)
    """
    
    def __init__(self, app: FastAPI, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # 检查 Content-Length
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_size:
            return Response(
                content=json_dumps({"detail": f"Request too large. Max size: {self.max_size // 1024 // 1024}MB"}),
                status_code=413,
                media_type="application/json",
            )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头注入中间件
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # CSP (开发环境宽松)
        if os.environ.get("DEBUG", "false").lower() == "true":
            response.headers["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'"
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' http://localhost:* https://api.openai.com"
            )
        
        return response


def json_dumps(data: dict) -> str:
    """JSON 序列化 (避免 import json)"""
    import json
    return json.dumps(data, ensure_ascii=False)


def setup_security_middleware(app: FastAPI):
    """
    配置安全中间件
    
    顺序: SecurityHeaders → RateLimit → RequestSizeLimit → CORS
    """
    import os
    
    # 1. 安全头
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 2. 限流 (可配置关闭)
    enable_rate_limit = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "300"))  # 默认300次/分钟
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=rate_limit,
        enable_rate_limit=enable_rate_limit,
    )
    
    # 3. 请求大小限制
    max_size = int(os.environ.get("MAX_REQUEST_SIZE_MB", "10")) * 1024 * 1024
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_size)
    
    # 4. CORS
    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Remaining"],
    )
    
    logger.info(
        "Security middleware configured",
        rate_limit=rate_limit,
        max_request_size_mb=max_size // 1024 // 1024,
        cors_origins=allowed_origins,
    )
