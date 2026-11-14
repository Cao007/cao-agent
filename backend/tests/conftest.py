import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_api


@pytest.fixture
def settings():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL test database")
    return Settings(_env_file=None, database_url=url, model_mode="demo")


@pytest.fixture
def client(settings):
    with TestClient(create_api(settings)) as client:
        yield client


@pytest.fixture
def login(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": f"test_{uuid4().hex}",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 201
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()
