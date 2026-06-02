"""
Test: Format export endpoints
"""
import pytest


class TestFormatExport:
    """导出格式相关端点"""

    def test_list_styles(self, client):
        resp = client.get("/api/format/styles")
        assert resp.status_code == 200

    def test_export_missing_body(self, client):
        resp = client.post("/api/format/export", json={})
        assert resp.status_code in (400, 422)
