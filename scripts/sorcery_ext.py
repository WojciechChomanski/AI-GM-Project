# scripts/sorcery_ext.py
from __future__ import annotations
import random

__all__ = [
    "is_sorceress",
    "present_spells_menu",
    "cast_spell",
    "on_new_round_tick",
    "apply_melee_vulnerability",
    "consume_evade_on_melee_if_any",
    "override_from_rules",
]

# --- core knobs (tuned to your spec) ---
MISCAST_BASE = 5                 # % base miscast chance
MELEE_VULN_MULT = 1.50           # +50% damage taken from MELEE
FADE_STEP_EXHAUST_STAMINA_TAX = 3
SHROUD_ONCE_PER_ENCOUNTER_FLAG = "_shroud_used"
MAX_CORRUPTION = 150

# Default spellbook (overridable via rules or per-character)
DEFAULT_SPELLS = {
    "veil_fog": {
        "label": "Veil Fog",
        "stamina": 5,
        "corruption": 5,
        "fog_duration": 1,        # rounds
        "bonus_vs_feared_pct": 5, # small synergy
        "atk_penalty": 20,        # −20 to attack rolls for affected units
    },
    "blood_pact": {
        "label": "Blood Pact",
        "stamina": 15,
        "hp_pct_cost": 10,
        "corruption": 10,
        "damage": 30,             # armor bypass (we pass zone=None to apply_damage)
        "self_dazed": 1,
    },
    "whisper_of_fear": {
        "label": "Whisper of Fear",
        "stamina": 10,
        "corruption": 5,
        "will_contest": True,
        "freeze_chance_pct": 25,  # skip next action
        "turn_on_allies_pct": 15, # placeholder hook
        "backlash_fail_chance_pct": 20,
        "backlash_damage": 5,
        "apply_fear_rounds": 1,
    },
    "fade_step": {
        "label": "Fade Step",
        "stamina": 10,
        "corruption": 3,
        "evade_next_melee": True,  # auto-negate next melee hit
        "exhaust_after": True,     # next ability +3 stamina
    },
    "shrouds_embrace": {
        "label": "Shroud's Embrace",
        "stamina": 30,
        "corruption": 20,          # +20
        "damage": 40,              # 20+20 veil damage (no resistances in this build)
        "radius": 5,
        "root_rounds": 1,          # all trapped (incl. caster)
        "heal_on_fear_pct": 15,    # heal 15% max HP if any enemy feared
        "spawn_chance_pct": 25,    # 25% chance to spawn a Veil entity
        "once_per_encounter": True,
        # optional cooldown can be injected via rules; we gate by once/encounter here
    }
}

# ========= rules override hook =========
def override_from_rules(rules: dict):
    """Pull simple overrides for spell costs/cooldowns from combat_rules.json root keys."""
    global DEFAULT_SPELLS
    if not isinstance(rules, dict):
        return
    # copy
    book = {k: dict(v) for k, v in DEFAULT_SPELLS.items()}

    def apply(src_key, dst_key, spell_id, caster_key=None):
        node = rules.get(src_key)
        if isinstance(node, dict) and spell_id in book:
            val = node.get(caster_key or dst_key)
            if val is not None:
                # ints for costs; if you ever store floats, cast accordingly
                book[spell_id][dst_key] = int(val)

    # Veil Fog
    apply("veil_fog",        "stamina",   "veil_fog",        "stamina_cost")
    # Blood Pact
    apply("blood_pact",      "stamina",   "blood_pact",      "stamina_cost")
    apply("blood_pact",      "hp_pct_cost","blood_pact",     "hp_cost_percent")
    apply("blood_pact",      "damage",    "blood_pact",      "damage_bonus")
    # Whisper of Fear
    apply("whisper_of_fear", "stamina",   "whisper_of_fear", "stamina_cost")
    # Fade Step
    apply("fade_step",       "stamina",   "fade_step",       "stamina_cost")
    # Shroud’s Embrace
    apply("shrouds_embrace", "stamina",   "shrouds_embrace", "stamina_cost")
    apply("shrouds_embrace", "cooldown",  "shrouds_embrace", "cooldown")

    DEFAULT_SPELLS = book

# ========= helpers =========
def is_sorceress(unit: dict) -> bool:
    return str(unit.get("class", "")).lower() == "sorceress"

def _is_female(unit: dict) -> bool:
    return str(unit.get("gender", "")).lower() == "female"

def _get_spellbook(unit: dict) -> dict:
    sb = unit.get("spells")
    return sb if isinstance(sb, dict) and sb else DEFAULT_SPELLS

def _st(unit: dict) -> int:
    return int(unit.get("max_stamina", 0))

