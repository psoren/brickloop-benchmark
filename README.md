# Brickloop Benchmark — proposal

Can an AI follow a LEGO manual, finish the build, and recover from mistakes?

**Status:** design proposal, September 2026. No released dataset, benchmark runner, or leaderboard yet.

- [Read the website](https://psoren.github.io/brickloop-benchmark/)
- [Read the full proposal](PROPOSAL.md)
- [How different models would run](RUNNER.md)

The proposed benchmark combines next-step placement, whole-manual reconstruction, and repair. It uses small real sets and controlled generated builds, reports them separately, and increases difficulty gradually.

## Local preview

No build or dependencies required:

```sh
python3 -m http.server 8794 --bind 127.0.0.1
```

Open `http://127.0.0.1:8794`. The site uses relative paths and can be served under a GitHub Pages project path. GitHub Pages is configured to publish `main` from the repository root; `.nojekyll` disables Jekyll processing.

Files: `index.html`, `styles.css`, `app.js`, and `PROPOSAL.md`. The interactive illustration is a schematic explanation of task inputs and outputs, not an actual benchmark case or physics simulator.

This repository contains only the public proposal and website. It contains no official PDFs, private project data, third-party model assets, or model results.
