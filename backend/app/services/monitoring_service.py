"""
性能监控服务 (方向V.3)

功能:
1. 系统资源监控 (CPU/内存/磁盘)
2. API请求指标收集 (延迟/状态码/端点)
3. 健康度评分算法
4. 指标快照与查询
5. Web Vitals 前端指标收集
"""

import os
import time
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RequestMetric:
    """单次请求指标"""
    timestamp: float
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: str = ""


@dataclass
class WebVitalMetric:
    """前端 Web Vitals 指标"""
    timestamp: float
    metric_name: str  # LCP / FID / CLS / TTFB / INP
    value: float
    url: str = ""
    user_agent: str = ""


@dataclass
class SystemSnapshot:
    """系统资源快照"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    open_files: int = 0
    thread_count: int = 0


@dataclass
class HealthScore:
    """健康度评分"""
    overall: float  # 0-100
    api_latency: float  # 0-100
    error_rate: float  # 0-100
    resource_usage: float  # 0-100
    details: Dict[str, Any] = field(default_factory=dict)


class MonitoringService:
    """性能监控服务"""

    def __init__(self, max_request_metrics: int = 10000, max_web_vitals: int = 5000):
        self._request_metrics: deque[RequestMetric] = deque(maxlen=max_request_metrics)
        self._web_vitals: deque[WebVitalMetric] = deque(maxlen=max_web_vitals)
        self._system_snapshots: deque[SystemSnapshot] = deque(maxlen=1440)  # 24h @ 1/min
        self._start_time = time.time()
        self._lock = threading.Lock()
        self._monitoring_enabled = os.environ.get("MONITORING_ENABLED", "true").lower() == "true"

        # 采集间隔
        self._collect_interval = int(os.environ.get("MONITORING_INTERVAL_SEC", "60"))

        # 尝试导入 psutil
        self._psutil_available = False
        try:
            import psutil  # noqa: F401
            self._psutil_available = True
        except ImportError:
            logger.warning("psutil not available, system metrics will be limited")

        # 启动后台采集
        if self._monitoring_enabled:
            self._start_background_collector()

    def _start_background_collector(self):
        """启动后台系统指标采集线程"""
        def _collect_loop():
            while True:
                try:
                    snapshot = self._collect_system_snapshot()
                    with self._lock:
                        self._system_snapshots.append(snapshot)
                except Exception as e:
                    logger.warning("System snapshot failed", error=str(e))
                time.sleep(self._collect_interval)

        thread = threading.Thread(target=_collect_loop, daemon=True, name="monitoring-collector")
        thread.start()
        logger.info("Monitoring background collector started", interval_sec=self._collect_interval)

    def _collect_system_snapshot(self) -> SystemSnapshot:
        """采集系统资源快照"""
        snapshot = SystemSnapshot(
            timestamp=time.time(),
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=0.0,
            thread_count=threading.active_count(),
        )

        if self._psutil_available:
            try:
                import psutil
                process = psutil.Process(os.getpid())

                snapshot.cpu_percent = process.cpu_percent(interval=0.1)
                mem_info = process.memory_info()
                snapshot.memory_used_mb = mem_info.rss / (1024 * 1024)

                sys_mem = psutil.virtual_memory()
                snapshot.memory_total_mb = sys_mem.total / (1024 * 1024)
                snapshot.memory_percent = sys_mem.percent

                disk = psutil.disk_usage("/")
                snapshot.disk_percent = disk.percent
                snapshot.disk_used_gb = disk.used / (1024 ** 3)
                snapshot.disk_total_gb = disk.total / (1024 ** 3)

                try:
                    snapshot.open_files = len(process.open_files())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except Exception as e:
                logger.warning("psutil collection failed", error=str(e))
        else:
            # 基础回退
            import resource as res_module
            try:
                snapshot.memory_used_mb = res_module.getrusage(res_module.RUSAGE_SELF).ru_maxrss / 1024
            except Exception:
                pass

        return snapshot

    def record_request(self, method: str, path: str, status_code: int,
                       duration_ms: float, client_ip: str = "") -> None:
        """记录API请求指标"""
        if not self._monitoring_enabled:
            return
        metric = RequestMetric(
            timestamp=time.time(),
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )
        with self._lock:
            self._request_metrics.append(metric)

    def record_web_vital(self, metric_name: str, value: float,
                         url: str = "", user_agent: str = "") -> None:
        """记录前端 Web Vitals 指标"""
        if not self._monitoring_enabled:
            return
        valid_names = {"LCP", "FID", "CLS", "TTFB", "INP", "FCP", "TBT"}
        if metric_name.upper() not in valid_names:
            logger.warning("Unknown web vital", name=metric_name)
            return
        vital = WebVitalMetric(
            timestamp=time.time(),
            metric_name=metric_name.upper(),
            value=value,
            url=url,
            user_agent=user_agent,
        )
        with self._lock:
            self._web_vitals.append(vital)

    def get_request_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取API请求统计"""
        cutoff = time.time() - minutes * 60
        with self._lock:
            recent = [m for m in self._request_metrics if m.timestamp >= cutoff]

        if not recent:
            return {"total_requests": 0, "period_minutes": minutes}

        durations = [m.duration_ms for m in recent]
        errors = [m for m in recent if m.status_code >= 400]

        # 按端点分组
        by_path: Dict[str, List[RequestMetric]] = {}
        for m in recent:
            by_path.setdefault(m.path, []).append(m)

        endpoint_stats = {}
        for path, metrics in by_path.items():
            durs = [m.duration_ms for m in metrics]
            errs = [m for m in metrics if m.status_code >= 400]
            endpoint_stats[path] = {
                "count": len(metrics),
                "avg_ms": sum(durs) / len(durs),
                "p50_ms": sorted(durs)[len(durs) // 2],
                "p99_ms": sorted(durs)[min(int(len(durs) * 0.99), len(durs) - 1)],
                "max_ms": max(durs),
                "error_count": len(errs),
            }

        # 按状态码分组
        by_status: Dict[int, int] = {}
        for m in recent:
            by_status[m.status_code] = by_status.get(m.status_code, 0) + 1

        return {
            "total_requests": len(recent),
            "period_minutes": minutes,
            "error_count": len(errors),
            "error_rate": len(errors) / len(recent),
            "avg_latency_ms": sum(durations) / len(durations),
            "p50_latency_ms": sorted(durations)[len(durations) // 2],
            "p99_latency_ms": sorted(durations)[min(int(len(durations) * 0.99), len(durations) - 1)],
            "by_status": by_status,
            "by_endpoint": endpoint_stats,
        }

    def get_web_vitals_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取Web Vitals统计"""
        cutoff = time.time() - minutes * 60
        with self._lock:
            recent = [v for v in self._web_vitals if v.timestamp >= cutoff]

        if not recent:
            return {"total_reports": 0, "period_minutes": minutes}

        by_name: Dict[str, List[WebVitalMetric]] = {}
        for v in recent:
            by_name.setdefault(v.metric_name, []).append(v)

        vital_stats = {}
        for name, metrics in by_name.items():
            values = [m.value for m in metrics]
            vital_stats[name] = {
                "count": len(metrics),
                "avg": sum(values) / len(values),
                "p50": sorted(values)[len(values) // 2],
                "p75": sorted(values)[min(int(len(values) * 0.75), len(values) - 1)],
                "p99": sorted(values)[min(int(len(values) * 0.99), len(values) - 1)],
                "worst": max(values),
            }

        return {"total_reports": len(recent), "period_minutes": minutes, "metrics": vital_stats}

    def get_system_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取系统资源统计"""
        cutoff = time.time() - minutes * 60
        with self._lock:
            recent = [s for s in self._system_snapshots if s.timestamp >= cutoff]

        if not recent:
            # 返回最新快照
            with self._lock:
                if self._system_snapshots:
                    latest = self._system_snapshots[-1]
                    return {"current": asdict(latest), "period_minutes": minutes}
            return {"current": None, "period_minutes": minutes}

        cpu_values = [s.cpu_percent for s in recent]
        mem_values = [s.memory_percent for s in recent]

        latest = recent[-1]
        return {
            "current": asdict(latest),
            "period_minutes": minutes,
            "avg_cpu": sum(cpu_values) / len(cpu_values),
            "peak_cpu": max(cpu_values),
            "avg_memory_percent": sum(mem_values) / len(mem_values),
            "peak_memory_percent": max(mem_values),
        }

    def calculate_health_score(self) -> HealthScore:
        """计算系统健康度评分"""
        # API延迟评分 (P99 < 200ms = 100, > 5s = 0)
        api_score = 100.0
        request_stats = self.get_request_stats(5)  # 最近5分钟
        if request_stats.get("total_requests", 0) > 0:
            p99 = request_stats.get("p99_latency_ms", 0)
            if p99 <= 200:
                api_score = 100
            elif p99 <= 500:
                api_score = 100 - (p99 - 200) / 300 * 20  # 80-100
            elif p99 <= 2000:
                api_score = 80 - (p99 - 500) / 1500 * 40  # 40-80
            elif p99 <= 5000:
                api_score = 40 - (p99 - 2000) / 3000 * 30  # 10-40
            else:
                api_score = max(0, 10 - (p99 - 5000) / 5000 * 10)

        # 错误率评分 (<1% = 100, >10% = 0)
        error_score = 100.0
        error_rate = request_stats.get("error_rate", 0)
        if error_rate <= 0.01:
            error_score = 100
        elif error_rate <= 0.05:
            error_score = 100 - (error_rate - 0.01) / 0.04 * 30
        elif error_rate <= 0.10:
            error_score = 70 - (error_rate - 0.05) / 0.05 * 40
        else:
            error_score = max(0, 30 - (error_rate - 0.10) / 0.90 * 30)

        # 资源使用评分 (<60% = 100, >90% = 0)
        resource_score = 100.0
        with self._lock:
            if self._system_snapshots:
                latest = self._system_snapshots[-1]
                mem = latest.memory_percent
                cpu = latest.cpu_percent
                usage = max(mem, cpu)
                if usage <= 60:
                    resource_score = 100
                elif usage <= 80:
                    resource_score = 100 - (usage - 60) / 20 * 30
                elif usage <= 90:
                    resource_score = 70 - (usage - 80) / 10 * 40
                else:
                    resource_score = max(0, 30 - (usage - 90) / 10 * 30)

        # 综合评分 (加权平均)
        overall = api_score * 0.35 + error_score * 0.35 + resource_score * 0.30

        return HealthScore(
            overall=round(overall, 1),
            api_latency=round(api_score, 1),
            error_rate=round(error_score, 1),
            resource_usage=round(resource_score, 1),
            details={
                "uptime_seconds": round(time.time() - self._start_time),
                "total_requests": len(self._request_metrics),
                "total_web_vitals": len(self._web_vitals),
                "psutil_available": self._psutil_available,
                "monitoring_enabled": self._monitoring_enabled,
            },
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘完整数据"""
        health = self.calculate_health_score()
        return {
            "health": asdict(health),
            "requests": self.get_request_stats(60),
            "system": self.get_system_stats(60),
            "web_vitals": self.get_web_vitals_stats(60),
            "slowest_endpoints": self._get_slowest_endpoints(5),
            "top_errors": self._get_top_errors(5),
        }

    def _get_slowest_endpoints(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最慢的端点"""
        stats = self.get_request_stats(60)
        by_endpoint = stats.get("by_endpoint", {})
        if not by_endpoint:
            return []
        sorted_endpoints = sorted(by_endpoint.items(), key=lambda x: x[1]["p99_ms"], reverse=True)
        return [
            {"path": path, **ep_stats}
            for path, ep_stats in sorted_endpoints[:limit]
        ]

    def _get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取错误最多的端点"""
        cutoff = time.time() - 3600
        with self._lock:
            recent = [m for m in self._request_metrics if m.timestamp >= cutoff and m.status_code >= 400]

        error_counts: Dict[str, int] = {}
        for m in recent:
            key = f"{m.method} {m.path} → {m.status_code}"
            error_counts[key] = error_counts.get(key, 0) + 1

        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"error": err, "count": count} for err, count in sorted_errors[:limit]]


# ── 全局单例 ──

_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
