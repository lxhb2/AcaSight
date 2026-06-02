"""
慢查询分析器 — 方向Q.1 辅助工具

自动扫描所有 API 端点，测量响应时间，生成分析报告。
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger()

BASE_URL = "http://localhost:8000"

# ── 端点定义 ──

QUICK_ENDPOINTS: List[Dict[str, Any]] = [
    # 基础状态
    {"method": "GET", "path": "/api/health", "category": "health", "threshold_ms": 100},
    {"method": "GET", "path": "/api/arch/status", "category": "status", "threshold_ms": 100},
    {"method": "GET", "path": "/api/figure-edit/status", "category": "status", "threshold_ms": 100},
    {"method": "GET", "path": "/api/search/sources", "category": "status", "threshold_ms": 100},
    {"method": "GET", "path": "/api/deep-research/sources", "category": "status", "threshold_ms": 100},
    
    # 列表端点
    {"method": "GET", "path": "/api/papers/", "category": "list", "threshold_ms": 300},
    {"method": "GET", "path": "/api/workflow/list", "category": "list", "threshold_ms": 300},
    {"method": "GET", "path": "/api/agent/skills", "category": "list", "threshold_ms": 200},
    
    # 搜索端点
    {"method": "GET", "path": "/api/literature/search", "params": {"query": "test", "limit": 5}, "category": "search", "threshold_ms": 2000},
    {"method": "GET", "path": "/api/papers/dimensions/search", "params": {"query": "neural"}, "category": "search", "threshold_ms": 2000},
    
    # 格式化 (POST)
    {"method": "POST", "path": "/api/arch/format", "body": {"raw_response": '{"k":"v"}', "expected_format": "json"}, "category": "compute", "threshold_ms": 200},
    {"method": "POST", "path": "/api/arch/detect-loop", "body": {"tool_calls": [{"name": "t", "args": {}}]}, "category": "compute", "threshold_ms": 200},
    
    # Zotero (外部)
    {"method": "GET", "path": "/api/zotero/status", "category": "external", "threshold_ms": 3000},
    {"method": "GET", "path": "/api/zotero/collections", "category": "external", "threshold_ms": 5000},
]


async def scan_endpoints(
    endpoints: Optional[List[Dict]] = None,
    rounds: int = 5,
) -> Dict[str, Any]:
    """
    扫描所有端点，返回性能报告
    
    Returns:
        {
            "summary": {...},
            "slow_queries": [...],
            "fast_queries": [...],
            "by_category": {...},
            "details": [...],
        }
    """
    eps = endpoints or QUICK_ENDPOINTS
    results = []
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        for ep in eps:
            method = ep["method"]
            path = ep["path"]
            category = ep.get("category", "unknown")
            threshold = ep.get("threshold_ms", 1000)
            params = ep.get("params")
            body = ep.get("body")
            
            latencies = []
            status_ok = True
            
            for _ in range(rounds):
                start = time.time()
                try:
                    if method == "GET":
                        resp = await client.get(path, params=params)
                    elif method == "POST":
                        resp = await client.post(path, json=body, params=params)
                    else:
                        continue
                    
                    elapsed_ms = (time.time() - start) * 1000
                    latencies.append(elapsed_ms)
                    
                    if resp.status_code >= 400:
                        status_ok = False
                        
                except Exception as e:
                    latencies.append(-1)
                    status_ok = False
                    logger.warning("Endpoint scan failed", path=path, error=str(e))
            
            # 统计
            valid = [l for l in latencies if l > 0]
            if valid:
                avg = sum(valid) / len(valid)
                p50 = sorted(valid)[len(valid) // 2]
                p95 = sorted(valid)[int(len(valid) * 0.95)] if len(valid) > 1 else valid[0]
                max_val = max(valid)
                min_val = min(valid)
            else:
                avg = p50 = p95 = max_val = min_val = -1
            
            is_slow = avg > threshold if avg > 0 else False
            
            results.append({
                "method": method,
                "path": path,
                "category": category,
                "threshold_ms": threshold,
                "avg_ms": round(avg, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "min_ms": round(min_val, 1),
                "max_ms": round(max_val, 1),
                "is_slow": is_slow,
                "status_ok": status_ok,
                "rounds": len(valid),
            })
    
    # 分析
    slow_queries = [r for r in results if r["is_slow"]]
    fast_queries = [r for r in results if not r["is_slow"] and r["avg_ms"] > 0]
    
    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "avg_ms": 0, "max_ms": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["avg_ms"] = round(
            (by_category[cat]["avg_ms"] * (by_category[cat]["count"] - 1) + max(r["avg_ms"], 0)) / by_category[cat]["count"], 1
        )
        by_category[cat]["max_ms"] = max(by_category[cat]["max_ms"], r["max_ms"])
    
    return {
        "summary": {
            "total_endpoints": len(results),
            "slow_count": len(slow_queries),
            "fast_count": len(fast_queries),
            "error_count": len([r for r in results if not r["status_ok"]]),
            "overall_avg_ms": round(sum(r["avg_ms"] for r in results if r["avg_ms"] > 0) / max(len([r for r in results if r["avg_ms"] > 0]), 1), 1),
        },
        "slow_queries": sorted(slow_queries, key=lambda x: -x["avg_ms"]),
        "fast_queries": sorted(fast_queries, key=lambda x: x["avg_ms"]),
        "by_category": by_category,
        "details": results,
    }


def format_report(report: Dict[str, Any]) -> str:
    """格式化报告为可读文本"""
    lines = []
    lines.append("=" * 70)
    lines.append("AcaSight 后端性能基准报告")
    lines.append("=" * 70)
    
    summary = report["summary"]
    lines.append(f"\n📊 总览: {summary['total_endpoints']} 端点 | "
                 f"慢查询: {summary['slow_count']} | "
                 f"快查询: {summary['fast_count']} | "
                 f"错误: {summary['error_count']}")
    lines.append(f"   全局平均响应时间: {summary['overall_avg_ms']}ms")
    
    # 慢查询
    if report["slow_queries"]:
        lines.append(f"\n🐌 慢查询 (超过阈值):")
        for sq in report["slow_queries"]:
            lines.append(f"   {sq['method']:4s} {sq['path']:40s} "
                        f"avg={sq['avg_ms']:7.1f}ms p95={sq['p95_ms']:7.1f}ms "
                        f"(阈值={sq['threshold_ms']}ms) [{sq['category']}]")
    
    # 快查询 Top 5
    lines.append(f"\n⚡ 最快端点 Top 5:")
    for fq in report["fast_queries"][:5]:
        lines.append(f"   {fq['method']:4s} {fq['path']:40s} "
                    f"avg={fq['avg_ms']:7.1f}ms p95={fq['p95_ms']:7.1f}ms [{fq['category']}]")
    
    # 按类别
    lines.append(f"\n📂 按类别:")
    for cat, data in sorted(report["by_category"].items()):
        lines.append(f"   {cat:12s}: {data['count']} 端点, avg={data['avg_ms']}ms, max={data['max_ms']}ms")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    report = asyncio.run(scan_endpoints())
    print(format_report(report))
    
    # 保存 JSON
    with open("benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("\n报告已保存至 benchmark_report.json")
