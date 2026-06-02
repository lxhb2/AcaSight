"""
AcaSight Backend Test Configuration
Tests run against the live backend server at localhost:8000
"""
import os
import pytest
import httpx

os.environ.setdefault("TESTING", "true")

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
RATE_LIMIT_BYPASS_SECRET = os.environ.get("RATE_LIMIT_BYPASS_SECRET", "acasight-test-bypass")


@pytest.fixture(scope="session")
def client():
    """Session-scoped httpx client for live server testing."""
    headers = {"X-RateLimit-Bypass": RATE_LIMIT_BYPASS_SECRET}
    with httpx.Client(base_url=BASE_URL, timeout=30.0, headers=headers) as c:
        yield c


@pytest.fixture
def api_base():
    """Base URL for API endpoints."""
    return BASE_URL


@pytest.fixture(autouse=True)
def _mark_test_data(request):
    """Automatically mark test-created data for cleanup."""
    request.node._test_created_data = []


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    """Clean up test database after test session."""
    yield
    test_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_acasight.db")
    if os.environ.get("TESTING", "false").lower() == "true" and os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass
