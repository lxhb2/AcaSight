"""
Test: Notes endpoints
"""
import pytest


class TestNotesList:
    """GET /api/notes/list"""

    def test_list_returns_200(self, client):
        resp = client.get("/api/notes/list")
        assert resp.status_code == 200


class TestNotesSave:
    """POST /api/notes/save"""

    def test_save_missing_body(self, client):
        resp = client.post("/api/notes/save", json={})
        assert resp.status_code in (400, 422)
