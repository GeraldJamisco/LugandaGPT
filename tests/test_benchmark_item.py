"""Item schema tests: strict fields, stable IDs, versions, and evidence."""

import tempfile
import unittest
from pathlib import Path

from benchmark.errors import ValidationError
from benchmark.item import category_counts, validate_item, validate_item_set
from benchmark.storage import read_jsonl, write_jsonl

from .benchmark_support import ambiguity_check, base_item, evidence_for, source_exception


class ItemValidationTests(unittest.TestCase):
    def test_valid_draft_item(self):
        record = validate_item(base_item())
        self.assertEqual(record["id"], "LGP-BENCH-INSTRUCTION-001")

    def test_missing_required_field_is_rejected(self):
        item = base_item()
        del item["prompt"]
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_unknown_field_is_rejected(self):
        item = base_item(synthetic=True)
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_id_prefix_must_match_category(self):
        item = base_item(id="LGP-BENCH-COLLOQUIAL-001")
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_id_number_must_start_at_one(self):
        item = base_item(id="LGP-BENCH-INSTRUCTION-000")
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_duplicate_ids_are_rejected(self):
        items = [base_item(), base_item()]
        with self.assertRaises(ValidationError):
            validate_item_set(items)

    def test_version_mismatch_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_item(base_item(), expected_version="0.2-draft")

    def test_bad_version_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_item(base_item(benchmark_version="1.0-draft"))

    def test_zero_major_version_is_not_an_approved_version(self):
        with self.assertRaises(ValidationError):
            validate_item(base_item(benchmark_version="0.1"))

    def test_approved_item_cannot_use_a_draft_version(self):
        with self.assertRaises(ValidationError):
            validate_item(base_item(review_status="approved"))

    def test_mixed_tracks_cannot_share_an_item_file(self):
        conversational = base_item()
        translation = base_item(
            id="LGP-BENCH-INSTRUCTION-002",
            track="translation_probe",
        )
        with self.assertRaises(ValidationError):
            validate_item_set([conversational, translation])

    def test_synthetic_fixture_cannot_be_approved_without_real_resolution(self):
        fixture = Path(__file__).parent / "fixtures" / "benchmark" / "synthetic_items.jsonl"
        item = read_jsonl(fixture)[0]
        item["benchmark_version"] = "1.0"
        item["review_status"] = "approved"
        with self.assertRaises(ValidationError):
            validate_item(item, evidence=evidence_for(item, approve=True))

    def test_single_turn_items_require_empty_turns(self):
        item = base_item(turns=[{"role": "user", "content": "again"}])
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_multi_turn_requires_a_user_follow_up(self):
        item = base_item(
            id="LGP-BENCH-MULTITURN-001",
            category="multi_turn",
            prompt_language="lg",
            response_language="lg",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "instruction_compliance",
                "relevance",
                "context_retention",
            ],
            turns=[{"role": "assistant", "content": "first answer"}],
        )
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["turns"].append({"role": "user", "content": "follow-up"})
        validate_item(item)

    def test_category_language_rules(self):
        formal = base_item(
            id="LGP-BENCH-FORMAL-001",
            category="formal_luganda",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "relevance",
                "appropriate_register",
            ],
        )
        with self.assertRaises(ValidationError):
            validate_item(formal)
        formal["prompt_language"] = "lg"
        formal["response_language"] = "lg"
        validate_item(formal)

        code_switch = base_item(
            id="LGP-BENCH-CODESWITCH-001",
            category="code_switching",
            prompt_language="lg",
            response_language="lg-en",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "instruction_compliance",
                "relevance",
                "appropriate_register",
            ],
        )
        with self.assertRaises(ValidationError):
            validate_item(code_switch)
        code_switch["prompt_language"] = "lg-en"
        validate_item(code_switch)

        explanation = base_item(
            id="LGP-BENCH-EXPLANATION-001",
            category="explanation_reasoning",
            prompt_language="lg-en",
            response_language="model_choice",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "relevance",
                "factual_reliability",
            ],
        )
        with self.assertRaises(ValidationError):
            validate_item(explanation)
        explanation["response_language"] = "lg-en"
        validate_item(explanation)

        instruction = base_item(
            prompt_language="lg",
            response_language="en",
        )
        validate_item(instruction)

    def test_translation_track_is_not_bound_to_conversational_language_rules(self):
        item = base_item(
            track="translation_probe",
            prompt_language="en",
            response_language="lg",
        )
        validate_item(item)

    def test_missing_required_dimension_is_rejected(self):
        item = base_item(
            scoring_dimensions=["semantic_correctness", "grammar_naturalness", "relevance"]
        )
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_factual_dimension_is_rejected_for_instruction_item(self):
        item = base_item(
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "instruction_compliance",
                "relevance",
                "factual_reliability",
            ]
        )
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_multi_turn_requires_context_dimension(self):
        item = base_item(
            id="LGP-BENCH-MULTITURN-001",
            category="multi_turn",
            prompt_language="lg",
            response_language="lg",
            scoring_dimensions=[
                "semantic_correctness",
                "grammar_naturalness",
                "instruction_compliance",
                "relevance",
            ],
            turns=[{"role": "user", "content": "follow-up"}],
        )
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_authored_reference_requires_native_note(self):
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
        )
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["reviewer_notes"] = [
            {
                "reviewer_id": "reviewer-1",
                "role": "native_reviewer",
                "date": "2026-10-20",
                "dimension": "reference_answer",
                "score": None,
                "note": "Synthetic reference reviewed.",
                "flag": "none",
            }
        ]
        validate_item(item)

    def test_not_applicable_reference_requires_ambiguity_note(self):
        item = base_item(reference_status="not_applicable", ambiguity_notes="")
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["ambiguity_notes"] = "Synthetic reason for not having a reference."
        validate_item(item)

    def test_non_original_source_requires_url_and_licence(self):
        item = base_item(
            source={
                "type": "other",
                "url": None,
                "licence": None,
                "inspiration": "Synthetic source.",
            }
        )
        with self.assertRaises(ValidationError):
            validate_item(item)
        validate_item(item, source_exception=source_exception(item))

    def test_original_source_must_not_claim_url_or_licence(self):
        item = base_item(
            source={
                "type": "original",
                "url": "https://example.invalid",
                "licence": "CC0",
                "inspiration": None,
            }
        )
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_cultural_item_requires_cultural_note(self):
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
        )
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["cultural_note"] = "Synthetic cultural note for tests."
        validate_item(item)

    def test_placeholder_prompt_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_item(base_item(prompt="<prompt text>"))

    def test_reviewer_note_fields_and_scores_are_strict(self):
        item = base_item()
        item["reviewer_notes"] = [
            {
                "reviewer_id": "reviewer-1",
                "role": "native_reviewer",
                "date": "2026-10-20",
                "dimension": "semantic_correctness",
                "score": 3,
                "note": "Synthetic note.",
                "flag": "none",
                "extra": "not allowed",
            }
        ]
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["reviewer_notes"][0].pop("extra")
        item["reviewer_notes"][0]["score"] = 6
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_reviewer_note_dimension_must_be_applicable(self):
        item = base_item()
        item["reviewer_notes"] = [
            {
                "reviewer_id": "reviewer-1",
                "role": "native_reviewer",
                "date": "2026-10-20",
                "dimension": "factual_reliability",
                "score": 3,
                "note": "Synthetic note.",
                "flag": "none",
            }
        ]
        with self.assertRaises(ValidationError):
            validate_item(item)

    def test_accepted_alternative_requires_attribution(self):
        item = base_item(accepted_alternatives=["TEST ALT"])
        with self.assertRaises(ValidationError):
            validate_item(item)
        item["reviewer_notes"] = [
            {
                "reviewer_id": "reviewer-1",
                "role": "native_reviewer",
                "date": "2026-10-20",
                "dimension": "semantic_correctness",
                "score": 3,
                "note": "Accepted alternative: TEST ALT",
                "flag": "none",
            }
        ]
        validate_item(item)

    def test_review_metadata_round_trips_without_loss(self):
        item = base_item(
            review_status="ambiguity_checked",
            ambiguity_notes="Synthetic ambiguity check completed.",
            contamination_notes="Synthetic contamination check completed.",
            reviewer_notes=[
                {
                    "reviewer_id": "reviewer-1",
                    "role": "native_reviewer",
                    "date": "2026-10-20",
                    "dimension": "semantic_correctness",
                    "score": 3,
                    "note": "Synthetic reviewer note.",
                    "flag": "none",
                }
            ],
        )
        evidence = {"ambiguity_checks": [ambiguity_check(item)]}
        validated = validate_item(item, evidence=evidence)
        with tempfile.TemporaryDirectory(prefix="lugandagpt-item-") as temporary:
            path = Path(temporary) / "items.jsonl"
            write_jsonl(path, [validated])
            loaded = read_jsonl(path)
        self.assertEqual(loaded, [validated])
        validate_item(loaded[0], evidence=evidence)

    def test_category_counts(self):
        items = [
            base_item(),
            base_item(id="LGP-BENCH-INSTRUCTION-002", prompt="Another synthetic item."),
        ]
        counts = category_counts(items)
        self.assertEqual(counts["instruction_following"], 2)
        self.assertEqual(counts["formal_luganda"], 0)


if __name__ == "__main__":
    unittest.main()
