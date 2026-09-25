"""
RUN LOCATION: Imported by main.py — not run directly.
This file defines the database tables (SQLAlchemy ORM models).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BloodGroup(str, enum.Enum):
    O_NEG = "O-"
    O_POS = "O+"
    A_NEG = "A-"
    A_POS = "A+"
    B_NEG = "B-"
    B_POS = "B+"
    AB_NEG = "AB-"
    AB_POS = "AB+"


class UrgencyLevel(str, enum.Enum):
    CRITICAL = "critical"   # immediate, life-threatening
    URGENT = "urgent"       # within hours
    STANDARD = "standard"   # within a day or two


class RequestStatus(str, enum.Enum):
    OPEN = "open"
    MATCHING = "matching"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AcceptanceStatus(str, enum.Enum):
    PENDING = "pending"        # donor accepted, en route, timer running
    FULFILLED = "fulfilled"    # this donor completed the donation
    STOOD_DOWN = "stood_down"  # another donor fulfilled first
    NO_SHOW = "no_show"        # donor missed the ETA window
    CANCELLED = "cancelled"    # donor backed out voluntarily


class Donor(Base):
    __tablename__ = "donors"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    blood_group = Column(Enum(BloodGroup), nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    is_available = Column(Boolean, default=True)         # toggled off while on an active request
    is_verified = Column(Boolean, default=False)          # hospital-verified after first donation
    is_suspended = Column(Boolean, default=False)          # admin action for repeat abuse

    reliability_score = Column(Float, default=50.0)        # 0-100, starts neutral
    total_donations = Column(Integer, default=0)
    total_no_shows = Column(Integer, default=0)

    cooldown_until = Column(DateTime, nullable=True)        # set after a no-show
    last_donation_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    acceptances = relationship("Acceptance", back_populates="donor")

    def has_active_request(self, db_session) -> bool:
        """A donor may hold only one PENDING acceptance at a time."""
        return db_session.query(Acceptance).filter(
            Acceptance.donor_id == self.id,
            Acceptance.status == AcceptanceStatus.PENDING
        ).count() > 0


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True)
    hospital_name = Column(String, nullable=False)
    blood_group_needed = Column(Enum(BloodGroup), nullable=False)
    units_needed = Column(Integer, default=1)

    urgency = Column(Enum(UrgencyLevel), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.OPEN)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    current_radius_km = Column(Float, default=5.0)   # tier: 5 -> 10 -> 20
    eta_window_minutes = Column(Integer, default=45)  # allowed travel time once accepted

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    fulfilled_at = Column(DateTime, nullable=True)

    acceptances = relationship("Acceptance", back_populates="request")


class Acceptance(Base):
    """
    A donor's acceptance of a request. Multiple donors can hold a PENDING
    acceptance on the same request simultaneously (parallel confirmation) —
    the first to complete flips to FULFILLED and the rest are stood down.
    """
    __tablename__ = "acceptances"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True)
    request_id = Column(String, ForeignKey("blood_requests.id"), nullable=False)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)

    status = Column(Enum(AcceptanceStatus), default=AcceptanceStatus.PENDING)

    accepted_at = Column(DateTime, default=datetime.utcnow)
    eta_deadline = Column(DateTime, nullable=False)   # accepted_at + request.eta_window_minutes
    resolved_at = Column(DateTime, nullable=True)      # when it became fulfilled/no_show/stood_down

    request = relationship("BloodRequest", back_populates="acceptances")
    donor = relationship("Donor", back_populates="acceptances")


class NotificationLog(Base):
    """Audit trail of who was notified, at what radius tier, and when."""
    __tablename__ = "notification_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True)
    request_id = Column(String, ForeignKey("blood_requests.id"), nullable=False)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)
    radius_tier_km = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

class UserType(str, enum.Enum):
    DONOR = "donor"
    HOSPITAL = "hospital"
    ADMIN = "admin"


class User(Base):
    """
    HemoLink authentication account.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)

    email = Column(String, nullable=True, unique=True)
    phone = Column(String, nullable=True, unique=True)

    password_hash = Column(String, nullable=False)

    user_type = Column(
        Enum(UserType),
        nullable=False,
        default=UserType.DONOR,
    )

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
