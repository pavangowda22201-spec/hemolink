"""
RUN LOCATION: Imported by main.py — not run directly.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BloodRequest, Donor, Acceptance
from app.schemas.schemas import AcceptanceOut
from app.services.acceptance_service import accept_request, fulfill_request

router = APIRouter(prefix="/acceptances", tags=["acceptances"])


@router.get("/donor/{donor_id}", response_model=List[AcceptanceOut])
def get_donor_acceptances(donor_id: str, db: Session = Depends(get_db)):
    """Returns a specific donor's acceptance history (pending, fulfilled, etc.)."""
    return (
        db.query(Acceptance)
        .filter(Acceptance.donor_id == donor_id)
        .order_by(Acceptance.accepted_at.desc())
        .all()
    )


@router.post("/{request_id}/accept/{donor_id}", response_model=AcceptanceOut)
def accept(request_id: str, donor_id: str, db: Session = Depends(get_db)):
    request = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    donor = db.query(Donor).filter(Donor.id == donor_id).first()
    if not request or not donor:
        raise HTTPException(status_code=404, detail="Request or donor not found.")

    try:
        return accept_request(db, request, donor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{acceptance_id}/fulfill", response_model=AcceptanceOut)
def fulfill(acceptance_id: str, db: Session = Depends(get_db)):
    """
    Called by hospital staff when the donor physically arrives and donates.
    Flips this acceptance to FULFILLED and stands down any other pending
    donors on the same request.
    """
    acceptance = db.query(Acceptance).filter(Acceptance.id == acceptance_id).first()
    if not acceptance:
        raise HTTPException(status_code=404, detail="Acceptance not found.")

    try:
        return fulfill_request(db, acceptance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
