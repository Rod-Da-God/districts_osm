import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import create_app
from routers import health_router


pytestmark = pytest.mark.integration


def test_health_returns_204_without_external_services() -> None:
    app = FastAPI()
    app.include_router(health_router)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 204


def test_create_app_registers_all_routes() -> None:
    app = create_app()

    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/districts/resolve" in paths
    assert "/districts/cities" in paths
    assert "/districts/cities/list" in paths
    assert "/metrics" in paths
