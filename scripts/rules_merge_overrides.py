#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
rules_merge_overrides.py
Load your base combat_rules.json, then merge class_overrides (e.g., from
rules/combat_rules_overrides_crusader.json) and an Order choice from
rules/orders/Crusader_Orders.json.

You can use this standalone or import load_rules_with_overrides(...) elsewhere.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Iterable, Optional

__all__ = ["load_rules_with_overrides", "deep_merge"]

HERE = Path(__file__).resolve().parent
RULES_DIR = (HERE / "../rules").resolve()

def _load_json(p: Path) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

def _merge_overrides(base_rules: Dict[str, Any], override_files: Iterable[Path]) -> None:
    if "class_overrides" not in base_rules:
        base_rules["class_overrides"] = {}
    for f in override_files:
        if f and f.exists():
            data = _load_json(f)
            if isinstance(data, dict) and "class_overrides" in data:
                deep_merge(base_rules["class_overrides"], data["class_overrides"])

def _apply_order(base_rules: Dict[str, Any], order_file: Path, order_id: Optional[str]) -> None:
    if not order_id or not order_file.exists():
        return
    data = _load_json(order_file)
    if not isinstance(data, dict) or "orders" not in data:
        return
    target_class = data.get("applies_to_class") or "Crusader_Knight"
    chosen = None
    for o in data["orders"]:
        if str(o.get("id")).lower() == str(order_id).lower():
            chosen = o
            break
    if not chosen:
        return
    co = chosen.get("class_overrides") or {}
    if "class_overrides" not in base_rules:
        base_rules["class_overrides"] = {}
    # Merge under the class node
    node = base_rules["class_overrides"].setdefault(target_class, {})
    deep_merge(node, co)

def load_rules_with_overrides(
    base_rules_path: Path,
    override_files: Optional[Iterable[Path]] = None,
    chosen_order: Optional[str] = None,
    order_file: Optional[Path] = None
) -> Dict[str, Any]:
    base_rules = _load_json(base_rules_path)
    _merge_overrides(base_rules, override_files or [])
    _apply_order(
        base_rules,
        order_file or (RULES_DIR / "orders" / "Crusader_Orders.json"),
        chosen_order
    )
    return base_rules

if __name__ == "__main__":
    # Example CLI usage:
    base = RULES_DIR / "combat_rules.json"
    extra = [RULES_DIR / "combat_rules_overrides_crusader.json"]
    order = "templar"  # change to "hospitaller" or "teutonic" or None
    merged = load_rules_with_overrides(base, extra, order)
    print(json.dumps(merged.get("class_overrides", {}).get("Crusader_Knight", {}), indent=2))
