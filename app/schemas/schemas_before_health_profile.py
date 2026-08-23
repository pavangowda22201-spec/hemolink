"""
RUN LOCATION: Imported by routers/*.py — not run directly.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.models import BloodGroup, UrgencyLevel, RequestStatus, AcceptanceStatus


class DonorCreate(BaseModel):
    name: str
    phone: str
    blood_group: BloodGroup
    latitude: float
    longitude: float


class DonorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    blood_group: BloodGroup
    is_available: bool
    is_verified: bool
    is_suspended: bool
    reliability_score: float
    total_donations: int
    total_no_shows: int
    cooldown_until: Optional[datetime] = None


class RequestCreate(BaseModel):
    hospital_name: str
    blood_group_needed: BloodGroup
    units_needed: int = 1
    urgency: UrgencyLevel
    latitude: float
    longitude: float
    eta_window_minutes: int = 45
    notes: Optional[str] = None


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hospital_name: str
    blood_group_needed: BloodGroup
    units_needed: int
    urgency: UrgencyLevel
    status: RequestStatus
    current_radius_km: float
    created_at: datetime
    fulfilled_at: Optional[datetime] = None


class CandidateOut(BaseModel):
    donor_id: str
    donor_name: str
    distance_km: float
    score: float


class AcceptanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    donor_id: str
    status: AcceptanceStatus
    accepted_at: datetime
    eta_deadline: datetime
    resolved_at: Optional[datetime] = None
