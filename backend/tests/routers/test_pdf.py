"""
Test: PDF endpoints
"""
import pytest


class TestPDFHash:
    """GET /api/pdf/hash"""

    def test_hash_returns_response(self, client):
        resp = client.get("/api/pdf/hash")
        # May need query params
        assert resp.status_code in (200, 400, 422)


class TestPDFProxy:
    """GET /api/pdf/proxy"""

    def test_proxy_returns_response(self, client):
        resp = client.get("/api/pdf/proxy")
        assert resp.status_code in (200, 400, 422)


class TestPDFUpload:
    """POST /api/pdf/upload"""

    def test_upload_no_file(self, client):
        resp = client.post("/api/pdf/upload")
        assert resp.status_code in (400, 422)


class TestPDFExtractText:
    """POST /api/pdf/extract-text"""

    def test_extract_missing_body(self, client):
        resp = client.post("/api/pdf/extract-text", json={})
        assert resp.status_code in (400, 422)


class TestPDFMerge:
    """POST /api/pdf/merge"""

    def test_merge_missing_body(self, client):
        resp = client.post("/api/pdf/merge", json={})
        assert resp.status_code in (400, 422)


class TestPDFSplit:
    """POST /api/pdf/split"""

    def test_split_missing_body(self, client):
        resp = client.post("/api/pdf/split", json={})
        assert resp.status_code in (400, 422)


class TestPDFRotate:
    """POST /api/pdf/rotate"""

    def test_rotate_missing_body(self, client):
        resp = client.post("/api/pdf/rotate", json={})
        assert resp.status_code in (400, 422)


class TestPDFWatermark:
    """POST /api/pdf/watermark"""

    def test_watermark_missing_body(self, client):
        resp = client.post("/api/pdf/watermark", json={})
        assert resp.status_code in (400, 422)


class TestPDFSearch:
    """POST /api/pdf/search"""

    def test_search_missing_body(self, client):
        resp = client.post("/api/pdf/search", json={})
        assert resp.status_code in (400, 422)
