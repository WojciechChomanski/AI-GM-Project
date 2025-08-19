

# rules/combat_engine.py

import random
from typing import Any, Dict, Iterable, List, Optional, Tuple

# =============================================================================
# Safe access / tiny helpers
# =============================================================================

def _get(ent: Any, key: str, default=None):
    if isinstance(ent, dict):
        return ent.get(key, default)
    return getattr(ent, key, default)

def _set(ent: Any, key: str, value):
    if isinstance(ent, dict):
        ent[key] = value
    else:
        setattr(ent, key, value)

def _safe_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _mod_from_stat(val: Optional[int]) -> int:
    """Convert a 0-100ish primary stat into a small d100 modifier."""
    try:
        if val is None:
            return 0
        return int(val) // 10
    except Exception:
        return 0

_DEFAULT_ZONES: List[str] = [
    "chest", "stomach",
    "left upper arm", "right upper arm",
    "left lower arm", "right lower arm",
    "left upper leg", "right upper leg",
    "left lower leg", "right lower leg",
    "head",
]

_STANCE_ATTACK = {"OFFENSIVE": +10, "NEUTRAL": 0, "DEFENSIVE": -10}
_STANCE_DEFENSE = {"OFFENSIVE": -10, "NEUTRAL": 0, "DEFENSIVE": +10}

# =============================================================================
# Combat Engine (backward-compatible return shape)
# =============================================================================

