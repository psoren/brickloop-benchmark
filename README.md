# Brickloop Benchmark — development harness

Can an AI follow a LEGO manual, finish the build, and recover from mistakes?

**Status:** development harness, September 2026. A scorer, six text fixtures, and
model adapters are implemented. A validated visual dataset and leaderboard are
still future work. No paid model results have been collected.

- [Read the website](https://psoren.github.io/brickloop-benchmark/)
- [Read the full proposal](PROPOSAL.md)
- [Run and compare different models](RUNNER.md)
- [Placement/action contract and scorer semantics](CONTRACT.md)

The proposed benchmark combines next-step placement, whole-manual reconstruction, and repair. It uses small real sets and controlled generated builds, reports them separately, and increases difficulty gradually.

## Try the harness

Python 3.10+, no dependencies or API keys for this smoke test:

```sh
python3 -m unittest discover -s tests -v
python3 -m brickbench run --tasks examples/dev/tasks.json --config configs/noop.json --out runs/noop
python3 -m brickbench score --run runs/noop --references examples/dev/references.json --out runs/noop/report.json
```

This runs an instruction-ignoring baseline. See [RUNNER.md](RUNNER.md) for real
OpenAI and Anthropic configurations and paired comparisons. The current cases
test the harness using explicit textual coordinates; they do not measure visual
instruction understanding. The scorer supports upright abstract rectangular
pieces and reports unsupported physical checks as unknown.

## Local preview

No build or dependencies required:

```sh
python3 -m http.server 8794 --bind 127.0.0.1
```

Open `http://127.0.0.1:8794`. The site uses relative paths and can be served under a GitHub Pages project path. GitHub Pages is configured to publish `main` from the repository root; `.nojekyll` disables Jekyll processing.

Files: `index.html`, `styles.css`, `app.js`, and `PROPOSAL.md`. The interactive illustration is a schematic explanation of task inputs and outputs, not an actual benchmark case or physics simulator.

This repository contains the public proposal, website, original development
fixtures, and Python harness. It contains no official PDFs, private project data,
third-party model assets, or paid model results.
