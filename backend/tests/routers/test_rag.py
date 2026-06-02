"""
Test: RAG endpoints
"""
import pytest


class TestRAGStatus:
    """GET /api/rag/status"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/rag/status")
        assert resp.status_code == 200

    def test_status_has_available_field(self, client):
        resp = client.get("/api/rag/status")
        data = resp.json()
        assert "available" in data


class TestRAGQuery:
    """POST /api/rag/query"""

    def test_query_returns_response(self, client):
        payload = {"question": "What is XRD?"}
        resp = client.post("/api/rag/query", json=payload)
        # RAG unavailable returns fallback
        assert resp.status_code in (200, 503)
