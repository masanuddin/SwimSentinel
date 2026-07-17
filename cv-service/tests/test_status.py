from fastapi.testclient import TestClient

from app.main import app


def test_status_reports_mock_mode():
    client = TestClient(app)

    response = client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "cv-service"
    assert payload["mode"] == "mock"
    assert payload["ready"] is True
    assert "http://localhost:5173" in payload["allowedOrigins"]


def test_cors_allows_vite_origin():
    client = TestClient(app)

    response = client.options(
        "/events",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
