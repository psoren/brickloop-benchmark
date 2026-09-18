"""Strict, intentionally narrow upright-part contract. Units are millimetres."""

import copy
import math

VERSION = "upright-v1"
EPSILON = 1e-6
# Abstract undecorated rectangular parts; not a catalog of official LEGO geometry.
CATALOG = {
    "brick-1x1": {"size_mm": [8, 8, 9.6], "yaw_symmetry": [0, 90, 180, 270]},
    "brick-1x2": {"size_mm": [8, 16, 9.6], "yaw_symmetry": [0, 180]},
    "brick-2x2": {"size_mm": [16, 16, 9.6], "yaw_symmetry": [0, 90, 180, 270]},
    "plate-2x4": {"size_mm": [16, 32, 3.2], "yaw_symmetry": [0, 180]},
}
RULES = """Return only a JSON object {\"actions\": [...]} with no markdown.
Actions: {\"op\":\"add\",\"piece\":{\"id\":\"unique-id\",\"part\":\"brick-1x2\",
\"color\":\"red\",\"position_mm\":[0,0,0],\"yaw_deg\":0}},
{\"op\":\"remove\",\"id\":\"existing-id\"}, or
{\"op\":\"move\",\"id\":\"existing-id\",\"position_mm\":[0,0,0],\"yaw_deg\":90}.
Coordinates: right-handed, z up, millimetres; origin at horizontal center of
the piece's bottom plane, excluding studs. At yaw 0, catalog size is x,y,z.
Yaw is counterclockwise about +z, one of 0,90,180,270. No tipping, reflection,
or scale. Frame is fixed: no alignment or snapping. IDs are bookkeeping only.
One stud = 8 mm; one plate height = 3.2 mm; one brick height = 9.6 mm.
Output all actions in one response. Empty actions leave the seed unchanged.
"""


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("incorrect object fields")


def pose(position, yaw):
    if (not isinstance(position, list) or len(position) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in position)):
        raise ValueError("position must contain three finite numbers")
    if type(yaw) is not int or yaw not in (0, 90, 180, 270):
        raise ValueError("yaw must be an integer quarter turn")


def assembly(pieces):
    if not isinstance(pieces, list) or len(pieces) > 1000:
        raise ValueError("assembly must be a list of at most 1000 pieces")
    seen = set()
    for p in pieces:
        keys(p, ("id", "part", "color", "position_mm", "yaw_deg"))
        if not isinstance(p["id"], str) or not p["id"] or p["id"] in seen:
            raise ValueError("piece IDs must be unique nonempty strings")
        seen.add(p["id"])
        if not isinstance(p["part"], str) or p["part"] not in CATALOG:
            raise ValueError("unsupported part")
        if not isinstance(p["color"], str) or not p["color"]:
            raise ValueError("color must be a nonempty case-sensitive string")
        pose(p["position_mm"], p["yaw_deg"])
    return pieces


def apply_actions(seed, response, max_actions):
    """Atomic batch: malformed output leaves the seed unchanged in the runner.

    Semantic errors (extra pieces, collisions, wrong inventory) are NOT repaired.
    """
    keys(response, ("actions",))
    actions = response["actions"]
    if not isinstance(actions, list) or len(actions) > max_actions:
        raise ValueError("action budget exceeded or invalid actions")
    state = {p["id"]: copy.deepcopy(p) for p in assembly(seed)}
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("action must be an object")
        op = action.get("op")
        if op == "add":
            keys(action, ("op", "piece"))
            p = assembly([action["piece"]])[0]
            if p["id"] in state:
                raise ValueError("add ID already exists")
            state[p["id"]] = copy.deepcopy(p)
        elif op in ("move", "remove"):
            keys(action, ("op", "id", "position_mm", "yaw_deg") if op == "move" else ("op", "id"))
            if not isinstance(action["id"], str) or action["id"] not in state:
                raise ValueError("unknown action ID")
            if op == "remove":
                del state[action["id"]]
            else:
                pose(action["position_mm"], action["yaw_deg"])
                state[action["id"]].update(position_mm=action["position_mm"], yaw_deg=action["yaw_deg"])
        else:
            raise ValueError("unsupported action")
    return assembly(list(state.values()))
