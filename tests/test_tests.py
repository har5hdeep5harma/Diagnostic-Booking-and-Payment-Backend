from fastapi.testclient import TestClient


def test_create_diagnostic_test_successfully(
    client: TestClient, auth_headers: dict
):
    response = client.post(
        "/tests",
        json={
            "name": "Complete Blood Count",
            "description": "Basic blood test",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Complete Blood Count"
    assert data["description"] == "Basic blood test"
    assert "id" in data


def test_unauthenticated_create_test_rejected(client: TestClient):
    response = client.post(
        "/tests",
        json={
            "name": "Complete Blood Count",
            "description": "Basic blood test",
        },
    )
    assert response.status_code == 401


def test_retrieve_diagnostic_test(client: TestClient, auth_headers: dict):
    create_res = client.post(
        "/tests",
        json={"name": "Urine Routine", "description": "Routine analysis"},
        headers=auth_headers,
    )
    test_id = create_res.json()["id"]

    get_res = client.get(f"/tests/{test_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == test_id
    assert data["name"] == "Urine Routine"
    assert data["description"] == "Routine analysis"
    assert data["centres"] == []


def test_retrieve_all_tests(client: TestClient, auth_headers: dict):
    client.post(
        "/tests",
        json={"name": "Test Alpha", "description": "Desc A"},
        headers=auth_headers,
    )
    client.post(
        "/tests",
        json={"name": "Test Beta", "description": "Desc B"},
        headers=auth_headers,
    )

    get_res = client.get("/tests")
    assert get_res.status_code == 200
    data = get_res.json()
    assert len(data) >= 2


def test_retrieve_nonexistent_test(client: TestClient):
    response = client.get("/tests/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_test_response_includes_available_centres_and_prices(
    client: TestClient, auth_headers: dict
):
    # 1. Create a diagnostic test
    t_res = client.post(
        "/tests",
        json={"name": "Blood Sugar Fasting", "description": "Glucose level"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    # 2. Create two centres
    c1_res = client.post(
        "/centres",
        json={"name": "North Diagnostics", "location": "Delhi"},
        headers=auth_headers,
    )
    c1_id = c1_res.json()["id"]

    c2_res = client.post(
        "/centres",
        json={"name": "South Care Lab", "location": "Chennai"},
        headers=auth_headers,
    )
    c2_id = c2_res.json()["id"]

    # 3. Associate test with both centres at different prices
    client.post(
        f"/centres/{c1_id}/tests",
        json={"test_id": test_id, "price": 150.00},
        headers=auth_headers,
    )
    client.post(
        f"/centres/{c2_id}/tests",
        json={"test_id": test_id, "price": 180.00},
        headers=auth_headers,
    )

    # 4. Retrieve test with its offering centres
    get_res = client.get(f"/tests/{test_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == test_id
    assert len(data["centres"]) == 2

    centre_ids = [c["centre_id"] for c in data["centres"]]
    assert c1_id in centre_ids
    assert c2_id in centre_ids

    for item in data["centres"]:
        if item["centre_id"] == c1_id:
            assert item["name"] == "North Diagnostics"
            assert item["location"] == "Delhi"
            assert float(item["price"]) == 150.00
        elif item["centre_id"] == c2_id:
            assert item["name"] == "South Care Lab"
            assert item["location"] == "Chennai"
            assert float(item["price"]) == 180.00
