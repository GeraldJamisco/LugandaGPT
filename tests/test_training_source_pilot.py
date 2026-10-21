"""Tests for the English source draft and translator export."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from training.cli import main
from training.errors import DataError
from training.source_pilot import (
    SOURCE_CAPABILITY_COUNTS,
    SOURCE_EVALUATION_CAPABILITY_COUNTS,
    SOURCE_PILOT_TOTAL,
    SOURCE_SPLIT_COUNTS,
    load_source_draft,
    validate_source_dataset,
    validate_source_exports,
    write_source_exports,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DRAFT = PROJECT_ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"
SOURCE_DIR = SOURCE_DRAFT.parent
AS_OF = date(2026, 10, 21)


class SourceDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded = load_source_draft(SOURCE_DRAFT, as_of=AS_OF)

    def test_exact_counts_and_capabilities(self):
        self.assertEqual(len(self.loaded["pilot"]), SOURCE_PILOT_TOTAL)
        self.assertEqual(len(self.loaded["evaluation"]), 24)
        self.assertEqual(
            self.loaded["summary"]["capability_counts"],
            SOURCE_CAPABILITY_COUNTS,
        )
        self.assertEqual(
            self.loaded["summary"]["evaluation_capability_counts"],
            SOURCE_EVALUATION_CAPABILITY_COUNTS,
        )

    def test_split_counts_are_exact(self):
        self.assertEqual(
            self.loaded["summary"]["pilot_split_counts"],
            SOURCE_SPLIT_COUNTS,
        )

    def test_composition_minimums(self):
        summary = self.loaded["summary"]
        self.assertGreaterEqual(summary["multi_sentence"], 30)
        self.assertGreaterEqual(summary["uncertainty_cases"], 12)
        self.assertGreaterEqual(summary["constraint_examples"], 10)
        self.assertGreaterEqual(summary["prior_context_conversations"], 8)

    def test_all_statuses_are_pending(self):
        for record in self.loaded["pilot"] + self.loaded["evaluation"]:
            self.assertEqual(record["translation_status"], "pending")
            self.assertEqual(record["native_review_status"], "pending")
            self.assertEqual(record["source_language"], "en")
        self.assertFalse(self.loaded["summary"]["training_authorized"])

    def test_evaluation_items_have_no_split_and_separate_ids(self):
        evaluation_ids = {record["item_id"] for record in self.loaded["evaluation"]}
        pilot_ids = {record["item_id"] for record in self.loaded["pilot"]}
        self.assertFalse(evaluation_ids & pilot_ids)
        for record in self.loaded["evaluation"]:
            self.assertIsNone(record["proposed_split"])

    def test_owner_confirmation_is_not_a_signed_agreement(self):
        confirmation = self.loaded["data"]["owner_confirmation"]
        self.assertIn("available", confirmation["statement"].casefold())
        self.assertIn("not documented", confirmation["formal_agreements"].casefold())
        self.assertIn("no signed", confirmation["formal_agreements"].casefold())

    def test_exports_validate(self):
        result = validate_source_exports(self.loaded, SOURCE_DIR)
        self.assertEqual(result["status"], "source_exports_valid")
        self.assertEqual(result["pilot_count"], 100)
        self.assertEqual(result["evaluation_count"], 24)
        self.assertEqual(result["translator_rows"], 124)
        self.assertFalse(result["training_authorized"])

    def test_translator_csv_distinguishes_english_and_luganda(self):
        import csv

        with (SOURCE_DIR / "translator_export.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 124)
        self.assertIn("source_prompt_en", rows[0])
        self.assertIn("source_context_lg", rows[0])
        self.assertIn("source_prompt_lg", rows[0])
        self.assertIn("final_assistant_response_lg", rows[0])
        for row in rows:
            self.assertEqual(row["translation_status"], "pending")
            self.assertEqual(row["native_review_status"], "pending")
            self.assertEqual(row["source_prompt_lg"], "")
            self.assertEqual(row["source_context_lg"], "")
            self.assertEqual(row["final_assistant_response_lg"], "")
            self.assertEqual(row["reviewer_id"], "")

    def test_manifest_is_not_training_authorization(self):
        manifest = json.loads(
            (SOURCE_DIR / "source_manifest.json").read_text(encoding="utf-8")
        )
        self.assertFalse(manifest["training_authorized"])
        self.assertEqual(manifest["pilot_count"], 100)
        self.assertEqual(manifest["evaluation_count"], 24)
        self.assertEqual(manifest["translation_status_counts"], {"pending": 124})
        self.assertEqual(manifest["native_review_status_counts"], {"pending": 124})

    def test_approved_translation_status_is_rejected_in_source_draft(self):
        data = copy.deepcopy(self.loaded["data"])
        data["pilot"][0]["translation_status"] = "approved"
        with self.assertRaises(DataError):
            validate_source_dataset(data, as_of=AS_OF)

    def test_evaluation_split_is_rejected(self):
        data = copy.deepcopy(self.loaded["data"])
        data["evaluation"][0]["proposed_split"] = "train"
        with self.assertRaises(DataError):
            validate_source_dataset(data, as_of=AS_OF)

    def test_duplicate_item_id_is_rejected(self):
        data = copy.deepcopy(self.loaded["data"])
        data["evaluation"][0]["item_id"] = data["pilot"][0]["item_id"]
        with self.assertRaises(DataError):
            validate_source_dataset(data, as_of=AS_OF)

    def test_duplicate_prompt_is_rejected(self):
        data = copy.deepcopy(self.loaded["data"])
        data["pilot"][1]["source_prompt"] = data["pilot"][0]["source_prompt"]
        with self.assertRaises(DataError):
            validate_source_dataset(data, as_of=AS_OF)

    def test_unknown_field_is_rejected(self):
        data = copy.deepcopy(self.loaded["data"])
        data["pilot"][0]["unreviewed_answer"] = "not allowed"
        with self.assertRaises(DataError):
            validate_source_dataset(data, as_of=AS_OF)

    def test_tampered_export_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-source-") as temporary:
            output = Path(temporary) / "source"
            write_source_exports(self.loaded, output)
            csv_path = output / "translator_export.csv"
            text = csv_path.read_text(encoding="utf-8")
            csv_path.write_text(
                text.replace(",pending,", ",approved,", 1), encoding="utf-8"
            )
            with self.assertRaises(DataError):
                validate_source_exports(self.loaded, output)


class SourceCliTests(unittest.TestCase):
    def _call(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validate_source_command(self):
        code, output, error = self._call(["validate-source", str(SOURCE_DRAFT)])
        self.assertEqual(code, 0, error)
        value = json.loads(output)
        self.assertEqual(value["status"], "source_draft_valid")
        self.assertEqual(value["pilot_count"], 100)
        self.assertEqual(value["evaluation_count"], 24)
        self.assertFalse(value["training_authorized"])

    def test_export_source_command(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-source-") as temporary:
            output = Path(temporary) / "export"
            code, printed, error = self._call(
                [
                    "export-source",
                    str(SOURCE_DRAFT),
                    "--output-dir",
                    str(output),
                ]
            )
            self.assertEqual(code, 0, error)
            value = json.loads(printed)
            self.assertEqual(value["status"], "source_exports_written")
            self.assertEqual(value["pilot_count"], 100)
            self.assertEqual(value["evaluation_count"], 24)
            self.assertFalse(value["training_authorized"])
            self.assertTrue((output / "pilot_en.jsonl").is_file())
            self.assertTrue((output / "evaluation_en.jsonl").is_file())
            self.assertTrue((output / "translator_export.csv").is_file())
            self.assertTrue((output / "source_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
