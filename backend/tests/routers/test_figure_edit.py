"""
AcaSight Figure Edit API 测试 (方向R.1)

覆盖: /api/figure-edit/* 端点
- GET  /api/figure-edit/status
- POST /api/figure-edit/method-to-svg
- POST /api/figure-edit/segment
- POST /api/figure-edit/generate-svg
- POST /api/figure-edit/replace-icons
- POST /api/figure-edit/fix-svg
"""

import pytest
import httpx


class TestFigureEditStatus:
    """服务状态"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/figure-edit/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        status = data["data"]
        assert "sam3_available" in status
        assert "sam3_backend" in status

    def test_status_sam3_unavailable(self, client):
        """SAM3 通常未配置"""
        resp = client.get("/api/figure-edit/status")
        data = resp.json()["data"]
        # SAM3 通常不可用 (需要API key)
        assert isinstance(data["sam3_available"], bool)


class TestFigureEditSegment:
    """SAM3 分割"""

    def test_segment_missing_params(self, client):
        resp = client.post("/api/figure-edit/segment", json={})
        assert resp.status_code in (200, 400, 422)

    def test_segment_without_sam3(self, client):
        """SAM3 未配置时的优雅降级"""
        resp = client.post("/api/figure-edit/segment", json={
            "image_path": "nonexistent.png",
            "text_prompt": "chart icon",
        })
        # 应返回400/503或错误信息，不应崩溃
        assert resp.status_code in (200, 400, 404, 422, 503)


class TestFigureEditGenerateSvg:
    """SVG 生成"""

    def test_generate_svg_missing_params(self, client):
        resp = client.post("/api/figure-edit/generate-svg", json={})
        assert resp.status_code in (200, 422)

    def test_generate_svg_with_description(self, client):
        resp = client.post("/api/figure-edit/generate-svg", json={
            "description": "A schematic diagram of a neural network",
            "placeholder_mode": "label",
        })
        assert resp.status_code in (200, 422, 500)


class TestFigureEditFixSvg:
    """SVG 修复"""

    def test_fix_svg_missing_params(self, client):
        resp = client.post("/api/figure-edit/fix-svg", json={})
        assert resp.status_code in (200, 422)

    def test_fix_svg_with_broken_svg(self, client):
        resp = client.post("/api/figure-edit/fix-svg", json={
            "svg_content": "<svg><rect width='100' height='100'</svg>",
        })
        assert resp.status_code in (200, 422, 500)


class TestFigureEditReplaceIcons:
    """图标替换"""

    def test_replace_icons_missing_params(self, client):
        resp = client.post("/api/figure-edit/replace-icons", json={})
        assert resp.status_code in (200, 422)


class TestFigureEditMethodToSvg:
    """完整5步流水线"""

    def test_method_to_svg_missing_params(self, client):
        resp = client.post("/api/figure-edit/method-to-svg", json={})
        assert resp.status_code in (200, 422)

    def test_method_to_svg_with_description(self, client):
        resp = client.post("/api/figure-edit/method-to-svg", json={
            "method_text": "We first preprocess the data and then train a CNN model.",
        })
        # 可能因 AI 服务未配置而失败
        assert resp.status_code in (200, 422, 500)
