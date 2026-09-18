"""Single-response development harness. No reference argument or scorer import."""

import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from . import VERSION
from .contract import CATALOG, RULES, VERSION as CONTRACT, apply_actions, assembly, keys


def reject_constant(value):
    raise ValueError("nonfinite JSON number")


def loads(text):
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number")
        return number

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    return json.loads(text, parse_constant=reject_constant, parse_float=finite_float,
                      object_pairs_hook=unique_object)


def read(path):
    return loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def source_hash():
    return digest({p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))})


def config_valid(config):
    required = {"provider", "model", "max_output_tokens", "max_actions", "timeout_seconds"}
    optional = {"api_key_env", "temperature", "reasoning_effort"}
    if not required <= config.keys() or config.keys() - required - optional:
        raise ValueError("invalid config fields")
    if config["provider"] not in ("noop", "openai", "anthropic"):
        raise ValueError("unsupported provider")
    if not isinstance(config["model"], str) or not config["model"]:
        raise ValueError("model ID is required")
    if config["model"].startswith("REPLACE_"):
        raise ValueError("replace the example model ID before running")
    for name in ("max_output_tokens", "max_actions", "timeout_seconds"):
        if type(config[name]) is not int or config[name] <= 0:
            raise ValueError("budgets must be positive integers")
    if config["provider"] != "noop" and not isinstance(config.get("api_key_env"), str):
        raise ValueError("api_key_env is required")
    if "temperature" in config and (type(config["temperature"]) not in (float, int)
                                   or not 0 <= config["temperature"] <= 2):
        raise ValueError("invalid temperature")
    if "reasoning_effort" in config and config["provider"] != "openai":
        raise ValueError("reasoning_effort is only implemented for OpenAI")
    return config


def packets(path):
    manifest = read(path)
    keys(manifest, ("schema", "cases"))
    if manifest["schema"] != CONTRACT or not isinstance(manifest["cases"], list) or not manifest["cases"]:
        raise ValueError("invalid task manifest")
    result = []
    seen = set()
    for case in manifest["cases"]:
        keys(case, ("id", "family", "source", "instructions", "inventory", "seed", "images"))
        if any(not isinstance(case[k], str) or not case[k] for k in ("id", "family", "source", "instructions")):
            raise ValueError("invalid case metadata")
        if case["id"] in seen:
            raise ValueError("duplicate case ID")
        seen.add(case["id"])
        assembly(case["seed"])
        if not isinstance(case["inventory"], list):
            raise ValueError("inventory must be a list")
        for item in case["inventory"]:
            keys(item, ("part", "color", "count"))
            if (item["part"] not in CATALOG or not isinstance(item["color"], str)
                    or type(item["count"]) is not int or item["count"] <= 0):
                raise ValueError("invalid inventory")
        images = []
        if not isinstance(case["images"], list):
            raise ValueError("images must be a list")
        for name in case["images"]:
            base = Path(path).resolve().parent
            asset = (base / name).resolve()
            if not asset.is_relative_to(base):
                raise ValueError("image escapes public task directory")
            media_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(asset.suffix.lower())
            if not media_type:
                raise ValueError("only PNG and JPEG image assets are supported")
            images.append({"media_type": media_type, "data": base64.b64encode(asset.read_bytes()).decode()})
        public = {k: case[k] for k in ("instructions", "inventory", "seed")}
        prompt = RULES + "\nCatalog:\n" + json.dumps(CATALOG, sort_keys=True) + "\nTask:\n" + json.dumps(public, sort_keys=True)
        result.append({"case": case, "packet": {"prompt": prompt, "images": images}})
    return result


def invoke(config, packet):
    if config["provider"] == "noop":
        return {"text": '{"actions": []}', "raw": {"baseline": "instruction-ignoring-noop"}, "complete": True, "usage": {}}
    # A hard per-case wall timeout; no automatic retry of potentially billed requests.
    try:
        process = subprocess.run([sys.executable, "-m", "brickbench.adapters"],
                                 input=json.dumps({"config": config, "packet": packet}),
                                 capture_output=True, text=True, timeout=config["timeout_seconds"],
                                 cwd=Path(__file__).resolve().parent.parent)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "billing_status": "unknown"}
    if process.returncode:
        return {"error": "adapter_process_failure"}
    return loads(process.stdout)


def _run(tasks, config_path, output):
    config = config_valid(read(config_path))
    cases = packets(tasks)
    for item in cases:
        item["packet"]["prompt"] += f"\nAction limit: {config['max_actions']}. One response; no retries.\n"
    if config["provider"] != "noop" and not os.environ.get(config["api_key_env"]):
        raise ValueError("missing API credential environment variable")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Excludes model config so matched model comparisons can check the common condition.
    condition = {"version": VERSION, "contract": CONTRACT, "source_hash": source_hash(),
                 "division": "model-only-single-response", "cases": cases,
                 "budgets": {k: config[k] for k in ("max_actions", "max_output_tokens", "timeout_seconds")}}
    meta = {"condition_hash": digest(condition), "condition": condition, "config": config}
    meta["run_hash"] = digest(meta)
    meta_path = output / "run.json"
    if meta_path.exists():
        if read(meta_path) != meta:
            raise ValueError("resume rejected: inputs, code, config, or assets changed")
    elif any(p.name != ".lock" for p in output.iterdir()):
        raise ValueError("new run requires an empty output directory")
    else:
        write(meta_path, meta)
    for index, item in enumerate(cases):
        path = output / f"case-{index:04d}.json"
        if path.exists():
            verify_record(read(path), meta["run_hash"], item["case"]["id"])
            continue
        pending = path.with_suffix(".pending")
        if pending.exists():
            raise ValueError("interrupted request has unknown billing state; inspect pending marker before explicitly removing it")
        pending.write_text("Request started. Do not automatically repeat after a crash.\n")
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        response = invoke(config, item["packet"])
        prediction = item["case"]["seed"]
        status = response.get("error", "complete" if response.get("complete") else "incomplete")
        actions = None
        if status == "complete":
            try:
                actions = loads(response["text"])
                prediction = apply_actions(prediction, actions, config["max_actions"])
            except (ValueError, TypeError, KeyError):
                status = "invalid_output"
        record = {"case_id": item["case"]["id"], "run_hash": meta["run_hash"],
                  "status": status, "response": response, "actions": actions,
                  "prediction": prediction, "started_at": started_at,
                  "seconds": time.monotonic() - started}
        record["record_hash"] = digest(record)
        write(path, record)
        pending.unlink()
    return {"run": str(output), "cases": len(cases), "condition_hash": meta["condition_hash"]}


def run(tasks, config_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".lock"
    try:
        with lock.open("x") as handle:
            handle.write("Run active. After a crash inspect pending requests before removing this lock.\n")
    except FileExistsError:
        raise ValueError("run is locked; another process or interrupted run may exist") from None
    try:
        return _run(tasks, config_path, output)
    finally:
        lock.unlink()


def verify_record(record, run_hash, case_id):
    payload = {k: v for k, v in record.items() if k != "record_hash"}
    if (record.get("record_hash") != digest(payload) or record.get("run_hash") != run_hash
            or record.get("case_id") != case_id):
        raise ValueError("prediction integrity check failed")
