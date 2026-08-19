"""
RUN LOCATION: Imported by routers/requests.py — not run directly.
This is the heart of the system: finds and ranks eligible donors for a request,
expanding the search radius in tiers when too few candidates are found.
"""
from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from app.models.models import Donor, BloodRequest, UrgencyLevel
from app.services.blood_compatibility import eligible_donor_groups
from app.services.geo import distance_km
from app.services.reliability_service import is_eligible_for_matching

# Tiered search radii, in km. Expansion happens if MIN_CANDIDATES isn't met.
RADIUS_TIERS_KM = [5.0, 10.0, 20.0]

# How many eligible donors we want to find before we stop expanding the radius.
MIN_CANDIDATES = 3

# Scoring weights — tuned so distance and reliability matter most,
# with urgency boosting how aggressively we favor speed (closeness).
WEIGHT_DISTANCE = 0.4
WEIGHT_RELIABILITY = 0.35
WEIGHT_VERIFIED = 0.15
WEIGHT_URGENCY_DISTANCE_BOOST = 0.1


@dataclass
class Candidate:
    donor: Donor
    distance_km: float
    score: float


def _urgency_multiplier(urgency: UrgencyLevel) -> float:
    return {
        UrgencyLevel.CRITICAL: 1.5,
        UrgencyLevel.URGENT: 1.2,
        UrgencyLevel.STANDARD: 1.0,
    }[urgency]


def _score_candidate(donor: Donor, dist_km: float, radius_km: float, urgency: UrgencyLevel) -> float:
    """
    Higher is better. Combines:
    - proximity (closer = higher, normalized against the current search radius)
    - reliability score (0-100, normalized to 0-1)
    - verification status bonus
    - urgency: for critical/urgent requests, distance matters even more
    """
    proximity_score = max(0.0, 1.0 - (dist_km / radius_km))
    reliability_norm = donor.reliability_score / 100.0
    verified_bonus = 1.0 if donor.is_verified else 0.0

    urgency_mult = _urgency_multiplier(urgency)
    distance_weight = WEIGHT_DISTANCE + (WEIGHT_URGENCY_DISTANCE_BOOST * (urgency_mult - 1.0))

    score = (
        distance_weight * proximity_score
        + WEIGHT_RELIABILITY * reliability_norm
        + WEIGHT_VERIFIED * verified_bonus
    )
    return round(score, 4)


def find_candidates_at_radius(
    db: Session, request: BloodRequest, radius_km: float
) -> List[Candidate]:
    """Fetch and score all eligible donors within radius_km of the request."""
    compatible_groups = eligible_donor_groups(request.blood_group_needed)

    all_donors = db.query(Donor).filter(Donor.blood_group.in_(compatible_groups)).all()

    candidates = []
    for donor in all_donors:
        if not is_eligible_for_matching(donor):
            continue
        if donor.has_active_request(db):
            continue  # limited to 1 active accepted request per donor

        dist = distance_km(request.latitude, request.longitude, donor.latitude, donor.longitude)
        if dist > radius_km:
            continue

        score = _score_candidate(donor, dist, radius_km, request.urgency)
        candidates.append(Candidate(donor=donor, distance_km=round(dist, 2), score=score))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def match_request(db: Session, request: BloodRequest) -> List[Candidate]:
    """
    Tiered search: start at 5km. If fewer than MIN_CANDIDATES eligible donors
    are found, expand to the next tier (10km, then 20km). Updates
    request.current_radius_km to reflect the tier that was actually used.
    """
    candidates: List[Candidate] = []

    for radius in RADIUS_TIERS_KM:
        candidates = find_candidates_at_radius(db, request, radius)
        request.current_radius_km = radius
        if len(candidates) >= MIN_CANDIDATES:
            break

    db.commit()
    return candidates
