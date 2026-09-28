"""
RUN LOCATION: Imported by routers/acceptances.py — not run directly.
Implements parallel confirmation and multi-donor fulfillment.

Multiple donors can hold a PENDING acceptance on the same request.
Each completed acceptance contributes units toward the request.
The request remains open/matching until all required units are fulfilled.
Also implements the ETA timer and no-show flagging.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    Acceptance,
    AcceptanceStatus,
    BloodRequest,
    RequestStatus,
    Donor,
)
from app.services.reliability_service import (
    reward_successful_donation,
    penalize_no_show,
    is_eligible_for_matching,
)
from app.services.blood_compatibility import is_compatible



def accept_request(db: Session, request: BloodRequest, donor: Donor) -> Acceptance:
    """
    A donor accepts a request.

    Multiple donors may hold a PENDING acceptance on the same request at once.
    This is intentional for parallel confirmation and multi-donor fulfillment.
    """
    if not is_eligible_for_matching(donor):
        raise ValueError(
            "Donor is not currently eligible (suspended, unavailable, or in cooldown)."
        )

    if not is_compatible(
        donor.blood_group,
        request.blood_group_needed,
    ):
        raise ValueError(
            "Donor blood group is not compatible with this request."
        )

    if donor.has_active_request(db):
        raise ValueError("Donor already has an active accepted request.")

    if request.status not in (RequestStatus.OPEN, RequestStatus.MATCHING):
        raise ValueError("Request is no longer open for acceptance.")

    remaining_units = max(
        0,
        request.units_needed - request.fulfilled_units,
    )

    if remaining_units <= 0:
        raise ValueError("Request has already been fully fulfilled.")

    acceptance = Acceptance(
        request_id=request.id,
        donor_id=donor.id,
        units_fulfilled=1,
        status=AcceptanceStatus.PENDING,
        eta_deadline=datetime.utcnow()
        + timedelta(minutes=request.eta_window_minutes),
    )

    donor.is_available = False
    request.status = RequestStatus.MATCHING

    db.add(acceptance)
    db.commit()
    db.refresh(acceptance)

    return acceptance


def fulfill_request(db: Session, acceptance: Acceptance) -> Acceptance:
    """
    Called when a donor actually completes the donation.

    Each successful acceptance contributes one unit by default.
    The request remains open/matching while units are still outstanding.

    Once all required units are fulfilled:
      - the request becomes FULFILLED
      - fulfilled_at is recorded
      - all other pending donors are stood down
      - those donors become available again

    Only the hospital fulfillment action counts a donation as completed.
    """

    if acceptance.status != AcceptanceStatus.PENDING:
        raise ValueError("This acceptance is no longer pending.")

    request = acceptance.request

    if request.status not in (
        RequestStatus.OPEN,
        RequestStatus.MATCHING,
    ):
        raise ValueError("Request is no longer accepting fulfillment.")

    remaining_units = max(
        0,
        request.units_needed - request.fulfilled_units,
    )

    if remaining_units <= 0:
        raise ValueError("Request has already been fully fulfilled.")

    now = datetime.utcnow()

    # One donor acceptance contributes one unit.
    units_to_fulfill = min(
        acceptance.units_fulfilled,
        remaining_units,
    )

    if units_to_fulfill <= 0:
        raise ValueError("No units remain to be fulfilled.")

    acceptance.units_fulfilled = units_to_fulfill
    acceptance.status = AcceptanceStatus.FULFILLED
    acceptance.resolved_at = now

    request.fulfilled_units += units_to_fulfill

    reward_successful_donation(db, acceptance.donor)
    acceptance.donor.is_available = True

    if request.fulfilled_units >= request.units_needed:
        # All required units have been fulfilled.
        request.fulfilled_units = request.units_needed
        request.status = RequestStatus.FULFILLED
        request.fulfilled_at = now

        # No additional donors are needed.
        other_pending = db.query(Acceptance).filter(
            Acceptance.request_id == request.id,
            Acceptance.id != acceptance.id,
            Acceptance.status == AcceptanceStatus.PENDING,
        ).all()

        for other in other_pending:
            other.status = AcceptanceStatus.STOOD_DOWN
            other.resolved_at = now
            other.donor.is_available = True
    else:
        # More units are still required.
        request.status = RequestStatus.MATCHING
        request.fulfilled_at = None

        # Other pending donors remain active because their contributions
        # may be needed for the remaining units.

    db.commit()
    db.refresh(acceptance)

    return acceptance


def check_and_flag_no_shows(db: Session) -> int:
    """
    Run this periodically (e.g. every minute via a scheduler/cron — see
    scripts/no_show_checker.py).

    Flags any PENDING acceptance whose ETA deadline has passed as a NO_SHOW
    and penalizes the donor.

    The request remains open/matching so other pending donors or a fresh
    matching run can still fulfill the remaining units.
    """
    now = datetime.utcnow()

    overdue = db.query(Acceptance).filter(
        Acceptance.status == AcceptanceStatus.PENDING,
        Acceptance.eta_deadline < now,
    ).all()

    for acceptance in overdue:
        acceptance.status = AcceptanceStatus.NO_SHOW
        acceptance.resolved_at = now
        acceptance.donor.is_available = True

        penalize_no_show(db, acceptance.donor)

    db.commit()

    return len(overdue)