def _cur_st(unit: dict) -> int:
    return int(unit.get("current_stamina", unit.get("max_stamina", 0)))

def _set_st(unit: dict, new_val: int):
    max_s = _st(unit)
    unit["current_stamina"] = max(0, min(max_s, int(new_val)))

def _spend_stamina(unit: dict, amount: int, round_log: list, tag="cast"):
    before = _cur_st(unit)
    _set_st(unit, before - amount)
    round_log.append(f"🫁 {unit['name']} stamina -{amount} ➜ ST: {unit.get('current_stamina',0)}/{unit.get('max_stamina',0)}")
    if tag == "cast" and unit.get("_exhaust_spell_tax", 0) > 0:
        unit["_exhaust_spell_tax"] = 0  # exhaust applies to ONE ability only

def _heal(unit: dict, amount: int, round_log: list):
    if amount <= 0: return
    before = int(unit.get("current_hp", unit.get("total_hp", 0)))
    total = int(unit.get("total_hp", before))
    after = min(total, before + int(amount))
    unit["current_hp"] = after
    gained = after - before
    if gained > 0:
        round_log.append(f"✨ {unit['name']} heals {gained} ➜ HP: {after}/{total}")

def _take_hp_cost(unit: dict, pct: int, round_log: list):
    total = int(unit.get("total_hp", 0))
    dmg = max(1, (total * pct) // 100)
    before = int(unit.get("current_hp", total))
    unit["current_hp"] = max(0, before - dmg)
    round_log.append(f"🩸 {unit['name']} sacrifices {dmg} HP for power ➜ HP: {unit['current_hp']}/{total}")

def _snowball_step(cur_cor: int) -> int:
    """Extra corruption per prior cast scales harder after 75."""
    return 2 if cur_cor < 75 else 5

def _add_corruption(unit: dict, base_amount: int, round_log: list):
    casts = int(unit.get("_casts_this_fight", 0))
    cur = int(unit.get("corruption_level", 0))
    extra_per_cast = _snowball_step(cur)
    extra = extra_per_cast * casts
    new_val = cur + base_amount + extra
    unit["corruption_level"] = max(0, min(MAX_CORRUPTION, new_val))
    unit["_casts_this_fight"] = casts + 1
    round_log.append(f"☣️ Corruption +{base_amount}+{extra} ➜ {unit['corruption_level']}/{MAX_CORRUPTION}")

def _miscast_chance(unit: dict) -> float:
    # corruption adds up to ~+7.5% at 150
    return MISCAST_BASE + (unit.get("corruption_level", 0) / 20.0)

def _roll(n=100):
    return random.randint(1, n)

def _apply_fear(target: dict, rounds: int, round_log: list):
    target["_feared_rounds"] = max(int(target.get("_feared_rounds", 0)), rounds)
    round_log.append(f"😱 {target['name']} is rattled by fear ({rounds} round).")

def _apply_fog(targets: list[dict], rounds: int, round_log: list, atk_penalty: int):
    for t in targets:
        t["_fogged_rounds"] = max(int(t.get("_fogged_rounds", 0)), rounds)
        t["_fog_atk_penalty"] = atk_penalty
    if targets:
        round_log.append(f"🌫️ Veil Fog spreads: enemies suffer -{atk_penalty} to attack rolls for {rounds} round.")

def _apply_root(unit: dict, rounds: int, round_log: list):
    unit["_rooted_rounds"] = max(int(unit.get("_rooted_rounds", 0)), rounds)

def _apply_dazed(unit: dict, rounds: int, round_log: list):
    unit["_dazed_rounds"] = max(int(unit.get("_dazed_rounds", 0)), rounds)
    round_log.append(f"💫 {unit['name']} is dazed ({rounds} round).")

def _exhaust(unit: dict, round_log: list):
    unit["_exhaust_spell_tax"] = FADE_STEP_EXHAUST_STAMINA_TAX
    round_log.append(f"😮‍💨 {unit['name']} is spell-exhausted: next ability +{FADE_STEP_EXHAUST_STAMINA_TAX} stamina.")

def _veil_aura(enemies: list[dict], round_log: list, aura_penalty=10):
    for e in enemies:
        e["_veil_aura_rounds"] = 1
        e["_veil_aura_penalty"] = aura_penalty
    round_log.append(f"👁️ Veil’s Whisper unsettles foes (−{aura_penalty} to their next attacks).")

def _spell_damage_mult(cor: int) -> float:
    # Threshold damage pressure:
    #  <60: 0%; 60: +10%; 90: +20%; 120: +30%; 150: +60%
    if cor >= 150:
        return 1.60
    if cor >= 120:
        return 1.30
    if cor >= 90:
        return 1.20
    if cor >= 60:
        return 1.10
    return 1.00

def _friendly_fire_chance(cor: int) -> int:
    # At 120+: 20% chance a damaging spell hits the caster instead
    return 20 if cor >= 120 else 0

def on_new_round_tick(player: dict, enemies: list[dict], round_log: list):
    """Decay temporary flags each round."""
    for u in [player] + enemies:
        for key in ["_feared_rounds", "_fogged_rounds", "_rooted_rounds", "_dazed_rounds", "_veil_aura_rounds"]:
            if u.get(key, 0) > 0:
                u[key] = int(u[key]) - 1
        # clear per-round aura penalties when rounds expire
        if u.get("_veil_aura_rounds", 0) <= 0:
            u["_veil_aura_penalty"] = 0
        # exhaust tax is cleared on the next cast (_spend_stamina)

def present_spells_menu(caster: dict) -> str | None:
    spells = _get_spellbook(caster)
    ids = list(spells.keys())
    print("Cast which spell?")
    for i, sid in enumerate(ids, 1):
        meta = spells[sid]
        st = meta.get("stamina", 0)
        label = meta.get("label", sid)
        extra = []
        if meta.get("hp_pct_cost"):
            extra.append(f"{meta['hp_pct_cost']}% HP")
        if meta.get("once_per_encounter"):
            extra.append("1/enc.")
        if sid == "shrouds_embrace" and caster.get(SHROUD_ONCE_PER_ENCOUNTER_FLAG, False):
            extra.append("USED")
        tax = int(caster.get("_exhaust_spell_tax", 0))
        tax_note = f" (+{tax})" if tax else ""
        print(f"  [{i}] {label} — {st}{tax_note} stamina" + (f" ({', '.join(extra)})" if extra else ""))
    print("  [0] Back (do melee attack instead)")
    raw = input("Choose (0-{0}): ".format(len(ids))).strip()
    if raw == "0" or raw == "":
        return None
    try:
        idx = int(raw)
        if 1 <= idx <= len(ids):
            return ids[idx-1]
    except:
        pass
    return None

def apply_melee_vulnerability(unit: dict, incoming_damage: int, is_melee: bool) -> int:
    if not is_melee:
        return incoming_damage
    if is_sorceress(unit):
        return int(round(incoming_damage * MELEE_VULN_MULT))
    return incoming_damage

def consume_evade_on_melee_if_any(unit: dict, round_log: list) -> bool:
    """If Fade Step gave 'evade next melee', consume it and cancel the hit."""
    if unit.get("_evade_next_melee", False):
        unit["_evade_next_melee"] = False
        round_log.append("🪽 Fade Step triggers: the melee hit is negated!")
        return True
    return False

# ------------------ main cast dispatcher -------------------
def cast_spell(
    caster: dict,
    enemies: list[dict],
    apply_damage_cb,   # function(attacker, target, raw_damage, round_log, zone=None, is_crit=False)
    round_log: list
) -> bool:
    if not _is_female(caster):
        round_log.append("⚠️ The Veil recoils—only women may wield this sorcery.")
        return True

    if caster.get("_dazed_rounds", 0) > 0:
        round_log.append(f"💫 {caster['name']} is dazed and cannot cast this round.")
        return True

    sid = present_spells_menu(caster)
    if sid is None:
        return False  # do melee instead

    if sid == "shrouds_embrace" and caster.get(SHROUD_ONCE_PER_ENCOUNTER_FLAG, False):
        round_log.append("⛔ Shroud's Embrace has already been used this encounter.")
        return True

    book = _get_spellbook(caster)
    meta = book.get(sid, {})
    stamina_cost = int(meta.get("stamina", 0)) + int(caster.get("_exhaust_spell_tax", 0))
    hp_pct_cost = int(meta.get("hp_pct_cost", 0))
    corruption_gain = int(meta.get("corruption", 0))

    if stamina_cost > caster.get("current_stamina", caster.get("max_stamina", 0)):
        round_log.append("⛔ Not enough stamina to cast.")
        return True

    # Passive aura applies whenever she casts
    _veil_aura(enemies, round_log, aura_penalty=10)

    # pay resource costs
    if hp_pct_cost:
        _take_hp_cost(caster, hp_pct_cost, round_log)
        if caster.get("current_hp", 0) <= 0:
            return True
    _spend_stamina(caster, stamina_cost, round_log, tag="cast")
    _add_corruption(caster, corruption_gain, round_log)

    # miscast?
    mis_roll = _roll()
    if mis_roll <= _miscast_chance(caster):
        c = caster.get("corruption_level", 0)
        if c < 60:
            dmg = 5
            caster["current_hp"] = max(0, caster.get("current_hp", 0) - dmg)
            round_log.append(f"☠️ Miscast! Backlash {dmg} HP to {caster['name']}.")
        elif c < 90:
            caster["corruption_level"] = min(MAX_CORRUPTION, caster.get("corruption_level", 0) + 10)
            _apply_dazed(caster, 1, round_log)
            round_log.append("☠️ Miscast! Veil surges (+10 corruption).")
        else:
            _apply_root(caster, 1, round_log)
            round_log.append("☠️ Miscast! The Veil roots the caster in place (1 round).")
        return True

    # pick a default target (single-target engine)
    target = enemies[0] if enemies else None
    cor = int(caster.get("corruption_level", 0))
    dmg_mult = _spell_damage_mult(cor)
    ffire_pct = _friendly_fire_chance(cor)

    # effects per spell
    if sid == "veil_fog":
        atk_pen = int(meta.get("atk_penalty", 20))
        _apply_fog(enemies, meta.get("fog_duration", 1), round_log, atk_penalty=atk_pen)
        return True

    if sid == "blood_pact":
        if target:
            # Friendly fire at high corruption?
            hit_self = _roll() <= ffire_pct
            victim = caster if hit_self else target
            base = int(meta.get("damage", 30))
            if victim is not caster and victim.get("_feared_rounds", 0) > 0:
                base = int(round(base * 1.05))
            dmg = int(round(base * dmg_mult))
            apply_damage_cb(caster, victim, dmg, round_log, zone=None, is_crit=False)
            if hit_self:
                round_log.append("🩶 The Veil twists—Blood Pact lashes back at the caster!")
        if meta.get("self_dazed"):
            _apply_dazed(caster, int(meta["self_dazed"]), round_log)
        return True

    if sid == "whisper_of_fear":
        if target:
            caster_wp = int(caster.get("willpower", 35))
            target_wp = int(target.get("willpower", 25))
            roll_c = _roll()
            roll_t = _roll()
            if roll_c + (caster_wp // 5) >= roll_t + (target_wp // 5):
                if _roll() <= meta.get("freeze_chance_pct", 25):
                    _apply_dazed(target, 1, round_log)
                else:
                    _apply_fear(target, int(meta.get("apply_fear_rounds", 1)), round_log)
            else:
                if _roll() <= meta.get("backlash_fail_chance_pct", 20):
                    dmg = int(meta.get("backlash_damage", 5))
                    caster["current_hp"] = max(0, caster.get("current_hp", 0) - dmg)
                    round_log.append(f"🔄 Backlash! {caster['name']} takes {dmg} HP.")
        return True

    if sid == "fade_step":
        caster["_evade_next_melee"] = True
        round_log.append(f"🪽 {caster['name']} blurs—next melee hit will be avoided.")
        if meta.get("exhaust_after"):
            _exhaust(caster, round_log)
        return True

    if sid == "shrouds_embrace":
        any_feared = any(e.get("_feared_rounds", 0) > 0 for e in enemies)
        base = int(meta.get("damage", 40))
        dmg = int(round(base * dmg_mult))
        # friendly fire check: if it procs, the AoE collapses onto the caster
        hit_self = _roll() <= ffire_pct
        if hit_self:
            apply_damage_cb(caster, caster, dmg, round_log, zone=None, is_crit=False)
            round_log.append("🕳️ The Shroud backlashes—Isolde is torn by her own rift!")
        else:
            for e in enemies:
                _apply_root(e, meta.get("root_rounds", 1), round_log)
                apply_damage_cb(caster, e, dmg, round_log, zone=None, is_crit=False)

        _apply_root(caster, meta.get("root_rounds", 1), round_log)
        if any_feared:
            heal_amt = (caster.get("total_hp", 0) * int(meta.get("heal_on_fear_pct", 15))) // 100
            _heal(caster, heal_amt, round_log)

        # spawn chance
        if _roll() <= int(meta.get("spawn_chance_pct", 25)):
            spawn = {
                "name": "Veil Spawn",
                "race": "Aberration",
                "total_hp": 20,
                "current_hp": 20,
                "max_stamina": 10,
                "weapon_equipped": True,
                "weapon": "improvised_claws",
                "armor": ["Light_Light"],
                "alive": True,
            }
            enemies.append(spawn)
            round_log.append("👾 The rift births a Veil Spawn—an enemy joins the fray next round!")

        caster[SHROUD_ONCE_PER_ENCOUNTER_FLAG] = True
        return True

    round_log.append("…the magic flickers but nothing happens.")
    return True



