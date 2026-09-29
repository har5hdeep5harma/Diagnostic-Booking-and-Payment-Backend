import os

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient):
    client.post(
        "/auth/signup",
        json={
            "name": "Auth User",
            "email": "auth@example.com",
            "password": "password123",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={
            "email": "auth@example.com",
            "password": "password123",
        },
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(client: TestClient):
    client.post(
        "/auth/signup",
        json={
            "name": "Other User",
            "email": "other@example.com",
            "password": "password123",
        },
    )
    login_res = client.post(
        "/auth/login",
        json={
            "email": "other@example.com",
            "password": "password123",
        },
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

