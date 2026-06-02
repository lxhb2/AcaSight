"""
AcaSight 后端性能基准测试 (方向Q.1)

使用 pytest-benchmark 对关键 API 端点进行性能基准测试。
测试目标:
1. 响应时间基准 (P50/P95/P99)
2. 慢查询识别 (>500ms)
3. 吞吐量基准 (RPS)
4. 内存敏感端点 (PDF/搜索/AI)

运行方式:
  pytest tests/bench/ -v --benchmark-only
  pytest tests/bench/ -v --benchmark-only --benchmark-sort=mean
"""

import json
import os
import time
from typing import Dict

import httpx
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
RATE_LIMIT_BYPASS_SECRET = os.environ.get("RATE_LIMIT_BYPASS_SECRET", "acasight-test-bypass")


@pytest.fixture(scope="module")
def bench_client():
    """性能测试用 httpx 客户端 (较长超时)"""
    headers = {"X-RateLimit-Bypass": RATE_LIMIT_BYPASS_SECRET}
    with httpx.Client(base_url=BASE_URL, timeout=60.0, headers=headers) as c:
        yield c


@pytest.fixture(scope="module")
def sample_paper_id(bench_client) -> str:
    """获取一个可用的 paper ID"""
    resp = bench_client.get("/api/papers/", params={"page": 1, "page_size": 1})
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        if isinstance(items, list) and items:
            return items[0].get("id", "test-paper-1")
    return "test-paper-1"


# ── 1. 基础端点基准 ──

class TestHealthBenchmark:
    """健康检查端点基准"""

    def test_health_endpoint(self, bench_client, benchmark):
        """GET /api/health — 最基础端点"""
        result = benchmark(bench_client.get, "/api/health")
        assert result.status_code == 200

    def test_arch_status(self, bench_client, benchmark):
        """GET /api/arch/status — 架构服务状态"""
        result = benchmark(bench_client.get, "/api/arch/status")
        assert result.status_code == 200

    def test_figure_edit_status(self, bench_client, benchmark):
        """GET /api/figure-edit/status — SVG编辑状态"""
        result = benchmark(bench_client.get, "/api/figure-edit/status")
        assert result.status_code == 200

    def test_search_sources(self, bench_client, benchmark):
        """GET /api/search/sources — 搜索源列表"""
        result = benchmark(bench_client.get, "/api/search/sources")
        assert result.status_code == 200

    def test_deep_research_sources(self, bench_client, benchmark):
        """GET /api/deep-research/sources — 检索源列表"""
        result = benchmark(bench_client.get, "/api/deep-research/sources")
        assert result.status_code == 200


# ── 2. 文献检索基准 ──

class TestSearchBenchmark:
    """搜索端点基准"""

    def test_papers_list(self, bench_client, benchmark):
        """GET /api/papers/ — 论文列表 (分页)"""
        result = benchmark(
            bench_client.get, "/api/papers/",
            params={"page": 1, "page_size": 20},
        )
        assert result.status_code in (200, 404)

    def test_literature_search(self, bench_client, benchmark):
        """GET /api/literature/search — 文献搜索"""
        result = benchmark(
            bench_client.get, "/api/literature/search",
            params={"query": "machine learning", "limit": 10},
        )
        assert result.status_code in (200, 404, 422)

    def test_papers_dimensions(self, bench_client, benchmark):
        """GET /api/papers/dimensions/search — 维度搜索"""
        result = benchmark(
            bench_client.get, "/api/papers/dimensions/search",
            params={"query": "neural network"},
        )
        assert result.status_code in (200, 404, 422)


# ── 3. CRUD 端点基准 ──

class TestCRUDBenchmark:
    """CRUD 操作基准"""

    def test_create_and_delete_paper(self, bench_client, benchmark):
        """POST + DELETE /api/papers/ — 论文创建+删除"""
        def _create_delete():
            create_resp = bench_client.post(
                "/api/papers/",
                json={
                    "title": "Benchmark Test Paper",
                    "authors": ["Test Author"],
                    "year": 2026,
                    "abstract": "Performance benchmark test",
                    "source": "benchmark",
                },
            )
            if create_resp.status_code == 200:
                data = create_resp.json()
                paper_id = data.get("id") if isinstance(data, dict) else None
                if paper_id:
                    bench_client.delete(f"/api/papers/{paper_id}")
            return create_resp.status_code

        # benchmark 不支持有副作用的操作直接跑，只测一次时间
        # 改用 manual timing
        start = time.time()
        for _ in range(10):
            _create_delete()
        elapsed = time.time() - start
        avg_ms = (elapsed / 10) * 1000

        # 记录到 benchmark
        benchmark.extra_info["avg_create_delete_ms"] = round(avg_ms, 1)
        assert avg_ms < 5000, f"Create+Delete avg {avg_ms:.0f}ms too slow (>5000ms)"


# ── 4. 工作流基准 ──

