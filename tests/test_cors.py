"""Tests for CORS headers."""

from fastapi.testclient import TestClient

from src.web.main import app


def test_cors_headers_present():
    """OPTIONS preflight returns CORS headers."""
    with TestClient(app) as client:
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert "access-control-allow-methods" in resp.headers
