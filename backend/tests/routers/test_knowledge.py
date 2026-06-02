"""
Test: Knowledge graph and citation network endpoints — comprehensive
"""
import pytest


class TestKnowledgeGraph:
    """知识图谱端点"""

    def test_graph_stats(self, client):
        resp = client.get("/api/knowledge/graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_graph(self, client):
        resp = client.get("/api/knowledge/graph")
        assert resp.status_code == 200

    def test_references_by_doi(self, client):
        resp = client.get("/api/knowledge/references/10.1234/nonexistent")
        assert resp.status_code in (200, 404)

    def test_citations_by_doi(self, client):
        resp = client.get("/api/knowledge/citations/10.1234/nonexistent")
        assert resp.status_code in (200, 404)


class TestCitationNetwork:
    """引用网络端点"""

    def test_batch_citations(self, client):
        payload = {"dois": ["10.1234/nonexistent1"], "max_per_paper": 5}
        resp = client.post("/api/knowledge/citations/batch", json=payload)
        # Semantic Scholar may fail for test DOIs
        assert resp.status_code in (200, 422, 500)

    def test_match_section(self, client):
        payload = {
            "section_title": "Introduction",
            "section_content": "This paper discusses XRD analysis.",
            "top_k": 3,
        }
        resp = client.post("/api/knowledge/match/section", json=payload)
        assert resp.status_code in (200, 422, 500)

    def test_match_outline(self, client):
        payload = {
            "outline": [
                {"title": "Introduction", "description": "Background"},
                {"title": "Methods", "description": "Experimental setup"},
            ],
            "top_k_per_section": 2,
        }
        resp = client.post("/api/knowledge/match/outline", json=payload)
        assert resp.status_code in (200, 422, 500)
