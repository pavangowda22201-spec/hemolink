"""
RUN LOCATION: Imported by matching_engine.py — not run directly.
Encodes standard blood donor -> recipient compatibility (ABO + Rh).
"""
from app.models.models import BloodGroup

# Map: recipient blood group -> set of blood groups that can donate to them.
# O- is the universal donor; AB+ is the universal recipient.
COMPATIBILITY_MAP = {
    BloodGroup.O_NEG: {BloodGroup.O_NEG},
    BloodGroup.O_POS: {BloodGroup.O_NEG, BloodGroup.O_POS},
    BloodGroup.A_NEG: {BloodGroup.O_NEG, BloodGroup.A_NEG},
    BloodGroup.A_POS: {BloodGroup.O_NEG, BloodGroup.O_POS, BloodGroup.A_NEG, BloodGroup.A_POS},
    BloodGroup.B_NEG: {BloodGroup.O_NEG, BloodGroup.B_NEG},
    BloodGroup.B_POS: {BloodGroup.O_NEG, BloodGroup.O_POS, BloodGroup.B_NEG, BloodGroup.B_POS},
    BloodGroup.AB_NEG: {BloodGroup.O_NEG, BloodGroup.A_NEG, BloodGroup.B_NEG, BloodGroup.AB_NEG},
    BloodGroup.AB_POS: set(BloodGroup),  # universal recipient — anyone can donate
}


def is_compatible(donor_group: BloodGroup, recipient_group: BloodGroup) -> bool:
    """Returns True if a donor of donor_group can safely donate to recipient_group."""
    return donor_group in COMPATIBILITY_MAP[recipient_group]


def eligible_donor_groups(recipient_group: BloodGroup) -> set:
    """All blood groups eligible to donate to the given recipient group."""
    return COMPATIBILITY_MAP[recipient_group]
