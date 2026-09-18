"""Deterministic fixed-frame multiset metrics; no physical-validity claims."""

from collections import Counter, deque
from .contract import CATALOG, EPSILON, assembly


def maximum_matching(edges, right_count):
    """Augmenting paths: each prediction and target can contribute at most once."""
    owners = [-1] * right_count

    # Iterative paths avoid a recursion limit on large duplicate inventories.
    for root in range(len(edges)):
        queue = deque([root])
        via, previous = {}, {root: None}
        endpoint = None
        while queue and endpoint is None:
            left = queue.popleft()
            for right in edges[left]:
                if right in via:
                    continue
                via[right] = left
                if owners[right] == -1:
                    endpoint = right
                    break
                child = owners[right]
                if child not in previous:
                    previous[child] = right
                    queue.append(child)
        while endpoint is not None:
            left = via[endpoint]
            owners[endpoint] = left
            endpoint = previous[left]
    return sum(owner >= 0 for owner in owners)


def metrics(tp, predicted, reference):
    return {"matched": tp, "predicted": predicted, "reference": reference,
            "precision": tp / predicted if predicted else float(reference == 0),
            "recall": tp / reference if reference else 1.0,
            "f1": 2 * tp / (predicted + reference) if predicted + reference else 1.0}


def score(prediction, reference):
    assembly(prediction)
    assembly(reference)
    identity = lambda p: (p["part"], p["color"])
    pcounts, rcounts = Counter(map(identity, prediction)), Counter(map(identity, reference))
    edges = []
    for p in prediction:
        edges.append([j for j, r in enumerate(reference)
                      if identity(p) == identity(r)
                      and max(abs(a - b) for a, b in zip(p["position_mm"], r["position_mm"])) <= EPSILON
                      and (p["yaw_deg"] - r["yaw_deg"]) % 360 in CATALOG[p["part"]]["yaw_symmetry"]])
    matched = maximum_matching(edges, len(reference))
    return {"inventory": metrics(sum((pcounts & rcounts).values()), len(prediction), len(reference)),
            "pose": metrics(matched, len(prediction), len(reference)),
            "exact_geometry": matched == len(prediction) == len(reference),
            "frame": "fixed", "epsilon_mm": EPSILON,
            "physical_checks": {name: "unknown" for name in ("collision", "connection", "support", "insertion")},
            "instruction_fidelity": "unknown"}
