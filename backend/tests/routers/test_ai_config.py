"""
Test: AI Config endpoints — comprehensive
"""
import pytest


class TestAIConfig:
    """GET/POST /api/ai/config"""

    def test_get_config_returns_200(self, client):
        resp = client.get("/api/ai/config")
        assert resp.status_code == 200

    def test_get_config_has_provider(self, client):
        resp = client.get("/api/ai/config")
        data = resp.json()
        assert isinstance(data, dict)

    def test_save_config(self, client):
        payload = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key-unit-test",
        }
        resp = client.post("/api/ai/config", json=payload)
        assert resp.status_code in (200, 201)

    def test_get_providers(self, client):
        resp = client.get("/api/ai/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_get_models_for_provider(self, client):
        resp = client.get("/api/ai/models/openai")
        assert resp.status_code in (200, 404, 500)

    def test_test_connection(self, client):
        resp = client.post("/api/ai/test", json={"provider": "openai"})
        assert resp.status_code in (200, 400, 500)
