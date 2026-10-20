"""End to end tests for the shared report and delivery pipeline.

Every Telegram call is mocked. These tests cover the behaviour the
dashboard, CLI and scheduler all depend on: full report content leaving the
pipeline, delivery state recorded honestly, retries that never regenerate
or resend, and generation failures reported as failures.
"""

import argparse
import unittest
from datetime import datetime, timezone
from unittest import mock

from reporter import runner, scheduler, store, telegram_client
from reporter import __main__ as cli

from .support import ReporterPathTestCase


class PipelineTestCase(ReporterPathTestCase):
    def allow_delivery_test(self):
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        store.write_state(state)

    @staticmethod
    def ok_send_report(rep, report_file, skip_parts=0, **kwargs):
        return {
            "ok": True,
            "message_ids": [101],
            "attempts": 1,
            "parts_sent": 1,
            "parts_total": 1,
        }

    @staticmethod
    def failing_send_report(rep, report_file, skip_parts=0, **kwargs):
        return {
            "ok": False,
            "error": "sendMessage failed (code 400): Bad Request: chat not found",
            "attempts": 2,
            "parts_sent": 1,
            "parts_total": 3,
        }


class RunOnceTests(PipelineTestCase):
    def test_generate_without_send_never_calls_telegram(self):
        with mock.patch.object(telegram_client, "send_report") as send:
            result = runner.run_once(send=False, data=self.synthetic_data())
        self.assertTrue(result["ok"])
        self.assertFalse(result["sent"])
        self.assertIsNone(result["delivery"]["ok"])
        send.assert_not_called()
        self.assertIsNotNone(store.load_report_json(result["report_id"]))

    def test_send_delivers_through_the_shared_pipeline(self):
        self.allow_delivery_test()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ) as send:
            result = runner.run_once(send=True, source="cli", data=self.synthetic_data())
        self.assertTrue(result["ok"])
        self.assertTrue(result["sent"])
        self.assertEqual(result["delivery"]["parts_total"], 1)
        send.assert_called_once()
        args, kwargs = send.call_args
        self.assertEqual(args[0]["report_id"], result["report_id"])
        self.assertEqual(args[1], f"{result['report_id']}.md")
        self.assertEqual(kwargs.get("skip_parts", 0), 0)

        state = store.read_state()
        self.assertTrue(state["last_delivery"]["ok"])
        self.assertEqual(state["last_delivered_report_id"], result["report_id"])
        self.assertEqual(state["pending_delivery"], {})
        self.assertEqual(state["last_report"]["report_id"], result["report_id"])

    def test_send_is_blocked_until_the_delivery_test_passes(self):
        with mock.patch.object(telegram_client, "send_report", side_effect=self.ok_send_report) as send:
            result = runner.run_once(send=True, data=self.synthetic_data())
        self.assertTrue(result["ok"])
        self.assertFalse(result["sent"])
        self.assertIn("delivery test", result["delivery"]["reason"])
        send.assert_not_called()
        state = store.read_state()
        self.assertFalse(state["last_delivery"]["ok"])
        self.assertEqual(
            state["pending_delivery"]["report_id"], result["report_id"]
        )

    def test_generation_failure_is_returned_not_raised_and_sends_nothing(self):
        with mock.patch.object(
            runner.report_mod, "generate_report", side_effect=RuntimeError("collector exploded")
        ), mock.patch.object(telegram_client, "send_report") as send:
            result = runner.run_once(send=True, data=self.synthetic_data())
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "generate")
        self.assertIn("collector exploded", result["error"])
        self.assertFalse(result["sent"])
        self.assertIsNone(result["report_id"])
        send.assert_not_called()
        state = store.read_state()
        self.assertFalse(state["last_report"]["ok"])
        self.assertIn("generation failed", self.delivery_log_text())

    def delivery_log_text(self):
        return self.delivery_log.read_text(encoding="utf-8") if self.delivery_log.exists() else ""


