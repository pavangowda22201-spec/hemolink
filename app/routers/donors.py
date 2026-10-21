from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import BloodGroup, Donor, User, UserType
from app.schemas.schemas import (
    DonorCreate,
    DonorOut,
    DonorUpdate,
    DonorLocationUpdate,
    PushTokenUpdate,
    HospitalDonorOut,
)

router = APIRouter(prefix="/donors", tags=["donors"])


@router.get("/", response_model=list[DonorOut])
def list_donors(db: Session = Depends(get_db)):
    return db.query(Donor).order_by(Donor.created_at.desc()).all()


@router.get("/search", response_model=list[HospitalDonorOut])
def search_donors(
    name: Optional[str] = Query(default=None, max_length=120),
    phone: Optional[str] = Query(default=None, max_length=32),
    blood_group: Optional[BloodGroup] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search registered donors using privacy-minimized hospital data."""
    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    query = db.query(Donor)

    if name and name.strip():
        query = query.filter(Donor.name.ilike(f"%{name.strip()}%"))

    if phone and phone.strip():
        query = query.filter(Donor.phone.ilike(f"%{phone.strip()}%"))

    if blood_group is not None:
        query = query.filter(Donor.blood_group == blood_group)

    return query.order_by(Donor.name.asc()).limit(limit).all()


@router.patch("/{donor_id}/verify", response_model=HospitalDonorOut)
def verify_donor(
    donor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a donor as identity-verified by an authenticated hospital."""
    if current_user.user_type != UserType.HOSPITAL:
        raise HTTPException(
            status_code=403,
            detail="Hospital account required.",
        )

    donor = db.query(Donor).filter(Donor.id == donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found.")

    donor.is_verified = True
    db.commit()
    db.refresh(donor)
    return donor

@router.get("/me", response_model=DonorOut)
def get_my_donor_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not created yet.",
        )

    return donor


@router.post("/me", response_model=DonorOut)
def create_my_donor_profile(
    payload: DonorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    existing = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Donor profile already exists for this account.",
        )

    phone = current_user.phone or payload.phone

    existing_phone = db.query(Donor).filter(
        Donor.phone == phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="A donor with this phone number already exists.",
        )

    donor = Donor(
        user_id=current_user.id,
        name=payload.name,
        phone=phone,
        blood_group=payload.blood_group,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    db.add(donor)
    db.commit()
    db.refresh(donor)

    return donor


@router.put("/me", response_model=DonorOut)
def update_my_donor_profile(
    payload: DonorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not created yet.",
        )

    existing_phone = db.query(Donor).filter(
        Donor.phone == payload.phone,
        Donor.id != donor.id,
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="A donor with this phone number already exists.",
        )

    donor.name = payload.name
    donor.phone = payload.phone
    donor.blood_group = payload.blood_group
    donor.latitude = payload.latitude
    donor.longitude = payload.longitude

    db.commit()
    db.refresh(donor)

    return donor


@router.patch("/me/availability", response_model=DonorOut)
def update_my_availability(
    is_available: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not created yet.",
        )

    donor.is_available = is_available

    db.commit()
    db.refresh(donor)

    return donor


@router.patch("/me/location", response_model=DonorOut)
def update_my_location(
    payload: DonorLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not created yet.",
        )

    donor.latitude = payload.latitude
    donor.longitude = payload.longitude
    donor.location_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(donor)

    return donor


@router.patch("/me/push-token", response_model=DonorOut)
def update_my_push_token(
    payload: PushTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_type != UserType.DONOR:
        raise HTTPException(
            status_code=403,
            detail="Donor account required.",
        )

    donor = db.query(Donor).filter(
        Donor.user_id == current_user.id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not created yet.",
        )

    push_token = payload.push_token.strip()

    if not push_token:
        raise HTTPException(
            status_code=400,
            detail="Push token cannot be empty.",
        )

    donor.push_token = push_token

    db.commit()
    db.refresh(donor)

    return donor


@router.post("/", response_model=DonorOut)
def register_donor(
    payload: DonorCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(Donor).filter(
        Donor.phone == payload.phone
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="A donor with this phone number already exists.",
        )

    donor = Donor(
        name=payload.name,
        phone=payload.phone,
        blood_group=payload.blood_group,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    db.add(donor)
    db.commit()
    db.refresh(donor)

    return donor
