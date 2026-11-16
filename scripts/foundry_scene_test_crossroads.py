# file: scripts/foundry_scene_test_crossroads.py
"""Test Crossroads Foundry Scene for Breath and the Veil.

Map: foundry/system/breath-and-the-veil/assets/maps/test-crossroads.webp
Grid: 32 x 32 squares, 128 px per square, 1 square = 1 m, canvas 4096 x 4096.
The stone fences along the roads block movement (climb them, or go around through
the crossroads). The wooden footbridge is a gap. House doors start closed.
"""
MAP_PX = 4096
GRID_SIZE = 128
SQUARES = 32
MAP_SRC = "systems/breath-and-the-veil/assets/maps/test-crossroads.webp"
THUMB_SRC = "systems/breath-and-the-veil/assets/maps/test-crossroads-thumb.webp"

# Geometry is in grid squares (0-32), converted to pixels at build time.
# Road fences sit on the 14 and 18 lines, leaving a 4 m wide road.
ROAD_FENCES = [
    # west side of the north-south road
    ((14, 0), (14, 14)),
    ((14, 18), (14, 32)),
    # east side of the north-south road
    ((18, 0), (18, 14)),
    ((18, 18), (18, 32)),
    # north side of the east-west road
    ((0, 14), (14, 14)),
    ((18, 14), (32, 14)),
    # south side of the east-west road (gap 21-25 is the footbridge)
    ((0, 18), (14, 18)),
    ((18, 18), (21, 18)),
    ((25, 18), (32, 18)),
    # south bank of the stream (east of the footbridge)
    ((25, 21), (32, 24)),
]

# Each house is a closed loop of points plus a door segment (two points on one edge).
# Loop points are listed clockwise and must include the door's two endpoints as
# consecutive points so the builder can swap that edge for a door wall.
HOUSES = [
    {  # NW L-shaped cottage, door on the south wall of the west wing
        "name": "nw-cottage",
        "loop": [(2, 2), (6, 2), (6, 4), (11, 4), (11, 9), (5, 9), (3, 9), (2, 9)],
        "door": ((5, 9), (3, 9)),
    },
    {  # NE burnt house, door on the south wall
        "name": "ne-house",
        "loop": [(20.5, 3.5), (30, 3.5), (30, 10), (25.5, 10), (23.8, 10), (20.5, 10)],
        "door": ((25.5, 10), (23.8, 10)),
    },
    {  # SW cottage, door on the north wall facing the road
        "name": "sw-cottage",
        "loop": [(2, 21), (3.5, 21), (5, 21), (11, 21), (11, 29), (2, 29)],
        "door": ((3.5, 21), (5, 21)),
    },
    {  # SE house by the stream, door on the north wall (the steps)
        "name": "se-house",
        "loop": [(20.5, 21), (23.5, 21), (25.2, 21), (29, 21), (29, 29), (20.5, 29)],
        "door": ((23.5, 21), (25.2, 21)),
    },
]


def _px(gx, gy):
    return int(round(gx * GRID_SIZE)), int(round(gy * GRID_SIZE))


def _same(a, b, eps=0.05):
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def _wall(_id, a, b, door=0, scene_id=""):
    x1, y1 = _px(*a)
    x2, y2 = _px(*b)
    rec = {
        "_id": _id,
        "_key": f"!scenes.walls!{scene_id}.{_id}",
        "c": [x1, y1, x2, y2],
        "light": 20,
        "sight": 20,
        "sound": 20,
        "move": 20,
        "dir": 0,
        "door": door,
        "ds": 0,
        "threshold": {"light": None, "sight": None, "sound": None, "attenuation": False},
        "flags": {},
    }
    return rec


def walls(doc_id, scene_id):
    out, n = [], 0

    def nid(label):
        nonlocal n
        n += 1
        return doc_id("scenes", f"wall-{n}-{label}")

    for a, b in ROAD_FENCES:
        out.append(_wall(nid("fence"), a, b, scene_id=scene_id))
    for house in HOUSES:
        loop = house["loop"]
        door = house["door"]
        for i, a in enumerate(loop):
            b = loop[(i + 1) % len(loop)]
            is_door = (_same(a, door[0]) and _same(b, door[1])) or (_same(a, door[1]) and _same(b, door[0]))
            out.append(_wall(nid(house["name"]), a, b, door=1 if is_door else 0, scene_id=scene_id))
    return out


def scene(doc_id):
    _id = doc_id("scenes", "test-crossroads")
    mid = MAP_PX // 2
    return {
        "_id": _id,
        "_key": f"!scenes!{_id}",
        "name": "Test Crossroads",
        "navName": "Test Crossroads",
        "navOrder": 0,
        "navigation": True,
        "active": False,
        "background": {
            "src": MAP_SRC,
            "tint": "#ffffff",
            "alpha": 1,
            "scaleX": 1,
            "scaleY": 1,
            "offsetX": 0,
            "offsetY": 0,
            "anchorX": 0,
            "anchorY": 0,
            "fit": "fill",
            "rotation": 0,
            "alphaThreshold": 0,
        },
        "foreground": None,
        "foregroundElevation": 0,
        "thumb": THUMB_SRC,
        "width": MAP_PX,
        "height": MAP_PX,
        "padding": 0.25,
        "initial": {"x": mid, "y": mid, "scale": 0.4},
        "backgroundColor": "#1a1610",
        "grid": {
            "type": 1,
            "size": GRID_SIZE,
            "style": "solidLines",
            "thickness": 1,
            "color": "#000000",
            "alpha": 0.2,
            "distance": 1,
            "units": "m",
        },
        "shiftX": 0,
        "shiftY": 0,
        "tokenVision": False,
        "fog": {
            "exploration": False,
            "reset": None,
            "overlay": None,
            "colors": {"explored": None, "unexplored": None},
        },
        "environment": {
            "darknessLevel": 0,
            "darknessLock": False,
            "cycle": True,
            "globalLight": {
                "enabled": True,
                "luminosity": 0,
                "bright": False,
                "color": None,
                "coloration": 1,
                "saturation": 0,
                "contrast": 0,
                "shadows": 0,
                "alpha": 0.5,
                "darkness": {"min": 0, "max": 1},
            },
            "base": {"hue": 0, "intensity": 0, "luminosity": 0, "saturation": 0, "shadows": 0},
            "dark": {"hue": 0.7, "intensity": 0, "luminosity": -0.25, "saturation": 0, "shadows": 0},
        },
        "walls": walls(doc_id, _id),
        "lights": [],
        "sounds": [],
        "drawings": [],
        "tokens": [],
        "notes": [],
        "tiles": [],
        "regions": [],
        "templates": [],
        "folder": None,
        "sort": 0,
        "ownership": {"default": 0},
        "flags": {
            "breath-and-the-veil": {
                "grid": {
                    "size_px": GRID_SIZE,
                    "distance": 1,
                    "units": "m",
                    "squares": SQUARES,
                    "map_px": MAP_PX,
                    "notes": "Each square is 1 metre. Stone fences along the roads block movement; climb them or go around through the crossroads. The wooden footbridge is a gap in the walls. House doors start closed. Token vision is off so the first test is easy to see; turn it on when you want fog of war.",
                }
            }
        },
        "playlist": None,
        "playlistSound": None,
        "journal": None,
        "journalEntryPage": None,
        "weather": "",
    }
