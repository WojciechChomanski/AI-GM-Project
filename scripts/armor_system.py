# file: scripts/armor_system.py
import json
import logging
import os
from typing import Dict, List, Optional

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def _safe_join(base_dir: str, path: str) -> str:
    """Join paths robustly; if path is already absolute, return it."""
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base_dir, path))


class ArmorPiece:
    """
    Armor with per-zone durability and per-type protection.

    Expected schema (in rules/armors.json):

    {
      "Medium_Heavy": {
        "standard": {
          "name": "Medium Heavy Armor",
          "coverage": ["chest","stomach","left_upper_arm","right_upper_arm","left_upper_leg","right_upper_leg"],
          "armor_rating": {"slashing": 6, "piercing": 3, "blunt": 4},
          "stamina_penalty": 6,
          "max_durability": 90,
          "weight": 25,
          "mobility_bonus": 0
        }
      },
      "Light_Light": {
        "standard": { ... }
      }
    }

    If your JSON has no variant layer (i.e., directly the dict above), the loader handles that too.
    """

    def __init__(
        self,
        name: str,
        coverage: List[str],
        armor_rating: Dict[str, int],
        stamina_penalty: int,
        max_durability: int,
        weight: int,
        mobility_bonus: int = 0,
        per_zone_durability: Optional[Dict[str, int]] = None,
    ):
        self.name = name
        self.coverage = list(coverage)
        self.armor_rating = dict(armor_rating)
        self.stamina_penalty = int(stamina_penalty)
        self.max_durability = int(max_durability)
        self.weight = int(weight)
        self.mobility_bonus = int(mobility_bonus)

        # Distribute durability per covered zone unless an explicit mapping is provided.
        if per_zone_durability:
            # Ensure only covered parts are included
            self.current_durability: Dict[str, int] = {
                zone: max(0, int(per_zone_durability.get(zone, 0))) for zone in self.coverage
            }
            self.per_zone_max: Dict[str, int] = dict(self.current_durability)
        else:
            zones = len(self.coverage) or 1
            per_zone = max(1, self.max_durability // zones)
            self.current_durability = {zone: per_zone for zone in self.coverage}
            self.per_zone_max = {zone: per_zone for zone in self.coverage}

    # --- Mechanics ---

    def _condition_multiplier(self, zone: str) -> float:
        """Less durability ⇒ less effective protection."""
        cur = max(0, self.current_durability.get(zone, 0))
        mx = max(1, self.per_zone_max.get(zone, 1))
        pct = cur / mx
        if pct >= 0.75:
            return 1.0
        if pct >= 0.50:
            return 0.75
        if pct >= 0.25:
            return 0.50
        if pct > 0:
            return 0.25
        return 0.0

    def absorb_damage(self, damage: int, damage_type: str, zone: Optional[str]) -> int:
        """
        Return the amount of damage absorbed (not the remainder).

        `zone` is required for per-zone durability. If zone is None or not covered,
        the armor doesn’t help.
        """
        if not zone or zone not in self.coverage:
            return 0

        if self.current_durability.get(zone, 0) <= 0:
            # Broken on this zone
            print(f"⚠️ {self.name} at {zone.replace('_',' ')} is broken and offers no protection!")
            return 0

        base_prot = int(self.armor_rating.get(damage_type, 0))
        prot = base_prot * self._condition_multiplier(zone)
        prot = int(round(prot))

        absorbed = min(max(0, int(damage)), prot)

        # Durability loss proportional to incoming damage (not absorbed), at least 1
        dur_loss = max(1, int(damage * 0.20))
        self.current_durability[zone] = max(0, self.current_durability[zone] - dur_loss)

        print(
            f"🛡️ {self.name} ({zone.replace('_',' ')}) absorbed {absorbed} "
            f"({damage_type}). Durability: {self.current_durability[zone]}/{self.per_zone_max[zone]}"
        )
        return absorbed

    # --- Maintenance/UI ---

    def condition_status(self, zone: Optional[str] = None) -> str:
        """Overall or per-zone condition label."""
        def label(pct: float) -> str:
            if pct >= 0.90:
                return "Pristine"
            if pct >= 0.75:
                return "Good"
            if pct >= 0.50:
                return "Worn"
            if pct >= 0.25:
                return "Damaged"
            if pct > 0:
                return "Critical"
            return "Broken"

        if zone:
            cur = self.current_durability.get(zone, 0)
            mx = max(1, self.per_zone_max.get(zone, 1))
            return label(cur / mx)

        # overall (mean)
        total_cur = sum(self.current_durability.values()) or 0
        total_max = sum(self.per_zone_max.values()) or 1
        return label(total_cur / total_max)

    def repair(self, skill_level: int, zone: Optional[str] = None) -> None:
        """
        Simple repair: restore a chunk; can’t exceed 85% of per-zone max if badly damaged.
        """
        eff = 0.20 + (max(0, int(skill_level)) * 0.05)
        eff = min(0.90, eff)
        targets = [zone] if zone and zone in self.coverage else list(self.coverage)

        for z in targets:
            cur = self.current_durability.get(z, 0)
            mx = self.per_zone_max.get(z, 1)
            if cur <= 0:
                print(f"💀 {self.name} at {z.replace('_',' ')} is beyond field repair!")
                continue

            add = int(mx * eff)
            # if more than 50% missing, cap at 85% of max
            if (mx - cur) > (mx * 0.5):
                hard_cap = int(mx * 0.85)
                self.current_durability[z] = min(cur + add, hard_cap)
            else:
                self.current_durability[z] = min(cur + add, mx)

            print(
                f"🔧 Repaired {self.name} ({z.replace('_',' ')}) → "
                f"{self.current_durability[z]}/{mx} ({self.condition_status(z)})"
            )


class ArmorSystem:
    def __init__(self, armor_file: str = "../rules/armors.json"):
        base_dir = os.path.dirname(__file__)
        self.armor_path = _safe_join(base_dir, armor_file)
        self.armors = self.load_armors(self.armor_path)

    def load_armors(self, file_path: str) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("armors.json must be a dictionary at the top level.")
        log.debug("Loaded armors from %s", file_path)
        return data

    def _resolve_armor_dict(self, key: str, variant: str = "standard") -> Optional[dict]:
        """
        Accept both:
          - {"Key": {"standard": {...}}}
          - {"Key": {...}}   (no variant layer)
        """
        block = self.armors.get(key)
        if not block:
            return None
        if isinstance(block, dict) and "coverage" in block and "armor_rating" in block:
            # no variant layer, this IS the armor dict
            return block
        # else expect a variant
        if isinstance(block, dict):
            return block.get(variant)
        return None

    def equip_armor(self, character, armor_type: str, variant: str = "standard") -> Optional[ArmorPiece]:
        """
        Replace string entries in character.armor with a real ArmorPiece object.
        Safe if character already has objects. Guards apply_armor_penalties() if present.
        """
        armor_data = self._resolve_armor_dict(armor_type, variant)
        if not armor_data:
            print(f"❌ Invalid armor: {armor_type} ({variant})")
            return None

        armor = ArmorPiece(
            name=armor_data["name"],
            coverage=armor_data["coverage"],
            armor_rating=armor_data["armor_rating"],
            stamina_penalty=armor_data["stamina_penalty"],
            max_durability=armor_data["max_durability"],
            weight=armor_data["weight"],
            mobility_bonus=armor_data.get("mobility_bonus", 0),
            per_zone_durability=armor_data.get("per_zone_durability"),  # optional map
        )

        # Ensure list exists
        if not hasattr(character, "armor") or character.armor is None:
            character.armor = []

        # Remove legacy string entries matching this key (so we don't trip code that expects objects)
        if isinstance(character.armor, list):
            character.armor = [a for a in character.armor if not (isinstance(a, str) and a == armor_type)]

        # Append the real armor object
        character.armor.append(armor)

        # Apply penalties only if the character implements it
        if hasattr(character, "apply_armor_penalties"):
            try:
                character.apply_armor_penalties()
            except Exception as e:
                log.warning("apply_armor_penalties failed on %s: %s", getattr(character, "name", "Unknown"), e)

        print(f"🛡️ {getattr(character, 'name', 'Unknown')} equips {armor.name}")
        log.debug("Equipped %s to %s", armor.name, getattr(character, "name", "Unknown"))
        return armor

