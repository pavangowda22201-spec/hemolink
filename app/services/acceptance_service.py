"""
RUN LOCATION: Imported by routers/acceptances.py — not run directly.
Implements parallel confirmation: several donors can accept the same request;
the first to actually complete the donation fulfills it, the rest stand down.
Also implements the ETA timer and no-show flagging.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    Acceptance, AcceptanceStatus, BloodRequest, RequestStatus, Donor
)
from app.services.reliability_service import (
    reward_successful_donation, penalize_no_show, is_eligible_for_matching
)


def accept_request(db: Session, request: BloodRequest, donor: Donor) -> Acceptance:
    """
    A donor accepts a request. Multiple donors may hold a PENDING acceptance
    on the same request at once — this is intentional (parallel confirmation).
    """
    if not is_eligible_for_matching(donor):
        raise ValueError("Donor is not currently eligible (suspended, unavailable, or in cooldown).")
    if donor.has_active_request(db):
        raise ValueError("Donor already has an active accepted request.")
    if request.status not in (RequestStatus.OPEN, RequestStatus.MATCHING):
        raise ValueError("Request is no longer open for acceptance.")

    acceptance = Acceptance(
        request_id=request.id,
        donor_id=donor.id,
        status=AcceptanceStatus.PENDING,
        eta_deadline=datetime.utcnow() + timedelta(minutes=request.eta_window_minutes),
    )
    donor.is_available = False  # locked out of other matching while pending
    request.status = RequestStatus.MATCHING

    db.add(acceptance)
    db.commit()
    db.refresh(acceptance)
    return acceptance


def fulfill_request(db: Session, acceptance: Acceptance) -> Acceptance:
    """
    Called when a donor actually completes the donation (e.g. hospital check-in).
    This donor is marked FULFILLED; every other PENDING acceptance on the same
    request is stood down and those donors freed up for future matching.
    """
    if acceptance.status != AcceptanceStatus.PENDING:
        raise ValueError("This acceptance is no longer pending.")

    now = datetime.utcnow()
    acceptance.status = AcceptanceStatus.FULFILLED
    acceptance.resolved_at = now

    request = acceptance.request
    request.status = RequestStatus.FULFILLED
    request.fulfilled_at = now

    reward_successful_donation(db, acceptance.donor)
    acceptance.donor.is_available = True

    # Stand down every other pending acceptance on this request
    other_pending = db.query(Acceptance).filter(
        Acceptance.request_id == request.id,
        Acceptance.id != acceptance.id,
        Acceptance.status == AcceptanceStatus.PENDING,
    ).all()

    for other in other_pending:
        other.status = AcceptanceStatus.STOOD_DOWN
        other.resolved_at = now
        other.donor.is_available = True  # freed up, no penalty — they didn't fail

    db.commit()
    db.refresh(acceptance)
    return acceptance


def check_and_flag_no_shows(db: Session) -> int:
    """
    Run this periodically (e.g. every minute via a scheduler/cron — see
    scripts/no_show_checker.py). Flags any PENDING acceptance whose ETA
    deadline has passed as a NO_SHOW and penalizes the donor.
    Returns the number of acceptances flagged.
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

        # Request stays open/matching so other pending donors (or a fresh
        # match run) can still fulfill it.

    db.commit()
    return len(overdue)
