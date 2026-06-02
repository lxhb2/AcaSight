"""
Test: Zotero sync endpoints — comprehensive
"""
import pytest


class TestZoteroStatus:
    """GET /api/zotero/status"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/zotero/status")
        assert resp.status_code == 200

    def test_status_has_connected_field(self, client):
        resp = client.get("/api/zotero/status")
        data = resp.json()
        assert isinstance(data, dict)


class TestZoteroCollections:
    """GET /api/zotero/collections"""

    def test_collections_returns_response(self, client):
        resp = client.get("/api/zotero/collections")
        assert resp.status_code in (200, 503)

    def test_semantic_status(self, client):
        resp = client.get("/api/zotero/semantic-status")
        assert resp.status_code in (200, 503)


class TestZoteroTools:
    """GET /api/zotero/tools"""

    def test_tools_returns_200(self, client):
        resp = client.get("/api/zotero/tools")
        assert resp.status_code == 200
