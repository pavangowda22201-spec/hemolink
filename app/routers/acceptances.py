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
    Donor,
    Acceptance,
    User,
    UserType,
)
from app.schemas.schemas import AcceptanceOut
from app.services.acceptance_service import accept_request, fulfill_request


router = APIRouter(
    prefix="/acceptances",
    tags=["acceptances"],
)


@router.get(
    "/donor/{donor_id}",
    response_model=List[AcceptanceOut],
)
def get_donor_acceptances(
    donor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a donor's acceptance history.

    Donors can only access their own acceptance history.
    Hospitals/admins are not allowed through this donor endpoint.
    """
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = (
        db.query(Donor)
        .filter(
            Donor.id == donor_id,
            Donor.user_id == current_user.id,
        )
        .first()
    )

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not found for this account.",
        )

    return (
        db.query(Acceptance)
        .filter(Acceptance.donor_id == donor.id)
        .order_by(Acceptance.accepted_at.desc())
        .all()
    )


@router.post(
    "/{request_id}/accept/{donor_id}",
    response_model=AcceptanceOut,
)
def accept(
    request_id: str,
    donor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authenticated donor accepts a blood request.

    The donor identity is taken from the authenticated account.
    The donor_id path parameter must match that account's donor profile.
    """

    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    request = (
        db.query(BloodRequest)
        .filter(BloodRequest.id == request_id)
        .first()
    )

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Request not found.",
        )

    donor = (
        db.query(Donor)
        .filter(
            Donor.id == donor_id,
            Donor.user_id == current_user.id,
        )
        .first()
    )

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not found for this account.",
        )

    try:
        acceptance = accept_request(
            db,
            request,
            donor,
        )

        # Store authenticated identity on the acceptance record.
        acceptance.user_id = current_user.id
        db.commit()
        db.refresh(acceptance)

        return acceptance

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "/{acceptance_id}/fulfill",
    response_model=AcceptanceOut,
)
def fulfill(
    acceptance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Called by hospital staff when the donor physically arrives
    and completes the donation.

    Only the authenticated hospital that created the request
    can fulfill its acceptance.
    """

    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    acceptance = (
        db.query(Acceptance)
        .filter(Acceptance.id == acceptance_id)
        .first()
    )

    if not acceptance:
        raise HTTPException(
            status_code=404,
            detail="Acceptance not found.",
        )

    request = (
        db.query(BloodRequest)
        .filter(
            BloodRequest.id == acceptance.request_id,
            BloodRequest.user_id == current_user.id,
        )
        .first()
    )

    if not request:
        raise HTTPException(
            status_code=403,
            detail="This request does not belong to the authenticated hospital.",
        )

    try:
        return fulfill_request(
            db,
            acceptance,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
