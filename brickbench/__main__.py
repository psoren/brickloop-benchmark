import argparse
import json
from pathlib import Path
import sys

from .runner import digest, read, run, source_hash, verify_record, write
from .scorer import score


def evaluate(run_dir, reference_path):
    directory = Path(run_dir)
    meta = read(directory / "run.json")
    if meta["run_hash"] != digest({k: v for k, v in meta.items() if k != "run_hash"}):
        raise ValueError("run metadata integrity check failed")
    refs = read(reference_path)
    cases = meta["condition"]["cases"]
    if set(refs) != {item["case"]["id"] for item in cases}:
        raise ValueError("reference case IDs must match the complete manifest")
    rows = []
    for index, item in enumerate(cases):
        case = item["case"]
        record = read(directory / f"case-{index:04d}.json")
        verify_record(record, meta["run_hash"], case["id"])
        result = score(record["prediction"], refs[case["id"]])
        rows.append({"case_id": case["id"], "family": case["family"], "source": case["source"],
                     "status": record["status"], "completed_exact": record["status"] == "complete" and result["exact_geometry"],
                     "seconds": record["seconds"], "usage": record["response"].get("usage", {}), **result})
    return {"label": "development fixtures; not benchmark results", "model": meta["config"],
            "condition_hash": meta["condition_hash"], "run_hash": meta["run_hash"],
            "scorer_hash": source_hash(), "references_hash": digest(refs), "cases": rows,
            "summary": {"n": len(rows), "completed_exact": sum(r["completed_exact"] for r in rows) / len(rows),
                        "mean_pose_f1": sum(r["pose"]["f1"] for r in rows) / len(rows),
                        "failures": sum(r["status"] != "complete" for r in rows),
                        "seconds": sum(r["seconds"] for r in rows), "cost_usd": None}}


def compare(paths):
    reports = [read(path) for path in paths]
    signatures = {(r["condition_hash"], r["scorer_hash"], r["references_hash"]) for r in reports}
    if len(signatures) != 1:
        raise ValueError("cannot compare different tasks, budgets, inference code, references, or scorers")
    return [{"provider": r["model"]["provider"], "model": r["model"]["model"],
             "settings": r["model"], **r["summary"]} for r in reports]


def main():
    parser = argparse.ArgumentParser(description="Brickloop development harness")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--tasks", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("score")
    p.add_argument("--run", required=True)
    p.add_argument("--references", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("compare")
    p.add_argument("reports", nargs="+")
    args = parser.parse_args()
    try:
        if args.command == "run":
            result = run(args.tasks, args.config, args.out)
        elif args.command == "score":
            result = evaluate(args.run, args.references)
            write(args.out, result)
        else:
            result = compare(args.reports)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
