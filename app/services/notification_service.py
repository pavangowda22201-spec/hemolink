"""
RUN LOCATION: Imported by routers/requests.py — not run directly.
Sends (and logs) notifications to candidate donors.

The actual SMS/push send is stubbed — swap send_sms/send_push
for a real provider (Twilio, FCM, etc.) when you're ready to go live.

A fulfilled request must never generate new donor notifications.
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.models import (
    NotificationLog,
    BloodRequest,
    RequestStatus,
)
from app.services.matching_engine import Candidate


def _build_message(request: BloodRequest, dist_km: float) -> str:
    remaining_units = max(
        0,
        request.units_needed - request.fulfilled_units,
    )

    return (
        f"Urgent: {request.blood_group_needed.value} blood needed at "
        f"{request.hospital_name} ({dist_km} km away). "
        f"Urgency: {request.urgency.value}. "
        f"Units remaining: {remaining_units}. "
        f"Tap to accept."
    )


def send_sms(phone: str, message: str) -> None:
    """STUB — wire up a real SMS provider (e.g. Twilio) here."""
    print(f"[SMS -> {phone}] {message}")


def notify_candidates(
    db: Session,
    request: BloodRequest,
    candidates: List[Candidate],
) -> None:
    """
    Notify eligible candidate donors and write audit logs.

    A fully fulfilled request is closed to new donor notifications.
    Partially fulfilled requests may continue notifying donors for
    their remaining units.
    """

    if request.status == RequestStatus.FULFILLED:
        return

    remaining_units = max(
        0,
        request.units_needed - request.fulfilled_units,
    )

    if remaining_units <= 0:
        return

    for candidate in candidates:
        message = _build_message(
            request,
            candidate.distance_km,
        )

        send_sms(
            candidate.donor.phone,
            message,
        )

        log = NotificationLog(
            request_id=request.id,
            donor_id=candidate.donor.id,
            radius_tier_km=request.current_radius_km,
            message=message,
        )

        db.add(log)

    db.commit()