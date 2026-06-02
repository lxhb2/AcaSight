"""
Test: Sync endpoints
"""
import pytest


class TestSyncStatus:
    """GET /api/sync/status"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/sync/status")
        assert resp.status_code == 200


class TestSyncCollections:
    """GET /api/sync/collections"""

    def test_collections_returns_200(self, client):
        resp = client.get("/api/sync/collections")
        assert resp.status_code == 200


class TestSyncScan:
    """GET /api/sync/scan"""

    def test_scan_returns_200(self, client):
        resp = client.get("/api/sync/scan")
        assert resp.status_code == 200


class TestSyncImport:
    """POST /api/sync/import"""

    def test_import_missing_body(self, client):
        resp = client.post("/api/sync/import", json={})
        assert resp.status_code in (200, 400, 422)
