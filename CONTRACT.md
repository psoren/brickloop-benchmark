# Development contract: upright-v1

Frozen scope for the first scorer/runner slice, not the full proposed benchmark.
The executable validator is [`brickbench/contract.py`](brickbench/contract.py).
Changes to coordinate, matching, or action semantics require a new contract version.

## Pieces and coordinates

```json
{
  "id": "piece-1",
  "part": "brick-1x2",
  "color": "red",
  "position_mm": [0, 0, 9.6],
  "yaw_deg": 90
}
```

Right-handed coordinates, **z up**, in millimetres. The placement origin is the
horizontal center of the bottom plane, excluding studs. At yaw zero, dimensions
are x/y/z; positive yaw is counterclockwise about +z. This is **not LDraw's frame
or unit system**. One stud is 8 mm, a plate height 3.2 mm, and a brick height 9.6 mm.

Only upright quarter turns (0, 90, 180, 270 degrees) are supported. Reflection,
scale, tipping, hinges, arbitrary 6D poses, decorated parts, and imported official
part geometry are outside this version. Unsupported parts are rejected explicitly.
The abstract undecorated catalog ignores molded branding and manufacturing detail.

| Part | Size x/y/z, mm | Equivalent local yaw offsets |
|---|---|---|
| brick-1x1 | 8 / 8 / 9.6 | 0, 90, 180, 270 |
| brick-1x2 | 8 / 16 / 9.6 | 0, 180 |
| brick-2x2 | 16 / 16 / 9.6 | 0, 90, 180, 270 |
| plate-2x4 | 16 / 32 / 3.2 | 0, 180 |

IDs must be unique nonempty strings within an assembly, but do not determine
scoring correspondence. Colors are exact case-sensitive labels. Positions must
be finite numbers; no implicit snapping or rounding. Assemblies are capped at
1,000 pieces for this development implementation.

## Actions

One response contains exactly an `actions` array:

```json
{"actions": [
  {"op": "add", "piece": {"id": "a", "part": "brick-1x2", "color": "red", "position_mm": [0, 0, 0], "yaw_deg": 0}},
  {"op": "move", "id": "a", "position_mm": [8, 0, 0], "yaw_deg": 90},
  {"op": "remove", "id": "a"}
]}
```

Add requires a new ID; move/remove require an existing ID. Unknown fields and
duplicate JSON fields are rejected. Actions apply in order, as an atomic batch.
Malformed, truncated, or over-budget output leaves the seed unchanged and marks
the case failed. There is no automatic JSON repair, retry, or second chance.
Extra pieces and wrong inventory remain in a well-formed prediction and reduce
its score. The action interpreter does not reject collisions or infer support.

## Scoring

The frame is fixed for every current case. There is no global alignment in this
slice; full-object rigid alignment remains a proposal for a future track.

Inventory matches part/color multisets. Pose correspondence additionally requires
every position component to differ by at most **1e-6 mm** and orientation to agree
under the catalog symmetry. A maximum-cardinality bipartite matching prevents
one piece from satisfying multiple target pieces. This release reports aggregate
counts only, so it does not select a minimum-residual correspondence or expose
an instance correspondence map.

For both inventory and pose, precision = matched/predicted, recall =
matched/reference, and F1 = 2×matched/(predicted+reference). Empty against empty
scores 1; empty against nonempty scores 0 F1. Exact geometry requires all pieces
matched with no extras or omissions. Completed-exact also requires a successful
model response; a failed call cannot pass by leaving a correct seed untouched.

Collision, connection, support, insertion, and instruction fidelity are always
**unknown**. Even exact agreement with a floating reference does not certify a
physically valid build. No edge F1, physical completion score, tolerant score,
correct-prefix length, or repair-specific metric is implemented yet.

## Development fixtures and release gate

`examples/dev/tasks.json` contains six original **text-only** fixtures: two each
for stacking, bridges, and repeated subassemblies, with 3–6 pieces. Coordinates
are stated in the instructions on purpose: these exercise the harness and output
contract, not visual LEGO reasoning. `references.json` is a separate scorer input.
Both are public development data, not hidden or contamination-resistant tests.

Before collecting publishable benchmark results:

1. Create six visual instruction cases with verified geometry and independent
   reference review, preserving family boundaries for later train/test splits.
2. Add two small real-manual transfer cases with evidence-backed reconstructions
   and appropriate redistribution permissions.
3. Implement sequential state, per-step checkpoints, next-step versus whole-build
   conditions, and repair/no-edit pairs; add scoped physical checks.
4. Run matched model trials and an instruction-ignoring baseline. Inspect failures
   and references before expanding the corpus or publishing rankings.

The positive/negative regression suite already covers duplicate-all, omission,
wrong part/color, half-stud and plate-height errors, quarter-turn symmetry,
mirroring in a fixed frame, numeric noise, malformed poses, matching ambiguity,
and explicit unknown physics. Decorated geometry and insertion fixtures await
the corresponding supported geometry/checks.
