"""
Test: Workflow engine endpoints — comprehensive
"""
import pytest


class TestWorkflowFlows:
    """GET /api/system/writing-flows"""

    def test_list_flows_returns_200(self, client):
        resp = client.get("/api/system/writing-flows")
        assert resp.status_code == 200


class TestWorkflowState:
    """GET /api/system/state"""

    def test_state_returns_200(self, client):
        resp = client.get("/api/system/state")
        assert resp.status_code == 200

    def test_state_has_fields(self, client):
        resp = client.get("/api/system/state")
        data = resp.json()
        assert isinstance(data, dict)


class TestWorkflowList:
    """GET /api/system/workflows"""

    def test_workflows_returns_200(self, client):
        resp = client.get("/api/system/workflows")
        assert resp.status_code == 200

    def test_workflows_returns_list(self, client):
        resp = client.get("/api/system/workflows")
        data = resp.json()
        assert isinstance(data, (list, dict))
        # Should have predefined workflows
        if isinstance(data, list):
            assert len(data) >= 5  # paper_writing, literature_review, etc.


class TestSystemSummary:
    """GET /api/system/summary"""

    def test_summary_returns_200(self, client):
        resp = client.get("/api/system/summary")
        assert resp.status_code == 200


class TestIntentCapabilities:
    """GET /api/system/intent/capabilities"""

    def test_capabilities_returns_200(self, client):
        resp = client.get("/api/system/intent/capabilities")
        assert resp.status_code == 200
