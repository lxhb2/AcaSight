"""
Test: Agent Tools API endpoints
"""
import pytest


class TestToolChatTools:
    """GET /api/agent/tool-chat/tools"""

    def test_tools_returns_200(self, client):
        resp = client.get("/api/agent/tool-chat/tools")
        assert resp.status_code == 200

    def test_tools_returns_list(self, client):
        resp = client.get("/api/agent/tool-chat/tools")
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestToolChatExecute:
    """POST /api/agent/tool-chat/execute"""

    def test_execute_missing_body(self, client):
        resp = client.post("/api/agent/tool-chat/execute", json={})
        assert resp.status_code in (400, 422)
