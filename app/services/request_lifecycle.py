"""
RUN LOCATION: Imported by background workers/services — not run directly.

Handles automatic lifecycle transitions for blood requests.

A request that remains active beyond the configured maximum lifetime
is marked EXPIRED. Any pending donor acceptances are stood down and
those donors are made available again.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    Acceptance,
    AcceptanceStatus,
    BloodRequest,
    RequestStatus,
)


REQUEST_MAX_AGE_HOURS = 6


def expire_stale_requests(db: Session) -> int:
    """
    Expire active requests older than REQUEST_MAX_AGE_HOURS.

    Returns the number of requests expired.

    Fulfilled, cancelled, and already-expired requests are ignored.
    Pending donor acceptances are stood down and their donors are
    returned to the available pool.
    """

    cutoff = datetime.utcnow() - timedelta(
        hours=REQUEST_MAX_AGE_HOURS
    )

    stale_requests = (
        db.query(BloodRequest)
        .filter(
            BloodRequest.status.in_(
                [
                    RequestStatus.OPEN,
                    RequestStatus.MATCHING,
                ]
            ),
            BloodRequest.created_at < cutoff,
        )
        .all()
    )

    if not stale_requests:
        return 0

    now = datetime.utcnow()

    for request in stale_requests:
        request.status = RequestStatus.EXPIRED

        pending_acceptances = (
            db.query(Acceptance)
            .filter(
                Acceptance.request_id == request.id,
                Acceptance.status == AcceptanceStatus.PENDING,
            )
            .all()
        )

        for acceptance in pending_acceptances:
            acceptance.status = AcceptanceStatus.STOOD_DOWN
            acceptance.resolved_at = now
            acceptance.donor.is_available = True

    db.commit()

    return len(stale_requests)