"""
Test: Writing endpoints — comprehensive
"""
import pytest


class TestWritingTemplates:
    """GET /api/writing/templates"""

    def test_templates_returns_200(self, client):
        resp = client.get("/api/writing/templates")
        assert resp.status_code == 200

    def test_templates_returns_structure(self, client):
        resp = client.get("/api/writing/templates")
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestResearchDirection:
    """POST /api/writing/research-direction"""

    def test_missing_body(self, client):
        resp = client.post("/api/writing/research-direction", json={})
        assert resp.status_code in (400, 422)


class TestExperimentDesign:
    """POST /api/writing/experiment-design"""

    def test_missing_body(self, client):
        resp = client.post("/api/writing/experiment-design", json={})
        assert resp.status_code in (400, 422)


class TestPolish:
    """POST /api/writing/polish"""

    def test_missing_body(self, client):
        resp = client.post("/api/writing/polish", json={})
        assert resp.status_code in (400, 422)


class TestGenerateAbstract:
    """POST /api/writing/generate-abstract"""

    def test_missing_body(self, client):
        resp = client.post("/api/writing/generate-abstract", json={})
        assert resp.status_code in (400, 422)


class TestWorkspaceCreate:
    """POST /api/writing/workspace/create"""

    def test_create_missing_body(self, client):
        resp = client.post("/api/writing/workspace/create", json={})
        assert resp.status_code in (200, 400, 422)


class TestDownloadPPT:
    """GET /api/writing/download-ppt"""

    def test_download_no_params(self, client):
        resp = client.get("/api/writing/download-ppt")
        assert resp.status_code in (200, 400, 404, 422)
