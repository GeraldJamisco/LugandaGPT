"""Report generation tests: activity, empty periods, spending, redaction."""

import json
import unittest
from datetime import datetime, timezone

from reporter import report, store

from .support import ReporterPathTestCase

PERIOD_START = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)


def verification_context(root, human=None, present=True, docs_environment=True):
    """A deterministic evidence context for exit-criteria verification.

    Tests build this instead of letting verification read the real
    repository, so statuses do not depend on the working machine.
    """
    repo = root / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    deliverables = ("AGENTS.md", "README.md", "data/README.md", ".gitignore")
    if present:
        for relative in deliverables:
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    if docs_environment:
        (docs / "ARCHITECTURE.md").write_text(
            "# Architecture\n\n## Environment constraints\n\n"
            "- Python 3, about 8 GB RAM.\n",
            encoding="utf-8",
        )
    return {
        "repo_root": repo,
        "docs_dir": docs,
        "gitignore_path": repo / ".gitignore",
        "git": {"available": True},
        "tracked_reporter_files": [],
        "human_verifications": human or {},
    }


class ReportWithActivityTests(ReporterPathTestCase):
    def _data_with_commit(self):
        commit = {
            "sha": "a" * 40,
            "subject": "add tokenizer smoke test",
            "author": "Tester",
            "authored_at": "2026-10-19T04:00:00+00:00",
        }
        data = self.synthetic_data()
        data["git"]["commits"] = [commit]
        data["git"]["head"] = commit
        return data

    def test_commit_is_reported_as_verified_completed_with_evidence(self):
        data = self._data_with_commit()
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        completed = rep["summary"]["verified_completed"]
        self.assertEqual(len(completed), 1)
        self.assertIn("add tokenizer smoke test", completed[0]["text"])
        self.assertIn("git commit", completed[0]["evidence"])
        self.assertTrue(rep["evidence"])

    def test_uncommitted_changes_are_repository_state_not_incomplete_work(self):
        data = self.synthetic_data()
        data["git"]["clean"] = False
        data["git"]["changes"] = [
            {"index_status": "M", "worktree_status": " ", "path": "docs/ROADMAP.md"}
        ]
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        # An uncommitted file is repository state, not evidence of unfinished
        # work, so it must not appear as an attempted or incomplete task.
        self.assertEqual(rep["summary"]["attempted_or_incomplete"], [])
        self.assertEqual(rep["summary"]["verified_completed"], [])
        self.assertEqual(rep["repository_state"]["changed_file_count"], 1)
        self.assertEqual(
            rep["repository_state"]["changed_files"][0]["path"], "docs/ROADMAP.md"
        )
        self.assertIn("not classified as an", rep["repository_state"]["note"])
        self.assertEqual(rep["new_activity_count"], 0)
        self.assertIn("repository state", markdown)
        self.assertNotIn("uncommitted working tree change(s) present", markdown)

    def test_uncommitted_changes_do_not_reduce_verified_activity_count(self):
        data = self.synthetic_data()
        data["git"]["clean"] = False
        data["git"]["changes"] = [
            {"index_status": "M", "worktree_status": " ", "path": f"file{i}.py"}
            for i in range(17)
        ]
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertEqual(rep["summary"]["attempted_or_incomplete"], [])
        self.assertEqual(rep["new_activity_count"], 0)
        self.assertEqual(rep["repository_state"]["changed_file_count"], 17)

    def test_plan_items_are_never_reported_as_completed(self):
        data = self.synthetic_data()
        data["roadmap"]["phases"] = [
            {
                "number": 4,
                "title": "Approved initial training",
                "status": "Blocked on Phase 3 and explicit approval.",
                "evidence": "docs/ROADMAP.md (Phase 4)",
            }
        ]
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        completed_text = json.dumps(rep["summary"]["verified_completed"])
        self.assertNotIn("Approved initial training", completed_text)

    def test_failing_test_record_is_reported_as_failure(self):
        self.write_test_run(
            "run-fail.json",
            {
                "recorded_at": "2026-10-19T05:00:00+00:00",
                "command": "python -m unittest",
                "exit_code": 1,
                "failures": 2,
                "errors": 0,
                "summary": "2 failures",
            },
        )
        data = self.synthetic_data()
        from reporter import collect

        data["tests"] = collect.collect_tests()
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertEqual(len(rep["summary"]["failed_or_unavailable"]), 1)
        self.assertEqual(rep["summary"]["verified_completed"], [])

    def test_human_activity_is_kept_in_its_own_section(self):
        data = self.synthetic_data()
        data["human_activity"] = {
            "status": "available",
            "reason": None,
            "entries": [
                {
                    "id": "human-1",
                    "text": "Agreed on benchmark size",
                    "recorded_at": "2026-10-19T03:00:00+00:00",
                    "source": "human-entered",
                }
            ],
        }
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertEqual(len(rep["summary"]["human_reported"]), 1)
        self.assertEqual(rep["summary"]["verified_completed"], [])


