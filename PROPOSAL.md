# Brickloop Benchmark

**A proposal for evaluating instruction following, complete assembly, and error recovery in LEGO-building AI.**

Version 0.1 · September 17, 2026 · Design draft

This document proposes the full evaluation protocol. A narrow [development contract and scorer](CONTRACT.md) and [model runner](RUNNER.md) are now implemented, with six text-only fixtures. The validated visual dataset, full evaluator, and paid model baselines have not been released. Numerical corpus sizes below are planning targets, not collected data or experimental results. Current implementation limits are documented in CONTRACT.md; the full geometry and interaction protocol below remains the target design.

## 1. The question we want to answer

Can an AI read a building manual, produce the intended digital model, and recover from its mistakes?

The main task is complete-manual reconstruction: instructions and an allowed parts library go in; a machine-readable assembly and action history come out. The system must carry its own state forward. Correct answers to isolated steps are useful diagnostics, but do not establish that the system can finish a build.

Our intended contribution is an evaluation combining long-horizon reconstruction, realistic manual conventions, and controlled repair tasks. It builds on existing LEGO research; it is not a claim to be the first LEGO benchmark.

## 2. Generated builds or actual sets?

**Recommendation: use both, with separate results and a common difficulty ladder. Start small in both.**

### Real-manual track: does the skill transfer?

Use small actual LEGO sets with accessible official instructions and independently verified digital references. Begin with ordinary bricks and plates, short manuals, and clearly observable placements. Size alone is insufficient: a small set with unusual connections may be harder to annotate and validate than a larger stack of conventional parts.

Real manuals test the distribution we care about: page layouts, parts-list insets, quantities, subassembly callouts, camera changes, and ambiguous views. Familiar public sets also carry memorization risk, so their scores should never be described as guaranteed contamination-free.

A downloaded community model is a candidate reference, not automatic ground truth. Check the exact set variant, parts, colors, poses, subassemblies, and official page alignment. Community `STEP` markers may follow a different construction sequence. Record evidence and unresolved alternatives. Exclude unresolved references from exact scoring and publish exclusion counts and reasons.

### Generated-build track: what causes failure?

Author original assemblies from a declared part vocabulary, with independently checked connections, collision geometry, and build sequences. Render their instruction pages and retain exact labels. Generate paired variations that change one factor: a view, quantity, offset, distractor part, or subassembly orientation.

Generated builds make it easier to control difficulty, create fresh challenges, and test scorer edge cases. Their weaknesses are generator bias, unrealistic manuals, and the possibility that generator and verifier share the same error. Independent validation and human audits are required; a generated label is not self-validating.

Hold out design families and construction templates, not just random seeds. A new seed applied to a familiar template is not strong evidence of structural generalization. Keep private challenge seeds and templates separate from published development examples.

### A paired transfer panel

Where references and usage rights permit, show the same held-out assembly through both an original manual and a generated manual. Evaluate the same endpoint under both renderings. If the sequences differ, compare whole-build results; use step-level paired scores only where the underlying states and operations are aligned.

Publish three result columns: generated builds, real manuals, and the paired transfer panel. Do not average them into a single score. Their proportions would otherwise obscure whether progress reflects real-manual transfer or familiarity with the generator.

## 3. Three task tracks

### A. Next step

Given a verified previous build and an instruction panel, predict the added components and their poses. In the **placement** condition, part identities and quantities are supplied. In the **page-reading** condition, the model must recover them from the page. Report these conditions separately.

Test legal-placement candidate selection as a separate assisted condition. Measure raw candidate recall, recall after validity filtering, recall after truncation to K, and picker accuracy conditional on the correct answer being available. An oracle picker provides a system ceiling; it is not a model baseline.

### B. Whole build — the primary track

Start from an empty assembly or a declared fixed seed. Present the full manual in the v0.1 condition, allowing revisits. Advance through construction using only the submitted state and allowed tools. Never replace the system's build with a correct prefix. Record additions, removals, moves, view operations, and termination.

The initial part inventory is supplied in v0.1 so catalog retrieval does not dominate the task. Later versions may add inventory discovery. Hidden poses, reference models, answer-bearing filenames, and target-derived annotations are unavailable to the model. Instructions themselves, including the final illustration, remain legitimate input.

A correct endpoint can be reached by an alternative valid sequence. Report endpoint correctness separately from fidelity to intermediate printed steps. Where order is genuinely required for insertion, assembly validity must enforce it.

### C. Repair

Provide instructions and a corrupted assembly state. Do not reveal the error type or location. Include both single-error cases and matched correct states requiring no change. Begin with controlled changes: wrong color, substituted part, missing or duplicate piece, half-stud/one-plate offset, asymmetric rotation, mirror error, and wrong repeat count.

