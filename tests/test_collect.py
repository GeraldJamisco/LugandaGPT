"""Collector tests: experiments, roadmap, decisions, human entries, usage."""

import json
import unittest
from pathlib import Path
from unittest import mock

from reporter import collect, config

from .support import ReporterPathTestCase


class TestRecordTests(ReporterPathTestCase):
    def test_tests_unavailable_when_no_records_exist(self):
        result = collect.collect_tests()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["runs"], [])
        self.assertIsNotNone(result["reason"])

    def test_tests_available_when_real_output_recorded(self):
        self.write_test_run(
            "run-1.json",
            {
                "recorded_at": "2026-10-19T10:00:00+00:00",
                "command": "python -m unittest discover -s tests",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "summary": "18 tests, 0 failures",
            },
        )
        result = collect.collect_tests()
        self.assertEqual(result["status"], "available")
        self.assertEqual(len(result["runs"]), 1)
        self.assertEqual(result["runs"][0]["exit_code"], 0)

    def test_malformed_record_is_flagged_not_ignored(self):
        self.test_runs_dir.mkdir(parents=True, exist_ok=True)
        (self.test_runs_dir / "broken.json").write_text("{not json", encoding="utf-8")
        result = collect.collect_tests()
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["runs"][0]["status"], "unreadable")


class DocumentParsingTests(ReporterPathTestCase):
    def test_template_entry_is_not_reported_as_an_experiment(self):
        doc = self.tmp_root / "EXPERIMENT_LOG.md"
        doc.write_text(
            "# Experiment Log\n"
            "## Template\n"
            "```\n"
            "### EXP-YYYY-NNN — <short title>\n"
            "- **Experiment ID:** EXP-YYYY-NNN\n"
            "```\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "EXPERIMENT_LOG", doc):
            result = collect.collect_experiments()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["entries"], [])

    def test_real_experiment_entry_is_parsed(self):
        doc = self.tmp_root / "EXPERIMENT_LOG.md"
        doc.write_text(
            "# Experiment Log\n"
            "### EXP-2026-001 — tokenizer smoke test\n"
            "- **Experiment ID:** EXP-2026-001\n"
            "- **Date:** 2026-10-19\n"
            "- **Results:** not run\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "EXPERIMENT_LOG", doc):
            result = collect.collect_experiments()
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["entries"][0]["id"], "EXP-2026-001")
        self.assertEqual(result["entries"][0]["fields"]["Date"], "2026-10-19")

    def test_experiment_log_missing_is_unavailable(self):
        with mock.patch.object(config, "EXPERIMENT_LOG", self.tmp_root / "none.md"):
            result = collect.collect_experiments()
        self.assertEqual(result["status"], "unavailable")

    def test_roadmap_reports_current_phase_and_blockers(self):
        doc = self.tmp_root / "ROADMAP.md"
        doc.write_text(
            "## Phase 0 — Project foundation\n"
            "**Status:** In progress.\n"
            "## Phase 1 — Research\n"
            "**Status:** Not started.\n"
            "## Phase 2 — Data\n"
            "**Status:** Blocked on Phase 1 approval.\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "ROADMAP_FILE", doc):
            result = collect.collect_roadmap()
        self.assertEqual(result["current_phase"]["number"], 0)
        self.assertEqual(len(result["phases"]), 3)
        self.assertEqual(len(result["blockers"]), 1)
        self.assertIn("Phase 2", result["blockers"][0]["text"])
        self.assertEqual(result["upcoming"][0]["number"], 1)

    def test_roadmap_exit_criteria_are_parsed_per_phase(self):
        doc = self.tmp_root / "ROADMAP.md"
        doc.write_text(
            "## Phase 0 - Project foundation\n"
            "**Status:** In progress.\n"
            "**Objectives**\n"
            "- Establish documentation.\n"
            "**Exit criteria**\n"
            "- Documentation inventory complete and internally consistent.\n"
            "- Environment requirements recorded.\n"
            "**Dependencies / Risks**\n"
            "- Small local machine.\n"
            "## Phase 1 - Research and baseline\n"
            "**Status:** Not started.\n"
            "**Exit criteria**\n"
            "- Survey complete.\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "ROADMAP_FILE", doc):
            result = collect.collect_roadmap()
        phase_zero = result["phases"][0]
        self.assertEqual(
            phase_zero["exit_criteria"],
            [
                "Documentation inventory complete and internally consistent.",
                "Environment requirements recorded.",
            ],
        )
        # Only exit criteria are captured; objectives and risks are not.
        self.assertNotIn("Establish documentation.", phase_zero["exit_criteria"])
        self.assertEqual(result["phases"][1]["exit_criteria"], ["Survey complete."])
        self.assertEqual(
            result["current_phase"]["exit_criteria"], phase_zero["exit_criteria"]
        )

    def test_roadmap_without_exit_criteria_reports_an_empty_list(self):
        doc = self.tmp_root / "ROADMAP.md"
        doc.write_text(
            "## Phase 0 - Project foundation\n**Status:** In progress.\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "ROADMAP_FILE", doc):
            result = collect.collect_roadmap()
        self.assertEqual(result["phases"][0]["exit_criteria"], [])

    def test_roadmap_missing_file_is_unavailable(self):
        with mock.patch.object(config, "ROADMAP_FILE", self.tmp_root / "none.md"):
            result = collect.collect_roadmap()
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["current_phase"])

    def test_open_decisions_are_collected(self):
        doc = self.tmp_root / "DECISIONS.md"
        doc.write_text(
            "## D-001 — first\n**Status:** Accepted.\n"
            "## D-005 — open one\n**Status:** Open.\n",
            encoding="utf-8",
        )
        with mock.patch.object(config, "DECISIONS_FILE", doc):
            result = collect.collect_decisions()
        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual([e["id"] for e in result["open"]], ["D-005"])


class HumanActivityTests(ReporterPathTestCase):
    def test_missing_file_is_unavailable(self):
        result = collect.collect_human_activity()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["entries"], [])

    def test_entries_are_marked_human_entered(self):
        self.human_file.write_text(
            json.dumps(
                [
                    {
                        "id": "human-1",
                        "recorded_at": "2026-10-19T10:00:00+00:00",
                        "text": "Reviewed data licensing notes",
                    }
                ]
            ),
            encoding="utf-8",
        )
        result = collect.collect_human_activity()
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["entries"][0]["source"], "human-entered")


class ApiUsageTests(ReporterPathTestCase):
    def test_missing_export_is_unavailable_not_zero(self):
        result = collect.collect_api_usage()
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["spend_usd"])

    def test_malformed_export_is_unavailable(self):
        self.api_file.write_text("{}", encoding="utf-8")
        result = collect.collect_api_usage()
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["spend_usd"])

    def test_valid_export_is_reported(self):
        self.api_file.write_text(
            json.dumps(
                {
                    "source": "provider billing export",
                    "retrieved_at": "2026-10-19T10:00:00+00:00",
                    "spend_usd": 0,
                }
            ),
            encoding="utf-8",
        )
        result = collect.collect_api_usage()
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["spend_usd"], 0)


class AggregateTests(unittest.TestCase):
    def test_collect_all_returns_every_source(self):
        data = collect.collect_all(commit_limit=3)
        for key in (
            "git",
            "tests",
            "experiments",
            "roadmap",
            "decisions",
            "human_activity",
            "api_usage",
            "warnings",
        ):
            self.assertIn(key, data)
        self.assertIsInstance(data["warnings"], list)


if __name__ == "__main__":
    unittest.main()
