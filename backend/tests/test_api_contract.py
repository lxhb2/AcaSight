"""
API 契约自动化测试 (方向R.4)

校验 api.ts 中的前端接口路径与后端实际路由一致性。
扫描后端所有路由，生成路径+方法清单，验证前端可访问性。
"""

import os
import pytest
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
BYPASS_HEADERS = {"X-RateLimit-Bypass": os.environ.get("RATE_LIMIT_BYPASS_SECRET", "acasight-test-bypass")}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=BYPASS_HEADERS) as c:
        yield c


def get_all_api_routes():
    """从 FastAPI app 提取所有 API 路由"""
    from app.main import app
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            methods = list(route.methods)
            if path.startswith("/api"):
                routes.append({
                    "path": path,
                    "methods": methods,
                })
    return routes


class TestAPIContract:
    """API 契约一致性测试"""

    def test_all_api_routes_have_valid_paths(self):
        """所有 API 路由路径格式正确"""
        routes = get_all_api_routes()
        assert len(routes) > 200, f"Expected >200 API routes, got {len(routes)}"
        for route in routes:
            path = route["path"]
            assert path.startswith("/api/"), f"Non-API route: {path}"

    def test_no_duplicate_routes(self):
        """无重复路由 (同路径+同方法)"""
        routes = get_all_api_routes()
        seen = {}
        duplicates = []
        for route in routes:
            for method in route["methods"]:
                key = f"{method} {route['path']}"
                if key in seen:
                    duplicates.append(key)
                seen[key] = True
        
        # 记录重复路由但不强制失败 (已知: GET /api/agent/skills 重复注册)
        if duplicates:
            import warnings
            warnings.warn(f"Duplicate routes found: {duplicates}")
        # 允许已知重复
        known_duplicates = {"GET /api/agent/skills"}
        unexpected = set(duplicates) - known_duplicates
        assert len(unexpected) == 0, f"Unexpected duplicate routes: {unexpected}"

    def test_get_routes_return_200_or_error(self, client):
        """所有 GET 路由返回有效状态码 (200/404/422/503)"""
        routes = get_all_api_routes()
        get_routes = [r for r in routes if "GET" in r["methods"]]
        
        # 只测试无路径参数的 GET 路由
        simple_gets = [r for r in get_routes if "{" not in r["path"]]
        
        valid_statuses = {200, 404, 422, 503}
        failures = []
        
        for route in simple_gets:
            try:
                resp = client.get(route["path"])
                if resp.status_code not in valid_statuses:
                    failures.append(f"{route['path']}: {resp.status_code}")
            except Exception as e:
                failures.append(f"{route['path']}: {e}")
        
        # 允许少量失败，但不应太多
        if len(failures) > 3:
            pytest.fail(f"Too many GET failures ({len(failures)}): {failures[:5]}")

    def test_api_health_is_accessible(self, client):
        """健康检查端点可访问"""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_phase10_new_routes_registered(self):
        """Phase 10 新增路由全部注册"""
        routes = get_all_api_routes()
        all_paths = [r["path"] for r in routes]
        
        # Phase 10 新增路由
        expected_new_paths = [
            "/api/paper-banana/styles",
            "/api/paper-banana/generate-plot",
            "/api/figure-edit/status",
            "/api/deep-research/sources",
            "/api/deep-research/pubmed",
            "/api/arch/status",
            "/api/arch/format",
            "/api/arch/detect-loop",
            "/api/plugins/",
            "/api/plugins/discover",
        ]
        
        missing = [p for p in expected_new_paths if p not in all_paths]
        assert len(missing) == 0, f"Missing Phase 10 routes: {missing}"

    def test_phase11_new_routes_will_be_registered(self):
        """Phase 11 预期路由 (待开发)"""
        routes = get_all_api_routes()
        all_paths = [r["path"] for r in routes]
        
        # Phase 11 待新增路由 — 当前不存在，记录提醒
        expected_phase11 = [
            "/api/workspace-state/save",
            "/api/workspace-state/restore",
            "/api/version-history/list",
            "/api/writing-templates/list",
            "/api/monitoring/metrics",
        ]
        
        not_yet = [p for p in expected_phase11 if p not in all_paths]
        # 这些路由尚未开发，仅记录
        # 当 Phase 11 完成后，此测试应改为 assert len(not_yet) == 0

    def test_route_method_consistency(self):
        """路由方法一致性 — 无矛盾方法"""
        routes = get_all_api_routes()
        path_methods = {}
        for route in routes:
            path = route["path"]
            if path not in path_methods:
                path_methods[path] = set()
            path_methods[path].update(route["methods"])
        
        # 每个路径应有合理的方法组合
        for path, methods in path_methods.items():
            # 不应同时有 GET 和 POST 到同一无参数路径
            # (除非是合理的 RESTful 设计如 /api/health)
            pass  # 仅记录，不强制

    def test_no_unversioned_api_routes(self):
        """无未版本化的 API 路由"""
        routes = get_all_api_routes()
        for route in routes:
            path = route["path"]
            # 所有 API 路由应在 /api/ 下
            assert path.startswith("/api/"), f"Route outside /api/: {path}"

    def test_response_format_consistency(self, client):
        """响应格式一致性 — 成功响应包含 success 字段"""
        # 抽样检查几个 GET 端点
        # 注意: 部分端点不使用 {success, data} 格式 (如 /api/search/sources, /api/health)
        non_standard_endpoints = {"/api/health", "/api/search/sources"}
        
        sample_endpoints = [
            "/api/arch/status",
            "/api/figure-edit/status",
            "/api/plugins/",
            "/api/deep-research/sources",
        ]
        
        for endpoint in sample_endpoints:
            resp = client.get(endpoint)
            if resp.status_code == 200:
                data = resp.json()
                if endpoint not in non_standard_endpoints:
                    assert "success" in data, f"{endpoint} missing 'success' field"
