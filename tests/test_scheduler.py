"""Scheduler tests: default off, gating, cadence, overlap, catch-up."""

import threading
import unittest
from datetime import datetime, timedelta, timezone

from reporter import config, scheduler, store

from .support import ReporterPathTestCase


class DefaultStateTests(ReporterPathTestCase):
    def test_scheduling_disabled_by_default(self):
        status = scheduler.schedule_status()
        self.assertFalse(status["enabled"])
        self.assertIsNone(status["next_run_at"])
        self.assertTrue(status["runs_in_process_only"])
        self.assertFalse(status["system_task_created"])

    def test_status_reports_eat_slots(self):
        status = scheduler.schedule_status()
        self.assertIn("EAT", status["timezone"])
        self.assertEqual(status["slots_eat"], "06:00, 14:00, 22:00 EAT")
        self.assertEqual(status["interval_hours"], config.DEFAULT_INTERVAL_HOURS)


class EnableDisableTests(ReporterPathTestCase):
    def _allow_delivery_test(self):
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        store.write_state(state)

    def _seed_report(self):
        """A saved report is a precondition for enabling the schedule."""
        from reporter import report

        rep, _, _ = report.generate_report(data=self.synthetic_data(), save=True)
        return rep

    def test_enable_refused_without_passed_delivery_test(self):
        self._seed_report()
        outcome = scheduler.set_enabled(True)
        self.assertFalse(outcome["ok"])
        self.assertIn("delivery test", outcome["reason"])
        self.assertFalse(scheduler.schedule_status()["enabled"])

    def test_enable_refused_without_a_saved_report(self):
        self._allow_delivery_test()
        outcome = scheduler.set_enabled(True)
        self.assertFalse(outcome["ok"])
        self.assertIn("no saved report", outcome["reason"])

    def test_enable_sets_next_slot_to_an_eat_boundary(self):
        self._seed_report()
        self._allow_delivery_test()
        outcome = scheduler.set_enabled(True, now=datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc))
        self.assertTrue(outcome["ok"])
        status = scheduler.schedule_status()
        self.assertTrue(status["enabled"])
        next_run = datetime.fromisoformat(status["next_run_at"])
        self.assertEqual(next_run.utcoffset(), timedelta(hours=3))
        self.assertIn(next_run.hour, (6, 14, 22))
        self.assertEqual(next_run.minute, 0)

    def test_disable_clears_next_run(self):
        self._seed_report()
        self._allow_delivery_test()
        scheduler.set_enabled(True)
        outcome = scheduler.set_enabled(False)
        self.assertTrue(outcome["ok"])
        status = scheduler.schedule_status()
        self.assertFalse(status["enabled"])
        self.assertIsNone(status["next_run_at"])

    def test_state_persists_across_process_restarts(self):
        self._seed_report()
        self._allow_delivery_test()
        scheduler.set_enabled(True)
        # read_state() reloads from disk, which is what a restart sees.
        self.assertTrue(store.read_state()["schedule"]["enabled"])


class CadenceTests(unittest.TestCase):
    def test_next_boundary_is_one_of_the_eat_slots(self):
        now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)  # 13:00 EAT
        boundary = scheduler.next_boundary(now)
        self.assertEqual(boundary.hour, 14)
        self.assertEqual(boundary.tzinfo, config.REPORT_TZ)

    def test_next_boundary_crosses_midnight_to_first_slot(self):
        now = datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc)  # 23:00 EAT
        boundary = scheduler.next_boundary(now)
        self.assertEqual((boundary.day, boundary.hour), (20, 6))

    def test_next_boundary_exactly_on_slot_goes_to_the_next_one(self):
        slot = datetime(2026, 10, 19, 14, 0, tzinfo=config.REPORT_TZ)
        boundary = scheduler.next_boundary(slot)
        self.assertEqual(boundary.hour, 22)

    def test_missed_windows_are_counted_for_reporting(self):
        now = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
        previous = now - timedelta(hours=16)  # crosses 24h of slots
        missed = scheduler.count_missed_boundaries(previous, now)
        self.assertGreaterEqual(missed, 2)


