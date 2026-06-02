"""
Test: Literature endpoints — comprehensive
"""
import pytest


class TestLiteratureSearch:
    """GET /api/literature/search"""

    def test_search_returns_200(self, client):
        resp = client.get("/api/literature/search?q=test")
        assert resp.status_code == 200

    def test_search_with_source(self, client):
        resp = client.get("/api/literature/search?q=test&source=all")
        assert resp.status_code == 200


class TestLiteratureSources:
    """GET /api/literature/sources"""

    def test_sources_returns_200(self, client):
        resp = client.get("/api/literature/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestLiteratureStatistics:
    """GET /api/literature/statistics"""

    def test_statistics_returns_200(self, client):
        resp = client.get("/api/literature/statistics")
        assert resp.status_code == 200


class TestLiteratureInit:
    """GET /api/literature/init-status"""

    def test_init_status_returns_200(self, client):
        resp = client.get("/api/literature/init-status")
        assert resp.status_code == 200


class TestLiteratureDecompose:
    """POST /api/literature/decompose"""

    def test_decompose_missing_body(self, client):
        resp = client.post("/api/literature/decompose", json={})
        assert resp.status_code in (400, 422)


class TestLiteratureDimensionQuery:
    """GET /api/literature/query-dimension"""

    def test_query_dimension_returns_response(self, client):
        # query-dimension is a GET endpoint
        resp = client.get("/api/literature/query-dimension")
        assert resp.status_code in (200, 400, 422)