class DuplicateAndRetryTests(PipelineTestCase):
    def _saved_report(self):
        result = runner.run_once(send=False, data=self.synthetic_data())
        return store.load_report_json(result["report_id"])

    def test_second_delivery_of_the_same_report_is_skipped(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ) as send:
            first = runner.deliver_report(rep, source="cli")
            second = runner.deliver_report(rep, source="scheduler")
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertTrue(second.get("duplicate"))
        self.assertEqual(send.call_count, 1)

    def test_failure_records_a_pending_delivery_without_touching_the_report(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        before = store.load_report_json(rep["report_id"])
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            outcome = runner.deliver_report(rep, source="scheduler")
        self.assertFalse(outcome["ok"])
        state = store.read_state()
        pending = state["pending_delivery"]
        self.assertEqual(pending["report_id"], rep["report_id"])
        self.assertEqual(pending["attempts"], 1)
        self.assertIn("chat not found", pending["last_error"])
        self.assertEqual(pending["parts_sent"], 1)
        self.assertEqual(pending["parts_total"], 3)
        self.assertTrue(pending["since"])
        self.assertFalse(state["last_delivery"]["ok"])
        self.assertNotEqual(state.get("last_delivered_report_id"), rep["report_id"])
        self.assertEqual(store.load_report_json(rep["report_id"]), before)

        # A second failure keeps the original 'since' and counts the attempt.
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            runner.deliver_report(rep, source="retry")
        pending = store.read_state()["pending_delivery"]
        self.assertEqual(pending["attempts"], 2)
        self.assertEqual(pending["since"], state["pending_delivery"]["since"])

    def test_retry_sends_the_saved_report_without_regenerating(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        generated_at = rep["generated_at"]
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            runner.deliver_report(rep, source="scheduler")
        with mock.patch.object(
            runner.report_mod,
            "generate_report",
            side_effect=AssertionError("retry must not regenerate"),
        ), mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ) as send:
            outcome = runner.retry_delivery()
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["report_id"], rep["report_id"])
        send.assert_called_once()
        self.assertEqual(send.call_args[0][0]["generated_at"], generated_at)

        state = store.read_state()
        self.assertEqual(state["pending_delivery"], {})
        self.assertEqual(state["last_delivered_report_id"], rep["report_id"])
        self.assertEqual(store.list_reports(limit=5)[0]["report_id"], rep["report_id"])

    def test_retry_of_an_undeleted_part_skips_the_parts_already_confirmed(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            runner.deliver_report(rep, source="scheduler")
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ) as send:
            runner.retry_delivery(report_id=rep["report_id"])
        self.assertEqual(send.call_args.kwargs.get("skip_parts"), 1)

    def test_retry_without_any_saved_report_fails_at_the_select_stage(self):
        outcome = runner.retry_delivery()
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["stage"], "select")
        self.assertIn("generate a report", outcome["reason"])

    def test_retry_of_an_already_delivered_report_sends_nothing(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ):
            runner.deliver_report(rep, source="cli")
        with mock.patch.object(telegram_client, "send_report") as send:
            outcome = runner.retry_delivery(report_id=rep["report_id"])
        self.assertTrue(outcome["ok"])
        self.assertTrue(outcome.get("duplicate"))
        send.assert_not_called()

    def test_retry_of_a_missing_report_file_fails_cleanly(self):
        self.allow_delivery_test()
        rep = self._saved_report()
        path = self.archive_dir / f"{rep['report_id']}.json"
        path.unlink()
        outcome = runner.retry_delivery(report_id=rep["report_id"])
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["stage"], "select")


class ReportingStatusTests(PipelineTestCase):
    def test_status_reports_saved_and_pending_state(self):
        empty = runner.reporting_status()
        self.assertIsNone(empty["latest_saved_report_id"])
        self.assertEqual(empty["saved_report_count"], 0)
        self.assertIsNone(empty["awaiting_delivery"])

        self.allow_delivery_test()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            result = runner.run_once(send=True, data=self.synthetic_data())

        status = runner.reporting_status()
        self.assertEqual(status["latest_saved_report_id"], result["report_id"])
        self.assertEqual(status["saved_report_count"], 1)
        self.assertEqual(status["last_report"]["report_id"], result["report_id"])
        self.assertFalse(status["last_delivery"]["ok"])
        self.assertEqual(status["awaiting_delivery"]["report_id"], result["report_id"])
        self.assertTrue(status["delivery_test_passed"])

    def test_status_never_contains_credentials(self):
        status = runner.reporting_status()
        blob = repr(status)
        self.assertNotIn("token", blob)
        self.assertNotIn("chat_id", blob)