class RunDueJobTests(ReporterPathTestCase):
    def test_overlapping_job_is_refused(self):
        started = threading.Event()
        release = threading.Event()
        results = []

        def blocking_job():
            started.set()
            release.wait(5)
            return {"report_id": "RPT-X"}

        worker = threading.Thread(
            target=lambda: results.append(scheduler.run_due_job(blocking_job))
        )
        worker.start()
        self.assertTrue(started.wait(5))
        second = scheduler.run_due_job(lambda: "should not run")
        release.set()
        worker.join(timeout=5)

        self.assertFalse(second["ok"])
        self.assertIn("still running", second["reason"])
        self.assertTrue(results[0]["ok"])
        self.assertTrue(results[0]["ran"])

    def test_job_failure_is_captured_not_raised(self):
        def boom():
            raise RuntimeError("collector exploded")

        outcome = scheduler.run_due_job(boom)
        self.assertFalse(outcome["ok"])
        self.assertTrue(outcome["ran"])
        self.assertIn("RuntimeError", outcome["error"])
        # The lock must be released so the next tick can run.
        self.assertTrue(scheduler.run_due_job(lambda: "ok")["ok"])


class TickTests(ReporterPathTestCase):
    def _enable_with_past_due(self, next_run):
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        state["schedule"]["enabled"] = True
        state["schedule"]["next_run_at"] = next_run.isoformat(timespec="seconds")
        store.write_state(state)

    def test_tick_does_nothing_while_disabled(self):
        ran = []

        thread = scheduler.Scheduler(lambda: ran.append(1), tick_seconds=999)
        outcome = thread.tick(now=datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc))
        self.assertFalse(outcome["ran"])
        self.assertEqual(ran, [])

    def test_tick_skips_when_not_due(self):
        now = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)  # 07:00 EAT
        self._enable_with_past_due(datetime(2026, 10, 19, 14, 0, tzinfo=config.REPORT_TZ))
        ran = []
        thread = scheduler.Scheduler(lambda: ran.append(1), tick_seconds=999)
        outcome = thread.tick(now=now)
        self.assertFalse(outcome["ran"])
        self.assertEqual(outcome["reason"], "not due")

    def test_tick_runs_due_job_once_and_schedules_next_slot(self):
        due = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)  # 07:00 EAT, slot 06:00 passed
        self._enable_with_past_due(datetime(2026, 10, 19, 6, 0, tzinfo=config.REPORT_TZ))
        ran = []
        thread = scheduler.Scheduler(lambda: ran.append("job"), tick_seconds=999)
        outcome = thread.tick(now=due)
        self.assertTrue(outcome["ran"])
        self.assertEqual(ran, ["job"])
        state = store.read_state()
        self.assertIsNotNone(state["schedule"]["last_attempt_at"])
        next_run = datetime.fromisoformat(state["schedule"]["next_run_at"])
        self.assertGreater(next_run, due)
        self.assertIn(next_run.hour, (6, 14, 22))

    def test_restart_with_many_missed_slots_runs_once(self):
        now = datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)  # 19:00 EAT
        long_ago = now - timedelta(hours=40)
        self._enable_with_past_due(long_ago)
        ran = []
        thread = scheduler.Scheduler(lambda: ran.append("job"), tick_seconds=999)
        outcome = thread.tick(now=now)
        self.assertTrue(outcome["ran"])
        self.assertEqual(ran, ["job"])  # one catch-up run, no burst
        state = store.read_state()
        skipped = state["schedule"]["last_result"]["missed_periods_skipped"]
        self.assertGreaterEqual(skipped, 1)
        self.assertGreater(datetime.fromisoformat(state["schedule"]["next_run_at"]), now)

    def test_last_result_is_recorded_for_the_dashboard(self):
        due = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)
        self._enable_with_past_due(datetime(2026, 10, 19, 6, 0, tzinfo=config.REPORT_TZ))
        thread = scheduler.Scheduler(
            lambda: {"report_id": "RPT-1", "activity_note": "no activity", "sent": False},
            tick_seconds=999,
        )
        thread.tick(now=due)
        result = store.read_state()["schedule"]["last_result"]
        self.assertEqual(result["report_id"], "RPT-1")
        self.assertEqual(result["summary"], "no activity")
        self.assertFalse(result["sent"])


if __name__ == "__main__":
    unittest.main()
