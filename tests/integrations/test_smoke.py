from fastapi.testclient import TestClient

from app import create_app

# Dummy тест для CI процесса, чтобы стадия проходила
def test_health_returns_204() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 204
