import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import careers  # noqa: E402
import ogre_hunger as H  # noqa: E402
import order_paths as O  # noqa: E402
import progression as P  # noqa: E402
import time_loop  # noqa: E402
from character import Character  # noqa: E402
from character_loader import find_class  # noqa: E402
from combat_health import CombatHealthManager  # noqa: E402
import character_store  # noqa: E402


class K:
    def __init__(self, cls="Crusader_Knight", **kw):
        self.name, self.class_name, self.race, self.gender = "K", cls, "Human", "Male"
        self.virtue = self.piety = 80
        self.corruption_level = 0
        self.__dict__.update(kw)
        O.start_at_creation(self, cls)


def test_paladin_is_no_longer_a_class():
    assert not find_class("Paladin")
    assert "Paladin" not in careers.DATA["classes"] and "Paladin" in careers.DATA["retired_classes"]


def test_crusader_starts_as_brother_knight():
    st = O.state(K())
    assert st["path"] == "crusader_knight" and st["rank"] == 1 and st["class_tier"] == 2


def test_paladin_honour_passive_only():
    k = K()
    assert O.grant_paladin(k)["ok"] is False
    st = O.state(k)
    st["rank"], st["sessions_at_rank"], st["reputation"] = 2, 4, 40
    O.record_deed(k, "veil_foe_slain", 3)
    assert O.grant_paladin(k, story_ok=False)["ok"] is False
    assert O.grant_paladin(k)["ok"] and O.is_paladin(k)
    p = O.paladin_passives(k)
    assert p["corruption_gain_mult"] == 0.75 and not any("damage" in key for key in p)
    k.virtue = 60
    assert O.paladin_passives(k) == {}  # Breath not full: passives sleep
    k.virtue = 80
    O.fall(k, 2)
    assert not O.is_paladin(k)


def _ogre(cls="Ogre_Brute", wil=30):
    c = Character()
    c.name, c.race, c.gender, c.class_name, c.willpower = "Grub", "Ogre", "Male", cls, wil
    c.body_parts = {"torso": 40, "left_arm": 20, "right_arm": 20, "head": 15}
    return CombatHealthManager(c)


def _friend():
    c = Character()
    c.name, c.race = "Friend", "Human"
    c.body_parts = {"torso": 30, "left_arm": 15, "right_arm": 15, "head": 10}
    return CombatHealthManager(c)


def test_hunger_states_and_recovery():
    m = _ogre()
    c = m.character
    H.eat(c, 6000)
    time_loop.day_tick(m)
    assert H.hunger_state(c)["id"] == "sated"
    for _ in range(2):
        H.eat(c, 2000)
        time_loop.day_tick(m)
    assert c.hunger["points"] == 8 and H.hunger_state(c)["id"] == "ravenous" and not H.is_fed(c)
    H.eat(c, 9000)
    time_loop.day_tick(m)
    assert c.hunger["points"] == 3


def test_starving_ogre_bites_nearest_companion_on_failed_check():
    m, f = _ogre(wil=0), _friend()
    m.character.hunger = {"points": 20, "kcal_today": 0}
    before = sum(f.health.values())
    rep = time_loop.day_tick(m, companions=[f], rng=random.Random(3))
    assert rep["hunger"]["bite"] and sum(f.health.values()) < before
    calm, f2 = _ogre(wil=200), _friend()
    calm.character.hunger = {"points": 20, "kcal_today": 0}
    assert time_loop.day_tick(calm, companions=[f2])["hunger"]["bite"] is None


def test_non_ogres_unaffected():
    f = _friend()
    assert "hunger" not in time_loop.day_tick(f)


def test_only_flesh_eater_devours():
    for cls in ("Ogre_Brute", "Ogre_Ravager", "Ogre_Behemoth", "Ogre_Stormbreaker"):
        assert H.devour(_ogre(cls), _friend(), True)["ok"] is False
    fe, v = _ogre("Ogre_Flesh_Eater"), _friend()
    fe.character.stamina = 20
    fe.health["torso"] -= 20
    fe._sync_total()
    assert H.devour(fe, v, False)["ok"] is False
    r = H.devour(fe, v, True)
    assert r["ok"] and r["healed"] == 15 and fe.character.corruption_level == 10
    assert fe.character.stamina == 10


def test_hunger_and_progression_saved(tmp_path):
    m = _ogre()
    m.character.hunger = {"points": 5, "kcal_today": 100}
    P.state(m.character)["order"] = {"path": "order_contractor"}
    character_store.save(m, str(tmp_path))
    back = character_store.load("Grub", str(tmp_path))
    assert back.character.hunger == {"points": 5, "kcal_today": 100}
    assert back.character.progression["order"]["path"] == "order_contractor"


def test_ravager_rips_but_does_not_eat():
    r = find_class("Ogre_Ravager")
    fr = r["abilities"]["active"]["flesh_rend"]
    assert fr["heal_hp"] == 0 and fr["corruption"] == 0 and "heal 1" not in fr["description"].lower()
    for a in r["abilities"].get("passive", {}).values():
        assert "corruption penalty" not in a["description"]
    assert not H.can_devour(_ogre("Ogre_Ravager").character)
