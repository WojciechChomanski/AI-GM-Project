#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilities for building per-character tone/style prompts.
Fix: avoid backslashes inside f-string expressions.
"""

def build_tone_prompt(character):
    name = character.get("name", "Unknown")
    background = character.get("background", "Unknown")
    speech_style = character.get("speech_style", "")
    emotions = character.get("emotional_state", [])
    quirks = character.get("quirks", [])

    # Precompute blocks to avoid backslashes inside f-string expressions
    emotions_block = ", ".join(emotions) if emotions else "None"
    if quirks:
        quirks_block = "- " + "\n- ".join(quirks)
    else:
        quirks_block = "None"

    prompt_text = (
        "You are to simulate the speaking style of the following character.\n\n"
        f"Name: {name}\n"
        f"Background: {background}\n"
        f"Speech Style: {speech_style}\n"
        f"Common Emotions: {emotions_block}\n"
        "Quirks:\n"
        f"{quirks_block}\n\n"
        "Keep responses within that tone and avoid breaking character unless explicitly instructed."
    )
    return prompt_text
