"""Exit-criteria verification tests: statuses, evidence and phase completion.

These tests build their own evidence context instead of reading the real
repository, so a status never depends on the machine running the suite.
"""

import re

from reporter import verify

from .support import ReporterPathTestCase

DOCUMENT_CRITERION = "Documentation inventory complete and internally consistent."
ENVIRONMENT_CRITERION = "Environment requirements recorded."
GIT_CRITERION = "Git hygiene in place (ignore rules validated; no secrets committed)."
UNKNOWN_CRITERION = "Some criterion with no registered automated check."

DELIVERABLES = ("AGENTS.md", "README.md", "data/README.md", ".gitignore")


def normalize(text):
    return re.sub(r"\s+", " ", str(text).strip().rstrip(".")).lower()


def human_record(note="Reviewed the evidence and accepted it."):
    return {
        "status": "verified complete",
        "verified_at": "2026-10-19T00:00:00+00:00",
        "author": "Project Owner",
        "note": note,
    }


def make_context(
    root,
    present=True,
    environment=True,
    gitignore=True,
    git_available=True,
    tracked=None,
    human=None,
):
    repo = root / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    if present:
        for relative in DELIVERABLES:
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
    if not gitignore:
        candidate = repo / ".gitignore"
        if candidate.exists():
            candidate.unlink()
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    if environment:
        (docs / "ARCHITECTURE.md").write_text(
            "# Architecture\n\n## Environment constraints\n\n"
            "- Python 3, about 8 GB RAM, limited free disk.\n",
            encoding="utf-8",
        )
    return {
        "repo_root": repo,
        "docs_dir": docs,
        "gitignore_path": repo / ".gitignore",
        "git": {"available": git_available},
        "tracked_reporter_files": tracked,
        "human_verifications": human or {},
    }


