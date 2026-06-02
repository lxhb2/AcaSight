"""
Test: Annotations endpoints
"""
import pytest


class TestAnnotationsStats:
    """GET /api/annotations/stats/{pdf_hash}"""

    def test_stats_returns_response(self, client):
        resp = client.get("/api/annotations/stats/00000000")
        assert resp.status_code in (200, 404)


class TestAnnotationsList:
    """GET /api/annotations"""

    def test_list_returns_200(self, client):
        resp = client.get("/api/annotations")
        assert resp.status_code == 200
