from fastapi.testclient import TestClient

from app.infrastructure.db.session import get_session
from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_returns_safe_503_when_database_is_unavailable() -> None:
    class UnavailableSession:
        async def execute(self, _query):
            raise ConnectionError("secret connection detail")

    async def unavailable_session():
        yield UnavailableSession()

    app.dependency_overrides[get_session] = unavailable_session
    try:
        response = TestClient(app).get("/health/db")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "service_unavailable", "message": "Database is unavailable"}
    }
    assert "secret connection detail" not in response.text
