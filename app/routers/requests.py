from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import (
    BloodRequest,
    Acceptance,
    Donor,
    User,
    UserType,
)
from app.schemas.schemas import (
    RequestCreate,
    RequestOut,
    AcceptanceOut,
    HospitalAcceptanceOut,
    DonorActiveRequestOut,
    RequestTrackingOut,
)

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


@router.post("/", response_model=RequestOut)
def create_request(
    payload: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a blood request for the authenticated hospital.
    """

    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    request = BloodRequest(
        user_id=current_user.id,
        hospital_name=payload.hospital_name,
        blood_group_needed=payload.blood_group_needed,
        units_needed=payload.units_needed,
        urgency=payload.urgency,
        latitude=payload.latitude,
        longitude=payload.longitude,
        eta_window_minutes=payload.eta_window_minutes,
        notes=payload.notes,
        current_radius_km=5.0,
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


@router.get("/", response_model=List[RequestOut])
def list_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns blood requests visible to the authenticated user.
    Hospitals only see their own requests.
    """

    query = db.query(BloodRequest)

    if current_user.user_type == UserType.HOSPITAL:
        query = query.filter(
            BloodRequest.user_id == current_user.id
        )

    return (
        query
        .order_by(BloodRequest.created_at.desc())
        .all()
    )


@router.get(
    "/donor/active",
    response_model=DonorActiveRequestOut,
)
def get_donor_active_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the authenticated donor's active pending acceptance
    and its associated blood request.
    """

    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = (
        db.query(Donor)
        .filter(Donor.user_id == current_user.id)
        .first()
    )

    if donor is None:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not found.",
        )

    acceptance = (
        db.query(Acceptance)
        .filter(
            Acceptance.donor_id == donor.id,
            Acceptance.status == "pending",
        )
        .order_by(Acceptance.accepted_at.desc())
        .first()
    )

    if acceptance is None:
        raise HTTPException(
            status_code=404,
            detail="No active donation found.",
        )

    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == acceptance.request_id)
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Blood request not found.",
        )

    return DonorActiveRequestOut(
        request=request,
        acceptance=acceptance,
    )


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns a single blood request by ID.
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

    return request


@router.get(
    "/{request_id}/acceptances",
    response_model=List[HospitalAcceptanceOut],
)
def get_request_acceptances(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns donor acceptance details for a hospital's own blood request.
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

    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    if request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only view donors for your own requests.",
        )

    acceptances = (
        db.query(Acceptance, Donor)
        .join(Donor, Donor.id == Acceptance.donor_id)
        .filter(Acceptance.request_id == request_id)
        .order_by(Acceptance.accepted_at.desc())
        .all()
    )

    return [
        HospitalAcceptanceOut(
            id=acceptance.id,
            request_id=acceptance.request_id,
            donor_id=acceptance.donor_id,
            units_fulfilled=acceptance.units_fulfilled,
            status=acceptance.status,
            accepted_at=acceptance.accepted_at,
            eta_deadline=acceptance.eta_deadline,
            resolved_at=acceptance.resolved_at,
            donor_name=donor.name,
            donor_phone=donor.phone,
            donor_blood_group=donor.blood_group,
            donor_is_verified=donor.is_verified,
            donor_reliability_score=donor.reliability_score,
            donor_total_donations=donor.total_donations,
        )
        for acceptance, donor in acceptances
    ]
