from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CentreTest, DiagnosticCentre, DiagnosticTest, User
from app.schemas import (
    CentreCreate,
    CentreDetailResponse,
    CentreResponse,
    CentreTestCreate,
    CentreTestItem,
    CentreTestResponse,
)

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.post("", response_model=CentreResponse, status_code=status.HTTP_201_CREATED)
def create_centre(
    payload: CentreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    centre = DiagnosticCentre(
        name=payload.name.strip(),
        location=payload.location.strip(),
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("", response_model=List[CentreResponse])
def get_all_centres(db: Session = Depends(get_db)):
    centres = db.query(DiagnosticCentre).all()
    return centres


@router.get("/{centre_id}", response_model=CentreDetailResponse)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic centre not found",
        )

    tests = [
        CentreTestItem(
            test_id=ct.test_id,
            name=ct.test.name,
            description=ct.test.description,
            price=ct.price,
        )
        for ct in centre.offered_tests
        if ct.test is not None
    ]

    return CentreDetailResponse(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        tests=tests,
    )


@router.post(
    "/{centre_id}/tests",
    response_model=CentreTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_test_to_centre(
    centre_id: int,
    payload: CentreTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic centre not found",
        )

    test = db.get(DiagnosticTest, payload.test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic test not found",
        )

    existing_association = (
        db.query(CentreTest)
        .filter(
            CentreTest.centre_id == centre_id,
            CentreTest.test_id == payload.test_id,
        )
        .first()
    )
    if existing_association:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diagnostic test already offered by this centre",
        )

    centre_test = CentreTest(
        centre_id=centre_id,
        test_id=payload.test_id,
        price=payload.price,
    )
    db.add(centre_test)
    db.commit()
    db.refresh(centre_test)

    return centre_test
