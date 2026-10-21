"""Pilot and evaluation schema tests."""

import unittest

from training.constants import CAPABILITY_COUNTS, VALIDATION_CHECKS
from training.errors import DataError
from training.pilot import (
    validate_audit_coverage,
    validate_collection,
    validate_evaluation_collection,
    validate_evaluation_record,
    validate_pilot_record,
)

from .training_support import (
    AS_OF,
    make_evaluation_records,
    make_pilot_splits,
    valid_evaluation_record,
    valid_pilot_record,
)


class PilotRecordTests(unittest.TestCase):
    def test_valid_record(self):
        record = valid_pilot_record()
        validated = validate_pilot_record(record, expected_split="train", as_of=AS_OF)
        self.assertEqual(validated["pilot_id"], "P-001")

    def test_missing_field_rejected(self):
        record = valid_pilot_record()
        del record["source_notes"]
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_unknown_field_rejected(self):
        record = valid_pilot_record()
        record["answer"] = "no"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_wrong_split_rejected(self):
        record = valid_pilot_record(split="validation")
        with self.assertRaises(DataError):
            validate_pilot_record(record, expected_split="train", as_of=AS_OF)

    def test_roles_must_alternate(self):
        record = valid_pilot_record()
        record["messages"][1]["role"] = "user"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_placeholder_content_rejected(self):
        record = valid_pilot_record()
        record["messages"][0]["content"] = "<Luganda prompt>"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_uncertainty_value_is_controlled(self):
        record = valid_pilot_record()
        record["expected_response"]["uncertainty_behavior"] = "maybe"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_reference_required_for_determinate_task(self):
        record = valid_pilot_record(capability="question_answering")
        record["reference_status"] = "not_required"
        record["reference_answer"] = None
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_draft_allows_incomplete_validation_but_not_bad_types(self):
        record = valid_pilot_record()
        record["validation"] = {name: False for name in VALIDATION_CHECKS}
        record["review_status"] = "draft"
        validate_pilot_record(record, require_trainable=False, as_of=AS_OF)
        with self.assertRaises(DataError):
            validate_pilot_record(record, require_trainable=True, as_of=AS_OF)

    def test_unresolved_licence_blocks_training(self):
        record = valid_pilot_record()
        record["licence"] = "pending"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)
        validate_pilot_record(record, require_trainable=False, as_of=AS_OF)

    def test_pii_review_blocks_training(self):
        record = valid_pilot_record()
        record["pii_check"] = "needs_review"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_author_cannot_be_reviewer(self):
        record = valid_pilot_record()
        record["reviewers"][0]["reviewer_id"] = "T-001"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_future_review_rejected(self):
        record = valid_pilot_record()
        record["reviewers"][0]["date"] = "2026-10-22"
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)

    def test_short_conversation_requires_follow_up(self):
        record = valid_pilot_record(capability="short_conversation")
        record["messages"] = record["messages"][:2]
        with self.assertRaises(DataError):
            validate_pilot_record(record, as_of=AS_OF)


class CollectionTests(unittest.TestCase):
    def test_synthetic_composition(self):
        splits = make_pilot_splits()
        self.assertEqual(len(splits["train"]), 70)
        self.assertEqual(len(splits["validation"]), 15)
        self.assertEqual(len(splits["heldout"]), 15)
        combined = splits["train"] + splits["validation"] + splits["heldout"]
        validated, counts, ids = validate_collection(
            combined, require_complete=True, require_approved=True, as_of=AS_OF
        )
        self.assertEqual(len(validated), 100)
        self.assertEqual(len(ids), 100)
        self.assertEqual(counts, CAPABILITY_COUNTS)
        coverage = validate_audit_coverage(splits["train"])
        self.assertEqual(coverage, {"required": 7, "covered": 7})

    def test_duplicate_id_rejected(self):
        records = [valid_pilot_record("P-001", split="train")]
        records.append(valid_pilot_record("P-001", split="train"))
        with self.assertRaises(DataError):
            validate_collection(
                records,
                expected_split="train",
                require_complete=False,
                as_of=AS_OF,
            )

    def test_audit_coverage_shortfall_rejected(self):
        splits = make_pilot_splits()
        for record in splits["train"][:7]:
            record["reviewers"] = [
                review for review in record["reviewers"] if review["role"] != "audit"
            ]
        with self.assertRaises(DataError):
            validate_audit_coverage(splits["train"])

    def test_capability_counts_must_match(self):
        records = [
            valid_pilot_record(
                f"P-{index + 1:03d}",
                capability="formal_comprehension",
                split="train",
            )
            for index in range(100)
        ]
        with self.assertRaises(DataError):
            validate_collection(
                records, require_complete=True, require_approved=False, as_of=AS_OF
            )


class EvaluationRecordTests(unittest.TestCase):
    def test_valid_evaluation_record(self):
        record = valid_evaluation_record()
        validated = validate_evaluation_record(record, as_of=AS_OF)
        self.assertEqual(validated["eval_id"], "E-001")

    def test_two_reviewers_required(self):
        record = valid_evaluation_record()
        record["reviewers"] = record["reviewers"][:1]
        with self.assertRaises(DataError):
            validate_evaluation_record(record, as_of=AS_OF)

    def test_evaluation_cannot_carry_pilot_split(self):
        record = valid_evaluation_record()
        record["split"] = "train"
        with self.assertRaises(DataError):
            validate_evaluation_record(record, as_of=AS_OF)

    def test_synthetic_evaluation_set_composition(self):
        records = make_evaluation_records()
        validated, counts, ids = validate_evaluation_collection(
            records, require_complete=True, require_approved=True, as_of=AS_OF
        )
        self.assertEqual(len(validated), 24)
        self.assertEqual(len(ids), 24)
        self.assertTrue(all(count == 4 for count in counts.values()))


if __name__ == "__main__":
    unittest.main()
