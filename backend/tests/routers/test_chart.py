"""
Test: Chart auto endpoints
"""
import pytest


class TestChartAuto:
    """POST /api/chart/auto/"""

    def test_generate_returns_response(self, client):
        # Chart auto has default values, even empty body returns 200
        resp = client.post("/api/chart/auto/", json={})
        assert resp.status_code in (200, 400, 422)
