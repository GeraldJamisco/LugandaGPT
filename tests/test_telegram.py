"""Telegram client tests. Every HTTP response is mocked: no network use."""

import json
import os
import unittest
import urllib.request
from unittest import mock

from reporter import collect, config, report, store, telegram_client

from .support import ReporterPathTestCase

FAKE_TOKEN = "123456789:" + "A" * 35
FAKE_CHAT = "-1001234567890"
BOT = config.BOT_USERNAME


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def env_patched(token=FAKE_TOKEN, chat_id=FAKE_CHAT):
    return mock.patch.dict(
        os.environ,
        {config.TOKEN_ENV: token or "", config.CHAT_ENV: chat_id or ""},
    )


class MissingConfigurationTests(ReporterPathTestCase):
    def test_missing_credentials_reported_without_any_network_call(self):
        with env_patched(token="", chat_id=""), mock.patch.object(
            urllib.request, "urlopen", side_effect=AssertionError("network used")
        ) as opened:
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["stage"], "configuration")
        self.assertEqual(len(outcome["problems"]), 2)
        opened.assert_not_called()

    def test_status_reports_configuration_only(self):
        with env_patched(token="", chat_id=""):
            status = telegram_client.status()
        self.assertFalse(status["ready"])
        self.assertFalse(status["token_configured"])
        self.assertIsNone(status["chat_id_masked"])

    def test_bot_username_is_not_accepted_as_chat_id(self):
        with env_patched(chat_id=f"@{BOT}"):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertTrue(
            any("bot username" in problem for problem in outcome["problems"])
        )

    def test_malformed_token_value_is_not_echoed(self):
        with env_patched(token="not-a-token"), mock.patch.object(
            urllib.request, "urlopen", side_effect=AssertionError("network used")
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        joined = json.dumps(outcome)
        self.assertNotIn("not-a-token", joined)


class VerificationTests(ReporterPathTestCase):
    def test_getme_success_verifies_expected_bot(self):
        payload = {"ok": True, "result": {"id": 1, "username": BOT, "first_name": "R"}}
        with env_patched(), mock.patch.object(
            urllib.request, "urlopen", return_value=FakeResponse(payload)
        ):
            outcome = telegram_client.run_delivery_test(send_real_message=False)
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["bot_username"], BOT)

    def test_unauthorized_response_fails_without_leaking_token(self):
        payload = {"ok": False, "error_code": 401, "description": "Unauthorized"}
        with env_patched(), mock.patch.object(
            urllib.request, "urlopen", return_value=FakeResponse(payload, status=401)
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["stage"], "getMe")
        self.assertNotIn(FAKE_TOKEN, json.dumps(outcome))
        state = store.read_state()
        self.assertFalse(state["telegram"]["delivery_test_passed"])
        self.assertNotIn(FAKE_TOKEN, json.dumps(state))

    def test_wrong_bot_username_fails_verification(self):
        payload = {"ok": True, "result": {"id": 2, "username": "Some_Other_Bot"}}
        with env_patched(), mock.patch.object(
            urllib.request, "urlopen", return_value=FakeResponse(payload)
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertIn("Some_Other_Bot", outcome["error"])
        self.assertIn(BOT, outcome["error"])

    def test_network_error_is_reported_as_network_error(self):
        import urllib.error

        with env_patched(), mock.patch.object(
            urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertIn("network error", outcome["error"])
        self.assertNotIn(FAKE_TOKEN, json.dumps(outcome))


class DeliveryTests(ReporterPathTestCase):
    def _responses(self):
        get_me = {"ok": True, "result": {"id": 1, "username": BOT}}
        sent = {"ok": True, "result": {"message_id": 42}}
        return [FakeResponse(get_me), FakeResponse(sent)]

    def test_successful_test_marks_state_and_logs_without_token(self):
        responses = self._responses()
        with env_patched(), mock.patch.object(
            urllib.request, "urlopen", side_effect=responses
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["message_id"], 42)
        state = store.read_state()
        self.assertTrue(state["telegram"]["delivery_test_passed"])
        self.assertEqual(state["telegram"]["bot_username"], BOT)
        self.assertTrue(state["telegram"]["chat_id_masked"].endswith("7890"))
        log = self.delivery_log.read_text(encoding="utf-8")
        self.assertIn("delivery test succeeded", log)
        self.assertNotIn(FAKE_TOKEN, log)
        self.assertNotIn(FAKE_TOKEN, json.dumps(state))

    def test_send_failure_is_reported_without_leaking_token(self):
        get_me = {"ok": True, "result": {"id": 1, "username": BOT}}
        sent = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: chat not found",
        }
        with env_patched(), mock.patch.object(
            urllib.request,
            "urlopen",
            side_effect=[FakeResponse(get_me), FakeResponse(sent, status=400)],
        ):
            outcome = telegram_client.run_delivery_test()
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["stage"], "sendMessage")
        self.assertIn("chat not found", outcome["error"])
        self.assertNotIn(FAKE_TOKEN, json.dumps(outcome))
        self.assertFalse(store.read_state()["telegram"]["delivery_test_passed"])


