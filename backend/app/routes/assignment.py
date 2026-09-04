from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.services.assessment import (
    create_assignment,
    get_assignment_by_number,
)


router = APIRouter(
    prefix="/api/v1/assignments",
    tags=["assignments"],
)


class AssignmentCreateRequest(BaseModel):
    assignment_number: str
    assignment_name: str


@router.post("")
def create_assignment_endpoint(
    request: AssignmentCreateRequest,
    db: Session = Depends(get_db),
):
    assignment_number = request.assignment_number.strip()
    assignment_name = request.assignment_name.strip()

    if not assignment_number:
        raise HTTPException(
            status_code=400,
            detail="Assignment number is required",
        )

    if not assignment_name:
        raise HTTPException(
            status_code=400,
            detail="Assignment name is required",
        )

    existing = get_assignment_by_number(
        db,
        assignment_number,
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Assignment number already exists",
        )

    assignment = create_assignment(
        db=db,
        assignment_number=assignment_number,
        assignment_name=assignment_name,
    )

    return {
        "assignment_id": assignment.assignment_id,
        "assignment_number": assignment.assignment_number,
        "assignment_name": assignment.assignment_name,
        "created_at": assignment.created_at,
    }


@router.get("/{assignment_number}")
def get_assignment_endpoint(
    assignment_number: str,
    db: Session = Depends(get_db),
):
    assignment = get_assignment_by_number(
        db,
        assignment_number,
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found",
        )

    return {
        "assignment_id": assignment.assignment_id,
        "assignment_number": assignment.assignment_number,
        "assignment_name": assignment.assignment_name,
        "created_at": assignment.created_at,
    }
