"""
RUN LOCATION: Imported by routers/requests.py — not run directly.
Sends (and logs) notifications to candidate donors. The actual SMS/push send
is stubbed — swap send_sms/send_push for a real provider (Twilio, FCM, etc.)
when you're ready to go live.
"""
from typing import List

from sqlalchemy.orm import Session

from app.models.models import NotificationLog, BloodRequest
from app.services.matching_engine import Candidate


def _build_message(request: BloodRequest, dist_km: float) -> str:
    return (
        f"Urgent: {request.blood_group_needed.value} blood needed at "
        f"{request.hospital_name} ({dist_km} km away). Urgency: {request.urgency.value}. "
        f"Tap to accept."
    )


def send_sms(phone: str, message: str) -> None:
    """STUB — wire up a real SMS provider (e.g. Twilio) here."""
    print(f"[SMS -> {phone}] {message}")


def notify_candidates(db: Session, request: BloodRequest, candidates: List[Candidate]) -> None:
    """Notifies each candidate donor and writes an audit log entry."""
    for candidate in candidates:
        message = _build_message(request, candidate.distance_km)
        send_sms(candidate.donor.phone, message)

        log = NotificationLog(
            request_id=request.id,
            donor_id=candidate.donor.id,
            radius_tier_km=request.current_radius_km,
            message=message,
        )
        db.add(log)

    db.commit()
