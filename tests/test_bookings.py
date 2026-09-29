from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models import Booking, BookingStatus, CentreTest
from tests.conftest import TestingSessionLocal


def _setup_centre_and_test(client: TestClient, auth_headers: dict, price: float = 450.00):
    c_res = client.post(
        "/centres",
        json={"name": "City Care Diagnostics", "location": "New Delhi"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    t_res = client.post(
        "/tests",
        json={"name": "Complete Blood Count", "description": "CBC panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    assoc_res = client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": price},
        headers=auth_headers,
    )
    assert assoc_res.status_code == 201

    return centre_id, test_id


def test_authenticated_user_can_create_booking_with_pending_status(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers, price=450.00)
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["centre_id"] == centre_id
    assert data["test_id"] == test_id
    assert float(data["amount"]) == 450.00
    assert "user_id" in data
    assert "id" in data


def test_booking_amount_comes_from_centre_test_and_cannot_be_manipulated(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers, price=600.00)
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    # Client attempts to send manipulated amount "10.00"
    response = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
            "amount": "10.00",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    # Amount must equal CentreTest.price (600.00), ignoring client input
    assert float(data["amount"]) == 600.00


def test_nonexistent_centre_rejected(client: TestClient, auth_headers: dict):
    _, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings",
        json={
            "centre_id": 9999,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "centre not found" in response.json()["detail"].lower()


def test_nonexistent_test_rejected(client: TestClient, auth_headers: dict):
    centre_id, _ = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": 9999,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "test not found" in response.json()["detail"].lower()


def test_test_not_offered_by_centre_rejected(
    client: TestClient, auth_headers: dict
):
    centre_id, _ = _setup_centre_and_test(client, auth_headers)

    # Create unassociated test
    other_test = client.post(
        "/tests",
        json={"name": "X-Ray Chest", "description": "Radiology"},
        headers=auth_headers,
    ).json()["id"]

    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": other_test,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "not offered" in response.json()["detail"].lower()


def test_invalid_past_appointment_rejected(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": past_time,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


def test_user_can_list_their_own_bookings(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers, price=300.00)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )

    response = client.get("/bookings", headers=auth_headers)
    assert response.status_code == 200
    bookings = response.json()
    assert len(bookings) == 1
    assert bookings[0]["centre_id"] == centre_id
    assert bookings[0]["test_id"] == test_id
    assert float(bookings[0]["amount"]) == 300.00
    assert bookings[0]["status"] == "PENDING"


def test_user_cannot_see_another_users_booking_in_list(
    client: TestClient, auth_headers: dict, other_auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    # User A creates a booking
    client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )

    # User B lists their bookings -> should be empty
    other_list_res = client.get("/bookings", headers=other_auth_headers)
    assert other_list_res.status_code == 200
    assert len(other_list_res.json()) == 0


def test_nonexistent_booking_returns_404(
    client: TestClient, auth_headers: dict
):
    response = client.get("/bookings/9999", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_user_cannot_access_another_users_booking_returns_403(
    client: TestClient, auth_headers: dict, other_auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    # User A creates booking
    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    # User B attempts to access User A's booking
    response = client.get(f"/bookings/{booking_id}", headers=other_auth_headers)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()


def test_user_can_cancel_their_pending_booking(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    # Cancel booking
    cancel_res = client.post(
        f"/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["id"] == booking_id
    assert data["status"] == "CANCELLED"


def test_user_cannot_cancel_another_users_booking(
    client: TestClient, auth_headers: dict, other_auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    cancel_res = client.post(
        f"/bookings/{booking_id}/cancel", headers=other_auth_headers
    )
    assert cancel_res.status_code == 403


def test_cancelled_booking_cannot_be_cancelled_again(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    # First cancel
    client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)

    # Second cancel attempt
    second_cancel = client.post(
        f"/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert second_cancel.status_code == 400
    assert "cannot cancel" in second_cancel.json()["detail"].lower()


def test_confirmed_booking_cannot_be_cancelled(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    # Update status to CONFIRMED directly
    with TestingSessionLocal() as db:
        b = db.get(Booking, booking_id)
        b.status = BookingStatus.CONFIRMED
        db.commit()

    cancel_res = client.post(
        f"/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert cancel_res.status_code == 400
    assert "cannot cancel" in cancel_res.json()["detail"].lower()


def test_failed_booking_cannot_be_cancelled(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]

    # Update status to FAILED directly
    with TestingSessionLocal() as db:
        b = db.get(Booking, booking_id)
        b.status = BookingStatus.FAILED
        db.commit()

    cancel_res = client.post(
        f"/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert cancel_res.status_code == 400
    assert "cannot cancel" in cancel_res.json()["detail"].lower()


def test_changing_centre_test_price_does_not_change_existing_booking_amount(
    client: TestClient, auth_headers: dict
):
    centre_id, test_id = _setup_centre_and_test(client, auth_headers, price=450.00)
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    # Create booking when price is 450.00
    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    booking_id = booking_res.json()["id"]
    assert float(booking_res.json()["amount"]) == 450.00

    # Modify CentreTest price in database to 500.00
    with TestingSessionLocal() as db:
        ct = (
            db.query(CentreTest)
            .filter(
                CentreTest.centre_id == centre_id,
                CentreTest.test_id == test_id,
            )
            .first()
        )
        ct.price = Decimal("500.00")
        db.commit()

    # Retrieve existing booking -> amount must remain 450.00
    get_booking_res = client.get(
        f"/bookings/{booking_id}", headers=auth_headers
    )
    assert get_booking_res.status_code == 200
    assert float(get_booking_res.json()["amount"]) == 450.00
