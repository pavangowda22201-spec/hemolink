"""
RUN LOCATION: Imported by routers/acceptances.py and the no-show checker job — not run directly.
Handles reliability score adjustments, cooldowns, and suspension for repeat abuse.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Donor

# --- Tunable constants ---
SCORE_REWARD_DONATION = 8.0
SCORE_PENALTY_NO_SHOW = 15.0
SCORE_MIN = 0.0
SCORE_MAX = 100.0

COOLDOWN_HOURS_AFTER_NO_SHOW = 36  # within the 24-48h range requested
NO_SHOW_SUSPEND_THRESHOLD = 3       # lifetime no-shows that trigger admin review/suspension


def reward_successful_donation(db: Session, donor: Donor) -> Donor:
    donor.reliability_score = min(SCORE_MAX, donor.reliability_score + SCORE_REWARD_DONATION)
    donor.total_donations += 1
    donor.last_donation_at = datetime.utcnow()
    if not donor.is_verified:
        # First donation gets hospital-verified separately (see verification_service),
        # but we still count it here.
        pass
    db.commit()
    db.refresh(donor)
    return donor


def penalize_no_show(db: Session, donor: Donor) -> Donor:
    donor.reliability_score = max(SCORE_MIN, donor.reliability_score - SCORE_PENALTY_NO_SHOW)
    donor.total_no_shows += 1
    donor.cooldown_until = datetime.utcnow() + timedelta(hours=COOLDOWN_HOURS_AFTER_NO_SHOW)

    if donor.total_no_shows >= NO_SHOW_SUSPEND_THRESHOLD:
        donor.is_suspended = True  # flagged for admin review / auto-suspended

    db.commit()
    db.refresh(donor)
    return donor


def is_eligible_for_matching(donor: Donor) -> bool:
    """Gatekeeper used by the matching engine before considering a donor a candidate."""
    if donor.is_suspended:
        return False
    if not donor.is_available:
        return False
    if donor.cooldown_until and donor.cooldown_until > datetime.utcnow():
        return False
    return True


def admin_unsuspend(db: Session, donor: Donor) -> Donor:
    """Manual admin override to lift a suspension."""
    donor.is_suspended = False
    db.commit()
    db.refresh(donor)
    return donor