class TestWorkflowBenchmark:
    """工作流端点基准"""

    def test_list_workflows(self, bench_client, benchmark):
        """GET /api/workflow/list — 工作流列表"""
        result = benchmark(bench_client.get, "/api/workflow/list")
        assert result.status_code in (200, 404)

    def test_writing_status(self, bench_client, benchmark):
        """GET /api/writing/status — 写作状态"""
        result = benchmark(bench_client.get, "/api/writing/status")
        assert result.status_code in (200, 404, 422)


# ── 5. Zotero 同步基准 ──

class TestZoteroBenchmark:
    """Zotero 端点基准"""

    def test_zotero_status(self, bench_client, benchmark):
        """GET /api/zotero/status — Zotero 连接状态"""
        result = benchmark(bench_client.get, "/api/zotero/status")
        assert result.status_code in (200, 404, 503)

    def test_zotero_collections(self, bench_client, benchmark):
        """GET /api/zotero/collections — Zotero 集合"""
        result = benchmark(bench_client.get, "/api/zotero/collections")
        assert result.status_code in (200, 404, 503)


# ── 6. AI 响应格式化基准 ──

class TestFormatterBenchmark:
    """AI 格式化服务基准"""

    def test_format_json(self, bench_client, benchmark):
        """POST /api/arch/format — JSON 提取"""
        result = benchmark(
            bench_client.post,
            "/api/arch/format",
            json={
                "raw_response": '```json\n{"key": "value", "count": 42, "items": [1, 2, 3]}\n```',
                "expected_format": "json",
            },
        )
        assert result.status_code == 200

    def test_format_svg(self, bench_client, benchmark):
        """POST /api/arch/format — SVG 提取"""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        result = benchmark(
            bench_client.post,
            "/api/arch/format",
            json={
                "raw_response": f'Here is the SVG:\n{svg_content}\nEnd.',
                "expected_format": "svg",
            },
        )
        assert result.status_code == 200

    def test_detect_loop(self, bench_client, benchmark):
        """POST /api/arch/detect-loop — 循环检测"""
        tool_calls = [
            {"name": "search", "args": {"query": "test"}},
            {"name": "search", "args": {"query": "test"}},
            {"name": "search", "args": {"query": "test"}},
        ]
        result = benchmark(
            bench_client.post,
            "/api/arch/detect-loop",
            json={"tool_calls": tool_calls},
        )
        assert result.status_code == 200


# ── 7. 慢查询阈值测试 ──

class TestSlowQueryThreshold:
    """
    慢查询阈值测试 — 标识响应时间超过阈值的端点
    
    阈值:
    - 基础 GET: <100ms
    - 搜索类: <2000ms (外部API)
    - 写入类: <500ms
    """

    SLOW_THRESHOLD_MS = {
        "health": 100,
        "status": 100,
        "list": 200,
        "search": 2000,
        "create": 500,
        "format": 200,
    }

    @pytest.mark.parametrize("endpoint,expected_max_ms", [
        ("/api/health", 100),
        ("/api/arch/status", 100),
        ("/api/figure-edit/status", 100),
        ("/api/search/sources", 100),
        ("/api/deep-research/sources", 100),
        ("/api/workflow/list", 200),
        ("/api/zotero/status", 200),
    ])
    def test_endpoint_latency(self, bench_client, endpoint, expected_max_ms):
        """验证端点响应时间在阈值内"""
        # 预热
        bench_client.get(endpoint)

        # 5次测量
        latencies = []
        for _ in range(5):
            start = time.time()
            resp = bench_client.get(endpoint)
            elapsed_ms = (time.time() - start) * 1000
            latencies.append(elapsed_ms)

        avg_ms = sum(latencies) / len(latencies)
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]

        assert avg_ms < expected_max_ms, (
            f"{endpoint} avg latency {avg_ms:.0f}ms exceeds {expected_max_ms}ms threshold "
            f"(p95={p95_ms:.0f}ms)"
        )


# ── 8. 并发吞吐量基准 ──

class TestConcurrencyBenchmark:
    """并发吞吐量测试"""

    def test_concurrent_health_checks(self, bench_client, benchmark):
        """并发健康检查 (模拟多用户)"""
        import concurrent.futures

        def _hit():
            return bench_client.get("/api/health")

        def _concurrent_batch():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(_hit) for _ in range(50)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            return results

        results = benchmark(_concurrent_batch)
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_format_requests(self, bench_client, benchmark):
        """并发格式化请求"""
        import concurrent.futures

        def _format():
            return bench_client.post(
                "/api/arch/format",
                json={
                    "raw_response": '{"test": true}',
                    "expected_format": "json",
                },
            )

        def _concurrent_batch():
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_format) for _ in range(20)]
                return [f.result() for f in concurrent.futures.as_completed(futures)]

        results = benchmark(_concurrent_batch)
        assert all(r.status_code == 200 for r in results)
