# file: scripts/time_utils.py

import json
import os

TIME_FILE = "rules/world_time.json"

def load_time():
    if not os.path.exists(TIME_FILE):
        return { "day": 1, "hour": 6 }
    with open(TIME_FILE, "r") as f:
        return json.load(f)

def save_time(data):
    with open(TIME_FILE, "w") as f:
        json.dump(data, f, indent=2)

def skip_time(hours: int):
    time = load_time()
    time["hour"] += hours

    while time["hour"] >= 24:
        time["hour"] -= 24
        time["day"] += 1

    save_time(time)
    print(f"⏳ Time skipped by {hours}h → Now Day {time['day']}, Hour {time['hour']}")

    return time