class EmptyPeriodTests(ReporterPathTestCase):
    def test_no_activity_is_reported_explicitly(self):
        rep, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertIn("No meaningful activity recorded", rep["activity_note"])
        self.assertIn("No meaningful activity recorded", markdown)
        self.assertEqual(rep["summary"]["verified_completed"], [])

    def test_empty_period_still_lists_sources_checked(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertIn("Sources checked", rep["activity_note"])


class SpendingTests(ReporterPathTestCase):
    def test_missing_usage_data_is_unavailable_not_zero(self):
        rep, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertEqual(rep["api_spending"]["status"], "unavailable")
        self.assertIsNone(rep["api_spending"]["spend_usd"])
        self.assertIn("Unavailable", markdown)


class SerializationAndContentTests(ReporterPathTestCase):
    def test_report_serializes_to_json(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        text = report.report_as_json(rep)
        self.assertEqual(json.loads(text)["report_id"], rep["report_id"])

    def test_markdown_has_required_sections(self):
        _, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        for heading in (
            "## Executive summary",
            "## Repository state",
            "## Verified completed work",
            "## Attempted or incomplete work",
            "## Failures and collection warnings",
            "## Human-reported activity",
            "## Tests",
            "## Experiments",
            "## Decisions and blockers",
            "## Verified spending",
            "## Next priorities (roadmap requirements, options and approvals)",
            "## Evidence index",
        ):
            self.assertIn(heading, markdown)

    def test_markdown_contains_no_em_dashes(self):
        _, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertNotIn("\u2014", markdown)

    def test_next_priorities_are_grouped_by_kind_with_labels(self):
        rep, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertTrue(rep["next_steps"])
        for step in rep["next_steps"]:
            self.assertIn("verified", step)
            self.assertIn(step.get("kind"), report.NEXT_STEP_LABELS)
        kinds = {step["kind"] for step in rep["next_steps"]}
        # Scheduling needs the owner's decision; billing export is optional.
        self.assertIn("approval", kinds)
        self.assertIn("optional", kinds)
        self.assertIn("needs owner decision or approval", markdown)
        self.assertIn("optional; not required by the roadmap", markdown)
        self.assertNotIn("suggestions, not verified work", markdown)


class ExecutiveSummaryTests(ReporterPathTestCase):
    def _report_with_recorded_test(self):
        self.write_test_run(
            "run-pass.json",
            {
                "recorded_at": "2026-10-19T05:00:00+00:00",
                "command": "python -m unittest discover -s tests",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "summary": "148 tests, 0 failures",
            },
        )
        from reporter import collect

        data = self.synthetic_data()
        data["tests"] = collect.collect_tests()
        return report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )

    def test_summary_answers_the_required_questions(self):
        rep, markdown, _ = self._report_with_recorded_test()
        summary = rep["executive_summary"]
        for key in (
            "changed",
            "completed",
            "incomplete",
            "core_research",
            "next_milestone",
            "owner_decisions",
        ):
            self.assertTrue(str(summary[key]).strip())
        self.assertIn("1 new activity item", summary["changed"])
        self.assertIn("1 verified item", summary["completed"])
        self.assertIn("Executive summary", markdown)

    def test_reporter_test_run_is_not_presented_as_core_research_advance(self):
        rep, _, _ = self._report_with_recorded_test()
        core = rep["executive_summary"]["core_research"]
        self.assertIn("No research result was recorded", core)
        self.assertIn("do not measure Luganda language quality", core)
        self.assertEqual(
            rep["summary"]["verified_completed"][0]["area"], "test verification"
        )
        self.assertNotIn("capability", rep["activity_note"])

    def test_uncommitted_changes_are_not_counted_as_incomplete(self):
        data = self.synthetic_data()
        data["git"]["clean"] = False
        data["git"]["changes"] = [
            {"index_status": "??", "worktree_status": "??", "path": "src/x.py"}
        ]
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        incomplete = rep["executive_summary"]["incomplete"]
        self.assertIn("repository state, not incomplete work", incomplete)
        self.assertNotIn("1 item", incomplete)

    def test_current_phase_exit_criteria_become_mandatory_items(self):
        data = self.synthetic_data()
        data["roadmap"]["current_phase"] = {
            "number": 0,
            "title": "Project foundation",
            "status": "In progress.",
            "evidence": "docs/ROADMAP.md (Phase 0)",
            "exit_criteria": [
                "Documentation inventory complete and internally consistent.",
                "Environment requirements recorded.",
            ],
        }
        data["verification_context"] = verification_context(
            self.tmp_root, human={}
        )
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        mandatory = [
            step for step in rep["next_steps"] if step["kind"] == "mandatory"
        ]
        self.assertEqual(len(mandatory), 2)
        self.assertIn("Phase 0 exit criterion", mandatory[0]["text"])
        self.assertIn("Documentation inventory", mandatory[0]["text"])
        self.assertEqual(mandatory[0]["status"], "needs_review")
        self.assertIn("status: needs review", markdown)
        self.assertIn("evidence:", markdown)
        # The phase must not be presented as complete.
        self.assertFalse(rep["phase_verification"]["summary"]["phase_complete"])
        self.assertIn(
            "recorded exit criteria are verified complete",
            rep["executive_summary"]["next_milestone"],
        )
        self.assertIn("is not complete", rep["executive_summary"]["phase_verification"])

    def test_missing_phase_details_do_not_invent_priorities(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        mandatory = [
            step for step in rep["next_steps"] if step["kind"] == "mandatory"
        ]
        self.assertEqual(mandatory, [])
        self.assertEqual(
            rep["executive_summary"]["next_milestone"],
            "Not determinable from docs/ROADMAP.md.",
        )

    def test_pending_verification_states_no_ordering_is_established(self):
        data = self.synthetic_data()
        data["roadmap"]["current_phase"] = {
            "number": 0,
            "title": "Project foundation",
            "status": "In progress.",
            "evidence": "docs/ROADMAP.md (Phase 0)",
            "exit_criteria": [
                "Documentation inventory complete and internally consistent.",
                "Environment requirements recorded.",
            ],
        }
        data["verification_context"] = verification_context(self.tmp_root, human={})
        rep, _, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertIn(
            "does not establish an ordering",
            rep["executive_summary"]["phase_verification"],
        )
        self.assertIsNone(rep["phase_verification"]["priority"]["criterion"])

    def test_phase_is_not_complete_while_a_mandatory_criterion_is_pending(self):
        data = self.synthetic_data()
        data["roadmap"]["current_phase"] = {
            "number": 0,
            "title": "Project foundation",
            "status": "In progress.",
            "evidence": "docs/ROADMAP.md (Phase 0)",
            "exit_criteria": [
                "Documentation inventory complete and internally consistent.",
                "Environment requirements recorded.",
            ],
        }
        data["verification_context"] = verification_context(
            self.tmp_root,
            human={
                "documentation inventory complete and internally consistent": {
                    "status": "verified complete",
                    "verified_at": "2026-10-19T00:00:00+00:00",
                    "author": "Owner",
                    "note": "Reviewed the inventory against the roadmap.",
                }
            },
        )
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        summary = rep["phase_verification"]["summary"]
        self.assertEqual(summary["verified_complete"], 1)
        self.assertFalse(summary["phase_complete"])
        self.assertIn("1 of 2", markdown)
        self.assertIn("phase not complete", markdown)
        self.assertIn("[verified complete]", markdown)

    def test_software_verification_stays_distinct_from_model_quality(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        software = rep["executive_summary"]["software_verification"]
        research = rep["executive_summary"]["core_research"]
        self.assertIn("do not measure Luganda language quality", software)
        self.assertIn("do not measure Luganda language quality", research)
        self.assertIn("No trained model exists", research)


class LatestTestEvidenceTests(ReporterPathTestCase):
    def _tests(self):
        from reporter import collect

        return collect.collect_tests()

    def test_latest_run_uses_recorded_timestamp_not_filename(self):
        # File order is a-newer then z-older, so a filename sort would pick
        # z-older. The recorded timestamp must win instead.
        self.write_test_run(
            "a-newer.json",
            {
                "recorded_at": "2026-10-19T09:00:00+00:00",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "tests_run": 200,
                "duration_seconds": 20.0,
            },
        )
        self.write_test_run(
            "z-older.json",
            {
                "recorded_at": "2026-10-19T01:00:00+00:00",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "tests_run": 148,
                "duration_seconds": 18.1,
            },
        )
        evidence = report.latest_test_evidence(self._tests())
        self.assertEqual(evidence["latest_run"]["file"], "a-newer.json")
        self.assertEqual(evidence["latest_run"]["tests_run"], 200)
        self.assertEqual(evidence["latest_run"]["duration_seconds"], 20.0)
        self.assertEqual(evidence["latest_successful_run"]["file"], "a-newer.json")
        self.assertTrue(evidence["latest_is_success"])

    def test_newer_failure_is_not_hidden_by_older_success(self):
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
                "failures": 2,
                "errors": 0,
                "tests_run": 163,
                "duration_seconds": 24.0,
            },
        )
        data = self.synthetic_data()
        data["tests"] = self._tests()
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        evidence = rep["test_evidence"]
        self.assertEqual(evidence["latest_run"]["file"], "2026-10-19-suite.json")
        self.assertEqual(evidence["latest_run"]["outcome"], "failed")
        self.assertFalse(evidence["latest_is_success"])
        self.assertEqual(
            evidence["latest_successful_run"]["file"], "2026-10-18-suite.json"
        )
        self.assertEqual(evidence["latest_successful_run"]["outcome"], "passed")
        summary = rep["executive_summary"]["software_verification"]
        self.assertIn("Latest recorded test run", summary)
        self.assertIn("it did not pass", summary)
        self.assertIn("not the latest run", summary)
        self.assertIn("Latest successful run: 2026-10-18-suite.json", summary)
        # The document must keep the two runs distinct as well.
        self.assertIn("Latest run:", markdown)
        self.assertIn("Latest successful run:", markdown)

    def test_missing_count_and_duration_are_reported_as_unavailable(self):
        self.write_test_run(
            "sparse.json",
            {
                "recorded_at": "2026-10-19T09:00:00+00:00",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
            },
        )
        evidence = report.latest_test_evidence(self._tests())
        run = evidence["latest_run"]
        self.assertIsNone(run["tests_run"])
        self.assertIsNone(run["duration_seconds"])
        line = report.describe_test_run(run)
        self.assertIn("test count unavailable", line)
        self.assertIn("duration unavailable", line)

    def test_run_without_timestamp_is_not_used_as_latest(self):
        self.write_test_run(
            "dated.json",
            {
                "recorded_at": "2026-10-19T01:00:00+00:00",
                "exit_code": 0,
                "failures": 0,
                "errors": 0,
                "tests_run": 10,
            },
        )
        self.write_test_run(
            "undated.json",
            {"exit_code": 0, "failures": 0, "errors": 0, "tests_run": 99},
        )
        evidence = report.latest_test_evidence(self._tests())
        self.assertEqual(evidence["latest_run"]["file"], "dated.json")
        self.assertEqual(evidence["undated_count"], 1)

    def test_no_recorded_run_claims_no_result(self):
        evidence = report.latest_test_evidence(self._tests())
        self.assertEqual(evidence["status"], "unavailable")
        self.assertIsNone(evidence["latest_run"])

    def test_legacy_record_without_numeric_fields_still_reads(self):
        # The committed convenience record keeps only a summary string; the
        # count must be reported unavailable rather than parsed from text.
        self.write_test_run(
            "legacy.json",
            {"recorded_at": "2026-10-19T09:00:00+00:00", "summary": "18 tests, 0 failures"},
        )
        evidence = report.latest_test_evidence(self._tests())
        run = evidence["latest_run"]
        self.assertIsNone(run["tests_run"])
        self.assertEqual(run["outcome"], "unknown")


class ReportingSnapshotTests(ReporterPathTestCase):
    def _prior_delivery_entry(self):
        return {
            "report_id": "RPT-20260101-000000-P8H",
            "ok": True,
            "at": "2026-01-01T00:00:05+00:00",
            "source": "scheduler",
            "parts_sent": 1,
            "parts_total": 1,
        }

    def test_snapshot_records_state_at_generation_time(self):
        state = store.read_state()
        state["last_delivery"] = self._prior_delivery_entry()
        state["schedule"]["enabled"] = False
        store.write_state(state)
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        snapshot = rep["reporting"]
        self.assertEqual(snapshot["observed_at"], rep["generated_at"])
        self.assertEqual(
            snapshot["last_delivery"]["report_id"], "RPT-20260101-000000-P8H"
        )
        self.assertFalse(snapshot["schedule_enabled"])

    def test_later_delivery_state_is_not_used_in_the_generation_snapshot(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        # Simulate the delivery that happens after generation.
        state = store.read_state()
        state["last_delivery"] = {
            "report_id": rep["report_id"],
            "ok": True,
            "at": rep["generated_at"],
            "source": "dashboard",
            "parts_sent": 2,
            "parts_total": 2,
        }
        store.write_state(state)
        self.assertIsNone(rep["reporting"]["last_delivery"])


class ReportingPeriodTests(ReporterPathTestCase):
    def test_on_demand_report_states_the_actual_covered_window(self):
        rep, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=datetime(2026, 10, 19, 7, 23, tzinfo=timezone.utc),
            period_end=PERIOD_END,
            source="dashboard",
        )
        self.assertEqual(rep["period"]["mode"], "on-demand")
        self.assertEqual(rep["period"]["covered_text"], "37 minutes")
        self.assertIn("on-demand report", markdown)
        self.assertIn("not a full 8h scheduled period", markdown)
        self.assertNotIn("(8h interval)", markdown)

    def test_scheduled_report_is_labelled_scheduled(self):
        rep, markdown, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            source="scheduler",
        )
        self.assertEqual(rep["period"]["mode"], "scheduled")
        self.assertIn("scheduled report", markdown)
        self.assertNotIn("on-demand", markdown)


    def test_report_states_model_status(self):
        rep, _, _ = report.generate_report(
            data=self.synthetic_data(),
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertIn("No trained LugandaGPT model exists", rep["model_status"])


class RedactionTests(ReporterPathTestCase):
    def test_secret_in_human_activity_is_redacted(self):
        fake_token = "123456789:" + "A" * 35
        data = self.synthetic_data()
        data["human_activity"] = {
            "status": "available",
            "reason": None,
            "entries": [
                {
                    "id": "human-1",
                    "text": f"pasted token {fake_token} into a note",
                    "recorded_at": "2026-10-19T03:00:00+00:00",
                    "source": "human-entered",
                }
            ],
        }
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertNotIn(fake_token, json.dumps(rep))
        self.assertNotIn(fake_token, markdown)

    def test_warning_text_is_redacted(self):
        data = self.synthetic_data()
        data["warnings"] = [
            {"source": "git", "error": "sk-abcdefghijklmnop failed somehow"}
        ]
        rep, markdown, _ = report.generate_report(
            data=data, period_start=PERIOD_START, period_end=PERIOD_END
        )
        self.assertNotIn("sk-abcdefghijklmnop", json.dumps(rep))
        self.assertNotIn("sk-abcdefghijklmnop", markdown)


if __name__ == "__main__":
    unittest.main()
