"""Review, calibration, adjudication, and agreement tests."""

import unittest

from benchmark.errors import ValidationError, WorkflowError
from benchmark.item import can_transition, transition_item, validate_item
from benchmark.review import (
    CalibrationSession,
    ReferenceReview,
    agreement_report,
    assert_blind_packet,
    build_adjudication,
    build_review_packet,
    material_disagreements,
    quadratic_weighted_kappa,
    summarize_scores,
    validate_independent_reviews,
    validate_response_review,
)
from benchmark.versioning import ExclusionRecord

from .benchmark_support import (
    ambiguity_check,
    base_item,
    evidence_for,
    raw_response,
    reference_review,
    response_review,
)


class ItemReviewEvidenceTests(unittest.TestCase):
    def test_ambiguity_status_requires_a_second_reviewer_record(self):
        item = base_item(review_status="ambiguity_checked")
        with self.assertRaises(ValidationError):
            validate_item(item)
        validate_item(item, evidence={"ambiguity_checks": [ambiguity_check(item)]})

    def test_intrinsic_ambiguity_requires_not_applicable_reference(self):
        item = base_item(
            review_status="ambiguity_checked",
            reference_status="pending",
            reference_answer=None,
        )
        evidence = {
            "ambiguity_checks": [
                ambiguity_check(item, outcome="intrinsic_ambiguity")
            ]
        }
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence)

    def test_calibration_items_must_be_separate(self):
        item = base_item(review_status="native_reviewed")
        evidence = evidence_for(item)
        evidence["calibration_sessions"] = [
            CalibrationSession(
                session_id="SYN-CAL-002",
                date="2026-10-20",
                reviewer_ids=("reviewer-1", "reviewer-2"),
                calibration_item_ids=(item["id"],),
                completed=True,
                notes="Synthetic invalid calibration session.",
            )
        ]
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence)

    def test_native_reviewed_requires_two_calibrated_reviewers(self):
        item = base_item(review_status="native_reviewed")
        with self.assertRaises(ValidationError):
            validate_item(item)
        validate_item(item, evidence=evidence_for(item))
        weak = evidence_for(item)
        weak["item_reviews"] = weak["item_reviews"][:1]
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=weak)

    def test_cultural_note_requires_native_approval(self):
        item = base_item(
            id="LGP-BENCH-CULTURAL-001",
            category="cultural_interpretation",
            prompt_language="lg",
            response_language="lg",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "relevance",
                "appropriate_register",
            ],
            cultural_note="Synthetic cultural note.",
            review_status="native_reviewed",
        )
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence_for(item, cultural_ok=False))
        validate_item(item, evidence=evidence_for(item, cultural_ok=True))

    def test_authored_reference_requires_a_matching_reference_review(self):
        item = base_item(
            id="LGP-BENCH-FORMAL-001",
            category="formal_luganda",
            prompt_language="lg",
            response_language="lg",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "relevance",
                "appropriate_register",
            ],
            reference_status="authored",
            reference_answer="SYNTHETIC REFERENCE",
            reviewer_notes=[
                {
                    "reviewer_id": "reviewer-1",
                    "role": "native_reviewer",
                    "date": "2026-10-20",
                    "dimension": "reference_answer",
                    "score": None,
                    "note": "Synthetic reference reviewed.",
                    "flag": "none",
                }
            ],
            review_status="native_reviewed",
        )
        evidence = evidence_for(item)
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence)
        evidence["reference_reviews"] = [reference_review(item)]
        validate_item(item, evidence=evidence)

    def test_malformed_review_evidence_is_rejected(self):
        item = base_item(review_status="native_reviewed")
        evidence = evidence_for(item)
        reviews = [review.to_dict() for review in evidence["item_reviews"]]
        del reviews[0]["date"]
        evidence["item_reviews"] = reviews
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence)

    def test_approval_evidence_requires_native_signoff(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        evidence = evidence_for(item, approve=True)
        approval = evidence["approval_record"].to_dict()
        del approval["native_review_signoff"]
        evidence["approval_record"] = approval
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence)

    def test_approved_requires_owner_record(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence_for(item))
        validate_item(item, evidence=evidence_for(item, approve=True))

    def test_pending_reference_blocks_approval(self):
        item = base_item(
            benchmark_version="1.0",
            review_status="approved",
            reference_status="pending",
            reference_answer=None,
        )
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence_for(item, approve=True))

    def test_reviewed_items_need_actual_check_notes(self):
        item = base_item(review_status="native_reviewed", contamination_notes="")
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence_for(item))
        approved = base_item(
            benchmark_version="1.0",
            review_status="approved",
            contamination_notes="Not checked",
        )
        with self.assertRaises(ValidationError):
            validate_item(approved, evidence=evidence_for(approved, approve=True))

    def test_supported_status_transitions(self):
        item = base_item(benchmark_version="1.0")
        self.assertFalse(can_transition("draft", "native_reviewed"))
        with self.assertRaises(WorkflowError):
            transition_item(item, "native_reviewed", date="2026-10-21")
        ambiguity = transition_item(
            item,
            "ambiguity_checked",
            date="2026-10-21",
            evidence={"ambiguity_checks": [ambiguity_check(item)]},
        )
        self.assertEqual(ambiguity["review_status"], "ambiguity_checked")
        native = transition_item(
            ambiguity,
            "native_reviewed",
            date="2026-10-21",
            evidence=evidence_for(item),
        )
        self.assertEqual(native["review_status"], "native_reviewed")
        approved = transition_item(
            native,
            "approved",
            date="2026-10-21",
            evidence=evidence_for(item, approve=True),
        )
        self.assertEqual(approved["review_status"], "approved")
        excluded = transition_item(
            approved,
            "excluded",
            date="2026-10-21",
            evidence={
                "exclusion_record": ExclusionRecord(
                    exclusion_id="SYN-EX-001",
                    item_id=item["id"],
                    version=item["benchmark_version"],
                    date="2026-10-21",
                    actor="Synthetic Reviewer",
                    reason="Synthetic exclusion.",
                )
            },
        )
        self.assertEqual(excluded["review_status"], "excluded")
        with self.assertRaises(WorkflowError):
            transition_item(excluded, "draft", date="2026-10-22")


