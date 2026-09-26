from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import (
    BloodRequest,
    Acceptance,
    User,
)
from app.schemas.schemas import (
    RequestOut,
    AcceptanceOut,
    DonorActiveRequestOut,
    RequestTrackingOut,
)


router = APIRouter(
    prefix="/requests",
    tags=["requests"],
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


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
):
    """Returns a single blood request by ID."""
    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == request_id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found",
        )

    return request


@router.get(
    "/{request_id}/acceptances",
    response_model=List[AcceptanceOut],
)
def get_request_acceptances(
    request_id: str,
    db: Session = Depends(get_db),
):
    """Returns every donor acceptance for a request."""
    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == request_id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found",
        )

    return (
        db.query(Acceptance)
        .filter(Acceptance.request_id == request_id)
        .order_by(Acceptance.accepted_at.desc())
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
    Returns the authenticated donor's current active request,
    including the request and acceptance information.
    """

    acceptance = (
        db.query(Acceptance)
        .filter(
            Acceptance.user_id == current_user.id,
            Acceptance.status == "PENDING",
        )
        .order_by(Acceptance.accepted_at.desc())
        .first()
    )

    if acceptance is None:
        return None

    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == acceptance.request_id)
        .first()
    )

    if request is None:
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
    """
    Returns live donor tracking information for a hospital-owned request.
    """

    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == request_id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found",
        )

    if request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to track this request",
        )

    acceptance = (
        db.query(Acceptance)
        .filter(
            Acceptance.request_id == request_id,
            Acceptance.status == "PENDING",
        )
        .order_by(Acceptance.accepted_at.desc())
        .first()
    )

    if acceptance is None:
        return RequestTrackingOut(
            request_id=request.id,
            hospital_name=request.hospital_name,
            hospital_latitude=request.latitude,
            hospital_longitude=request.longitude,
            donor_id=None,
            donor_latitude=None,
            donor_longitude=None,
            acceptance_id=None,
            status=None,
            accepted_at=None,
            eta_deadline=None,
        )

    donor = None

    if acceptance.donor_id:
        from app.models.models import Donor

        donor = (
            db.query(Donor)
            .filter(Donor.id == acceptance.donor_id)
            .first()
        )

    return RequestTrackingOut(
        request_id=request.id,
        hospital_name=request.hospital_name,
        hospital_latitude=request.latitude,
        hospital_longitude=request.longitude,
        donor_id=acceptance.donor_id,
        donor_latitude=donor.latitude if donor else None,
        donor_longitude=donor.longitude if donor else None,
        acceptance_id=acceptance.id,
        status=acceptance.status,
        accepted_at=acceptance.accepted_at,
        eta_deadline=acceptance.eta_deadline,
    )