Score whether the target is restored, whether unaffected parts are preserved, and how many edits were needed. Define an edit vocabulary before evaluating minimality. Compare against a proven minimum only where an oracle establishes it; otherwise report edit count and a reference bound without claiming optimality. Later tasks can include early mistakes whose effects appear several steps later and genuinely ambiguous evidence warranting abstention.

## 4. A curriculum based on reasoning demands

The piece ranges are initial selection guides, not definitions of difficulty. Assign tags for sequence length, branching/candidate ambiguity, occlusion, connector families, and nesting depth.

| Level | Indicative pieces | Skills | Initial status |
|---|---:|---|---|
| 0 — Foundations | 5–20 | Counts, colors, direct stacking, right-angle rotations | Pilot |
| 1 — Small builds | 20–60 | Several pages, asymmetric parts, offsets, viewpoint changes | Pilot |
| 2 — Subassemblies | 60–150 | Nested callouts, repeated versus mirrored builds, local-to-global transforms | Expansion |
| 3 — Hidden structure | 150–400 | Occlusion, underside work, multi-support placement, side studs | Expansion |
| 4 — Mechanisms | Variable | Pins, axles, hinges, articulation, insertion dependencies | Research track |

Do not place a complex ten-part mechanism in Foundations. Unsupported connector families belong in an explicitly exploratory track until validated. Expanding the vocabulary changes the benchmark version rather than silently changing historical scores.

## 5. Proposed first pilot

Aim for **12 verified real builds and 12 generated builds**, concentrated in Levels 0–1. Select 120 diagnostic steps from each source and derive 60 repair cases: 40 corrupted cases and 20 clean controls, balanced between sources. These are feasibility targets. A smaller fully verified corpus is preferable to a nominal target filled with uncertain references.

Choose cases before running models. Publish the selection manifest, exclusions, difficulty tags, reference status, and hashes. Keep a public development slice and a separate evaluation slice, split by build family before any synthetic expansion. The 24-build pilot is for validating the protocol, not fine-grained model ranking; do not subdivide its results into statistically unsupported claims.

Success of the pilot means the inputs are usable, references are trustworthy, the scorer rejects known failures, and the three tracks reveal distinguishable failure modes. Expand after that: more independent builds, more styles and families, then longer manuals and mechanisms.

## 6. Inputs, outputs, and allowed assistance

Each case declares the instruction assets, catalog and inventory, starting state, units, coordinate conventions, permitted actions/tools, and resource budget. Each submission contains a structured placement/action trace and a final LDraw-compatible assembly. A canonical assembly representation is used for scoring so a particular output language is not privileged.

Run direct pose, connection-relative, and enumerate-and-pick systems against the same task contracts, but identify the representation and assistance in result tables. Maintain separate model-only and tool-assisted divisions. Rendering, code execution, snapping, candidate enumeration, and validator feedback must be declared. If an adapter repairs or snaps a prediction, record that operation and its cost rather than silently fixing the answer.

For v0.1, use a closed asset environment: no web lookup of the set or its model. Publish model/version, prompt hash, temperature and sampling settings, image resolution, tool versions, retries, timeouts, token usage, latency, and cost. Allow at most one scored submission per trial; retries consume the declared budget. Repeated trials use the same preregistered budget and remain individually visible.

## 7. What counts as success?

Keep four dimensions separate: inventory, physical geometry, instruction fidelity, and presentation. Render quality does not compensate for geometric mistakes.

**Primary outcome: exact whole-build completion.** No extra or missing components; correct identities/colors and symmetry-equivalent poses; a single declared global rigid alignment permitted for the complete object. Reflections are not equivalent rotations. Numeric tolerance accommodates representation precision, not a half-stud or one-plate error. Publish the chosen thresholds and their calibration fixtures before baselines.

**Physical verification is a distinct result.** Report pass, fail, or unknown for connection legality, collision, support, and insertion feasibility, along with coverage. A collision-free final model need not have a feasible insertion sequence. Static connection graphs alone do not prove clutch strength or stability under load. A fully verified completion requires both geometric completion and all checks required by that track to pass.

Supporting metrics:

- Part/color precision, recall, and F1, with extra pieces penalized.
- Pose precision/recall/F1 using one-to-one instance matching and valid part symmetries; decoration may remove geometric symmetry.
- Typed connector-edge F1 within verified connector coverage.
- Exact step success, first-error position, and correct prefix length.
- Repair success, unnecessary edits, and no-edit accuracy on clean controls.
- Confidence/abstention on explicitly ambiguous tasks, reported as a coverage-versus-error curve.
- Wall-clock time, token usage, tool calls, and inference cost.

Use maximum-cardinality matching over valid correspondences, then minimize residual error. Do not let duplicate pieces inflate recall into a perfect score. For fixed-prefix tasks, retain the supplied frame; never recenter each predicted step to hide drift. Report exact and tolerant metrics separately.

