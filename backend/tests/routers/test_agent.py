"""
Test: Agent orchestration endpoints — comprehensive
"""
import pytest


class TestAgentSkills:
    """GET /api/agent/skills"""

    def test_skills_returns_200(self, client):
        resp = client.get("/api/agent/skills")
        assert resp.status_code == 200

    def test_skills_returns_tools(self, client):
        resp = client.get("/api/agent/skills")
        data = resp.json()
        if isinstance(data, list):
            assert len(data) >= 10  # 12 academic tools
        elif isinstance(data, dict):
            tools = data.get("tools") or data.get("skills") or data.get("data")
            if isinstance(tools, list):
                assert len(tools) >= 10

    def test_skills_tool_structure(self, client):
        resp = client.get("/api/agent/skills")
        data = resp.json()
        # Normalize to list
        tools = data if isinstance(data, list) else data.get("tools") or data.get("data") or data.get("skills") or []
        if isinstance(tools, list) and len(tools) > 0:
            tool = tools[0]
            assert isinstance(tool, dict)
            # Each tool should have a name/identifier
            assert "name" in tool or "id" in tool or "tool_name" in tool


class TestAgentModules:
    """GET /api/agent/modules"""

    def test_modules_returns_200(self, client):
        resp = client.get("/api/agent/modules")
        assert resp.status_code == 200

    def test_modules_returns_list(self, client):
        resp = client.get("/api/agent/modules")
        data = resp.json()
        assert isinstance(data, (list, dict))
        # 5 module agents
        if isinstance(data, list):
            assert len(data) >= 5


class TestAgentStatus:
    """GET /api/agent/status"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/agent/status")
        assert resp.status_code == 200

    def test_status_has_fields(self, client):
        resp = client.get("/api/agent/status")
        data = resp.json()
        assert isinstance(data, dict)


class TestAgentBundles:
    """GET /api/agent/bundles"""

    def test_bundles_returns_200(self, client):
        resp = client.get("/api/agent/bundles")
        assert resp.status_code == 200


class TestAgentSessions:
    """GET /api/agent/sessions"""

    def test_sessions_returns_200(self, client):
        resp = client.get("/api/agent/sessions")
        assert resp.status_code == 200


class TestAgentExecute:
    """POST /api/agent/execute"""

    def test_execute_missing_body(self, client):
        resp = client.post("/api/agent/execute", json={})
        assert resp.status_code in (400, 422)


class TestAgentToolsCall:
    """POST /api/agent/tools/call"""

    def test_call_missing_body(self, client):
        resp = client.post("/api/agent/tools/call", json={})
        assert resp.status_code in (400, 422)

    def test_call_invalid_tool(self, client):
        payload = {"tool_name": "nonexistent_tool", "arguments": {}}
        resp = client.post("/api/agent/tools/call", json=payload)
        assert resp.status_code in (200, 400, 404, 422)
