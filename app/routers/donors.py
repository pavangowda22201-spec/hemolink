"""
RUN LOCATION: Imported by main.py — not run directly.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Donor
from app.schemas.schemas import DonorCreate, DonorOut

router = APIRouter(prefix="/donors", tags=["donors"])


@router.get("/", response_model=List[DonorOut])
def list_donors(db: Session = Depends(get_db)):
    """Returns all registered donors, most recently registered first."""
    return db.query(Donor).order_by(Donor.created_at.desc()).all()


@router.post("/", response_model=DonorOut)
def register_donor(payload: DonorCreate, db: Session = Depends(get_db)):
    existing = db.query(Donor).filter(Donor.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="A donor with this phone number already exists.")

    donor = Donor(**payload.dict())
    db.add(donor)
    db.commit()
    db.refresh(donor)
    return donor


@router.get("/{donor_id}", response_model=DonorOut)
def get_donor(donor_id: str, db: Session = Depends(get_db)):
    donor = db.query(Donor).filter(Donor.id == donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found.")
    return donor


@router.post("/{donor_id}/verify", response_model=DonorOut)
def verify_donor(donor_id: str, db: Session = Depends(get_db)):
    """
    Called by hospital staff after a donor's FIRST donation is confirmed
    in person. Sets the verified badge / trust boost.
    """
    donor = db.query(Donor).filter(Donor.id == donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found.")

    donor.is_verified = True
    db.commit()
    db.refresh(donor)
    return donor