class CombatEngine:
    """
    Robust, drop-in combat engine.

    IMPORTANT: attack_roll returns a TWO-TUPLE:
        (hit: bool, damage_list: List[Tuple[str,int]])

    This matches your adventure.py which does:
        hit, damage = engine.attack_roll(...)

    The engine prints cinematic logs, tolerates messy inputs, and never raises
    'too many values to unpack' because damage is always a clean list of pairs.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()
        self.last_outcome: Dict[str, Any] = {}

    # ----------------- dice / utility -----------------

    def _d100(self) -> int:
        return self.rng.randint(1, 100)

    def _choose_defense_type(self, defender: Any) -> str:
        """Prefer Block (shield) > Parry (weapon) > Dodge."""
        if bool(_get(defender, "shield_equipped", False)):
            return "Block"
        if bool(_get(defender, "weapon_equipped", False)):
            return "Parry"
        return "Dodge"

    def _iter_damage_items(self, damage_parts: Any) -> Iterable[Tuple[str, int]]:
        """
        Normalizer (kept for compatibility if you ever pass custom damage in):
        yields (part, dmg) from dicts, list/tuples, or list of dicts.
        """
        if not damage_parts:
            return []
        if isinstance(damage_parts, dict):
            for part, dmg in damage_parts.items():
                if part is None:
                    continue
                yield (str(part), _safe_int(dmg, 0))
            return
        if isinstance(damage_parts, (list, tuple)):
            for entry in damage_parts:
                if isinstance(entry, (list, tuple)) and entry:
                    part = entry[0]
                    dmg = entry[1] if len(entry) > 1 else 0
                    yield (str(part), _safe_int(dmg, 0))
                elif isinstance(entry, dict):
                    part = entry.get("part") or entry.get("zone")
                    if part is None:
                        continue
                    dmg = entry.get("damage") or entry.get("amount") or 0
                    yield (str(part), _safe_int(dmg, 0))
            return
        if isinstance(damage_parts, str):
            yield (damage_parts.lower(), 0)

    def _distribute_damage(self, amount: int, attack_type: str, aimed_zone: Optional[str]) -> Dict[str, int]:
        """Pick target zone(s) and return {zone: amount}."""
        amount = max(0, _safe_int(amount, 0))
        if amount == 0:
            return {}
        if (attack_type or "").lower() == "aimed" and aimed_zone:
            return {str(aimed_zone).lower(): amount}
        zone = self.rng.choice(_DEFAULT_ZONES)
        return {zone: amount}

    # ----------------- main API -----------------

    def attack_roll(
        self,
        attacker: Any,
        defender: Any,
        weapon_damage: int,
        attack_type: str = "normal",
        aimed_zone: Optional[str] = None,
        chosen_stance: str = "NEUTRAL",
        ambush_bonus: int = 0,
        damage_type: str = "slashing",
        # Extra params accepted for compatibility; not required here:
        attacker_health: Optional[Any] = None,
        defender_health: Optional[Any] = None,
        roll_penalty: int = 0,
        opponents: Optional[List[Any]] = None,
        environment: str = "open",
        **kwargs,
    ) -> Tuple[bool, List[Tuple[str, int]]]:
        """
        Resolve an attack. RETURNS (hit, damage_list).

        We DO NOT modify defender HP here; your game handles armor/HP/death.
        """
        # Normalize stance
        stance = (chosen_stance or "NEUTRAL").upper()
        if stance not in _STANCE_ATTACK:
            stance = "NEUTRAL"

        attacker_name = _get(attacker, "name", "Attacker")
        defender_name = _get(defender, "name", "Defender")

        # --- Attack roll calc ---
        atk_roll = self._d100()
        atk_mod = 0

        # Dex as primary for to-hit; allow dexterity_modifier too
        dex = _get(attacker, "dexterity", None)
        if dex is None:
            dex = _get(attacker, "dexterity_modifier", None)
            if dex is not None:
                atk_mod += _safe_int(dex, 0)
                dex = None
        if dex is not None:
            atk_mod += _mod_from_stat(dex)

        # weapon skill (if provided)
        weapon_skill = 0
        skills = _get(attacker, "skills", {}) or {}
        if isinstance(skills, dict):
            for k in ("swordsmanship", "club_smash", "weapon_skill"):
                if k in skills:
                    try:
                        weapon_skill = int(skills[k])
                        break
                    except Exception:
                        pass

        atk_total = (
            atk_roll
            + atk_mod
            + weapon_skill
            + _STANCE_ATTACK[stance]
            + _safe_int(ambush_bonus, 0)
            - _safe_int(roll_penalty, 0)
        )

        # --- Defense roll calc ---
        defense_kind = self._choose_defense_type(defender)
        def_roll = self._d100()
        def_mod = 0
        if defense_kind == "Dodge":
            def_mod += _mod_from_stat(_get(defender, "agility", _get(defender, "dexterity", None)))
        elif defense_kind == "Parry":
            def_mod += _mod_from_stat(_get(defender, "dexterity", _get(defender, "agility", None)))
        else:  # Block
            def_mod += _mod_from_stat(_get(defender, "toughness", _get(defender, "strength", None)))

        def_total = def_roll + def_mod + _STANCE_DEFENSE[stance]

        # --- Cinematic logs (keep your style) ---
        print(f"⚔️ {attacker_name} is in {stance} stance")
        print(f"🛡️ {defender_name} is in NEUTRAL stance")  # defender stance unknown; display neutral
        print(
            f"⚔️ {attacker_name} rolls {atk_roll} + {weapon_skill} (Weapon Skill) + "
            f"{_mod_from_stat(_get(attacker,'dexterity',None))} (Dexterity) - 0 (Stress) - 0 (Pain) + "
            f"{int(_safe_int(ambush_bonus,0))} (Ambush) = {atk_total} to attack!"
        )
        print(
            f"🛡️ {defender_name} rolls {def_roll} + {def_mod} (Stat) - 0 (Stress) - 0 (Pain) = "
            f"{def_total} to defend! ({defense_kind})"
        )

        # --- Miss -> (False, []) and we're done ---
        if atk_total <= def_total:
            print(f"❌ {attacker_name} misses or {defender_name} successfully defends!")
            self.last_outcome = {
                "hit": False,
                "attack_total": atk_total,
                "defense_total": def_total,
                "defense_kind": defense_kind,
                "damage": [],
            }
            return False, []

        # --- Hit! Distribute damage but DON'T touch HP here ---
        dmg_map = self._distribute_damage(weapon_damage, attack_type, aimed_zone)
        damage_list: List[Tuple[str, int]] = [(str(part), _safe_int(dmg, 0)) for part, dmg in dmg_map.items()]

        # Optional: chip weapon durability if present
        weapon = _get(attacker, "weapon", None)
        if isinstance(weapon, dict) and "durability" in weapon:
            try:
                chip = self.rng.randint(1, 3)
                weapon["durability"] = max(0, _safe_int(weapon["durability"], 0) - chip)
                wname = weapon.get("type", "weapon")
                print(f"⚔️ {attacker_name}'s {str(wname).capitalize()} durability: {weapon['durability']}")
            except Exception:
                pass

        # Stash last outcome for debugging/telemetry if needed
        self.last_outcome = {
            "hit": True,
            "attack_total": atk_total,
            "defense_total": def_total,
            "defense_kind": defense_kind,
            "damage": damage_list[:],  # list of (part, dmg)
            "attack_type": attack_type,
            "aimed_zone": aimed_zone,
            "stance": stance,
            "ambush_bonus": _safe_int(ambush_bonus, 0),
            "damage_type": damage_type,
        }

        return True, damage_list
