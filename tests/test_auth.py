from fastapi.testclient import TestClient


def test_successful_signup(client: TestClient):
    response = client.post(
        "/auth/signup",
        json={
            "name": "Harsh",
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Harsh"
    assert data["email"] == "harsh@example.com"
    assert "id" in data
    assert "password_hash" not in data
    assert "password" not in data


def test_duplicate_email_rejected(client: TestClient):
    client.post(
        "/auth/signup",
        json={
            "name": "Harsh",
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )

    # Attempt to signup with same email in different case
    response = client.post(
        "/auth/signup",
        json={
            "name": "Harsh Duplicate",
            "email": "HARSH@EXAMPLE.COM",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_successful_login(client: TestClient):
    client.post(
        "/auth/signup",
        json={
            "name": "Harsh",
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert len(data["access_token"]) > 10


def test_wrong_password_rejected(client: TestClient):
    client.post(
        "/auth/signup",
        json={
            "name": "Harsh",
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "harsh@example.com",
            "password": "wrongpassword123",
        },
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_invalid_jwt_rejected(client: TestClient):
    # Request without token
    res_no_token = client.get("/auth/me")
    assert res_no_token.status_code == 401

    # Request with invalid token
    res_invalid_token = client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid.token.value"}
    )
    assert res_invalid_token.status_code == 401


def test_authenticated_dependency_retrieves_user(client: TestClient):
    signup_res = client.post(
        "/auth/signup",
        json={
            "name": "Harsh",
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )
    user_id = signup_res.json()["id"]

    login_res = client.post(
        "/auth/login",
        json={
            "email": "harsh@example.com",
            "password": "securepassword123",
        },
    )
    token = login_res.json()["access_token"]

    me_res = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["id"] == user_id
    assert data["name"] == "Harsh"
    assert data["email"] == "harsh@example.com"
    assert "password_hash" not in data
