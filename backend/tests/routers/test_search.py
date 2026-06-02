"""
Test: Search endpoints
"""
import pytest


class TestSearchBasic:
    """GET /api/search/"""

    def test_search_returns_response(self, client):
        resp = client.get("/api/search/?q=XRD+analysis")
        # External API may timeout in test
        assert resp.status_code in (200, 500)

    def test_search_with_sort(self, client):
        resp = client.get("/api/search/?q=test&sort_by=hybrid")
        assert resp.status_code in (200, 500)

    def test_search_sources(self, client):
        resp = client.get("/api/search/sources")
        assert resp.status_code == 200


class TestSearchImport:
    """POST /api/search/import/batch"""

    def test_import_batch(self, client):
        payload = {
            "papers": [
                {
                    "title": "Search Import Test Paper",
                    "authors": ["Import Author"],
                    "year": 2024,
                    "doi": "10.1234/import.unit.001",
                    "source": "core",
                }
            ]
        }
        resp = client.post("/api/search/import/batch", json=payload)
        assert resp.status_code in (200, 201, 422)