class ScheduledRunTests(PipelineTestCase):
    def _enabled_scheduler(self, job_fn):
        rep = runner.run_once(send=False, data=self.synthetic_data())
        self.allow_delivery_test()
        scheduler.set_enabled(True, now=datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc))
        self.assertTrue(store.read_state()["schedule"]["enabled"])
        self.assertIsNotNone(rep["report_id"])
        return scheduler.Scheduler(job_fn)

    def test_due_run_delivers_and_records_the_result(self):
        loop = self._enabled_scheduler(
            lambda: runner.run_once(
                send=True, source="scheduler", data=self.synthetic_data()
            )
        )
        self.allow_delivery_test()
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ):
            outcome = loop.tick(now=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc))
        self.assertTrue(outcome["ran"])
        last = store.read_state()["schedule"]["last_result"]
        self.assertTrue(last["ok"])
        self.assertTrue(last["generated"])
        self.assertTrue(last["sent"])
        self.assertTrue(last["delivery_ok"])
        self.assertIsNotNone(last["report_id"])
        self.assertIsNotNone(last["summary"])

    def test_due_run_reports_a_delivery_failure(self):
        loop = self._enabled_scheduler(
            lambda: runner.run_once(
                send=True, source="scheduler", data=self.synthetic_data()
            )
        )
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.failing_send_report
        ):
            loop.tick(now=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc))
        last = store.read_state()["schedule"]["last_result"]
        self.assertTrue(last["generated"])
        self.assertFalse(last["delivery_ok"])
        self.assertIn("chat not found", last["delivery_error"])
        self.assertEqual(last["delivery_parts_sent"], 1)
        self.assertEqual(last["delivery_parts_total"], 3)
        pending = store.read_state()["pending_delivery"]
        self.assertEqual(pending["report_id"], last["report_id"])

    def test_due_run_records_a_generation_failure_without_sending(self):
        # Seed the preconditions first, then break generation for the due run.
        loop = self._enabled_scheduler(
            lambda: runner.run_once(send=True, data=self.synthetic_data())
        )
        with mock.patch.object(
            runner.report_mod,
            "generate_report",
            side_effect=RuntimeError("collector exploded"),
        ), mock.patch.object(telegram_client, "send_report") as send:
            loop.tick(now=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc))
            send.assert_not_called()
        last = store.read_state()["schedule"]["last_result"]
        self.assertFalse(last["ok"])
        self.assertEqual(last["stage"], "generate")
        self.assertIn("collector exploded", last["error"])
        self.assertFalse(last["generated"])

    def test_disabled_schedule_never_runs_a_job(self):
        loop = scheduler.Scheduler(lambda: self.fail("job must not run"))
        outcome = loop.tick(now=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc))
        self.assertFalse(outcome["ran"])
        self.assertEqual(outcome["reason"], "scheduling disabled")


class CliDeliverTests(PipelineTestCase):
    def _args(self, report_id=None):
        return argparse.Namespace(report_id=report_id)

    def test_deliver_command_prints_the_retry_outcome(self):
        self.allow_delivery_test()
        result = runner.run_once(send=False, data=self.synthetic_data())
        with mock.patch.object(
            telegram_client, "send_report", side_effect=self.ok_send_report
        ):
            code = cli.cmd_deliver(self._args(result["report_id"]))
        self.assertEqual(code, 0)

    def test_deliver_command_fails_when_there_is_nothing_to_send(self):
        code = cli.cmd_deliver(self._args())
        self.assertEqual(code, 1)

    def test_report_command_fails_on_generation_failure(self):
        with mock.patch.object(
            runner.report_mod,
            "generate_report",
            side_effect=RuntimeError("collector exploded"),
        ):
            code = cli.cmd_report(argparse.Namespace(send=False, source="cli"))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
