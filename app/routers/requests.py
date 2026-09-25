"""
RUN LOCATION: Imported by main.py — not run directly.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import (
    BloodRequest,
    Acceptance,
    AcceptanceStatus,
    RequestStatus,
    User,
    UserType,
)
from app.schemas.schemas import (
    RequestCreate,
    RequestOut,
    CandidateOut,
    RequestMatchOut,
    AcceptanceOut,
    DonorActiveRequestOut,
    RequestTrackingOut,
    DonorTrackingOut,
)
from app.services.matching_engine import find_candidates_at_radius, match_request
from app.services.notification_service import notify_candidates

router = APIRouter(prefix="/requests", tags=["requests"])


def _redact_donor_name(name: str) -> str:
    """Return a useful but privacy-minimized donor label for hospital matching."""
    parts = [part for part in name.split() if part]

    if not parts:
        return "Verified donor"

    return " ".join(
        f"{part[0].upper()}\u2022\u2022\u2022"
        for part in parts[:2]
    )


@router.get("/", response_model=List[RequestOut])
def list_requests(
    db: Session = Depends(get_db),
):
    """Returns all blood requests, most recently created first."""
    return (
        db.query(BloodRequest)
        .order_by(BloodRequest.created_at.desc())
        .all()
    )


@router.get(
    "/{request_id}/acceptances",
    response_model=List[AcceptanceOut],
)
def get_request_acceptances(
    request_id: str,
    db: Session = Depends(get_db),
):
    """Returns every donor acceptance for a request."""
    return (
        db.query(Acceptance)
        .filter(Acceptance.request_id == request_id)
        .all()
    )


@router.get(
    "/donor/active",
    response_model=DonorActiveRequestOut | None,
)
def get_donor_active_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the donor's current active accepted request.

    Only the authenticated donor can access this endpoint.
    A pending acceptance is considered active.
    """

    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    acceptance = (
        db.query(Acceptance)
        .filter(
            Acceptance.user_id == current_user.id,
            Acceptance.status == AcceptanceStatus.PENDING,
        )
        .order_by(Acceptance.accepted_at.desc())
        .first()
    )

    if not acceptance:
        return None

    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == acceptance.request_id)
        .first()
    )

    if not request:
        return None

    return DonorActiveRequestOut(
        request=request,
        acceptance=acceptance,
    )


@router.get(
    "/{request_id}/tracking",
    response_model=RequestTrackingOut,
)
def get_request_tracking(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns live donor tracking data for the owning hospital."""

    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    request = (
        db.query(BloodRequest)
        .filter(
            BloodRequest.id == request_id,
            BloodRequest.user_id == current_user.id,
        )
        .first()
    )

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Request not found for this hospital.",
        )

    acceptances = (
        db.query(Acceptance)
        .filter(
            Acceptance.request_id == request.id,
            Acceptance.status.in_(
                [
                    AcceptanceStatus.PENDING,
                    AcceptanceStatus.FULFILLED,
                ]
            ),
        )
        .order_by(Acceptance.accepted_at.asc())
        .all()
    )

    donors = []

    for acceptance in acceptances:
        donor = acceptance.donor

        if not donor:
            continue

        donors.append(
            DonorTrackingOut(
                donor_id=donor.id,
                donor_name=_redact_donor_name(donor.name),
                latitude=donor.latitude,
                longitude=donor.longitude,
                status=acceptance.status,
                accepted_at=acceptance.accepted_at,
                eta_deadline=acceptance.eta_deadline,
                resolved_at=acceptance.resolved_at,
            )
        )

    return RequestTrackingOut(
        request_id=request.id,
        hospital_latitude=request.latitude,
        hospital_longitude=request.longitude,
        donors=donors,
    )