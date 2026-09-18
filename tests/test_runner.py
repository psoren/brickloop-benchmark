import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from brickbench.__main__ import compare, evaluate
from brickbench.adapters import call, extract, request_body
from brickbench.runner import digest, loads, packets, read, run, write

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "examples/dev/tasks.json"
REFS = ROOT / "examples/dev/references.json"
CONFIG = ROOT / "configs/noop.json"


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "run"

    def test_offline_end_to_end_and_resume(self):
        run(TASKS, CONFIG, self.out)
        original = (self.out / "case-0000.json").read_bytes()
        with patch("brickbench.runner.invoke", side_effect=AssertionError("must not rerun")):
            run(TASKS, CONFIG, self.out)
        self.assertEqual(original, (self.out / "case-0000.json").read_bytes())
        report = evaluate(self.out, REFS)
        self.assertEqual(report["summary"]["n"], 6)
        self.assertEqual(report["summary"]["completed_exact"], 0)
        self.assertEqual(report["summary"]["failures"], 0)

    def test_adapter_receives_only_public_inputs(self):
        def fake(config, packet):
            self.assertEqual(set(packet), {"prompt", "images"})
            self.assertNotIn("references", packet["prompt"])
            return {"text": '{"actions": []}', "complete": True}
        with patch("brickbench.runner.invoke", side_effect=fake):
            run(TASKS, CONFIG, self.out)

    def test_failed_calls_stay_in_denominator(self):
        with patch("brickbench.runner.invoke", return_value={"error": "timeout"}):
            run(TASKS, CONFIG, self.out)
        report = evaluate(self.out, REFS)
        self.assertEqual(report["summary"]["n"], 6)
        self.assertEqual(report["summary"]["failures"], 6)

    def test_invalid_output_keeps_seed(self):
        with patch("brickbench.runner.invoke", return_value={"text": '{"actions":[{"op":"bad"}]}', "complete": True}):
            run(TASKS, CONFIG, self.out)
        self.assertEqual(read(self.out / "case-0000.json")["status"], "invalid_output")
        self.assertEqual(evaluate(self.out, REFS)["summary"]["failures"], 6)

    def test_nonfinite_and_duplicate_json_rejected(self):
        for text in ['{"x": NaN}', '{"x": 1e999}', '{"actions": [], "actions": [1]}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                loads(text)

    def test_run_lock_prevents_concurrent_requests(self):
        self.out.mkdir()
        (self.out / ".lock").write_text("another process")
        with patch("brickbench.runner.invoke", side_effect=AssertionError("must not call")):
            with self.assertRaisesRegex(ValueError, "locked"):
                run(TASKS, CONFIG, self.out)

    def test_perfect_outputs_score_one_in_test_only(self):
        # Test-only oracle lives outside the runner; never presented as a model result.
        refs = read(REFS)
        responses = [{"text":json.dumps({"actions":[{"op":"add", "piece":p} for p in ref]}),
                      "complete":True} for ref in refs.values()]
        with patch("brickbench.runner.invoke", side_effect=responses):
            run(TASKS, CONFIG, self.out)
        self.assertEqual(evaluate(self.out, REFS)["summary"]["completed_exact"], 1)

    def test_tamper_and_changed_config_rejected(self):
        run(TASKS, CONFIG, self.out)
        changed = read(CONFIG)
        changed["max_actions"] += 1
        config_path = Path(self.temp.name) / "config.json"
        write(config_path, changed)
        with self.assertRaisesRegex(ValueError, "resume rejected"):
            run(TASKS, config_path, self.out)
        p = self.out / "case-0000.json"
        data = read(p)
        data["prediction"] = read(REFS)["stack-a"]
        write(p, data)
        with self.assertRaisesRegex(ValueError, "integrity"):
            evaluate(self.out, REFS)

    def test_pending_request_not_repeated(self):
        run(TASKS, CONFIG, self.out)
        (self.out / "case-0000.json").unlink()
        (self.out / "case-0000.pending").write_text("uncertain billing")
        with self.assertRaisesRegex(ValueError, "billing"):
            run(TASKS, CONFIG, self.out)

    def test_compare_requires_same_condition(self):
        run(TASKS, CONFIG, self.out)
        report = evaluate(self.out, REFS)
        a, b = Path(self.temp.name)/"a.json", Path(self.temp.name)/"b.json"
        write(a, report)
        write(b, report)
        self.assertEqual(len(compare([a,b])), 2)
        report["condition_hash"] = "changed"
        write(b, report)
        with self.assertRaises(ValueError):
            compare([a,b])

    def test_assets_and_prompt_are_frozen_in_condition(self):
        first = packets(TASKS)
        second = copy.deepcopy(first)
        second[0]["packet"]["images"] = [{"media_type":"image/png", "data":"AA=="}]
        self.assertNotEqual(digest(first), digest(second))


class AdapterTests(unittest.TestCase):
    def test_http_envelopes_with_mocked_transport(self):
        import urllib.error
        for provider in ("openai", "anthropic"):
            raw = ({"status":"completed", "output":[]} if provider == "openai"
                   else {"stop_reason":"end_turn", "content":[]})
            config = {"provider":provider, "model":"snapshot", "api_key_env":"TEST_BENCH_KEY",
                      "max_output_tokens":1024, "timeout_seconds":10}
            with patch.dict("os.environ", {"TEST_BENCH_KEY":"test-placeholder"}):
                with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(raw).encode())) as transport:
                    result = call(config, {"prompt":"public only", "images":[]})
                    request = transport.call_args.args[0]
                    self.assertEqual(json.loads(request.data)["model"], "snapshot")
                    self.assertNotIn("test-placeholder", json.dumps(result))
                    self.assertTrue(result["complete"])
                with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://test",429,"rate limit",{},None)):
                    self.assertEqual(call(config, {"prompt":"public only", "images":[]}),
                                     {"error":"http_error", "http_status":429})

    def test_same_text_and_image_bytes(self):
        packet = {"prompt":"shared prompt", "images":[{"media_type":"image/png", "data":"AA=="}]}
        config = {"model":"snapshot", "max_output_tokens":1024}
        openai = request_body("openai", config, packet)
        anthropic = request_body("anthropic", config, packet)
        self.assertEqual(openai["input"][0]["content"][0]["text"], anthropic["messages"][0]["content"][0]["text"])
        self.assertTrue(openai["input"][0]["content"][1]["image_url"].endswith(anthropic["messages"][0]["content"][1]["source"]["data"]))
        self.assertFalse(openai["store"])
        self.assertEqual(openai["max_output_tokens"], anthropic["max_tokens"])

    def test_parse_provider_response_and_truncation(self):
        raw = {"status":"completed", "output":[{"type":"reasoning"}, {"type":"message", "content":[{"type":"output_text", "text":'{}'}]}], "usage":{"output_tokens":4}}
        self.assertEqual(extract("openai", raw)["text"], '{}')
        raw["status"] = "incomplete"
        self.assertFalse(extract("openai", raw)["complete"])
        raw = {"stop_reason":"max_tokens", "content":[{"type":"text", "text":'{}'}]}
        self.assertFalse(extract("anthropic", raw)["complete"])
        raw["stop_reason"] = "end_turn"
        self.assertTrue(extract("anthropic", raw)["complete"])


if __name__ == "__main__":
    unittest.main()
