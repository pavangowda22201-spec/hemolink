"""
RUN LOCATION: Imported by main.py — not run directly.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BloodRequest, Acceptance
from app.schemas.schemas import (
    RequestCreate,
    RequestOut,
    CandidateOut,
    RequestMatchOut,
    AcceptanceOut,
)
from app.services.matching_engine import find_candidates_at_radius, match_request
from app.services.notification_service import notify_candidates

router = APIRouter(prefix="/requests", tags=["requests"])


def _redact_donor_name(name: str) -> str:
    """Return a useful but privacy-minimized donor label for hospital matching."""
    parts = [part for part in name.split() if part]
    if not parts:
        return "Verified donor"
    return " ".join(f"{part[0].upper()}\u2022\u2022\u2022" for part in parts[:2])


@router.get("/", response_model=List[RequestOut])
def list_requests(db: Session = Depends(get_db)):
    """Returns all blood requests, most recently created first."""
    return db.query(BloodRequest).order_by(BloodRequest.created_at.desc()).all()


@router.get("/{request_id}/acceptances", response_model=List[AcceptanceOut])
def get_request_acceptances(request_id: str, db: Session = Depends(get_db)):
    """Returns every donor acceptance (pending, fulfilled, stood down, no-show) for a request."""
    return db.query(Acceptance).filter(Acceptance.request_id == request_id).all()


@router.get("/{request_id}/matches", response_model=List[RequestMatchOut])
def get_request_matches(request_id: str, db: Session = Depends(get_db)):
    """
    Returns the current eligible donor pool at the request's already-selected
    search radius. This is read-only: it does not re-notify donors or rematch.
    """
    request = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")

    candidates = find_candidates_at_radius(db, request, request.current_radius_km)
    return [
        RequestMatchOut(
            donor_label=_redact_donor_name(candidate.donor.name),
            blood_group=candidate.donor.blood_group,
            distance_km=candidate.distance_km,
            score=candidate.score,
            reliability_score=candidate.donor.reliability_score,
            is_verified=candidate.donor.is_verified,
            is_available=candidate.donor.is_available,
        )
        for candidate in candidates
    ]


@router.post("/", response_model=RequestOut)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    """
    Creates a request AND immediately runs the tiered matching + notification
    flow (5km -> 10km -> 20km until enough eligible donors are found).
    """
    request = BloodRequest(**payload.dict())
    db.add(request)
    db.commit()
    db.refresh(request)

    candidates = match_request(db, request)
    notify_candidates(db, request, candidates)

    return request


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: str, db: Session = Depends(get_db)):
    request = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")
    return request


@router.post("/{request_id}/rematch", response_model=list[CandidateOut])
def rematch_request(request_id: str, db: Session = Depends(get_db)):
    """
    Manually re-run matching for a request (e.g. after a no-show leaves it
    still unfulfilled). Notifies any newly found candidates.
    """
    request = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")

    candidates = match_request(db, request)
    notify_candidates(db, request, candidates)

    return [
        CandidateOut(
            donor_id=c.donor.id,
            donor_name=c.donor.name,
            distance_km=c.distance_km,
            score=c.score,
        )
        for c in candidates
    ]