class CriterionStatusTests(ReporterPathTestCase):
    def test_verified_complete_needs_a_human_record_with_a_note(self):
        context = make_context(
            self.tmp_root,
            human={normalize(DOCUMENT_CRITERION): human_record()},
        )
        record = verify.verify_criteria([DOCUMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "verified_complete")
        self.assertEqual(record["status_label"], "verified complete")
        self.assertTrue(record["evidence_available"])
        self.assertIn("Reviewed the evidence", record["evidence"][0])

    def test_human_record_without_a_note_is_not_verified_complete(self):
        context = make_context(
            self.tmp_root,
            human={
                normalize(DOCUMENT_CRITERION): {
                    "status": "verified complete",
                    "author": "Project Owner",
                }
            },
        )
        record = verify.verify_criteria([DOCUMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "needs_review")
        self.assertFalse(record["evidence_available"])
        self.assertIn("no supporting note", record["reason"])

    def test_missing_required_document_is_incomplete_with_evidence(self):
        context = make_context(self.tmp_root, present=False)
        record = verify.verify_criteria([DOCUMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "incomplete")
        self.assertIn("missing", " ".join(record["evidence"]))
        self.assertFalse(record["human_review_required"])

    def test_existing_files_alone_are_only_needs_review(self):
        context = make_context(self.tmp_root)
        record = verify.verify_criteria([DOCUMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "needs_review")
        self.assertTrue(record["evidence_available"])
        self.assertTrue(record["human_review_required"])

    def test_unregistered_criterion_is_not_verified(self):
        context = make_context(self.tmp_root)
        record = verify.verify_criteria([UNKNOWN_CRITERION], context)[0]
        self.assertEqual(record["status"], "not_verified")
        self.assertFalse(record["evidence_available"])
        self.assertIn("no evidence", record["reason"].lower())

    def test_evidence_never_contains_em_dashes(self):
        context = make_context(
            self.tmp_root,
            human={
                normalize(DOCUMENT_CRITERION): human_record(
                    note="Reviewed \u2014 and accepted."
                )
            },
        )
        record = verify.verify_criteria([DOCUMENT_CRITERION], context)[0]
        self.assertNotIn("\u2014", " ".join(record["evidence"]))


class GitHygieneTests(ReporterPathTestCase):
    def test_missing_gitignore_is_incomplete(self):
        context = make_context(self.tmp_root, gitignore=False)
        record = verify.verify_criteria([GIT_CRITERION], context)[0]
        self.assertEqual(record["status"], "incomplete")

    def test_tracked_reporter_data_is_incomplete(self):
        context = make_context(
            self.tmp_root, tracked=["reports/reporter/state.json"]
        )
        record = verify.verify_criteria([GIT_CRITERION], context)[0]
        self.assertEqual(record["status"], "incomplete")
        self.assertIn("reports/reporter/state.json", " ".join(record["evidence"]))

    def test_clean_ignore_rules_still_need_human_review(self):
        context = make_context(self.tmp_root, tracked=[])
        record = verify.verify_criteria([GIT_CRITERION], context)[0]
        self.assertEqual(record["status"], "needs_review")

    def test_git_unavailable_is_still_needs_review_with_evidence(self):
        context = make_context(self.tmp_root, git_available=False, tracked=None)
        record = verify.verify_criteria([GIT_CRITERION], context)[0]
        self.assertEqual(record["status"], "needs_review")
        self.assertTrue(record["evidence_available"])


class EnvironmentTests(ReporterPathTestCase):
    def test_recorded_environment_needs_human_review(self):
        context = make_context(self.tmp_root, environment=True)
        record = verify.verify_criteria([ENVIRONMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "needs_review")
        self.assertIn("Environment constraints", record["evidence"][0])

    def test_absent_environment_record_is_incomplete(self):
        context = make_context(self.tmp_root, environment=False)
        record = verify.verify_criteria([ENVIRONMENT_CRITERION], context)[0]
        self.assertEqual(record["status"], "incomplete")
        self.assertFalse(record["evidence_available"])


class PhaseCompletionTests(ReporterPathTestCase):
    def _context_with_one_verified(self):
        return make_context(
            self.tmp_root,
            human={normalize(DOCUMENT_CRITERION): human_record()},
        )

    def test_phase_not_complete_while_any_criterion_is_pending(self):
        context = self._context_with_one_verified()
        records = verify.verify_criteria(
            [DOCUMENT_CRITERION, ENVIRONMENT_CRITERION], context
        )
        summary = verify.summarize(records)
        self.assertFalse(summary["phase_complete"])
        self.assertEqual(summary["verified_complete"], 1)
        self.assertEqual(summary["pending"], 1)

    def test_phase_complete_only_when_every_criterion_is_verified(self):
        context = make_context(
            self.tmp_root,
            human={
                normalize(DOCUMENT_CRITERION): human_record(),
                normalize(ENVIRONMENT_CRITERION): human_record(),
            },
        )
        records = verify.verify_criteria(
            [DOCUMENT_CRITERION, ENVIRONMENT_CRITERION], context
        )
        summary = verify.summarize(records)
        self.assertTrue(summary["phase_complete"])
        self.assertEqual(summary["verified_complete"], 2)

    def test_no_criteria_is_never_complete(self):
        summary = verify.summarize([])
        self.assertFalse(summary["phase_complete"])
        self.assertEqual(summary["total"], 0)


class PriorityTests(ReporterPathTestCase):
    def test_single_incomplete_is_named_as_highest_priority(self):
        context = make_context(self.tmp_root, present=False, environment=True)
        records = verify.verify_criteria(
            [DOCUMENT_CRITERION, ENVIRONMENT_CRITERION], context
        )
        priority = verify.highest_priority(records)
        self.assertIn("Documentation inventory", priority["criterion"])
        self.assertIn("only criterion recorded as incomplete", priority["basis"])

    def test_several_incomplete_criteria_establish_no_ordering(self):
        context = make_context(self.tmp_root, present=False)
        records = verify.verify_criteria(
            ["Documentation inventory A", "Documentation inventory B"], context
        )
        priority = verify.highest_priority(records)
        self.assertIsNone(priority["criterion"])
        self.assertIn("does not establish an ordering", priority["basis"])

    def test_several_pending_of_equal_standing_establish_no_ordering(self):
        context = make_context(self.tmp_root)
        records = verify.verify_criteria(
            [DOCUMENT_CRITERION, ENVIRONMENT_CRITERION], context
        )
        priority = verify.highest_priority(records)
        self.assertIsNone(priority["criterion"])
        self.assertIn("does not establish an ordering", priority["basis"])
