from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models import Booking, BookingStatus, Payment, PaymentStatus
from tests.conftest import TestingSessionLocal


def _setup_booking(client: TestClient, auth_headers: dict, price: float = 550.00):
    c_res = client.post(
        "/centres",
        json={"name": "Premier Lab", "location": "Connaught Place"},
        headers=auth_headers,
    )
    centre_id = c_res.json()["id"]

    t_res = client.post(
        "/tests",
        json={"name": "Kidney Function Test", "description": "KFT panel"},
        headers=auth_headers,
    )
    test_id = t_res.json()["id"]

    client.post(
        f"/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": price},
        headers=auth_headers,
    )

    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    booking_res = client.post(
        "/bookings",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time,
        },
        headers=auth_headers,
    )
    assert booking_res.status_code == 201
    return booking_res.json()["id"]


# ============================================================
# 1. PAYMENT ENDPOINT TESTS
# ============================================================


def test_authenticated_user_can_make_successful_payment(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=550.00)

    res = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["booking_id"] == booking_id
    assert data["status"] == "SUCCESS"
    assert float(data["amount"]) == 550.00
    assert data["payment_reference"].startswith("PAY-")

    # Verify booking status became CONFIRMED
    booking_res = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "CONFIRMED"


def test_authenticated_user_can_make_failed_payment(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=550.00)

    res = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "FAILED"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["booking_id"] == booking_id
    assert data["status"] == "FAILED"

    # Verify booking status became FAILED
    booking_res = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "FAILED"


def test_payment_amount_comes_from_booking_amount_ignoring_client_payload(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=720.00)

    # Attempt to send client-manipulated amount
    res = client.post(
        "/payments",
        json={
            "booking_id": booking_id,
            "payment_status": "SUCCESS",
            "amount": "1.00",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert float(res.json()["amount"]) == 720.00


def test_payment_nonexistent_booking_returns_404(
    client: TestClient, auth_headers: dict
):
    res = client.post(
        "/payments",
        json={"booking_id": 9999, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_another_user_cannot_pay_for_someone_elses_booking(
    client: TestClient, auth_headers: dict, other_auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)

    res = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=other_auth_headers,
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_cancelled_booking_cannot_be_paid(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)

    # Cancel booking
    cancel_res = client.post(
        f"/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert cancel_res.status_code == 200

    # Attempt payment
    pay_res = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert pay_res.status_code == 400
    assert "cancelled" in pay_res.json()["detail"].lower()


def test_already_processed_booking_cannot_be_processed_again(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)

    # First successful payment
    pay1 = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert pay1.status_code == 200

    # Second payment attempt
    pay2 = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert pay2.status_code == 400
    assert "cannot process" in pay2.json()["detail"].lower()


# ============================================================
# 2. WEBHOOK ENDPOINT TESTS
# ============================================================


def test_successful_webhook_creates_payment_and_confirms_booking(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=400.00)

    # Webhook does NOT require JWT authentication
    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_test_001",
            "booking_id": booking_id,
            "payment_reference": "PAY-TEST-001",
            "status": "SUCCESS",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["booking_id"] == booking_id
    assert data["payment_reference"] == "PAY-TEST-001"
    assert data["status"] == "SUCCESS"
    assert float(data["amount"]) == 400.00

    # Verify booking status in database
    booking_res = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "CONFIRMED"


def test_failed_webhook_creates_payment_and_fails_booking(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=400.00)

    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_test_002",
            "booking_id": booking_id,
            "payment_reference": "PAY-TEST-002",
            "status": "FAILED",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "FAILED"

    booking_res = client.get(f"/bookings/{booking_id}", headers=auth_headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "FAILED"


def test_webhook_nonexistent_booking_returns_404(client: TestClient):
    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_nonexistent",
            "booking_id": 9999,
            "payment_reference": "PAY-NONEXISTENT",
            "status": "SUCCESS",
        },
    )
    assert res.status_code == 404
    assert "booking not found" in res.json()["detail"].lower()


def test_webhook_cancelled_booking_rejected(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)
    client.post(f"/bookings/{booking_id}/cancel", headers=auth_headers)

    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_cancelled",
            "booking_id": booking_id,
            "payment_reference": "PAY-CANCELLED",
            "status": "SUCCESS",
        },
    )
    assert res.status_code == 400
    assert "cancelled" in res.json()["detail"].lower()


def test_webhook_idempotency_repeated_identical_event(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=500.00)

    payload = {
        "event_id": "evt_idempotent_01",
        "booking_id": booking_id,
        "payment_reference": "PAY-IDEM-01",
        "status": "SUCCESS",
    }

    # First delivery
    res1 = client.post("/payments/webhook", json=payload)
    assert res1.status_code == 200
    payment_id = res1.json()["id"]

    # Verify exactly 1 Payment record exists
    with TestingSessionLocal() as db:
        count = (
            db.query(Payment)
            .filter(Payment.webhook_event_id == "evt_idempotent_01")
            .count()
        )
        assert count == 1

    # Second delivery with exact same event
    res2 = client.post("/payments/webhook", json=payload)
    assert res2.status_code == 200
    assert res2.json()["id"] == payment_id
    assert res2.json()["payment_reference"] == "PAY-IDEM-01"

    # Verify STILL exactly 1 Payment record exists
    with TestingSessionLocal() as db:
        count = (
            db.query(Payment)
            .filter(Payment.webhook_event_id == "evt_idempotent_01")
            .count()
        )
        assert count == 1
        booking = db.get(Booking, booking_id)
        assert booking.status == BookingStatus.CONFIRMED


def test_webhook_conflicting_second_event_rejected(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)

    # Initial event confirms booking
    res1 = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_initial_01",
            "booking_id": booking_id,
            "payment_reference": "PAY-INITIAL-01",
            "status": "SUCCESS",
        },
    )
    assert res1.status_code == 200

    # Conflicting second event attempting to fail the already-confirmed booking
    res2 = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_conflict_01",
            "booking_id": booking_id,
            "payment_reference": "PAY-CONFLICT-01",
            "status": "FAILED",
        },
    )
    assert res2.status_code == 400
    assert "already been confirmed" in res2.json()["detail"].lower()

    # Verify booking remained CONFIRMED and original payment remains intact
    with TestingSessionLocal() as db:
        b = db.get(Booking, booking_id)
        assert b.status == BookingStatus.CONFIRMED
        payments = db.query(Payment).filter(Payment.booking_id == booking_id).all()
        assert len(payments) == 1
        assert payments[0].webhook_event_id == "evt_initial_01"


