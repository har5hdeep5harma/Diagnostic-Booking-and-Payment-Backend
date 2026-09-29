# Diagnostic Booking and Payment Backend

A backend REST API service for a healthcare diagnostic platform that enables users to browse diagnostic tests across diagnostic centres, book appointments, and handle simulated payment processing with webhook idempotency.

---

## 1. Project Overview

The **Diagnostic Booking and Payment Backend** is built for the EVE Healthcare SDE Intern Hiring Assignment. The application provides an end-to-end workflow:
1. **User Authentication**: Secure user registration, credential verification, and JWT issuance.
2. **Diagnostic Catalog**: Management of diagnostic centres, catalog of diagnostic tests, and association of tests to centres with centre-specific pricing.
3. **Appointment Bookings**: Booking appointments at specific centres with frozen price snapshots and appointment scheduling validations.
4. **Simulated Payments & Webhook Ingestion**: Processing payments via direct simulated requests or external webhooks, enforcing state transitions and idempotency guarantees.

---

## 2. Technology Stack

- **Language**: Python 3.12+
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (high-performance asynchronous REST API framework)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **ORM & Database Toolkit**: [SQLAlchemy 2.x](https://www.sqlalchemy.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (driver: `psycopg2-binary`) / SQLite (in-memory for automated tests)
- **Data Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/)
- **Authentication & Security**: Passlib with Bcrypt (`bcrypt<=4.0.1`), Python-Jose for JWT
- **Testing**: [pytest](https://pytest.org/) and HTTPX via `fastapi.testclient.TestClient`
- **Containerization**: Docker Compose (for local PostgreSQL service)

---

## 3. Architecture

The system follows a clean, layered architecture without unnecessary overengineering:

```
FastAPI Application
       │
   Routers (Presentation & Validation)
   ├── auth.py
   ├── centres.py
   ├── tests.py
   ├── bookings.py
   └── payments.py
       │
SQLAlchemy ORM (Domain Models & Transaction Boundaries)
       │
PostgreSQL Database
```

### Core Domain Entities

- **User**: Registered platform user with unique email and bcrypt-hashed credentials.
- **DiagnosticCentre**: Physical healthcare location (name, address, contact info).
- **DiagnosticTest**: Standard medical test offering (name, description).
- **CentreTest**: Association table representing the availability of a test at a centre, holding the centre-specific price.
- **Booking**: User appointment for a specific test at a centre; stores a price snapshot taken at booking time and manages the lifecycle state (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`).
- **Payment**: Payment transaction linked to a booking; captures the payment status (`SUCCESS`, `FAILED`), reference number, and optional `webhook_event_id` for idempotency.

---

## 4. Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── auth.py              # Password hashing & JWT token verification utilities
│   ├── database.py          # SQLAlchemy engine, session maker, Base, and get_db
│   ├── main.py              # FastAPI app initialization, router registration, lifespan
│   ├── models.py            # SQLAlchemy 2.x domain models
│   ├── schemas.py           # Pydantic v2 schemas for request validation & responses
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # /auth/signup, /auth/login, /auth/me
│       ├── bookings.py      # /bookings endpoints
│       ├── centres.py       # /centres endpoints
│       ├── payments.py      # /payments and /payments/webhook
│       └── tests.py         # /tests endpoints
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures and isolated SQLite in-memory test DB
│   ├── test_auth.py         # Auth tests (signup, login, invalid JWT, get current user)
│   ├── test_bookings.py     # Booking flow, price snapshot, cancellation, permissions
│   ├── test_centres.py      # Centre creation, retrieval, test associations
│   ├── test_payments.py     # Payment simulation, webhook idempotency, conflicts
│   └── test_tests.py        # Test catalog creation and centre retrieval
├── .env.example             # Example environment variables template
├── .gitignore               # Ignored cache, virtual env, and database files
├── docker-compose.yml       # Docker Compose definition for local PostgreSQL 16
├── requirements.txt         # Minimal, pinned Python package dependencies
└── README.md                # Project documentation and operational guide
```

---

## 5. Setup Requirements

- **Python**: Version 3.12 or higher.
- **PostgreSQL**: Version 14+ (PostgreSQL 16 recommended via Docker Compose or native local service).
- **Docker & Docker Compose** *(Optional)*: Recommended for quickly bootstrapping a dedicated PostgreSQL database container without installing PostgreSQL locally.

---

## 6. Environment Setup

Create a `.env` configuration file from the provided `.env.example`:

```bash
# Windows PowerShell / CMD
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

### Environment Variables Explanation

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg2://postgres:postgres@localhost:5432/eve_healthcare` |
| `POSTGRES_USER` | PostgreSQL superuser for Docker Compose | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker Compose | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name | `eve_healthcare` |
| `POSTGRES_PORT` | PostgreSQL exposed host port | `5432` |
| `JWT_SECRET_KEY` | Secret key used to sign and verify JWT tokens | `change-this-in-production` |
| `JWT_ALGORITHM` | Cryptographic algorithm for JWT | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity duration in minutes | `30` |

> **Note**: Never commit production credentials or actual secret keys to source control. `.env` is excluded in `.gitignore`.

---

## 7. Installation

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```

2. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 8. Database Setup

### Option A: Using Docker Compose (Recommended)
If Docker is installed on your machine, spin up a dedicated PostgreSQL container:
```bash
docker compose up -d
```
This provisions a PostgreSQL 16 instance listening on port 5432 with persistent storage under the `postgres_data` volume.

### Option B: Using an Existing Local PostgreSQL Installation
1. Start your local PostgreSQL server service.
2. Create the target database using `psql` or pgAdmin:
   ```sql
   CREATE DATABASE eve_healthcare;
   ```
3. Update `DATABASE_URL` in `.env` with your username and password:
   ```env
   DATABASE_URL=postgresql+psycopg2://<YOUR_USER>:<YOUR_PASSWORD>@localhost:5432/eve_healthcare
   ```

> **Automatic Schema Provisioning**: The application utilizes SQLAlchemy's metadata creation (`Base.metadata.create_all(bind=engine)`) during startup. All tables and constraints are created automatically when the FastAPI server initializes.

---

## 9. Running the Application

With the virtual environment activated and the database ready:

```bash
uvicorn app.main:app --reload
```

The application will start at `http://127.0.0.1:8000`.

---

## 10. API Documentation

Interactive OpenAPI documentation is generated automatically by FastAPI:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 11. Complete API Endpoint Table

| Method | Endpoint | Purpose | Authentication |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/signup` | Register a new user account with hashed password | Public |
| `POST` | `/auth/login` | Authenticate credentials and receive a JWT access token | Public |
| `GET` | `/auth/me` | Retrieve the authenticated user's profile | Bearer JWT |
| `POST` | `/centres` | Register a new diagnostic centre | Bearer JWT |
| `GET` | `/centres` | Retrieve all registered diagnostic centres | Public |
| `GET` | `/centres/{centre_id}` | Retrieve details of a centre and tests offered with prices | Public |
| `POST` | `/centres/{centre_id}/tests` | Associate a test with a centre and set its price | Bearer JWT |
| `POST` | `/tests` | Create a new diagnostic test in the catalog | Bearer JWT |
| `GET` | `/tests` | Retrieve all diagnostic tests | Public |
| `GET` | `/tests/{test_id}` | Retrieve details of a test and centres offering it with prices | Public |
| `POST` | `/bookings` | Create an appointment booking (starts in `PENDING`) | Bearer JWT |
| `GET` | `/bookings` | List all bookings belonging to the authenticated user | Bearer JWT |
| `GET` | `/bookings/{booking_id}` | Get details of a specific booking owned by the user | Bearer JWT |
| `POST` | `/bookings/{booking_id}/cancel` | Cancel a `PENDING` booking | Bearer JWT |
| `POST` | `/payments` | Simulate a direct payment (`SUCCESS` or `FAILED`) | Bearer JWT |
| `POST` | `/payments/webhook` | Process an idempotent external payment webhook | Public (Webhook) |
| `GET` | `/health` | Service health status check | Public |

---

## 12. Example Requests

### 1. User Signup
```http
POST /auth/signup
Content-Type: application/json

{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "securepassword123"
}
```

### 2. User Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "jane@example.com",
  "password": "securepassword123"
}
```
*Response*:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Create Diagnostic Centre
```http
POST /centres
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "Apollo Diagnostics Central",
  "address": "123 Health Ave, Bangalore",
  "contact_number": "+91-9876543210"
}
```

### 4. Create Diagnostic Test
```http
POST /tests
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "name": "Comprehensive Lipid Profile",
  "description": "Measures total cholesterol, HDL, LDL, and triglycerides"
}
```

### 5. Associate Test with Centre
```http
POST /centres/{centre_id}/tests
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "test_id": "b1b36952-b13c-4435-bbd4-fdf054668aa0",
  "price": 850.00
}
```

### 6. Create Booking
```http
POST /bookings
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "centre_id": "a021e8e8-144c-473d-82d3-9bcfe0dd04e4",
  "test_id": "b1b36952-b13c-4435-bbd4-fdf054668aa0",
  "appointment_date": "2026-10-15T09:30:00"
}
```
*Response*:
```json
{
  "id": "e2e92c2e-4b68-450f-bcda-3df473215886",
  "user_id": "...",
  "centre_id": "a021e8e8-144c-473d-82d3-9bcfe0dd04e4",
  "test_id": "b1b36952-b13c-4435-bbd4-fdf054668aa0",
  "appointment_date": "2026-10-15T09:30:00",
  "amount": 850.00,
  "status": "PENDING",
  "created_at": "..."
}
```

### 7. Process Simulated Payment
```http
POST /payments
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "booking_id": "e2e92c2e-4b68-450f-bcda-3df473215886",
  "status": "SUCCESS",
  "payment_reference": "PAY-SIM-1001"
}
```

### 8. Webhook Ingestion
```http
POST /payments/webhook
Content-Type: application/json

{
  "event_id": "evt_wh_987654321",
  "booking_id": "e2e92c2e-4b68-450f-bcda-3df473215886",
  "status": "SUCCESS",
  "payment_reference": "TXN_EXT_55001"
}
```

---

## 13. Database & Schema Design

### Entity Relationship Highlights

1. **CentreTest Stores Centre-Specific Test Pricing**:
   - Different diagnostic centres may charge different prices for the exact same test.
   - `centre_tests` table maintains a compound unique constraint: `UNIQUE(centre_id, test_id)`.
   - The price is stored using a high-precision `Numeric(10, 2)` decimal column.

2. **Booking.amount Stores a Price Snapshot**:
   - When a booking is created, the system fetches the current price from `centre_tests` and saves it into `bookings.amount`.
   - If a diagnostic centre later raises or lowers their test price, existing bookings preserve their original agreed-upon price snapshot.

3. **Payment.amount Comes From Booking.amount**:
   - The client payload does not supply the payment amount.
   - Both the simulated payment endpoint and the webhook extract the exact amount directly from `Booking.amount`, preventing client-side price tampering.

4. **Webhook Event Uniqueness**:
   - `payments.webhook_event_id` is an index-backed nullable column with a `UNIQUE` constraint, providing database-level protection against duplicate webhook deliveries.
   - `payments.payment_reference` is also constrained to be `UNIQUE`.

---

## 14. Booking State Transitions

The application enforces a deterministic, one-way state machine for bookings:

```
                  ┌───────────────┐
                  │    PENDING    │
                  └──┬───┬─────┬──┘
                     │   │     │
          Payment    │   │     │  Payment
          SUCCESS    │   │     │  FAILED
                     │   │     │
                     ▼   │     ▼
        ┌─────────────┐  │   ┌────────────┐
        │  CONFIRMED  │  │   │   FAILED   │
        └─────────────┘  │   └────────────┘
                         │
             User Cancel │
                         ▼
                  ┌─────────────┐
                  │  CANCELLED  │
                  └─────────────┘
```

- **PENDING → CONFIRMED**: Triggered when a payment or webhook reports `SUCCESS`.
- **PENDING → FAILED**: Triggered when a payment or webhook reports `FAILED`.
- **PENDING → CANCELLED**: Triggered when the booking owner calls `/bookings/{id}/cancel`.
- **Terminal States**:
  - Once a booking is in `CONFIRMED`, `FAILED`, or `CANCELLED`, it cannot be transitioned again.
  - Attempting to pay for or cancel an already processed booking yields an `HTTP 400 Bad Request`.
  - Conflicting webhooks received after a terminal state has been reached are rejected with `HTTP 400 Bad Request`.

---

## 15. Webhook Idempotency

External webhook providers (e.g., Stripe, Razorpay) guarantee *at-least-once* delivery, which may result in duplicate webhook payloads.

### How Idempotency is Guaranteed:
1. Every incoming webhook carries a unique `event_id`.
2. The endpoint checks if a `Payment` with `webhook_event_id == event_id` already exists in the database:
   - **Identical Repeated Event**: If the incoming `event_id` exists with the exact same `booking_id` and `status`, the endpoint returns `HTTP 200 OK` with the existing payment record. **No duplicate payment is created, and the booking remains in its confirmed state.**
   - **Conflicting Event**: If the same `event_id` is sent with a conflicting status or booking ID, or if an event tries to overwrite an already finalized booking with a different status, the request is rejected with `HTTP 400 Bad Request`.
3. In addition to application-level checks, a database `UNIQUE` constraint on `payments.webhook_event_id` provides an unbreakable consistency boundary against concurrent race conditions.

---

## 16. Edge Cases Handled

The application features comprehensive validation and error handling:

- **Duplicate Email Registration**: Returns `HTTP 400 Bad Request` if an email is already registered.
- **Invalid Credentials**: Returns `HTTP 401 Unauthorized` for incorrect password or non-existent email without leaking user existence.
- **Malformed / Expired JWT**: Returns `HTTP 401 Unauthorized` with `WWW-Authenticate: Bearer`.
- **Non-Existent Centre / Test**: Returns `HTTP 404 Not Found` when creating associations or bookings.
- **Unavailable Test at Centre**: Returns `HTTP 400 Bad Request` if a user attempts to book a test at a centre that does not offer it.
- **Invalid Pricing**: Returns `HTTP 422 Unprocessable Entity` if price is non-positive or poorly formatted.
- **Past Appointment Dates**: Returns `HTTP 400 Bad Request` if `appointment_date` is in the past.
- **Multi-Tenant Booking Access Control**: Users can only inspect and cancel their own bookings. Attempting to view or cancel another user's booking returns `HTTP 403 Forbidden` (or `404` for listings).
- **Payment on Cancelled Bookings**: Returns `HTTP 400 Bad Request` if payment is attempted on a cancelled booking.
- **Client Amount Manipulation**: Client payloads cannot submit monetary amounts; amounts are strictly computed from `Booking.amount`.
- **Duplicate Payment Reference**: Rejects conflicting duplicate references with `HTTP 400 Bad Request`.
- **Atomic State Consistency**: Payment creation and booking state transitions execute within a single atomic SQLAlchemy database transaction.

---

## 17. Testing

The repository contains a comprehensive automated test suite built with `pytest` and `fastapi.testclient.TestClient`.

### Running Tests
Execute the entire test suite:
```bash
pytest -v
```

### Test Suite Summary
- **Total Tests**: 56
- **Passed**: 56
- **Failed**: 0
- **Skipped**: 0
- **Test Categories**:
  - `tests/test_auth.py` (6 tests): Sign up, duplicate email, login, wrong password, JWT handling, protected `/auth/me`.
  - `tests/test_centres.py` (11 tests): Centre creation, retrieval, association with tests, duplicate associations, invalid prices.
  - `tests/test_tests.py` (6 tests): Test creation, retrieval, available centres with price listings.
  - `tests/test_bookings.py` (16 tests): Booking creation, price snapshot integrity, date validations, permissions, cancellation workflow.
  - `tests/test_payments.py` (17 tests): Simulated payments, atomic booking status updates, webhook idempotency, duplicate reference handling, conflict detection.

All automated tests execute against an isolated in-memory SQLite database (`StaticPool`) configured via `tests/conftest.py`, ensuring tests run reproducibly without altering host environments.

---

## 18. Assumptions

1. **Simulated Payments**: Payments are simulated directly via `/payments` and `/payments/webhook`; no external third-party payment gateway SDK is embedded.
2. **Simplified Role Model**: Any authenticated user can create catalog entries (centres and tests) for testing convenience. A full enterprise RBAC system is outside the scope of this assignment.
3. **No Calendar Slot Inventory**: Bookings validate future appointment dates, but physical time slot capacities/calendars are not restricted.
4. **No Refund / Chargeback Workflow**: Cancellation of a confirmed booking with refund handling is excluded.
5. **No Webhook Cryptographic Signatures**: Standard JSON webhooks are processed with unique event IDs; HMAC signature verification headers are outside the current specification.

---

## 19. What Would Be Improved With More Time

1. **Alembic Database Migrations**: Introduce an Alembic migration pipeline for managing incremental schema revisions and rollbacks in production environments.
2. **Webhook HMAC Signature Verification**: Add cryptographic signing (e.g., `Stripe-Signature` or `X-Razorpay-Signature`) to authenticate webhook dispatchers.
3. **Real Payment Gateway Integration**: Connect to Stripe or Razorpay APIs with webhooks and checkout sessions.
4. **Concurrency Handling & Row Locking**: Implement pessimistic locking (`SELECT ... FOR UPDATE`) in booking/payment flows to prevent race conditions under extreme concurrent load.
5. **Pagination & Filtering**: Add cursor-based pagination and search filters to `/centres`, `/tests`, and `/bookings`.
6. **Structured JSON Logging**: Implement structured, correlation-ID-tagged logging for request tracking and observability.
7. **Rate Limiting**: Protect authentication and payment endpoints against brute-force and abuse using token-bucket rate limiters.
8. **Production Deployment Container**: Build a multi-stage production Dockerfile and Kubernetes deployment manifests.
