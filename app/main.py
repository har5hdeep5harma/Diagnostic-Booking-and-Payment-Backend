from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine
import app.models  # Registers models on Base.metadata
from app.routers import auth, bookings, centres, payments, tests
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Diagnostic Booking and Payment API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(tests.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return {"status": "ok"}