Aggregate whole-build outcomes per independent build family and show uncertainty intervals using families as the resampling unit. Publish both step-micro and build-macro diagnostics. Timeouts, malformed predictions, and system errors remain in the fixed denominator; reference defects are versioned exclusions, not quiet removals.

## 8. Integrity before scale

Keep every related build, rerelease, alternate rendering, and synthetic derivative on one side of the train/development/test boundary. Record known public-data exposure. Do not claim existing official sets are unseen merely because they were held out of our training pipeline.

Separate model-visible files from scorer-only reference assets at the filesystem and tool boundary. Freeze predictions before score disclosure. Hash the dataset, prompts, part catalog, scorer, and submissions. Log actions without exposing hidden labels through validator error messages.

Build scorer fixtures before model baselines: exact positive; duplicate-all; omitted/substituted/wrong-color parts; half-stud and one-plate offsets; symmetric/asymmetric rotations; decorated parts; mirrored subassemblies; reordered identical instances; touching without mating; blocked insertion; missing connector metadata. Correct cases must pass, known errors must fail the relevant check, and unsupported physics must remain unknown.

Reference annotation should have separate construction and verification passes with evidence for each placement. Genuine ambiguity needs admissible alternatives or exclusion from exact scoring. Catalog aliases and flexible/articulated parts require an explicit equivalence policy; keep unresolved cases outside the initial exact track.

## 9. Baselines and useful experiments

Start with a random legal-candidate picker, an oracle-candidate ceiling, a zero-shot vision-language model, and a tool-assisted version of that same model. Add an instruction-trained system when available. Model-only and tool-assisted outcomes get separate columns.

Run paired comparisons changing one factor: supplied versus inferred piece identities; correct versus predicted prefix; direct poses versus legal candidates; tools versus no tools; generated versus real instructions for aligned held-out builds. These comparisons isolate recognition, accumulated error, representation, tool benefit, and transfer.

The public results interface should replay the manual panel and evolving build, highlight the first divergence, and display component-level differences. It should also expose failure/unknown categories and resource usage. This proposal site shows a schematic interaction only; it contains no model results.

## 10. Running multiple models

Use one task controller, model-specific adapters, and an independent scorer. The controller owns state, task assets, tools, and resource budgets. Each adapter translates the same input contract into a provider's request format and returns structured actions. The scorer receives frozen outputs and hidden references after inference.

Maintain separate model-only and tool-assisted divisions, with an identical tool environment within each comparison. Record exact model versions, prompt and input hashes, adapter versions, settings, retries, and actual usage. Preserve provider-native responses as well as normalized actions. Model-specific preprocessing and incompatible context limits must be visible, not silently changed.

Save resumable case traces and predictions. Evaluation can then rescore every model after a scorer correction without repeating paid inference. Compare models on identical case families and budgets, retain failures in the denominator, and publish repeated trials where affordable. See [the runner design](RUNNER.md) for the adapter contract, budget policy, and proposed command interface.

## 11. Related work

- [Snap Spatial Benchmark](https://eng.snap.com/spatial_intelligence): structured spatial tasks and typed validators inspire the scoring approach.
- [BC-Bench / Brick-Composer](https://arxiv.org/abs/2606.05445): direct precedent for instruction-conditioned brick selection and pose estimation.
- [LEGO-Puzzles](https://arxiv.org/abs/2503.19990): visual reasoning and multi-step planning diagnostics.
- [BrickAGI](https://github.com/withtally/brickagi): catalog, task compliance, and supported buildability checks for generated designs.
- [MEPNet](https://arxiv.org/abs/2207.12572): visual LEGO manuals translated into machine-executable assembly plans.
- [InstructioNet](https://arxiv.org/abs/2410.01111): self-created visual instructions and sequential reconstruction.
- [BrickNet](https://arxiv.org/abs/2604.22984): graph-based representations for generative brick assembly.

These tasks have different inputs and scoring contracts. Their published percentages are not directly comparable with the proposed benchmark. Reuse requires pinning each release and verifying metric definitions, data availability, and permitted use.

## 12. Decisions still open

The recommended source strategy is hybrid; the exact first builds, train/evaluation allocation, rendering style, pose tolerances, part vocabulary, inference budget, and human-baseline protocol remain to be fixed. Proposed corpus sizes and piece bands should change if reference verification or pilot behavior shows they are inappropriate.

Completed development slice: upright placement/action contract, positive/negative scorer tests, and a single-response hosted-API runner. Next deliverables, in order: independently verified visual pilot manifest; sequential isolated runner and three task adapters; baseline runs with traces; public results and a larger challenge pool. Text-only harness fixtures are not the visual pilot.

This repository publishes original proposal text and a schematic illustration. Future releases should publish source links, provenance, and only assets with verified redistribution permission. It currently includes no official instruction PDFs or third-party model files. LEGO is a trademark of the LEGO Group; this independent project is not affiliated with or endorsed by the LEGO Group.
