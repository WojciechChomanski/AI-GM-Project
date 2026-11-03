import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from healing_system import HealingSystem  # noqa: E402


def _ally():
    return NS(name="Ally", status_effects=[{"name": "salt_kiss"}, {"name": "bleeding"}])


def test_passive_purge_needs_full_breath_and_verdict():
    hs, ally = HealingSystem(), _ally()
    judge = NS(name="J", class_name="Holy_Judge", virtue=80, piety=90, corruption_level=0, stamina=0)
    assert hs.breath_purge(judge, [ally], trigger="manual") == []
    assert hs.breath_purge(judge, [ally]) == ["Ally"] and ally.status_effects == [{"name": "bleeding"}]
    assert judge.stamina == 0  # no stamina: passive


def test_no_purge_without_breath_or_for_cleric():
    hs = HealingSystem()
    low = NS(name="J", class_name="Holy_Judge", virtue=40, piety=90, corruption_level=0)
    assert hs.breath_purge(low, [_ally()]) == []
    cleric = NS(name="C", class_name="Cleric", virtue=90, piety=90, corruption_level=0)
    assert hs.breath_purge(cleric, [_ally()]) == []
