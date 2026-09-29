from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, PaymentStatus


# Health Check
class HealthResponse(BaseModel):
    status: str


# Authentication Schemas
class UserSignup(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Diagnostic Centre Schemas
class CentreCreate(BaseModel):
    name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)


class CentreResponse(BaseModel):
    id: int
    name: str
    location: str

    model_config = ConfigDict(from_attributes=True)


class CentreTestItem(BaseModel):
    test_id: int
    name: str
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class CentreDetailResponse(BaseModel):
    id: int
    name: str
    location: str
    tests: List[CentreTestItem] = []

    model_config = ConfigDict(from_attributes=True)


class CentreTestCreate(BaseModel):
    test_id: int
    price: Decimal = Field(..., gt=0, decimal_places=2)


class CentreTestResponse(BaseModel):
    id: int
    centre_id: int
    test_id: int
    price: Decimal = Field(..., gt=0, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


# Diagnostic Test Schemas
class TestCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


class TestResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TestCentreItem(BaseModel):
    centre_id: int
    name: str
    location: str
    price: Decimal = Field(..., gt=0, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class TestDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    centres: List[TestCentreItem] = []

    model_config = ConfigDict(from_attributes=True)


# Booking Schemas
class BookingCreate(BaseModel):
    centre_id: int
    test_id: int
    appointment_datetime: datetime


class BookingListItemResponse(BaseModel):
    id: int
    centre_id: int
    test_id: int
    appointment_datetime: datetime
    amount: Decimal = Field(..., decimal_places=2)
    status: BookingStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BookingListItemResponse):
    user_id: int


# Payment Schemas
class PaymentRequest(BaseModel):
    booking_id: int
    payment_status: PaymentStatus


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    payment_reference: str
    amount: Decimal = Field(..., decimal_places=2)
    status: PaymentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentWebhookRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    booking_id: int
    payment_reference: str = Field(..., min_length=1)
    status: PaymentStatus


