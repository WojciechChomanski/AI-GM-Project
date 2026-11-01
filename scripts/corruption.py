# file: scripts/corruption.py
"""Corruption stages, permanent marks, visibility and corrupted-creature HP (docs/ADVANTAGES_DISADVANTAGES.md).
Data: rules/corruption_marks.json. Corruption is GM-only (rules/stat_visibility.json). PLACEHOLDER numbers."""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def data():
    with open(os.path.join(ROOT, "rules/corruption_marks.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def stage(level):
    """Highest stage reached at this corruption level, or None below the first threshold."""
    cur = None
    for s in data()["stages"]:
        if level >= s["threshold"]:
            cur = s
    return cur


def visibility(level):
    s = stage(level)
    return s["visibility"] if s else "none"


def marks(peak_level):
    """Physical marks the body carries. Marks are permanent: pass the PEAK corruption ever reached,
    not the current (purged) value."""
    out = []
    for s in data()["stages"]:
        if peak_level >= s["threshold"]:
            out += s.get("marks", [])
    return out


def visible_to_others(peak_level):
    """Can an ordinary observer notice it at a glance? Only from visible_from (75) on."""
    return peak_level >= data()["visible_from"]


def player_hint(level):
    s = stage(level)
    return s["player_hint"] if s else ""


class Tracker:
    """Current corruption plus the permanent peak (purging lowers current, never the marks)."""

    def __init__(self, level=0):
        self.level = level
        self.peak = level

    def add(self, n):
        self.level = max(0, min(100, self.level + n))
        self.peak = max(self.peak, self.level)

    def purge(self, n):
        self.level = max(0, self.level - n)

    @property
    def marks(self):
        return marks(self.peak)

    @property
    def lost(self):
        return self.level >= 100


def hp_multiplier(override=None, tier="ordinary"):
    """Explicit override, else tier multiplier (ordinary x3, special x4)."""
    if override is not None:
        return override
    cc = data()["corrupted_creature"]
    return cc.get("tiers", {}).get(tier or "ordinary", cc["hp_multiplier"])


class CorruptedCreature:
    """pool = natural_hp * M; effective = normal + breath * M; dead when effective >= pool.
    wound_ratio = min(1, effective / natural_hp) drives wound/pain penalties, so it still degrades."""

    def __init__(self, natural_hp, multiplier=None, tier="ordinary"):
        self.natural_hp = natural_hp
        self.m = hp_multiplier(multiplier, tier)
        self.pool = natural_hp * self.m
        self.effective = 0
        self.breath_effective = 0  # part of effective that came from full-Breath wounds (not regenerated)

    def take(self, damage, breath=False):
        add = damage * (self.m if breath else 1)
        self.effective += add
        if breath:
            self.breath_effective += add
        return self.effective

    @property
    def hp(self):
        return max(0, self.pool - self.effective)

    @property
    def dead(self):
        return self.effective >= self.pool

    @property
    def wound_ratio(self):
        return min(1.0, self.effective / self.natural_hp) if self.natural_hp else 1.0
