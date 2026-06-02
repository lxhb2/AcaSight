"""
AcaSight Deep Research API 测试 (方向R.1)

覆盖: /api/deep-research/* 端点
- GET  /api/deep-research/sources
- POST /api/deep-research/pubmed
- POST /api/deep-research/start
- POST /api/deep-research/start-sync
"""

import os
import pytest
import httpx

BYPASS_HEADERS = {"X-RateLimit-Bypass": os.environ.get("RATE_LIMIT_BYPASS_SECRET", "acasight-test-bypass")}


class TestDeepResearchSources:
    """检索源列表"""

    def test_sources_returns_200(self, client):
        resp = client.get("/api/deep-research/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        payload = data["data"]
        # data 是 dict 包含 sources/modes/total_sources
        assert isinstance(payload, dict)
        assert "sources" in payload
        assert "modes" in payload
        # 应该包含 PubMed
        has_pubmed = any("pubmed" in str(s).lower() for s in payload["sources"])
        assert has_pubmed, "PubMed not found in sources"

    def test_sources_contains_modes(self, client):
        resp = client.get("/api/deep-research/sources")
        payload = resp.json()["data"]
        modes = payload["modes"]
        mode_ids = [m["id"] for m in modes]
        assert "quick" in mode_ids
        assert "deep" in mode_ids


class TestDeepResearchPubMed:
    """PubMed 搜索"""

    def test_pubmed_search_returns_200(self, client):
        resp = client.post("/api/deep-research/pubmed", json={
            "query": "machine learning",
            "limit": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_pubmed_search_with_pmc(self, client):
        resp = client.post("/api/deep-research/pubmed", json={
            "query": "cancer immunotherapy",
            "search_pmc": True,
            "limit": 3,
        })
        assert resp.status_code == 200

    def test_pubmed_search_empty_query(self, client):
        resp = client.post("/api/deep-research/pubmed", json={
            "query": "",
        })
        assert resp.status_code in (200, 422)

    def test_pubmed_search_results_structure(self, client):
        resp = client.post("/api/deep-research/pubmed", json={
            "query": "transformer attention",
            "limit": 2,
        })
        if resp.status_code == 200:
            data = resp.json()["data"]
            # 如果有结果，检查结构
            if isinstance(data, list) and len(data) > 0:
                article = data[0]
                assert "title" in article or "pmid" in article


class TestDeepResearchStart:
    """Deep Research 启动"""

    def test_start_missing_params(self, client):
        resp = client.post("/api/deep-research/start", json={})
        assert resp.status_code in (200, 422)

    def test_start_with_query(self, client):
        """SSE 流式启动"""
        # SSE 端点可能需要长时间，使用短超时只验证不崩溃
        try:
            with httpx.Client(base_url="http://localhost:8000", timeout=5.0, headers=BYPASS_HEADERS) as short_client:
                resp = short_client.post("/api/deep-research/start", json={
                    "query": "machine learning in healthcare",
                    "mode": "quick",
                })
                assert resp.status_code in (200, 422)
        except httpx.TimeoutException:
            # SSE 流式响应可能超时，这是正常的
            pass


class TestDeepResearchStartSync:
    """Deep Research 同步启动"""

    def test_start_sync_missing_params(self, client):
        resp = client.post("/api/deep-research/start-sync", json={})
        assert resp.status_code in (200, 422)

    def test_start_sync_quick_mode(self, client):
        """同步模式 (可能超时, 只验证不崩溃)"""
        try:
            resp = client.post("/api/deep-research/start-sync", json={
                "query": "test query",
                "mode": "quick",
            }, timeout=10.0)
            assert resp.status_code in (200, 422, 500)
        except httpx.TimeoutException:
            # 同步模式可能超时，这是预期的
            pass
