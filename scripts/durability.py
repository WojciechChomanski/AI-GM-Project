# file: scripts/durability.py
"""Permanent wear for weapons and armour (see docs/DURABILITY.md).

ALL NUMBERS ARE PLACEHOLDERS for testing; they will be tuned after play.

Model (owner rules):
  * Every item has an ORIGINAL maximum durability and a CURRENT maximum.
  * Every time the durability lost since the last mark reaches 30% of the
    CURRENT maximum, the current maximum permanently drops by 5% of the
    ORIGINAL maximum (100 -> 95 -> 90 ...) and the wear counter resets.
    Repairs never reset the counter: it is cumulative wear since the last mark.
  * Repairs restore durability only up to the current maximum.
  * current maximum <= 0 -> the item is destroyed.
  * Quality: for every 10% of the original maximum permanently lost
    - weapon damage drops by 1 per 10 base damage (rounded, min. 1 per step
      for weapons with >= 5 base damage),
    - armour rating drops by 1 per damage type (never below 0).

`Wear` only tracks marks / maximum / counter. The item itself keeps its current
durability value (armour: `current_durability[zone]`, weapons: `_weapon_durability`).
"""
import math

MARK_FRACTION = 0.30            # wear since last mark that triggers a mark (of CURRENT max)
MARK_LOSS_FRACTION = 0.05       # permanent loss per mark (of ORIGINAL max)
QUALITY_STEP_FRACTION = 0.10    # one quality step per 10% of original max lost
FIELD_REPAIR_CAP = 0.85         # existing field-repair rule: >50% missing -> repair stops at 85% of max
WEAPON_LOSS_PER_ATTACK = 0.5    # combat_rules.json weapon_durability.loss_per_attack
WEAPON_LOSS_ON_PARRY = 1.0      # combat_rules.json weapon_durability.loss_on_parry
_EPS = 1e-9


def half_up(x: float) -> int:
    """Round half up (not banker's rounding)."""
    return int(math.floor(x + 0.5 + _EPS))


class Wear:
    """Permanent-wear tracker for one durability pool (one armour zone, or one weapon)."""

    def __init__(self, original_max: float, marks: int = 0, counter: float = 0.0):
        self.original_max = float(original_max)
        self.marks = int(marks)
        self.counter = float(counter)   # durability lost since the last mark

    # --- state ---
    @property
    def current_max(self) -> float:
        value = self.original_max * (1.0 - self.marks * MARK_LOSS_FRACTION)
        return 0.0 if value <= _EPS else value

    @property
    def destroyed(self) -> bool:
        return self.original_max > 0 and self.current_max <= 0

    @property
    def lost_fraction(self) -> float:
        """Share of the ORIGINAL maximum that is permanently gone (0..1)."""
        if self.original_max <= 0:
            return 0.0
        return min(1.0, self.marks * MARK_LOSS_FRACTION)

    def quality_steps(self) -> int:
        """Number of quality steps lost: one per 10% of the original max gone."""
        return int(self.lost_fraction / QUALITY_STEP_FRACTION + _EPS)

    # --- mechanics ---
    def lose(self, points: float) -> int:
        """Register `points` of durability actually lost. Returns how many new
        marks that triggered (usually 0 or 1). The caller then clamps its current
        durability to `current_max`."""
        points = float(points)
        if points <= 0 or self.destroyed:
            return 0
        self.counter += points
        new_marks = 0
        while not self.destroyed and self.counter + _EPS >= MARK_FRACTION * self.current_max:
            self.counter -= MARK_FRACTION * self.current_max
            self.marks += 1
            new_marks += 1
        if self.destroyed:
            self.counter = 0.0
        elif self.counter < _EPS:
            self.counter = 0.0
        return new_marks

    def clamp(self, current: float) -> float:
        """Current durability can never exceed the current maximum."""
        return min(float(current), self.current_max)

    def repair(self, current: float, points: float, field_cap: float = None) -> float:
        """Return the new current durability after restoring `points`. Never above
        the current maximum. With `field_cap` (e.g. 0.85) the old field-repair rule
        applies: if more than half of the maximum is missing, one repair stops at
        field_cap x current maximum."""
        cmax = self.current_max
        if cmax <= 0:
            return 0.0
        current = min(float(current), cmax)
        cap = cmax
        if field_cap is not None and (cmax - current) > cmax * 0.5:
            cap = cmax * field_cap
        return max(current, min(current + max(0.0, float(points)), cap))

    def to_dict(self) -> dict:
        return {"original_max": self.original_max, "marks": self.marks, "counter": self.counter}

    @classmethod
    def from_dict(cls, d: dict) -> "Wear":
        return cls(d["original_max"], d.get("marks", 0), d.get("counter", 0.0))


# --- quality helpers -------------------------------------------------------

def weapon_loss_per_step(base_damage: float) -> int:
    """Damage lost per quality step: 1 per 10 base damage, rounded half up;
    at least 1 for weapons with >= 5 base damage (below 5: proportional, may be 0)."""
    n = half_up(base_damage / 10.0)
    if base_damage >= 5:
        n = max(1, n)
    return n


def weapon_damage_after_wear(base_damage: float, steps: int, destroyed: bool = False) -> int:
    """Base damage of a worn weapon. A weapon that is still alive never drops below
    1 (placeholder floor); a destroyed weapon deals no weapon damage (0)."""
    if destroyed:
        return 0
    base = half_up(base_damage)
    if base <= 0:
        return 0
    return max(1, base - steps * weapon_loss_per_step(base_damage))


def armor_rating_after_wear(rating: float, steps: int) -> float:
    """Armour rating of one damage type after `steps` quality steps (never below 0)."""
    return max(0.0, float(rating) - steps)
