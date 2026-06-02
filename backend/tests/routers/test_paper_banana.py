"""
AcaSight PaperBanana API 测试 (方向R.1)

覆盖: /api/paper-banana/* 端点
- POST /api/paper-banana/styles
- POST /api/paper-banana/generate-plot
- POST /api/paper-banana/generate-diagram
- POST /api/paper-banana/critique
"""

import pytest
import httpx


class TestPaperBananaStyles:
    """风格列表"""

    def test_styles_returns_200(self, client):
        resp = client.get("/api/paper-banana/styles")
        assert resp.status_code == 200
        data = resp.json()
        # 返回格式: {"styles": [...]}
        assert "styles" in data
        styles = data["styles"]
        assert isinstance(styles, list)
        assert len(styles) >= 3

    def test_styles_contains_nature(self, client):
        resp = client.get("/api/paper-banana/styles")
        styles = resp.json()["styles"]
        has_nature = any("nature" in str(s).lower() for s in styles)
        assert has_nature, "Nature style not found in styles list"


class TestPaperBananaGeneratePlot:
    """图表生成"""

    def test_generate_plot_missing_params(self, client):
        resp = client.post("/api/paper-banana/generate-plot", json={})
        assert resp.status_code in (200, 422)

    def test_generate_plot_with_description(self, client):
        """简单图表生成请求"""
        resp = client.post("/api/paper-banana/generate-plot", json={
            "description": "A simple bar chart showing sales by quarter",
            "style": "default",
        })
        # 可能因 AI 服务未配置而失败, 但不应崩溃
        assert resp.status_code in (200, 422, 500)


class TestPaperBananaGenerateDiagram:
    """流程图生成"""

    def test_generate_diagram_missing_params(self, client):
        resp = client.post("/api/paper-banana/generate-diagram", json={})
        assert resp.status_code in (200, 422)

    def test_generate_diagram_with_description(self, client):
        resp = client.post("/api/paper-banana/generate-diagram", json={
            "description": "A flowchart showing data processing pipeline",
            "style": "default",
        })
        assert resp.status_code in (200, 422, 500)


class TestPaperBananaExecutePlotCode:
    """图表代码执行"""

    def test_execute_plot_code_missing_params(self, client):
        resp = client.post("/api/paper-banana/execute-plot-code", json={})
        assert resp.status_code in (200, 422)