class MessageHandlingTests(ReporterPathTestCase):
    @staticmethod
    def inflate(rep):
        """Make the rendered document long enough to need several parts."""
        rep.setdefault("executive_summary", {})["changed"] = (
            "long activity note " * 2000
        )
        return rep

    def test_empty_message_refused(self):
        with env_patched():
            with self.assertRaises(telegram_client.TelegramError):
                telegram_client.send_message("   ")

    def test_over_length_message_refused_before_any_network_call(self):
        with env_patched(), mock.patch.object(
            urllib.request, "urlopen", side_effect=AssertionError("network used")
        ) as opened:
            with self.assertRaises(telegram_client.TelegramError):
                telegram_client.send_message("x" * (config.TELEGRAM_MESSAGE_LIMIT + 1))
        opened.assert_not_called()

    def test_split_text_respects_the_limit_and_loses_nothing(self):
        text = "line one\n" * 900
        chunks = telegram_client.split_text(text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), config.TELEGRAM_MESSAGE_LIMIT)
        self.assertEqual("".join(chunks).count("line one"), 900)

    def test_report_document_contains_the_required_sections(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        self.assertIn("LugandaGPT Project Report", document)
        self.assertIn(f"Report ID: {rep['report_id']}", document)
        for heading in (
            "1) Executive summary",
            "2) Verified completed work",
            "3) Attempted or incomplete work",
            "4) Recorded failures and collection warnings",
            "5) Human-reported activity",
            "6) Git activity and working-tree status",
            "7) Recorded test results",
            "8) Experiments and recorded results",
            "9) Blockers and outstanding decisions",
            "10) Next priorities (roadmap)",
            "11) Verified spending",
            "12) Reporting and delivery health",
            "13) Saved local report and evidence",
        ):
            self.assertIn(heading, document)
        self.assertIn(f"{rep['report_id']}.md", document)
        self.assertIn("No trained LugandaGPT model exists", document)
        self.assertIn("What changed:", document)
        self.assertIn("Core research and model development:", document)

    def test_document_never_claims_the_current_report_was_delivered(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        # The delivery that follows generation must not appear as this
        # document's own status; the text is built before Telegram answers.
        state = store.read_state()
        state["last_delivery"] = {
            "report_id": rep["report_id"],
            "ok": True,
            "at": rep["generated_at"],
            "source": "dashboard",
        }
        store.write_state(state)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        self.assertIn("Last delivery before this run: none recorded", document)
        self.assertIn("before this message", document)
        self.assertIn("not claimed here", document)
        self.assertNotIn(
            f"Last delivery before this run: report {rep['report_id']}", document
        )

    def test_document_uses_the_generation_time_state_snapshot(self):
        state = store.read_state()
        state["last_delivery"] = {
            "report_id": "RPT-20260101-000000-P8H",
            "ok": True,
            "at": "2026-01-01T00:00:05+00:00",
            "source": "scheduler",
        }
        store.write_state(state)
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        self.assertIn(
            "Last delivery before this run: report RPT-20260101-000000-P8H",
            document,
        )
        self.assertIn(f"State observed at generation ({rep['generated_at']})", document)

    def test_document_separates_latest_run_from_latest_success(self):
        self.write_test_run(
            "2026-10-18-suite.json",
            {
                "recorded_at": "2026-10-18T10:00:00+00:00",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "tests_run": 148,
                "duration_seconds": 18.1,
            },
        )
        self.write_test_run(
            "2026-10-19-suite.json",
            {
                "recorded_at": "2026-10-19T10:00:00+00:00",
                "exit_code": 1,
                "failures": 1,
                "errors": 0,
                "tests_run": 163,
                "duration_seconds": 24.0,
            },
        )
        data = self.synthetic_data()
        data["tests"] = collect.collect_tests()
        rep, _, _ = report.generate_report(data=data, save=True)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        self.assertIn("Latest run: 2026-10-19-suite.json", document)
        self.assertIn("Latest successful run: 2026-10-18-suite.json", document)
        self.assertIn("do not measure Luganda language quality", document)

    def test_document_shows_exit_criterion_verification_status(self):
        data = self.synthetic_data()
        data["roadmap"]["current_phase"] = {
            "number": 0,
            "title": "Project foundation",
            "status": "In progress.",
            "evidence": "docs/ROADMAP.md (Phase 0)",
            "exit_criteria": [
                "Documentation inventory complete and internally consistent."
            ],
        }
        data["verification_context"] = {
            "repo_root": self.tmp_root / "absent-repo",
            "docs_dir": self.tmp_root / "absent-docs",
            "gitignore_path": self.tmp_root / ".gitignore",
            "git": {"available": True},
            "tracked_reporter_files": [],
            "human_verifications": {},
        }
        rep, _, _ = report.generate_report(data=data, save=True)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        self.assertIn("Mandatory exit criteria for the current phase", document)
        self.assertIn("[incomplete]", document)
        self.assertIn("evidence", document)

    def test_document_does_not_present_uncommitted_changes_as_incomplete(self):
        data = self.synthetic_data()
        data["git"]["clean"] = False
        data["git"]["changes"] = [
            {"index_status": "M", "worktree_status": " ", "path": "docs/ROADMAP.md"}
        ]
        rep, _, _ = report.generate_report(data=data, save=True)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        incomplete_section = document.split(
            "3) Attempted or incomplete work"
        )[1].split("4)")[0]
        self.assertIn("None recorded in this period.", incomplete_section)
        self.assertIn("not incomplete tasks", incomplete_section)
        self.assertIn("docs/ROADMAP.md", document)
        self.assertIn("not classified as an incomplete task", document)

    def test_large_report_is_split_into_labelled_parts_not_shortened(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        self.inflate(rep)
        document = telegram_client.build_report_document(rep, f"{rep['report_id']}.md")
        parts = telegram_client.split_report_parts(document, rep["report_id"])
        self.assertGreater(len(parts), 1)
        for index, part in enumerate(parts, start=1):
            self.assertLessEqual(len(part), config.TELEGRAM_MESSAGE_LIMIT)
            self.assertIn(f"part {index} of {len(parts)}", part)
        bodies = []
        for part in parts:
            lines = part.splitlines()
            # drop the two header lines added for multi part reports
            bodies.append("\n".join(lines[2:]))
        stripped = "".join("".join(body.split()) for body in bodies)
        self.assertEqual(stripped, "".join(document.split()))

    def test_send_report_sends_every_part_in_order(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        self.inflate(rep)
        parts = telegram_client.split_report_parts(
            telegram_client.build_report_document(rep, f"{rep['report_id']}.md"),
            rep["report_id"],
        )
        sent = []

        def record(text, **kwargs):
            sent.append(text)
            return {"ok": True, "message_id": len(sent)}

        with mock.patch.object(telegram_client, "send_message", side_effect=record):
            outcome = telegram_client.send_report(rep, f"{rep['report_id']}.md")
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["parts_total"], len(parts))
        self.assertEqual(outcome["parts_sent"], len(parts))
        self.assertEqual(sent, parts)

    def test_send_report_resumes_without_resending_confirmed_parts(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        self.inflate(rep)
        parts = telegram_client.split_report_parts(
            telegram_client.build_report_document(rep, f"{rep['report_id']}.md"),
            rep["report_id"],
        )
        self.assertGreater(len(parts), 1)
        sent = []

        def fail_on_second(text, **kwargs):
            sent.append(text)
            if len(sent) == 2:
                raise telegram_client.TelegramError("Bad Request: chat not found")
            return {"ok": True, "message_id": len(sent)}

        with mock.patch.object(telegram_client, "send_message", side_effect=fail_on_second):
            first = telegram_client.send_report(
                rep, f"{rep['report_id']}.md", retries=0
            )
        self.assertFalse(first["ok"])
        self.assertEqual(first["parts_sent"], 1)

        def record(text, **kwargs):
            sent.append(text)
            return {"ok": True, "message_id": len(sent)}

        with mock.patch.object(telegram_client, "send_message", side_effect=record):
            second = telegram_client.send_report(
                rep, f"{rep['report_id']}.md", skip_parts=first["parts_sent"]
            )
        self.assertTrue(second["ok"])
        self.assertEqual(sent.count(parts[0]), 1)

    def test_send_report_refuses_to_claim_success_from_an_inconsistent_state(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        with mock.patch.object(
            telegram_client, "send_message", side_effect=AssertionError("sent again")
        ):
            outcome = telegram_client.send_report(
                rep, f"{rep['report_id']}.md", skip_parts=99
            )
        self.assertFalse(outcome["ok"])
        self.assertTrue(outcome.get("needs_manual_check"))

    def test_send_report_retries_transient_network_errors(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        calls = {"n": 0}

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise telegram_client.TelegramError("network error: timed out")
            return {"ok": True, "message_id": 7}

        delays = []
        with mock.patch.object(telegram_client, "send_message", side_effect=flaky):
            outcome = telegram_client.send_report(rep, f"{rep['report_id']}.md", retry_sleep=delays.append)
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["attempts"], 3)
        self.assertEqual(len(delays), 2)

    def test_send_report_gives_up_and_records_failure(self):
        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        with mock.patch.object(
            telegram_client,
            "send_message",
            side_effect=telegram_client.TelegramError("network error: refused"),
        ):
            outcome = telegram_client.send_report(
                rep, f"{rep['report_id']}.md", retries=1, retry_sleep=lambda _: None
            )
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["attempts"], 2)
        self.assertIn("delivery failed", self.delivery_log.read_text(encoding="utf-8"))


class RunnerDeliveryGuardTests(ReporterPathTestCase):
    """runner.deliver_report is the single delivery gate for every caller."""

    def test_delivery_blocked_until_test_passes(self):
        from reporter import runner

        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        outcome = runner.deliver_report(rep, source="test")
        self.assertFalse(outcome["ok"])
        self.assertIn("delivery test has not passed", outcome["reason"])

    def test_duplicate_delivery_is_skipped_after_restart(self):
        from reporter import runner

        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        state["last_delivered_report_id"] = rep["report_id"]
        store.write_state(state)
        with mock.patch.object(
            telegram_client, "send_report", side_effect=AssertionError("sent twice")
        ):
            outcome = runner.deliver_report(rep, source="test")
        self.assertTrue(outcome["ok"])
        self.assertIn("duplicate send skipped", outcome["reason"])


if __name__ == "__main__":
    unittest.main()
