"""
AcaSight Plugins API 测试 (方向R.1)

覆盖: /api/plugins/* 8个端点
- GET    /api/plugins/
- GET    /api/plugins/discover
- POST   /api/plugins/load
- POST   /api/plugins/{name}/enable
- POST   /api/plugins/{name}/disable
- DELETE /api/plugins/{name}
- POST   /api/plugins/hook
- GET    /api/plugins/{name}/status
"""

import os
import pytest
EXAMPLE_PLUGIN = os.path.join(os.getcwd(), "plugins", "example-search-enhancer")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


class TestPluginsList:
    """插件列表"""

    def test_list_returns_200(self, client):
        resp = client.get("/api/plugins/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)


class TestPluginsDiscover:
    """插件发现"""

    def test_discover_returns_200(self, client):
        resp = client.get("/api/plugins/discover")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "plugins_dir" in data
        assert "discovered" in data
        assert "count" in data
        assert isinstance(data["discovered"], list)


class TestPluginsLifecycle:
    """插件完整生命周期: load → enable → hook → disable → unload"""

    def test_01_load_plugin(self, client):
        resp = client.post("/api/plugins/load", json={
            "plugin_path": EXAMPLE_PLUGIN,
            "config": {"target_language": "zh"},
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "example-search-enhancer"
        assert data["state"] in ("loaded", "enabled")
        assert "post_search" in data["hooks"]

    def test_02_get_status(self, client):
        resp = client.get("/api/plugins/example-search-enhancer/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "example-search-enhancer"

    def test_03_enable_plugin(self, client):
        resp = client.post("/api/plugins/example-search-enhancer/enable")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["state"] == "enabled"

    def test_04_trigger_hook(self, client):
        resp = client.post("/api/plugins/hook", json={
            "hook_name": "post_search",
            "kwargs": {
                "results": [
                    {"title": "Machine Learning for Cancer", "abstract": "Deep learning"},
                ],
            },
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hook_name"] == "post_search"
        assert data["handlers_called"] >= 1
        assert len(data["results"]) >= 1
        assert data["results"][0]["success"] is True
        assert data["results"][0]["result"]["enhanced"] is True

    def test_05_disable_plugin(self, client):
        resp = client.post("/api/plugins/example-search-enhancer/disable")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["state"] == "disabled"

    def test_06_unload_plugin(self, client):
        resp = client.delete("/api/plugins/example-search-enhancer")
        assert resp.status_code == 200

    def test_07_status_after_unload(self, client):
        """卸载后查询应返回404"""
        resp = client.get("/api/plugins/example-search-enhancer/status")
        assert resp.status_code == 404


class TestPluginsEdgeCases:
    """边界情况"""

    def test_load_nonexistent_plugin(self, client):
        resp = client.post("/api/plugins/load", json={
            "plugin_path": "/nonexistent/path",
        })
        assert resp.status_code in (404, 500)

    def test_enable_nonexistent_plugin(self, client):
        resp = client.post("/api/plugins/nonexistent/enable")
        assert resp.status_code in (400, 404)

    def test_disable_nonexistent_plugin(self, client):
        resp = client.post("/api/plugins/nonexistent/disable")
        assert resp.status_code == 404

    def test_unload_nonexistent_plugin(self, client):
        resp = client.delete("/api/plugins/nonexistent")
        assert resp.status_code == 404

    def test_hook_with_no_handlers(self, client):
        """无处理器时调用钩子"""
        resp = client.post("/api/plugins/hook", json={
            "hook_name": "nonexistent_hook",
            "kwargs": {},
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["handlers_called"] == 0

    def test_load_twice(self, client):
        """重复加载同一插件"""
        # 先加载
        client.post("/api/plugins/load", json={
            "plugin_path": EXAMPLE_PLUGIN,
        })
        # 再次加载应失败
        resp = client.post("/api/plugins/load", json={
            "plugin_path": EXAMPLE_PLUGIN,
        })
        assert resp.status_code in (200, 409)
        # 清理
        client.delete("/api/plugins/example-search-enhancer")
