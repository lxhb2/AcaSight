"""
AcaSight Backend Router Test Configuration
"""
import os
import pytest
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
RATE_LIMIT_BYPASS_SECRET = os.environ.get("RATE_LIMIT_BYPASS_SECRET", "acasight-test-bypass")


@pytest.fixture(scope="module")
def client():
    """Module-scoped httpx client with rate limit bypass."""
    headers = {"X-RateLimit-Bypass": RATE_LIMIT_BYPASS_SECRET}
    with httpx.Client(base_url=BASE_URL, timeout=60.0, headers=headers) as c:
        yield c
