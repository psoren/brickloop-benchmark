# Running different models

**Implemented development slice, September 2026:** a Python standard-library CLI,
fixed-frame scorer, six text fixtures, and OpenAI/Anthropic API adapters. Provider
requests are covered by local tests; live paid runs have not been performed.
There is no validated visual corpus or leaderboard yet. See [CONTRACT.md](CONTRACT.md).

## Run it now

Requires Python 3.10+. From the repository root, no installation or API key is
needed for the instruction-ignoring baseline:

```sh
python3 -m unittest discover -s tests -v
python3 -m brickbench run --tasks examples/dev/tasks.json --config configs/noop.json --out runs/noop
python3 -m brickbench score --run runs/noop --references examples/dev/references.json --out runs/noop/report.json
```

For real models, copy `configs/openai.json` and `configs/anthropic.json`, replace
`REPLACE_WITH_EXACT_MODEL_ID` with the exact model IDs available to your accounts,
and set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in your local environment. Keep keys
out of files and shell history. Then run the same tasks and budgets:

```sh
python3 -m brickbench run --tasks examples/dev/tasks.json --config configs/openai.json --out runs/model-a
python3 -m brickbench run --tasks examples/dev/tasks.json --config configs/anthropic.json --out runs/model-b
python3 -m brickbench score --run runs/model-a --references examples/dev/references.json --out runs/model-a/report.json
python3 -m brickbench score --run runs/model-b --references examples/dev/references.json --out runs/model-b/report.json
python3 -m brickbench compare runs/model-a/report.json runs/model-b/report.json
```

The two `run` commands above make billable API requests. Start with a small
explicit budget. Defaults are one call per case, 4,096 output tokens, 64 actions,
and 120 seconds per case, with **zero retries**. Six cases therefore permit at
most six calls per run, excluding any deliberate reruns in new output directories.
Input-token charges are additional; no dollar-cost estimator or spend cap exists.
Model IDs, provider defaults, and supported sampling parameters must be reviewed
before interpreting a comparison. `temperature` is optional; OpenAI additionally
accepts `reasoning_effort`. Unspecified provider settings remain provider defaults,
not an assertion of equal inference compute. Anthropic extended-thinking controls
are not implemented. Use separate output directories for repeated trials.

## What this release does

- Runs **model-only, single-response assembly** from a declared seed. No renderer,
  interactive tools, automatic correction, or sequential feedback is supplied.
- Sends the same prompt and original PNG/JPEG bytes through native API envelopes.
  Provider image preprocessing and token accounting may differ. The included
  text fixtures have no images and are only a plumbing check.
- Freezes task packets, image bytes, configuration, code hash, budgets, raw provider
  responses, actions, final predictions, timestamps, latency, and reported usage.
- Evaluates inventory F1, pose F1, and exact geometry separately from call success.
  Failures stay in the denominator. Physical checks remain unknown and cost is null.
- Resumes completed cases without calling again, verifies saved hashes, and rejects
  changed inputs/configuration/code. Hashes detect accidental modification; they
  are not signatures or a defense against someone rewriting an entire run.
- Stops ambiguous crash recovery with `.pending` markers. Inspect billing/request
  state before explicitly removing a pending marker and retrying. A `.lock` stops
  concurrent writers; after a process crash inspect the run before removing it.
- Scores saved runs offline and rejects comparisons with differing task/budget,
  inference-code, reference, or scorer hashes. Reports retain the model settings;
  a matching condition hash alone does not make those settings scientifically fair.

Inference takes **no reference path**. Only public packet fields enter the API
request; the hosted models receive no filesystem or other tools. Reference files
are public in this development repo. This is data separation for the hosted API
path, **not a sandbox** for an untrusted local agent. A future local/tool-assisted
adapter needs a separate execution environment without mounted scoring assets.

