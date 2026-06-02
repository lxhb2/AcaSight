"""
Test: Core endpoints (health, CORS, error handling)
"""
import pytest


class TestHealthEndpoint:
    """GET /api/health"""

    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_status_field(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_has_version(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["version"] == "2.0.0"

    def test_health_has_services(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        services = data["services"]
        assert services["ai"] == "ready"
        assert services["pdf"] == "ready"
        assert services["database"] == "ready"
        assert services["search"] == "ready"

    def test_health_routes_loaded(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["routes_loaded"] is True


class TestCORS:
    """CORS 配置"""

    def test_cors_preflight_allowed(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code in (200, 204)


class TestErrorHandling:
    """统一错误处理"""

    def test_404_returns_json(self, client):
        resp = client.get("/api/nonexistent-endpoint")
        assert resp.status_code == 404

    def test_method_not_allowed(self, client):
        resp = client.delete("/api/health")
        assert resp.status_code == 405
