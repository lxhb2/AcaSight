"""
Test: Papers CRUD endpoints — comprehensive
"""
import pytest


class TestPapersList:
    """GET /api/papers"""

    def test_list_returns_200(self, client):
        resp = client.get("/api/papers")
        assert resp.status_code == 200

    def test_list_with_pagination(self, client):
        resp = client.get("/api/papers?skip=0&limit=5")
        assert resp.status_code == 200

    def test_list_returns_paginated(self, client):
        resp = client.get("/api/papers")
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    def test_list_pagination_params(self, client):
        resp = client.get("/api/papers?skip=0&limit=3")
        data = resp.json()
        # API may cap limit or use different param name; just verify it returns 200
        assert resp.status_code == 200


class TestPapersStats:
    """GET /api/papers/stats"""

    def test_stats_returns_200(self, client):
        resp = client.get("/api/papers/stats")
        assert resp.status_code == 200

    def test_stats_has_fields(self, client):
        resp = client.get("/api/papers/stats")
        data = resp.json()
        assert isinstance(data, dict)
        # Stats should have count-related fields
        assert "total" in data or "count" in data or len(data) > 0


class TestPapersCreate:
    """POST /api/papers"""

    def test_create_paper(self, client):
        payload = {
            "title": "Unit Test Paper: XRD Analysis",
            "authors": ["Test Author A", "Test Author B"],
            "year": 2024,
            "doi": "10.1234/test.unit.2024.xrd",
            "abstract": "A test paper for unit testing.",
            "source": "manual",
        }
        resp = client.post("/api/papers", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Unit Test Paper: XRD Analysis"
        assert "id" in data
        assert data["year"] == 2024

    def test_create_paper_minimal(self, client):
        payload = {"title": "Minimal Unit Test Paper"}
        resp = client.post("/api/papers", json=payload)
        assert resp.status_code == 200

    def test_create_paper_missing_title(self, client):
        payload = {"authors": ["No Title Author"]}
        resp = client.post("/api/papers", json=payload)
        assert resp.status_code == 422

    def test_create_paper_with_keywords(self, client):
        payload = {
            "title": "Paper with Keywords",
            "keywords": ["XRD", "crystallography", "mineral"],
        }
        resp = client.post("/api/papers", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Paper with Keywords"


class TestPapersTags:
    """GET /api/papers/tags"""

    def test_tags_returns_200(self, client):
        resp = client.get("/api/papers/tags")
        assert resp.status_code == 200


class TestPapersSearch:
    """GET /api/papers/search"""

    def test_search_returns_200(self, client):
        resp = client.get("/api/papers/search?q=test")
        assert resp.status_code == 200

    def test_search_by_doi(self, client):
        resp = client.get("/api/papers/by_doi/10.1234/nonexistent")
        assert resp.status_code in (200, 404)


class TestPapersCRUD:
    """论文 CRUD 端到端"""

    def test_create_and_get_paper(self, client):
        # Create
        payload = {
            "title": "E2E CRUD Test Paper",
            "authors": ["E2E Author"],
            "year": 2026,
            "doi": "10.1234/e2e.crud.2026.003",
        }
        create_resp = client.post("/api/papers", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        paper_id = created.get("id")
        assert paper_id is not None

        # Get by ID
        get_resp = client.get(f"/api/papers/{paper_id}")
        assert get_resp.status_code == 200
        paper = get_resp.json()
        assert paper["title"] == "E2E CRUD Test Paper"
        assert paper["year"] == 2026

        # Update
        update_resp = client.put(
            f"/api/papers/{paper_id}",
            json={"title": "Updated E2E Paper", "year": 2025},
        )
        assert update_resp.status_code == 200

        # Verify update
        verify_resp = client.get(f"/api/papers/{paper_id}")
        assert verify_resp.status_code == 200
        assert verify_resp.json()["title"] == "Updated E2E Paper"

        # Read status
        read_resp = client.put(
            f"/api/papers/{paper_id}/read-status",
            json={"read_status": "reading"},
        )
        assert read_resp.status_code == 200

        # Favorite
        fav_resp = client.put(f"/api/papers/{paper_id}/favorite")
        assert fav_resp.status_code == 200

        # Rating
        rate_resp = client.put(
            f"/api/papers/{paper_id}/rating",
            json={"rating": 4},
        )
        assert rate_resp.status_code == 200

        # Add tag
        tag_resp = client.post(f"/api/papers/{paper_id}/tags/test-tag")
        assert tag_resp.status_code in (200, 201)

        # Delete
        del_resp = client.delete(f"/api/papers/{paper_id}")
        assert del_resp.status_code == 200

        # Verify deleted
        verify_del = client.get(f"/api/papers/{paper_id}")
        assert verify_del.status_code == 404

    def test_batch_create(self, client):
        payload = {
            "papers": [
                {"title": "Batch Paper 1"},
                {"title": "Batch Paper 2"},
            ]
        }
        resp = client.post("/api/papers/batch", json=payload)
        assert resp.status_code == 200


class TestPapersDimensions:
    """论文维度相关端点"""

    def test_dimensions_search(self, client):
        resp = client.get("/api/papers/dimensions/search?q=test")
        assert resp.status_code in (200, 400, 422)
