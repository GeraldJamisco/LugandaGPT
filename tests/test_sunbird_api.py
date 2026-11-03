"""Tests for the Sunbird API client and CLI. No real network request is made."""

import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from sunbird_api import (
    ApiError,
    AuthError,
    BudgetGuardError,
    ConfigError,
    SunbirdClient,
    SunbirdError,
)
from sunbird_api.cli import build_tasks, main

TOKEN = "SECRET-TOKEN-123"
PREFIX = "Translate from English to Luganda: "


class FakeResponse:
    def __init__(self, payload, status=200):
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def chat_payload(text=" Wasuze otya "):
    return {
        "id": "chat-1",
        "object": "chat.completion",
        "model": "sunflower-14b",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def http_error(status, body=b"", headers=None):
    return urllib.error.HTTPError(
        "https://api.sunbird.ai/x", status, "error", headers or {}, io.BytesIO(body)
    )


class ScriptedOpener:
    """Returns or raises the next scripted outcome and remembers each request."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def echo_opener(request, timeout=None):
    body = json.loads(request.data.decode("utf-8"))
    content = body["messages"][-1]["content"]
    english = content[len(PREFIX):]
    return FakeResponse(chat_payload(f"LG({english})"))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ledger = Path(self._tmp.name) / "ledger.jsonl"
        self.sleeps = []

    def client(self, opener, **kwargs):
        kwargs.setdefault("token", TOKEN)
        kwargs.setdefault("ledger_path", self.ledger)
        return SunbirdClient(opener=opener, sleep=self.sleeps.append, **kwargs)

    def test_chat_parses_result_and_sends_bearer_token(self):
        opener = ScriptedOpener([FakeResponse(chat_payload())])
        result = self.client(opener).chat(
            [{"role": "user", "content": "Hello"}], purpose="test"
        )
        self.assertEqual(result.text, "Wasuze otya")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.usage["total_tokens"], 15)
        request = opener.requests[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertTrue(request.full_url.endswith("/tasks/chat/completions"))
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["model"], "sunflower-14b")
        self.assertFalse(sent["stream"])

    def test_ledger_has_usage_and_hash_but_no_prompt_or_token(self):
        opener = ScriptedOpener([FakeResponse(chat_payload())])
        self.client(opener).translate("Good morning, farmers")
        text = self.ledger.read_text(encoding="utf-8")
        record = json.loads(text.strip())
        self.assertEqual(record["outcome"], "ok")
        self.assertEqual(record["total_tokens"], 15)
        self.assertEqual(len(record["prompt_sha256"]), 64)
        self.assertNotIn("Good morning", text)
        self.assertNotIn(TOKEN, text)

    def test_translate_uses_the_sunflower_translation_phrasing(self):
        opener = ScriptedOpener([FakeResponse(chat_payload())])
        self.client(opener).translate("  Where is the hospital?  ")
        sent = json.loads(opener.requests[0].data.decode("utf-8"))
        self.assertEqual(
            sent["messages"], [{"role": "user", "content": PREFIX + "Where is the hospital?"}]
        )

    def test_missing_credentials_name_the_environment_variable(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            client = SunbirdClient(opener=ScriptedOpener([]), sleep=self.sleeps.append)
            with self.assertRaises(ConfigError) as caught:
                client.check()
        self.assertIn("SUNBIRD_API_TOKEN", str(caught.exception))

    def test_old_model_identifier_is_rejected_before_any_request(self):
        opener = ScriptedOpener([])
        with self.assertRaises(ConfigError):
            self.client(opener).chat(
                [{"role": "user", "content": "Hi"}], model="Sunbird/Sunflower-14B"
            )
        self.assertEqual(opener.requests, [])

    def test_bad_arguments_are_rejected(self):
        client = self.client(ScriptedOpener([]))
        good = [{"role": "user", "content": "Hi"}]
        with self.assertRaises(ConfigError):
            client.chat([])
        with self.assertRaises(ConfigError):
            client.chat([{"role": "robot", "content": "Hi"}])
        with self.assertRaises(ConfigError):
            client.chat(good, temperature=5)
        with self.assertRaises(ConfigError):
            client.chat(good, max_tokens=0)
        with self.assertRaises(ConfigError):
            client.translate("   ")

    def test_rate_limit_is_retried_using_retry_after(self):
        opener = ScriptedOpener(
            [http_error(429, headers={"Retry-After": "2"}), FakeResponse(chat_payload())]
        )
        result = self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(result.attempts, 2)
        self.assertEqual(self.sleeps, [2.0])

    def test_retries_stop_after_the_limit(self):
        opener = ScriptedOpener([http_error(503) for _ in range(4)])
        with self.assertRaises(ApiError) as caught:
            self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(len(self.sleeps), 3)
        self.assertEqual(len(opener.requests), 4)

    def test_read_timeout_is_retried_then_reported_clearly(self):
        opener = ScriptedOpener([TimeoutError("The read operation timed out")] * 4)
        with self.assertRaises(SunbirdError) as caught:
            self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertIn("no reply from Sunbird", str(caught.exception))
        self.assertEqual(len(opener.requests), 4)

    def test_read_timeout_then_success(self):
        opener = ScriptedOpener([TimeoutError("t"), FakeResponse(chat_payload("ok"))])
        result = self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(result.text, "ok")

    def test_expired_token_is_replaced_by_logging_in_again(self):
        opener = ScriptedOpener(
            [http_error(401), FakeResponse({"access_token": "NEW"}), FakeResponse(chat_payload())]
        )
        client = self.client(opener, username="user@example.org", password="pw")
        client.chat([{"role": "user", "content": "Hi"}])
        self.assertTrue(opener.requests[1].full_url.endswith("/auth/token"))
        self.assertIn(b"username=", opener.requests[1].data)
        self.assertEqual(opener.requests[2].get_header("Authorization"), "Bearer NEW")

    def test_rejected_token_without_login_details_raises_auth_error(self):
        opener = ScriptedOpener([http_error(401)])
        with self.assertRaises(AuthError) as caught:
            self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_request_cap_blocks_the_next_request(self):
        opener = ScriptedOpener([FakeResponse(chat_payload()), FakeResponse(chat_payload())])
        client = self.client(opener, request_cap=1)
        client.chat([{"role": "user", "content": "One"}])
        with self.assertRaises(BudgetGuardError):
            client.chat([{"role": "user", "content": "Two"}])
        self.assertEqual(len(opener.requests), 1)

    def test_unexpected_response_shape_is_an_error(self):
        opener = ScriptedOpener([FakeResponse({"choices": []})])
        with self.assertRaises(SunbirdError):
            self.client(opener).chat([{"role": "user", "content": "Hi"}])

    def test_error_text_is_truncated_and_failures_reach_the_ledger(self):
        opener = ScriptedOpener([http_error(422, body=b"x" * 2000)])
        with self.assertRaises(ApiError) as caught:
            self.client(opener).chat([{"role": "user", "content": "Hi"}])
        self.assertLess(len(str(caught.exception)), 400)
        record = json.loads(self.ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(record["outcome"], "ApiError")
        self.assertEqual(record["http_status"], 422)

    def test_repr_does_not_show_the_token(self):
        self.assertNotIn(TOKEN, repr(self.client(ScriptedOpener([]))))


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.input = root / "source.csv"
        self.output = root / "out" / "suggestions.csv"
        self.ledger = root / "ledger.jsonl"
        columns = ["item_id", "source_context_en", "prior_turns_en", "source_prompt_en",
                   "reference_answer_or_rubric_en"]
        turns = json.dumps([
            {"role": "user", "content": "Is the event on Wednesday?"},
            {"role": "assistant", "content": "It moved to Friday."},
        ])
        rows = [
            ["E-001", "The library opens Saturday.", "", "When does it open?", "On Saturday."],
            ["P-001", "", turns, "And the venue?", "The same hall."],
            ["P-002", "", "", "Say thank you.", "Thank you."],
        ]
        with open(self.input, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)

    def run_cli(self, *extra, opener=echo_opener, cap="25"):
        def factory(args):
            return SunbirdClient(
                token=TOKEN, opener=opener, sleep=lambda s: None,
                request_cap=args.max_requests, ledger_path=self.ledger,
            )

        argv = ["translate-source", "--input", str(self.input), "--output", str(self.output),
                "--ledger", str(self.ledger), "--max-requests", cap, *extra]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv, client_factory=factory)
        return code, out.getvalue(), err.getvalue()

    def test_tasks_count_one_request_per_prior_turn(self):
        with open(self.input, newline="", encoding="utf-8") as handle:
            tasks = build_tasks(list(csv.DictReader(handle)))
        self.assertEqual(len(tasks), 8)
        self.assertEqual(sum(t["requests"] for t in tasks), 9)

    def test_dry_run_needs_no_token_and_sends_nothing(self):
        def forbidden(args):
            raise AssertionError("client must not be created on a dry run")

        out = io.StringIO()
        argv = ["translate-source", "--input", str(self.input), "--output", str(self.output),
                "--dry-run"]
        with contextlib.redirect_stdout(out):
            code = main(argv, client_factory=forbidden)
        report = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report["requests_pending"], 9)
        self.assertFalse(report["sent_anything"])
        self.assertFalse(self.output.exists())

    def test_full_run_writes_labelled_machine_suggestions(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        with open(self.output, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["machine_output"] == "true" for r in rows))
        self.assertTrue(all(r["review_status"] == "unreviewed" for r in rows))
        prompt = next(r for r in rows if r["item_id"] == "E-001" and r["field"] == "source_prompt")
        self.assertEqual(prompt["sunbird_luganda"], "LG(When does it open?)")
        turns = next(r for r in rows if r["field"] == "prior_turns")
        translated = json.loads(turns["sunbird_luganda"])
        self.assertEqual([t["role"] for t in translated], ["user", "assistant"])
        self.assertEqual(translated[1]["content"], "LG(It moved to Friday.)")

    def test_cap_stops_cleanly_and_a_second_run_resumes(self):
        code, out, err = self.run_cli(cap="4")
        first = json.loads(out)
        self.assertEqual(code, 0, err)
        self.assertEqual(first["status"], "request_cap_reached")
        self.assertEqual(first["tasks_written_this_run"], 3)
        self.assertEqual(first["requests_made"], 3)
        code, out, err = self.run_cli(cap="10")
        second = json.loads(out)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["tasks_written_this_run"], 5)
        self.assertEqual(second["requests_made"], 6)
        code, out, err = self.run_cli()
        self.assertEqual(json.loads(out)["status"], "nothing_to_do")

    def test_api_error_stops_the_run_and_keeps_progress(self):
        calls = {"n": 0}

        def flaky(request, timeout=None):
            calls["n"] += 1
            if calls["n"] == 3:
                raise http_error(422, b"bad request")
            return echo_opener(request)

        code, out, err = self.run_cli(opener=flaky)
        self.assertEqual(code, 2)
        self.assertIn("HTTP 422", err)
        self.assertEqual(json.loads(out)["status"], "error")
        with open(self.output, newline="", encoding="utf-8") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 2)

    def test_token_never_lands_in_outputs(self):
        code, out, err = self.run_cli()
        for text in (out, err, self.output.read_text(encoding="utf-8"),
                     self.ledger.read_text(encoding="utf-8")):
            self.assertNotIn(TOKEN, text)

    def test_missing_columns_are_reported(self):
        self.input.write_text("item_id,source_prompt_en\nE-1,Hi\n", encoding="utf-8")
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("missing columns", err)


class RunBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.input = root / "items.jsonl"
        self.output = root / "out.csv"
        self.ledger = root / "ledger.jsonl"
        items = [
            {"id": "LGP-BENCH-A-001", "prompt": "Prompt one", "turns": [], "review_status": "draft"},
            {"id": "LGP-BENCH-A-002", "prompt": "Prompt two", "turns": [], "review_status": "excluded"},
            {"id": "LGP-BENCH-A-003", "prompt": "Prompt three", "turns": [], "review_status": "draft"},
        ]
        self.input.write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")

    def run_cli(self, *extra, cap="25"):
        def factory(args):
            return SunbirdClient(token=TOKEN, opener=echo_opener, sleep=lambda s: None,
                                 request_cap=args.max_requests, ledger_path=self.ledger)
        argv = ["run-benchmark", "--input", str(self.input), "--output", str(self.output),
                "--ledger", str(self.ledger), "--max-requests", cap, *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(argv, client_factory=factory)
        return code, json.loads(out.getvalue())

    def test_excluded_items_are_skipped_and_answers_are_saved(self):
        code, report = self.run_cli()
        self.assertEqual(code, 0)
        with open(self.output, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([r["item_id"] for r in rows], ["LGP-BENCH-A-001", "LGP-BENCH-A-003"])
        self.assertTrue(all(r["field"] == "benchmark_response" for r in rows))
        self.assertTrue(all(r["machine_output"] == "true" for r in rows))
        self.assertEqual(report["requests_made"], 2)

    def test_cap_and_resume(self):
        _, first = self.run_cli(cap="1")
        self.assertEqual(first["status"], "request_cap_reached")
        _, second = self.run_cli()
        self.assertEqual(second["items_written_this_run"], 1)

    def test_dry_run_sends_nothing(self):
        out = io.StringIO()
        def forbidden(args):
            raise AssertionError("no client on dry run")
        with contextlib.redirect_stdout(out):
            main(["run-benchmark", "--input", str(self.input), "--output", str(self.output), "--dry-run"],
                 client_factory=forbidden)
        self.assertEqual(json.loads(out.getvalue())["requests_pending"], 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
