from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DiagnosticTest, User
from app.schemas import TestCentreItem, TestCreate, TestDetailResponse, TestResponse

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.post("", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = DiagnosticTest(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("", response_model=List[TestResponse])
def get_all_tests(db: Session = Depends(get_db)):
    tests = db.query(DiagnosticTest).all()
    return tests


@router.get("/{test_id}", response_model=TestDetailResponse)
def get_test(test_id: int, db: Session = Depends(get_db)):
    test = db.get(DiagnosticTest, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic test not found",
        )

    centres = [
        TestCentreItem(
            centre_id=ct.centre_id,
            name=ct.centre.name,
            location=ct.centre.location,
            price=ct.price,
        )
        for ct in test.centres
        if ct.centre is not None
    ]

    return TestDetailResponse(
        id=test.id,
        name=test.name,
        description=test.description,
        centres=centres,
    )
