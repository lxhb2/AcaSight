"""
Test: Chat endpoints (AI对话)
"""
import pytest


class TestChatProviders:
    """GET /api/chat/providers"""

    def test_providers_returns_200(self, client):
        resp = client.get("/api/chat/providers")
        assert resp.status_code == 200


class TestChatSummary:
    """POST /api/chat/summary"""

    def test_summary_missing_body(self, client):
        resp = client.post("/api/chat/summary", json={})
        assert resp.status_code in (400, 422)


class TestChatTranslate:
    """POST /api/chat/translate"""

    def test_translate_missing_body(self, client):
        resp = client.post("/api/chat/translate", json={})
        assert resp.status_code in (400, 422)


class TestChatResearchGaps:
    """POST /api/chat/research-gaps"""

    def test_research_gaps_missing_body(self, client):
        resp = client.post("/api/chat/research-gaps", json={})
        assert resp.status_code in (400, 422)
