# file: scripts/first_aid.py
"""Kept for old imports. There is ONE bandage rule now (healing_system.HealingSystem ->
bleeding.attempt_bandage), which works on the real wound list in CombatHealthManager."""


class FirstAidSystem:
    def __init__(self):
        from healing_system import HealingSystem
        self._healing = HealingSystem()

    def attempt_bandage(self, healer, target, item_name="basic_bandage"):
        return self._healing.attempt_bandage(healer, target, item_name)
