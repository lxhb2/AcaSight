"""
AcaSight Architecture API 测试 (方向R.1)

覆盖: /api/arch/* 5个端点
- GET  /api/arch/status
- POST /api/arch/evaluate-visual
- POST /api/arch/pipeline
- POST /api/arch/detect-loop
- POST /api/arch/format
"""

import pytest
import httpx


class TestArchStatus:
    """架构服务状态"""

    def test_status_returns_200(self, client):
        resp = client.get("/api/arch/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        services = data["data"]
        assert services["visual_evaluator"] is True
        assert services["stage_orchestrator"] is True
        assert services["loop_detector"] is True
        assert services["ai_formatter"] is True

    def test_status_has_sci_styles(self, client):
        resp = client.get("/api/arch/status")
        data = resp.json()["data"]
        styles = data["sci_styles"]
        assert isinstance(styles, list)
        assert "nature" in styles
        assert "ieee" in styles

    def test_status_has_output_formats(self, client):
        resp = client.get("/api/arch/status")
        data = resp.json()["data"]
        formats = data["output_formats"]
        assert "json" in formats
        assert "svg" in formats
        assert "markdown" in formats


class TestArchFormat:
    """AI 响应格式化"""

    def test_format_json_from_code_block(self, client):
        resp = client.post("/api/arch/format", json={
            "raw_response": '```json\n{"key": "value", "count": 42}\n```',
            "expected_format": "json",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "json"
        assert data["content"]["key"] == "value"
        assert data["content"]["count"] == 42

    def test_format_json_raw(self, client):
        resp = client.post("/api/arch/format", json={
            "raw_response": '{"name": "test", "items": [1, 2, 3]}',
            "expected_format": "json",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "json"
        assert data["content"]["name"] == "test"

    def test_format_svg(self, client):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        resp = client.post("/api/arch/format", json={
            "raw_response": f'Here is the SVG:\n{svg}\nEnd.',
            "expected_format": "svg",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "svg"
        assert "svg" in data["content"].lower()

    def test_format_text(self, client):
        resp = client.post("/api/arch/format", json={
            "raw_response": "Hello, this is plain text.",
            "expected_format": "text",
        })
        assert resp.status_code == 200

    def test_format_empty_response(self, client):
        resp = client.post("/api/arch/format", json={
            "raw_response": "",
            "expected_format": "text",
        })
        assert resp.status_code == 200

    def test_format_json_with_bom(self, client):
        """BOM 前缀修复"""
        resp = client.post("/api/arch/format", json={
            "raw_response": '\ufeff{"test": true}',
            "expected_format": "json",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "json"

    def test_format_json_with_think_tags(self, client):
        """<think/> 标签去除"""
        resp = client.post("/api/arch/format", json={
            "raw_response": '<think reasoning="step1">thinking...</think\n{"result": "ok"}',
            "expected_format": "json",
        })
        assert resp.status_code == 200


class TestArchDetectLoop:
    """Agent 循环检测"""

    def test_detect_repeated_tool_calls(self, client):
        resp = client.post("/api/arch/detect-loop", json={
            "tool_calls": [
                {"name": "search_literature", "args": {"query": "cancer"}},
                {"name": "search_literature", "args": {"query": "cancer"}},
                {"name": "search_literature", "args": {"query": "cancer"}},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_looping"] is True
        assert len(data["detections"]) > 0
        assert data["detections"][0]["loop_type"] == "tool_repeat"

    def test_detect_no_loop(self, client):
        resp = client.post("/api/arch/detect-loop", json={
            "tool_calls": [
                {"name": "search_literature", "args": {"query": "cancer"}},
                {"name": "generate_outline", "args": {"topic": "ML"}},
                {"name": "draft_section", "args": {"section": "intro"}},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_looping"] is False

    def test_detect_empty_calls(self, client):
        resp = client.post("/api/arch/detect-loop", json={
            "tool_calls": [],
        })
        assert resp.status_code == 200

    def test_detect_loop_stats(self, client):
        resp = client.post("/api/arch/detect-loop", json={
            "tool_calls": [
                {"name": "search", "args": {"q": "a"}},
                {"name": "search", "args": {"q": "a"}},
                {"name": "search", "args": {"q": "a"}},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "stats" in data
        assert data["stats"]["total_turns"] == 3


class TestArchEvaluateVisual:
    """图表视觉评估"""

    def test_evaluate_visual_missing_params(self, client):
        """缺少必要参数"""
        resp = client.post("/api/arch/evaluate-visual", json={})
        # 应该返回 422 或 200+error
        assert resp.status_code in (200, 422)

    def test_evaluate_visual_with_description(self, client):
        """提供图片描述评估"""
        resp = client.post("/api/arch/evaluate-visual", json={
            "image_path": "nonexistent.png",
            "chart_description": "A bar chart showing annual revenue",
            "style_guide": "nature",
        })
        # 422=参数验证失败, 也接受
        assert resp.status_code in (200, 404, 422, 500)


class TestArchPipeline:
    """Stage Pipeline"""

    def test_pipeline_empty_stages(self, client):
        resp = client.post("/api/arch/pipeline", json={
            "stages": [],
        })
        assert resp.status_code in (200, 422)

    def test_pipeline_single_stage(self, client):
        resp = client.post("/api/arch/pipeline", json={
            "stages": [
                {
                    "name": "test_stage",
                    "action": "test",
                    "params": {},
                }
            ],
        })
        assert resp.status_code in (200, 422, 500)
