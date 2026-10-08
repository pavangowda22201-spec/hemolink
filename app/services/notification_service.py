"""
RUN LOCATION: Imported by routers/requests.py — not run directly.

Sends (and logs) notifications to candidate donors.

The actual SMS/push send is stubbed — swap send_sms/send_push
for a real provider (Twilio, FCM, etc.) when you're ready to go live.

A fulfilled request must never generate new donor notifications.

A donor is notified at most once per request. When the matching radius
expands, only newly discovered donors are notified.
"""

from typing import List
import json
import urllib.request
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

def send_push(push_token: str, message: str) -> None:
    """Send an emergency push notification through Expo."""
    payload = {
        "to": push_token,
        "sound": "default",
        "title": "HemoLink Emergency",
        "body": message,
        "channelId": "hemolink-emergency",
        "priority": "high",
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        "https://exp.host/--/api/v2/push/send",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        result = response.read().decode("utf-8")
        print(f"[EXPO PUSH] {response.status}: {result}")

def _already_notified(
    db: Session,
    request_id: str,
    donor_id: str,
) -> bool:
    """Return True if this donor has already been notified for this request."""
    return (
        db.query(NotificationLog)
        .filter(
            NotificationLog.request_id == request_id,
            NotificationLog.donor_id == donor_id,
        )
        .first()
        is not None
    )


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

    A donor is notified only once for a given request, so radius
    expansion does not duplicate notifications to donors who were
    already contacted at a smaller radius.
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
        if _already_notified(
            db,
            request.id,
            candidate.donor.id,
        ):
            continue

        message = _build_message(
            request,
            candidate.distance_km,
        )

        if candidate.donor.push_token:
            try:
                send_push(
                    candidate.donor.push_token,
                    message,
                )
            except Exception as exc:
                print(
                    f'[EXPO PUSH ERROR -> donor {candidate.donor.id}] {exc}'
                )
        else:
            print(
                f'[EXPO PUSH SKIPPED -> donor {candidate.donor.id}] No push token registered.'
            )

        log = NotificationLog(
            request_id=request.id,
            donor_id=candidate.donor.id,
            radius_tier_km=request.current_radius_km,
            message=message,
        )

        db.add(log)

    db.commit()
