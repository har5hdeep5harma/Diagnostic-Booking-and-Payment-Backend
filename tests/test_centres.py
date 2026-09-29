from fastapi.testclient import TestClient


def test_create_centre_successfully(client: TestClient, auth_headers: dict):
    response = client.post(
        "/centres",
        json={"name": "City Diagnostics", "location": "Delhi"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "City Diagnostics"
    assert data["location"] == "Delhi"
    assert "id" in data


def test_unauthenticated_create_centre_rejected(client: TestClient):
    response = client.post(
        "/centres",
        json={"name": "City Diagnostics", "location": "Delhi"},
    )
    assert response.status_code == 401


def test_retrieve_centre(client: TestClient, auth_headers: dict):
    create_res = client.post(
        "/centres",
        json={"name": "Metro Health Lab", "location": "Mumbai"},
        headers=auth_headers,
    )
    centre_id = create_res.json()["id"]

    get_res = client.get(f"/centres/{centre_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == centre_id
    assert data["name"] == "Metro Health Lab"
    assert data["location"] == "Mumbai"
    assert data["tests"] == []


def test_retrieve_all_centres(client: TestClient, auth_headers: dict):
    client.post(
        "/centres",
        json={"name": "Centre A", "location": "Location A"},
        headers=auth_headers,
    )
    client.post(
        "/centres",
        json={"name": "Centre B", "location": "Location B"},
        headers=auth_headers,
    )

    get_res = client.get("/centres")
    assert get_res.status_code == 200
    data = get_res.json()
    assert len(data) >= 2


def test_retrieve_nonexistent_centre(client: TestClient):
    response = client.get("/centres/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_associate_test_with_centre_successfully(
    client: TestClient, auth_headers: dict
):
    # 1. Create centre
    c_res = client.post(
        "/centres",
        json={"name": "Care Diagnostics", "location": "Bangalore"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    # 2. Create test
    t_res = client.post(
        "/tests",
        json={"name": "Lipid Profile", "description": "Cholesterol panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    # 3. Associate test with centre
    assoc_res = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 750.00},
        headers=auth_headers,
    )
    assert assoc_res.status_code == 201
    assoc_data = assoc_res.json()
    assert assoc_data["centre_id"] == centre_id
    assert assoc_data["test_id"] == test_id
    assert float(assoc_data["price"]) == 750.00


def test_duplicate_centre_test_association_rejected(
    client: TestClient, auth_headers: dict
):
    c_res = client.post(
        "/centres",
        json={"name": "Care Diagnostics", "location": "Bangalore"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    t_res = client.post(
        "/tests",
        json={"name": "Lipid Profile", "description": "Cholesterol panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    # First association
    client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 750.00},
        headers=auth_headers,
    )

    # Duplicate association
    dup_res = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 800.00},
        headers=auth_headers,
    )
    assert dup_res.status_code == 400
    assert "already offered" in dup_res.json()["detail"].lower()


def test_associate_invalid_centre_rejected(
    client: TestClient, auth_headers: dict
):
    t_res = client.post(
        "/tests",
        json={"name": "Lipid Profile", "description": "Cholesterol panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    response = client.post(
        "/centres/9999/tests",
        json={"test_id": test_id, "price": 500.00},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "centre not found" in response.json()["detail"].lower()


def test_associate_invalid_test_rejected(
    client: TestClient, auth_headers: dict
):
    c_res = client.post(
        "/centres",
        json={"name": "Care Diagnostics", "location": "Bangalore"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    response = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": 9999, "price": 500.00},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "test not found" in response.json()["detail"].lower()


def test_associate_invalid_price_rejected(
    client: TestClient, auth_headers: dict
):
    c_res = client.post(
        "/centres",
        json={"name": "Care Diagnostics", "location": "Bangalore"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    t_res = client.post(
        "/tests",
        json={"name": "Lipid Profile", "description": "Cholesterol panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    # Price = 0 (rejected by gt=0)
    res_zero = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 0.00},
        headers=auth_headers,
    )
    assert res_zero.status_code == 422

    # Negative price
    res_neg = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": -50.00},
        headers=auth_headers,
    )
    assert res_neg.status_code == 422


def test_centre_response_includes_offered_tests_and_prices(
    client: TestClient, auth_headers: dict
):
    # Create centre
    c_res = client.post(
        "/centres",
        json={"name": "Apex Lab", "location": "Pune"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    # Create two tests
    t1_res = client.post(
        "/tests",
        json={"name": "CBC", "description": "Blood Count"},
        headers=auth_headers,
    )
    t1_id = t1_res.json()["id"]

    t2_res = client.post(
        "/tests",
        json={"name": "Thyroid", "description": "T3, T4, TSH"},
        headers=auth_headers,
    )
    t2_id = t2_res.json()["id"]

    # Associate both tests
    client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": t1_id, "price": 300.00},
        headers=auth_headers,
    )
    client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": t2_id, "price": 600.00},
        headers=auth_headers,
    )

    # Retrieve centre
    get_res = client.get(f"/centres/{centre_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == centre_id
    assert len(data["tests"]) == 2

    test_ids = [t["test_id"] for t in data["tests"]]
    assert t1_id in test_ids
    assert t2_id in test_ids

    # Verify prices and descriptions
    for item in data["tests"]:
        if item["test_id"] == t1_id:
            assert float(item["price"]) == 300.00
            assert item["name"] == "CBC"
        elif item["test_id"] == t2_id:
            assert float(item["price"]) == 600.00
            assert item["name"] == "Thyroid"