def test_webhook_duplicate_payment_reference_rejected(
    client: TestClient, auth_headers: dict
):
    booking_id1 = _setup_booking(client, auth_headers)
    booking_id2 = _setup_booking(client, auth_headers)

    # First payment uses reference "PAY-SHARED-REF"
    res1 = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_ref_1",
            "booking_id": booking_id1,
            "payment_reference": "PAY-SHARED-REF",
            "status": "SUCCESS",
        },
    )
    assert res1.status_code == 200

    # Second payment with different event and different booking attempts to reuse same reference
    res2 = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_ref_2",
            "booking_id": booking_id2,
            "payment_reference": "PAY-SHARED-REF",
            "status": "SUCCESS",
        },
    )
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_webhook_does_not_require_jwt_auth(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers)

    # Request without any Authorization header
    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_noauth",
            "booking_id": booking_id,
            "payment_reference": "PAY-NOAUTH",
            "status": "SUCCESS",
        },
    )
    assert res.status_code == 200


def test_webhook_payment_amount_comes_from_booking_amount(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=850.00)

    res = client.post(
        "/payments/webhook",
        json={
            "event_id": "evt_amount_check",
            "booking_id": booking_id,
            "payment_reference": "PAY-AMOUNT-CHECK",
            "status": "SUCCESS",
            "amount": "10.00",  # Manipulated field in JSON ignored
        },
    )
    assert res.status_code == 200
    assert float(res.json()["amount"]) == 850.00


def test_payment_and_booking_update_atomically(
    client: TestClient, auth_headers: dict
):
    booking_id = _setup_booking(client, auth_headers, price=350.00)

    res = client.post(
        "/payments",
        json={"booking_id": booking_id, "payment_status": "SUCCESS"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    payment_id = res.json()["id"]

    # In database, both must be committed together
    with TestingSessionLocal() as db:
        p = db.get(Payment, payment_id)
        b = db.get(Booking, booking_id)
        assert p is not None
        assert b is not None
        assert p.status == PaymentStatus.SUCCESS
        assert b.status == BookingStatus.CONFIRMED
        assert p.amount == b.amount
