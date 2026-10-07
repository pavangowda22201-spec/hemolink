from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import (
    Acceptance,
    AcceptanceStatus,
    BloodRequest,
    Donor,
    User,
    UserType,
)
from app.services.auth_service import decode_access_token
from app.services.tracking_hub import tracking_hub


router = APIRouter(
    prefix="/tracking",
    tags=["tracking"],
)


@router.websocket("/requests/{request_id}")
async def request_tracking(
    websocket: WebSocket,
    request_id: str,
):
    """
    Authenticated live tracking channel for one blood request.

    The dashboard connects with:
    /tracking/requests/{request_id}?token=<JWT>

    Only the hospital that owns the request or an admin can connect.
    """

    db: Session = SessionLocal()

    try:
        token = websocket.query_params.get("token")

        if not token:
            await websocket.close(
                code=1008,
                reason="Authentication required.",
            )
            return

        try:
            payload = decode_access_token(token)
        except Exception:
            await websocket.close(
                code=1008,
                reason="Invalid or expired authentication token.",
            )
            return

        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(
                code=1008,
                reason="Invalid authentication token.",
            )
            return

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user or not user.is_active:
            await websocket.close(
                code=1008,
                reason="Account is inactive or not found.",
            )
            return

        if user.user_type not in (
            UserType.HOSPITAL,
            UserType.ADMIN,
        ):
            await websocket.close(
                code=1008,
                reason="Hospital or admin account required.",
            )
            return

        request = (
            db.query(BloodRequest)
            .filter(BloodRequest.id == request_id)
            .first()
        )

        if not request:
            await websocket.close(
                code=1008,
                reason="Request not found.",
            )
            return

        if (
            user.user_type == UserType.HOSPITAL
            and request.user_id != user.id
        ):
            await websocket.close(
                code=1008,
                reason="You do not own this request.",
            )
            return

        await tracking_hub.connect(request_id, websocket)

        # Send the current active donor locations immediately.
        active_acceptances = (
            db.query(Acceptance, Donor)
            .join(Donor, Acceptance.donor_id == Donor.id)
            .filter(
                Acceptance.request_id == request_id,
                Acceptance.status == AcceptanceStatus.PENDING,
                Donor.latitude.isnot(None),
                Donor.longitude.isnot(None),
            )
            .all()
        )

        for acceptance, donor in active_acceptances:
            await websocket.send_json(
                {
                    "type": "donor_location",
                    "donor_id": donor.id,
                    "donor_name": donor.name,
                    "latitude": donor.latitude,
                    "longitude": donor.longitude,
                    "location_updated_at": (
                        donor.location_updated_at.isoformat()
                        if donor.location_updated_at
                        else None
                    ),
                    "status": acceptance.status.value,
                    "accepted_at": (
                        acceptance.accepted_at.isoformat()
                        if acceptance.accepted_at
                        else None
                    ),
                    "eta_deadline": (
                        acceptance.eta_deadline.isoformat()
                        if acceptance.eta_deadline
                        else None
                    ),
                }
            )

        try:
            while True:
                await websocket.receive_text()

        except WebSocketDisconnect:
            pass

    finally:
        await tracking_hub.disconnect(request_id, websocket)
        db.close()
