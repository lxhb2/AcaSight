"""
Test: Template endpoints
"""
import pytest


class TestTemplates:
    """GET /api/templates"""

    def test_list_returns_200(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