API formats were checked against [official OpenAI image-input documentation](https://developers.openai.com/api/docs/guides/images-vision)
and [Anthropic's Messages documentation](https://platform.claude.com/docs/en/build-with-claude/working-with-messages).
The OpenAI adapter uses Responses; the Anthropic adapter uses Messages. Additional
providers can implement the same `request_body` / `extract` boundary; Gemini and
local model adapters have not been implemented.

## Target architecture beyond this release

The following sections describe the larger proposed protocol. Sequential state,
tool assistance, resumable within-case checkpoints, full 6D geometry, and the
additional metrics below remain future work.

## One task contract, multiple adapters

```text
Frozen task manifest + model configuration
                    ↓
          Shared task controller
                    ↓
          Model-specific adapter
       ↙            ↓            ↘
 Hosted API    Local inference    Custom system
       ↘            ↓            ↙
      Structured actions + final assembly
                    ↓
       Frozen predictions and tool trace
                    ↓
          Independent evaluator
                    ↓
      Per-case results + comparison report
```

The controller owns task state, budgets, and tool access. An adapter handles a provider's message and image format, authentication, and response parsing. The evaluator owns hidden references. Model requests never receive scoring assets.

Adapters must not contain model-specific hints, silent geometry fixes, or retries outside the common policy. If a model needs snapping or candidate enumeration, those are declared tools in an assisted condition. A separately trained custom pipeline is a system entry, not relabeled as the underlying model alone.

## Model configuration

Register an exact model identifier and provider adapter, with supported image formats, context/output limits, sampling settings, reasoning mode when applicable, and an environment-variable name for credentials. Never store keys in manifests or logs. Store the effective configuration and adapter commit with each run.

Use native provider adapters or a declared compatible-server adapter for locally served models. Normalize the public task semantics and output schema; do not assume different providers implement identical image preprocessing, reasoning controls, or token accounting.

## The task packet

Every model in a comparison receives the same instruction asset bytes at a declared resolution, catalog/inventory, coordinate conventions, task prompt, and allowed output/action schema. The same case order and reset rules apply. Per-step placement conditions may supply the correct prefix; whole-build conditions never do.

If the full manual does not fit all models, declare a common page-retrieval protocol or a separate long-context division. Do not silently truncate one model's input. Unsupported task/model combinations are recorded as not supported, rather than quietly shrinking a model's test set.

## Two primary divisions

| Division | Model access | What is being compared |
|---|---|---|
| Model-only | Task packet and maintained state; no external code, renderer, candidates, or validator feedback | Instruction understanding and placement decisions under the declared interaction protocol |
| Tool-assisted | Identical task tools, state transitions, feedback, and limits | The model plus a fixed building environment |

Both divisions can be sequential. Model-only does not mean the entire build must fit one response. The controller applies well-formed actions and supplies the resulting state; physical-validator feedback is available only in a condition that explicitly allows it. Schema errors follow a fixed repair policy and count toward the budget.

The tool-assisted vocabulary might include `inspect_part`, `render_state`, `enumerate_placements`, `apply_actions`, and `validate_state`. Tools may inspect the submitted build and public catalog. They cannot access the hidden intended answer. Never expose target similarity as a feedback tool in the main track.

## Budget and retry policy

Set common caps on actions, tool calls, wall-clock time, and generated tokens, while logging provider-reported reasoning tokens separately where available. Tokens are not perfectly comparable across providers. Report results under at least one preregistered fixed-budget condition; later add cost-versus-success curves.

Transport retries repeat the same request, have a bounded policy, and are logged. New sampled answers, self-corrections, and schema-repair attempts consume the inference budget. Choose an explicit policy for billed requests whose responses are lost. Stop on exhaustion and retain the partial assembly.

Use repeated trials where budget permits. Temperature zero is not a guarantee of determinism. Publish model snapshots, dates, trial counts, settings, actual costs, and latency; do not compare a best-of-many sample for one model with one attempt for another.

## Inference and evaluation are separate jobs

Inference saves input hashes, raw responses, parsed actions, checkpoints, final predictions, and tool events. Each case has a stable ID; resuming a run continues unfinished cases without rerunning completed ones. Hash and freeze predictions before scoring.

Evaluation is deterministic where the chosen geometry checks permit it. It reads frozen predictions and protected references, then emits metric components, failures, unknown checks, and resource totals. A scorer bug can be fixed and every saved run rescored without calling any model again. Publish both the old and new scorer versions and revised results.

An illustrative future command interface would be:

```sh
# Proposed commands for future tracks; use python3 -m brickbench above today.
brickbench run --manifest pilot-v1.json --model model-a --division model-only --trials 3
brickbench run --manifest pilot-v1.json --model model-b --division model-only --trials 3
brickbench run --manifest pilot-v1.json --model model-a --division tool-assisted --trials 3
brickbench score --runs runs/ --scorer scorer-v1
brickbench compare --runs runs/ --group-by source,level,track,division
```

## Reports

The comparison table should include whole-build completion, pose F1, correct-prefix length, repair success, no-edit accuracy, verified physical coverage, cost, and latency. Separate real/generated inputs, task tracks, and assistance divisions. Show sample counts and family-level uncertainty; paired model comparisons should use the same cases. Retain timeouts, parse failures, and exhausted runs in the evaluation denominator.

Useful first entries are a random legal-candidate picker, an oracle-candidate ceiling, a general vision-language model, and the same model using the fixed tool environment. Add more model adapters after one complete inference → freeze → score → report cycle is validated.
