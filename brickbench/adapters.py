"""Network adapters. Only public packet + model configuration enter this worker."""

import json
import os
import sys
import urllib.error
import urllib.request


def request_body(provider, config, packet):
    text = packet["prompt"]
    images = packet["images"]
    if provider == "openai":
        content = [{"type": "input_text", "text": text}]
        content += [{"type": "input_image", "image_url": "data:" + i["media_type"] + ";base64," + i["data"],
                     "detail": "high"} for i in images]
        body = {"model": config["model"], "input": [{"role": "user", "content": content}],
                "max_output_tokens": config["max_output_tokens"], "store": False}
        if "reasoning_effort" in config:
            body["reasoning"] = {"effort": config["reasoning_effort"]}
    elif provider == "anthropic":
        content = [{"type": "text", "text": text}]
        content += [{"type": "image", "source": {"type": "base64", **i}} for i in images]
        body = {"model": config["model"], "messages": [{"role": "user", "content": content}],
                "max_tokens": config["max_output_tokens"]}
        if "reasoning_effort" in config:
            raise ValueError("reasoning_effort is not implemented for this adapter")
    else:
        raise ValueError("unsupported network adapter")
    if "temperature" in config:
        body["temperature"] = config["temperature"]
    return body


def extract(provider, raw):
    if provider == "openai":
        text = "".join(c["text"] for item in raw.get("output", []) if item.get("type") == "message"
                       for c in item.get("content", []) if c.get("type") == "output_text")
        complete = raw.get("status") == "completed"
    else:
        text = "".join(c["text"] for c in raw.get("content", []) if c.get("type") == "text")
        complete = raw.get("stop_reason") == "end_turn"
    return {"text": text, "raw": raw, "complete": complete, "usage": raw.get("usage", {})}


def call(config, packet):
    provider = config["provider"]
    body = request_body(provider, config, packet)
    key = os.environ[config["api_key_env"]]
    if provider == "openai":
        url = "https://api.openai.com/v1/responses"
        headers = {"Authorization": "Bearer " + key}
    else:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=config["timeout_seconds"]) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as error:
        # Do not log request headers, credentials, or arbitrary server error bodies.
        return {"error": "http_error", "http_status": error.code}
    return extract(provider, raw)


if __name__ == "__main__":
    try:
        job = json.load(sys.stdin)
        result = call(job["config"], job["packet"])
    except Exception as error:
        result = {"error": type(error).__name__}
    print(json.dumps(result))