class ResponseReviewTests(unittest.TestCase):
    def test_note_required_for_extreme_scores(self):
        item = base_item()
        with self.assertRaises(ValidationError):
            response_review(item, score=4)
        response_review(item, score=4, note="Synthetic reason.")
        response_review(item, score=3)

    def test_adjudicator_fields_are_consistent(self):
        item = base_item()
        record = response_review(
            item,
            reviewer_id="adjudicator-1",
            role="adjudicator",
            adjudicated_score=4,
            adjudicator_id="adjudicator-1",
            adjudication_note="Synthetic adjudication.",
        )
        self.assertEqual(record.adjudicated_score, 4)
        with self.assertRaises(ValidationError):
            response_review(
                item,
                reviewer_id="adjudicator-1",
                role="adjudicator",
                adjudicated_score=None,
                adjudicator_id="adjudicator-1",
                adjudication_note="Synthetic adjudication.",
            )

    def test_dimension_must_be_applicable(self):
        item = base_item()
        record = response_review(item, dimension="factual_reliability")
        with self.assertRaises(ValidationError):
            validate_response_review(record, item)

    def test_material_disagreement_and_adjudication(self):
        item = base_item()
        left = response_review(item, reviewer_id="reviewer-1", score=1, note="Synthetic low score.")
        right = response_review(item, reviewer_id="reviewer-2", score=5, note="Synthetic high score.")
        findings = material_disagreements([left, right])
        self.assertEqual(len(findings), 1)
        adjudication = build_adjudication(
            records=[left, right],
            review_id="SYN-ADJ-001",
            item=item,
            run_id="LGP-RUN-2026-001",
            reviewer_id="adjudicator-1",
            date="2026-10-20",
            dimension="semantic_correctness",
            adjudicated_score=5,
            note="Synthetic adjudication after disagreement.",
        )
        self.assertEqual(adjudication.role, "adjudicator")
        self.assertEqual(adjudication.adjudicated_score, 5)
        with self.assertRaises(WorkflowError):
            build_adjudication(
                records=[left],
                review_id="SYN-ADJ-002",
                item=item,
                run_id="LGP-RUN-2026-001",
                reviewer_id="adjudicator-1",
                date="2026-10-20",
                dimension="semantic_correctness",
                adjudicated_score=5,
                note="No disagreement exists.",
            )

    def test_adjudicator_must_be_a_third_reviewer(self):
        item = base_item()
        left = response_review(item, reviewer_id="reviewer-1", score=1, note="Synthetic low score.")
        right = response_review(item, reviewer_id="reviewer-2", score=5, note="Synthetic high score.")
        with self.assertRaises(WorkflowError):
            build_adjudication(
                records=[left, right],
                review_id="SYN-ADJ-003",
                item=item,
                run_id="LGP-RUN-2026-001",
                reviewer_id="reviewer-1",
                date="2026-10-20",
                dimension="semantic_correctness",
                adjudicated_score=3,
                note="Synthetic self-adjudication attempt.",
            )

    def test_agreement_report_includes_kappa(self):
        item1 = base_item()
        item2 = base_item(id="LGP-BENCH-INSTRUCTION-002")
        records = [
            response_review(item1, reviewer_id="reviewer-1", score=3),
            response_review(item1, reviewer_id="reviewer-2", score=3),
            response_review(item2, reviewer_id="reviewer-1", score=4, note="Synthetic."),
            response_review(item2, reviewer_id="reviewer-2", score=3),
        ]
        report = agreement_report(records)
        self.assertIn("semantic_correctness", report)
        dimension = report["semantic_correctness"]
        self.assertEqual(dimension["pairs"], 2)
        self.assertAlmostEqual(dimension["exact_agreement"], 0.5)
        self.assertAlmostEqual(dimension["within_one_agreement"], 1.0)
        self.assertIsNotNone(dimension["quadratic_weighted_kappa"])

    def test_agreement_report_handles_missing_scores_and_small_samples(self):
        item = base_item()
        left = response_review(item, reviewer_id="reviewer-1", score=3).to_dict()
        missing = response_review(item, reviewer_id="reviewer-2", score=3).to_dict()
        missing["score"] = None
        report = agreement_report([left, missing])
        dimension = report["semantic_correctness"]
        self.assertEqual(dimension["pairs"], 0)
        self.assertEqual(dimension["missing_pairs"], 1)
        self.assertIsNone(dimension["exact_agreement"])
        self.assertIsNone(dimension["within_one_agreement"])
        self.assertIsNone(dimension["quadratic_weighted_kappa"])

        one_reviewer = agreement_report([left])["semantic_correctness"]
        self.assertEqual(one_reviewer["pairs"], 0)
        self.assertIsNone(one_reviewer["exact_agreement"])
        self.assertIsNone(quadratic_weighted_kappa([], []))

    def test_material_disagreement_ignores_missing_scores(self):
        item = base_item()
        left = response_review(item, reviewer_id="reviewer-1", score=3).to_dict()
        left["score"] = None
        right = response_review(
            item,
            reviewer_id="reviewer-2",
            score=5,
            note="Synthetic high score.",
        )
        self.assertEqual(material_disagreements([left, right]), [])

    def test_review_packet_is_blind_and_preserves_response(self):
        item = base_item()
        packet = build_review_packet(
            item,
            raw_response(raw_response="TEST\nsecond line"),
            packet_id="SYN-PKT-001",
        )
        self.assertTrue(packet["blind"])
        self.assertEqual(packet["response"], "TEST\nsecond line")
        self.assertEqual(packet["ambiguity_notes"], item["ambiguity_notes"])
        self.assertNotIn("model_id", packet)
        self.assertNotIn("model_revision", packet)
        self.assertNotIn("run_id", packet)
        assert_blind_packet(packet)
        packet["model_id"] = "leaked/model"
        with self.assertRaises(ValidationError):
            assert_blind_packet(packet)
        leaked = {"blind": True, "model": "leaked/model"}
        with self.assertRaises(ValidationError):
            assert_blind_packet(leaked)

    def test_independent_scoring_rejects_duplicates_and_short_panels(self):
        item = base_item()
        first = response_review(item, reviewer_id="reviewer-1", score=3)
        duplicate = response_review(item, reviewer_id="reviewer-1", score=4, note="Synthetic.")
        with self.assertRaises(ValidationError):
            validate_independent_reviews([first, duplicate])
        second = response_review(item, reviewer_id="reviewer-2", score=3)
        validate_independent_reviews([first, second], minimum_reviewers=2)
        with self.assertRaises(ValidationError):
            validate_independent_reviews([first], minimum_reviewers=2)

    def test_independent_scoring_defaults_to_two_and_requires_calibration(self):
        item = base_item()
        first = response_review(item, reviewer_id="reviewer-1", score=3)
        second = response_review(item, reviewer_id="reviewer-2", score=3)
        validate_independent_reviews([first, second])
        with self.assertRaises(ValidationError):
            validate_independent_reviews([first, second], minimum_reviewers=1)
        with self.assertRaises(ValidationError):
            validate_independent_reviews([first])
        uncalibrated = response_review(
            item,
            reviewer_id="reviewer-2",
            score=3,
            calibration_completed=False,
        )
        with self.assertRaises(ValidationError):
            validate_independent_reviews([first, uncalibrated])
        malformed = first.to_dict()
        del malformed["date"]
        with self.assertRaises(ValidationError):
            validate_independent_reviews([malformed, second])
        with self.assertRaises(ValidationError):
            validate_independent_reviews([])

    def test_reference_review_hash_must_be_a_hex_digest(self):
        with self.assertRaises(ValidationError):
            ReferenceReview(
                review_id="SYN-REF-001",
                item_id="LGP-BENCH-INSTRUCTION-001",
                reviewer_id="reviewer-1",
                role="native_reviewer",
                date="2026-10-20",
                approved=True,
                note="Synthetic reference review.",
                reference_sha256="z" * 64,
            )

    def test_summary_has_no_composite_and_separates_tracks(self):
        item = base_item()
        record = response_review(item, score=3)
        summary = summarize_scores([record], {item["id"]: item})
        self.assertEqual(summary["track"], "conversational")
        self.assertNotIn("overall", summary)
        self.assertNotIn("composite", summary)
        self.assertIn("semantic_correctness", summary["dimensions"])
        self.assertEqual(summary["dimensions"]["semantic_correctness"]["applicable_items"], 1)
        self.assertEqual(summary["dimensions"]["factual_reliability"]["applicable_items"], 0)

        translation = base_item(
            id="LGP-BENCH-INSTRUCTION-002",
            track="translation_probe",
            prompt="SYNTHETIC TRANSLATION PROBE. Not benchmark content.",
        )
        translation_record = response_review(translation, score=3)
        with self.assertRaises(WorkflowError):
            summarize_scores(
                [record, translation_record],
                {item["id"]: item, translation["id"]: translation},
            )


if __name__ == "__main__":
    unittest.main()
