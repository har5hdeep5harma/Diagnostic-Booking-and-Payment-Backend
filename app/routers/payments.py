import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, BookingStatus, Payment, PaymentStatus, User
from app.schemas import PaymentRequest, PaymentResponse, PaymentWebhookRequest

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def process_payment(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to pay for this booking",
        )

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process payment for a booking with status {booking.status.value}",
        )

    payment_reference = f"PAY-{uuid.uuid4().hex.upper()}"

    payment = Payment(
        booking_id=booking.id,
        payment_reference=payment_reference,
        amount=booking.amount,
        status=payload.payment_status,
    )

    if payload.payment_status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.FAILED

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


@router.post("/webhook", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
@router.post("/webhook/", response_model=PaymentResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def payment_webhook(
    payload: PaymentWebhookRequest,
    db: Session = Depends(get_db),
):
    # 1. Idempotency check: event_id already processed
    existing_event = (
        db.query(Payment)
        .filter(Payment.webhook_event_id == payload.event_id)
        .first()
    )
    if existing_event:
        return existing_event

    # 2. Validate booking existence
    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # 3. Check for cancelled booking
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payment for a cancelled booking",
        )

    # 4. Check for already confirmed or failed booking (conflicting event edge case)
    if booking.status == BookingStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking has already been confirmed",
        )

    if booking.status == BookingStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking payment has already failed",
        )

    # 5. Check if payment_reference already exists
    existing_ref = (
        db.query(Payment)
        .filter(Payment.payment_reference == payload.payment_reference)
        .first()
    )
    if existing_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment reference already exists",
        )

    # 6. Create payment and update booking in a single transaction
    payment = Payment(
        booking_id=booking.id,
        payment_reference=payload.payment_reference,
        amount=booking.amount,
        status=payload.status,
        webhook_event_id=payload.event_id,
    )

    if payload.status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.FAILED

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment
