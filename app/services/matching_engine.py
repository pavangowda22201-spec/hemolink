"""
RUN LOCATION: Imported by routers/requests.py — not run directly.

This is the heart of the system: finds and ranks eligible donors for a
request, expanding the search radius in tiers when too few candidates
are found.

A fully fulfilled request is never matched again.
"""

from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from app.models.models import (
    Donor,
    BloodRequest,
    RequestStatus,
    UrgencyLevel,
)
from app.services.blood_compatibility import eligible_donor_groups
from app.services.geo import distance_km
from app.services.reliability_service import is_eligible_for_matching


# Tiered search radii, in km. Expansion happens if MIN_CANDIDATES
# isn't met.
RADIUS_TIERS_KM = [5.0, 10.0, 20.0]

# How many eligible donors we want to find before we stop
# expanding the radius.
MIN_CANDIDATES = 3

# Scoring weights — distance and reliability matter most,
# with urgency boosting how aggressively we favor speed.
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


def _score_candidate(
    donor: Donor,
    dist_km: float,
    radius_km: float,
    urgency: UrgencyLevel,
) -> float:
    """
    Higher is better. Combines:
    - proximity (closer = higher, normalized against the current search radius)
    - reliability score (0-100, normalized to 0-1)
    - verification status bonus
    - urgency: for critical/urgent requests, distance matters even more
    """
    proximity_score = max(
        0.0,
        1.0 - (dist_km / radius_km),
    )

    reliability_norm = donor.reliability_score / 100.0
    verified_bonus = 1.0 if donor.is_verified else 0.0

    urgency_mult = _urgency_multiplier(urgency)

    distance_weight = (
        WEIGHT_DISTANCE
        + (
            WEIGHT_URGENCY_DISTANCE_BOOST
            * (urgency_mult - 1.0)
        )
    )

    score = (
        distance_weight * proximity_score
        + WEIGHT_RELIABILITY * reliability_norm
        + WEIGHT_VERIFIED * verified_bonus
    )

    return round(score, 4)


def find_candidates_at_radius(
    db: Session,
    request: BloodRequest,
    radius_km: float,
) -> List[Candidate]:
    """
    Fetch and score all eligible donors within radius_km
    of the request.
    """
    compatible_groups = eligible_donor_groups(
        request.blood_group_needed
    )

    all_donors = (
        db.query(Donor)
        .filter(
            Donor.blood_group.in_(compatible_groups)
        )
        .all()
    )

    candidates = []

    for donor in all_donors:
        if not is_eligible_for_matching(donor):
            continue

        if donor.has_active_request(db):
            continue

        # Skip donors without a usable location.
        if donor.latitude is None or donor.longitude is None:
            continue

        dist = distance_km(
            request.latitude,
            request.longitude,
            donor.latitude,
            donor.longitude,
        )

        if dist > radius_km:
            continue

        score = _score_candidate(
            donor,
            dist,
            radius_km,
            request.urgency,
        )

        candidates.append(
            Candidate(
                donor=donor,
                distance_km=round(dist, 2),
                score=score,
            )
        )

    candidates.sort(
        key=lambda candidate: candidate.score,
        reverse=True,
    )

    return candidates


def match_request(
    db: Session,
    request: BloodRequest,
) -> List[Candidate]:
    """
    Tiered search:

    1. Start at 5km.
    2. Expand to 10km if fewer than MIN_CANDIDATES are found.
    3. Expand to 20km if still insufficient.
    4. Stop once enough eligible donors are found.

    A fully fulfilled request is closed to new matching and
    returns no candidates.
    """

    if request.status == RequestStatus.FULFILLED:
        return []

    candidates: List[Candidate] = []

    for radius in RADIUS_TIERS_KM:
        candidates = find_candidates_at_radius(
            db,
            request,
            radius,
        )

        request.current_radius_km = radius

        if len(candidates) >= MIN_CANDIDATES:
            break

    db.commit()

    return candidates
