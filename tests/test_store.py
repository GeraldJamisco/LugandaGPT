"""Storage tests: history preservation, dedupe, id validation, state."""

import json
import unittest
from datetime import datetime, timezone

from reporter import config, report, store

from .support import ReporterPathTestCase

COMMIT = {
    "sha": "b" * 40,
    "subject": "foundation commit",
    "author": "Tester",
    "authored_at": "2026-10-19T01:00:00+00:00",
}


def _data_with_commit():
    data = ReporterPathTestCase.synthetic_data()
    data["git"]["commits"] = [dict(COMMIT)]
    data["git"]["head"] = dict(COMMIT)
    return data


class HistoryTests(ReporterPathTestCase):
    def test_reports_are_preserved_and_never_overwritten(self):
        first_end = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
        second_end = datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)
        rep1, _, created1 = report.generate_report(
            data=_data_with_commit(),
            period_end=first_end,
            period_start=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),
        )
        rep2, _, created2 = report.generate_report(
            data=_data_with_commit(),
            period_end=second_end,
            period_start=first_end,
        )
        self.assertTrue(created1)
        self.assertTrue(created2)
        self.assertNotEqual(rep1["report_id"], rep2["report_id"])
        stored = store.list_reports()
        self.assertEqual(len(stored), 2)
        for meta in stored:
            self.assertTrue((self.archive_dir / f"{meta['report_id']}.json").exists())
            self.assertTrue((self.archive_dir / f"{meta['report_id']}.md").exists())

    def test_saving_same_report_id_twice_does_not_overwrite(self):
        end = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
        start = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
        rep, _, created1 = report.generate_report(
            data=_data_with_commit(), period_end=end, period_start=start
        )
        _, _, created2 = report.generate_report(
            data=_data_with_commit(), period_end=end, period_start=start
        )
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(len(store.list_reports()), 1)

    def test_list_reports_returns_newest_first(self):
        for day, hour in ((19, 8), (19, 16), (20, 0)):
            report.generate_report(
                data=self.synthetic_data(),
                period_end=datetime(2026, 10, day, hour, 0, tzinfo=timezone.utc),
                period_start=datetime(2026, 10, day, 0, 0, tzinfo=timezone.utc),
            )
        ids = [meta["report_id"] for meta in store.list_reports()]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids, reverse=True))


class DedupeTests(ReporterPathTestCase):
    def test_repeated_activity_is_flagged_in_the_next_report(self):
        first_end = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
        second_end = datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)
        report.generate_report(
            data=_data_with_commit(),
            period_end=first_end,
            period_start=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),
        )
        rep2, _, _ = report.generate_report(
            data=_data_with_commit(), period_end=second_end, period_start=first_end
        )
        self.assertEqual(rep2["new_event_count"], 0)
        self.assertGreater(rep2["duplicate_event_count"], 0)
        self.assertEqual(rep2["summary"]["verified_completed"], [])

    def test_prior_event_ids_are_collected_from_history(self):
        report.generate_report(
            data=_data_with_commit(),
            period_end=datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc),
            period_start=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),
        )
        prior = store.previous_event_ids()
        self.assertIn(f"commit:{'b' * 40}", prior)

    def test_same_commit_twice_in_one_report_is_flagged(self):
        data = self.synthetic_data()
        data["git"]["commits"] = [dict(COMMIT), dict(COMMIT)]
        rep, _, _ = report.generate_report(
            data=data,
            period_end=datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc),
            period_start=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(rep["duplicate_event_count"], 1)
        self.assertEqual(rep["new_event_count"], 1)


class ReportIdValidationTests(ReporterPathTestCase):
    def test_valid_ids_accepted(self):
        self.assertTrue(store.is_valid_report_id("RPT-20261019-080000-P8H"))

    def test_path_traversal_ids_rejected(self):
        for bad in (
            "../../etc/passwd",
            "..\\..\\secrets",
            "RPT-20261019-080000-P8H/../../../x",
            "",
            None,
        ):
            with self.subTest(bad=bad):
                self.assertFalse(store.is_valid_report_id(bad))
                with self.assertRaises(ValueError):
                    store.report_paths(bad)

    def test_load_rejects_invalid_id(self):
        with self.assertRaises(ValueError):
            store.load_report_json("../../etc/passwd")


class StateTests(ReporterPathTestCase):
    def test_scheduling_is_disabled_by_default(self):
        state = store.read_state()
        self.assertFalse(state["schedule"]["enabled"])
        self.assertEqual(
            state["schedule"]["interval_hours"], config.DEFAULT_INTERVAL_HOURS
        )

    def test_state_round_trip_persists_locally(self):
        state = store.read_state()
        state["schedule"]["enabled"] = True
        store.write_state(state)
        self.assertTrue(store.read_state()["schedule"]["enabled"])
        self.assertTrue(self.state_file.exists())

    def test_default_state_never_contains_credentials(self):
        text = json.dumps(store.default_state())
        self.assertNotIn("token", text.lower())
        self.assertNotIn("BOT_TOKEN", text)


class HumanActivityStoreTests(ReporterPathTestCase):
    def test_entries_are_persisted_with_ids(self):
        store.append_human_activity("Reviewed benchmark draft", author="director")
        entries = json.loads(self.human_file.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "human-1")

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            store.append_human_activity("   ")


class DeliveryLogTests(ReporterPathTestCase):
    def test_delivery_log_redacts_tokens(self):
        fake_token = "987654321:" + "B" * 35
        store.append_delivery_log(f"send failed for {fake_token}")
        content = self.delivery_log.read_text(encoding="utf-8")
        self.assertNotIn(fake_token, content)
        self.assertIn("[REDACTED]", content)


if __name__ == "__main__":
    unittest.main()
