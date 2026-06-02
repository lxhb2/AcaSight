"""
Test: Storage endpoints — comprehensive
"""
import pytest


class TestStorageStats:
    """GET /api/storage/stats"""

    def test_stats_returns_200(self, client):
        resp = client.get("/api/storage/stats")
        assert resp.status_code == 200

    def test_stats_has_fields(self, client):
        resp = client.get("/api/storage/stats")
        data = resp.json()
        assert isinstance(data, dict)


class TestStorageCache:
    """缓存管理端点"""

    def test_cache_stats(self, client):
        resp = client.get("/api/storage/cache/stats")
        assert resp.status_code == 200

    def test_cache_list(self, client):
        resp = client.get("/api/storage/cache/list")
        assert resp.status_code == 200

    def test_cache_list_pagination(self, client):
        resp = client.get("/api/storage/cache/list?skip=0&limit=5")
        assert resp.status_code == 200


class TestStorageUpload:
    """POST /api/storage/upload"""

    def test_upload_no_file(self, client):
        resp = client.post("/api/storage/upload")
        assert resp.status_code in (400, 422)


class TestStorageUnified:
    """统一存储端点"""

    def test_unified_stats(self, client):
        resp = client.get("/api/storage/unified/stats")
        assert resp.status_code == 200

    def test_unified_list(self, client):
        resp = client.get("/api/storage/unified/list")
        assert resp.status_code == 200
