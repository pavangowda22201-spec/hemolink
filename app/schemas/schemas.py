"""
RUN LOCATION: Imported by routers/*.py — not run directly.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import (
    BloodGroup,
    UrgencyLevel,
    RequestStatus,
    AcceptanceStatus,
)


class DonorCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=32)
    blood_group: BloodGroup
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DonorUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=32)
    blood_group: BloodGroup
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


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
    model_config = ConfigDict(str_strip_whitespace=True)

    hospital_name: str = Field(min_length=2, max_length=160)
    blood_group_needed: BloodGroup
    units_needed: int = Field(default=1, ge=1, le=100)
    urgency: UrgencyLevel
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    eta_window_minutes: int = Field(default=45, ge=5, le=1440)
    notes: Optional[str] = Field(default=None, max_length=2000)


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hospital_name: str
    blood_group_needed: BloodGroup
    units_needed: int
    urgency: UrgencyLevel
    status: RequestStatus
    latitude: float
    longitude: float
    current_radius_km: float
    eta_window_minutes: int
    notes: Optional[str] = None
    created_at: datetime
    fulfilled_at: Optional[datetime] = None


class CandidateOut(BaseModel):
    donor_id: str
    donor_name: str
    distance_km: float
    score: float


class RequestMatchOut(BaseModel):
    """Privacy-minimized candidate data for the hospital workspace."""

    donor_label: str
    blood_group: BloodGroup
    distance_km: float
    score: float
    reliability_score: float
    is_verified: bool
    is_available: bool


class AcceptanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    donor_id: str
    status: AcceptanceStatus
    accepted_at: datetime
    eta_deadline: datetime
    resolved_at: Optional[datetime] = None