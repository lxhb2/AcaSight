"""
漏桶速率限制器 — BabelDOC 风格

特性:
- 漏桶算法
- 线程安全（threading.Lock）
- 支持动态调整 QPS
- 使用 time.monotonic() 防止系统时间变化影响
"""

import threading
import time


class RateLimiter:
    """漏桶速率限制器"""

    def __init__(self, max_qps: int):
        if max_qps <= 0:
            raise ValueError("max_qps must be positive")
        self.max_qps = max_qps
        self.min_interval = 1.0 / max_qps
        self.lock = threading.Lock()
        self.next_request_time = time.monotonic()

    def wait(self):
        """等待直到可以发出下一个请求"""
        with self.lock:
            now = time.monotonic()
            wait_duration = self.next_request_time - now
            if wait_duration > 0:
                time.sleep(wait_duration)
            now = time.monotonic()
            self.next_request_time = max(self.next_request_time, now) + self.min_interval

    def set_max_qps(self, max_qps: int):
        """动态调整 QPS"""
        if max_qps <= 0:
            raise ValueError("max_qps must be positive")
        with self.lock:
            self.max_qps = max_qps
            self.min_interval = 1.0 / max_qps