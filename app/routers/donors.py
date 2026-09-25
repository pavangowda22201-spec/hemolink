from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import Donor, User, UserType
from app.schemas.schemas import DonorCreate, DonorOut

router = APIRouter(prefix="/donors", tags=["donors"])


@router.get("/", response_model=List[DonorOut])
def list_donors(db: Session = Depends(get_db)):
    return db.query(Donor).order_by(Donor.created_at.desc()).all()


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

    donor = db.query(Donor).filter(Donor.user_id == current_user.id).first()

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

    donor = Donor(**payload.dict())

    db.add(donor)
    db.commit()
    db.refresh(donor)

    return donor


@router.get("/{donor_id}", response_model=DonorOut)
def get_donor(
    donor_id: str,
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(
        Donor.id == donor_id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor not found.",
        )

    return donor


@router.post("/{donor_id}/verify", response_model=DonorOut)
def verify_donor(
    donor_id: str,
    db: Session = Depends(get_db),
):
    donor = db.query(Donor).filter(
        Donor.id == donor_id
    ).first()

    if not donor:
        raise HTTPException(
            status_code=404,
            detail="Donor not found.",
        )

    donor.is_verified = True

    db.commit()
    db.refresh(donor)

    return donor