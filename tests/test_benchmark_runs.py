"""Evaluation-run manifest and raw-response storage tests."""

import tempfile
import unittest
from pathlib import Path

from benchmark.errors import RunError, ValidationError
from benchmark.runs import CostRecord, RawResponse, RunManifest, RunStore
from benchmark.storage import sha256_file, write_jsonl

from .benchmark_support import cost_record, raw_response, run_manifest


class RunManifestTests(unittest.TestCase):
    def test_planned_run_is_valid(self):
        manifest = run_manifest()
        self.assertEqual(manifest.run_status, "planned")
        self.assertEqual(manifest.completed_item_count, 0)

    def test_moving_model_revision_is_rejected(self):
        with self.assertRaises(ValidationError):
            run_manifest(model_revision="main")

    def test_missing_decoding_field_is_rejected(self):
        decoding = dict(run_manifest().decoding)
        del decoding["stop_sequences"]
        with self.assertRaises(ValidationError):
            run_manifest(decoding=decoding)

    def test_run_manifest_rejects_non_list_errors(self):
        value = run_manifest().to_dict()
        value["errors"] = "not a list"
        with self.assertRaises(ValidationError):
            RunManifest.from_dict(value)

    def test_completed_run_requires_finish_metadata_and_counts(self):
        with self.assertRaises(ValidationError):
            run_manifest(run_status="completed")
        run_manifest(
            run_status="completed",
            finished_at="2026-10-20T10:01:00+00:00",
            wall_clock_seconds=60.0,
            completed_item_count=1,
        )
        with self.assertRaises(ValidationError):
            run_manifest(
                run_status="completed",
                finished_at="2026-10-20T10:01:00+00:00",
                wall_clock_seconds=60.0,
                completed_item_count=0,
            )
        with self.assertRaises(ValidationError):
            run_manifest(
                run_status="completed",
                finished_at="2026-10-20T10:01:00+00:00",
                wall_clock_seconds=60.0,
                completed_item_count=1,
                expected_item_count=None,
            )

    def test_failed_run_requires_an_error(self):
        with self.assertRaises(ValidationError):
            run_manifest(run_status="failed")
        with self.assertRaises(ValidationError):
            run_manifest(
                run_status="failed",
                finished_at="2026-10-20T10:01:00+00:00",
                errors=("",),
            )
        run_manifest(
            run_status="failed",
            finished_at="2026-10-20T10:01:00+00:00",
            errors=({"message": "Synthetic failure."},),
        )

    def test_completed_run_rejects_errors(self):
        with self.assertRaises(ValidationError):
            run_manifest(
                run_status="completed",
                finished_at="2026-10-20T10:01:00+00:00",
                wall_clock_seconds=60.0,
                completed_item_count=1,
                errors=({"message": "Synthetic failure."},),
            )

    def test_adapter_metadata_must_be_complete(self):
        with self.assertRaises(ValidationError):
            run_manifest(adapter_id="synthetic-adapter")
        run_manifest(
            base_model_id="synthetic/base",
            base_model_revision="abcdef0123456789",
            adapter_id="synthetic/adapter",
            adapter_revision="0123456789abcdef",
        )

    def test_manifest_hash_changes_with_metadata(self):
        first = run_manifest()
        second = run_manifest(model_revision="abcdef0123456789")
        self.assertNotEqual(first.manifest_sha256(), second.manifest_sha256())

    def test_paid_api_cost_requires_approval_and_fields(self):
        with self.assertRaises(ValidationError):
            CostRecord(
                kind="paid_api",
                amount=1.0,
                currency="USD",
                approved_budget=2.0,
                approval_reference=None,
                details={},
            )
        record = CostRecord(
            kind="paid_api",
            amount=1.0,
            currency="USD",
            approved_budget=2.0,
            approval_reference="Synthetic approval.",
            details={
                "provider": "synthetic",
                "model": "synthetic/model",
                "input_tokens": 10,
                "output_tokens": 2,
                "unit_price": 0.01,
                "total": 1.0,
                "cap": 2.0,
            },
        )
        self.assertEqual(record.amount, 1.0)
        with self.assertRaises(ValidationError):
            CostRecord(
                kind="paid_api",
                amount=1.0,
                currency=None,
                approved_budget=2.0,
                approval_reference="Synthetic approval.",
                details={
                    "provider": "synthetic",
                    "model": "synthetic/model",
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "unit_price": 0.01,
                    "total": 1.0,
                    "cap": 2.0,
                },
            )
        with self.assertRaises(ValidationError):
            CostRecord(
                kind="native_review",
                amount=100.0,
                currency="USD",
                approved_budget=None,
                approval_reference="Synthetic approval.",
                details={"reviewer_hours": 10.0, "rate": 10.0},
            )
        value = cost_record().to_dict()
        value["unexpected"] = True
        with self.assertRaises(ValidationError):
            CostRecord.from_dict(value)


class RunStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lugandagpt-runs-")
        self.root = Path(self.tmp.name)
        self.store = RunStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_id_cannot_be_reused(self):
        self.store.create_manifest(run_manifest())
        with self.assertRaises(RunError):
            self.store.create_manifest(run_manifest())

    def test_raw_response_is_preserved_verbatim(self):
        self.store.write_manifest(run_manifest())
        original = "TEST\nline two with Unicode: \u00e9"
        response = raw_response(raw_response=original)
        self.store.append_raw_response(response)
        stored = self.store.read_raw_responses("LGP-RUN-2026-001")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].raw_response, original)

    def test_raw_response_revision_must_match_manifest(self):
        self.store.write_manifest(run_manifest())
        with self.assertRaises(RunError):
            self.store.append_raw_response(
                raw_response(model_revision="abcdef0123456789")
            )

    def test_finalize_marks_incomplete_run(self):
        self.store.write_manifest(run_manifest(expected_item_count=2))
        self.store.append_raw_response(raw_response())
        manifest = self.store.finalize(
            "LGP-RUN-2026-001",
            expected_item_count=2,
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "incomplete")
        self.assertEqual(manifest.completed_item_count, 1)

    def test_finalize_without_responses_is_incomplete(self):
        self.store.write_manifest(run_manifest(expected_item_count=1))
        manifest = self.store.finalize(
            "LGP-RUN-2026-001",
            expected_item_count=1,
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "incomplete")
        self.assertEqual(manifest.completed_item_count, 0)
        self.assertFalse(manifest.errors)

    def test_finalize_marks_completed_run(self):
        self.store.write_manifest(run_manifest(expected_item_count=1))
        self.store.append_raw_response(raw_response())
        manifest = self.store.finalize(
            "LGP-RUN-2026-001",
            expected_item_count=1,
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "completed")
        self.assertEqual(manifest.completed_item_count, 1)
        self.assertEqual(manifest.wall_clock_seconds, 60.0)

    def test_finalized_run_cannot_accept_more_raw_responses(self):
        self.store.write_manifest(run_manifest(expected_item_count=1))
        self.store.append_raw_response(raw_response())
        self.store.finalize(
            "LGP-RUN-2026-001",
            expected_item_count=1,
            finished_at="2026-10-20T10:01:00+00:00",
        )
        with self.assertRaises(RunError):
            self.store.append_raw_response(raw_response(sample_index=1))
        with self.assertRaises(RunError):
            self.store.finalize(
                "LGP-RUN-2026-001",
                expected_item_count=1,
                finished_at="2026-10-20T10:02:00+00:00",
            )

    def test_cost_ledger_records_multiple_cost_types(self):
        self.store.write_manifest(run_manifest())
        self.store.append_cost("LGP-RUN-2026-001", cost_record())
        native = CostRecord(
            kind="native_review",
            amount=100.0,
            currency="USD",
            approved_budget=200.0,
            approval_reference="Synthetic approval.",
            details={"reviewer_hours": 10.0, "rate": 10.0},
        )
        self.store.append_cost("LGP-RUN-2026-001", native)
        costs = self.store.read_costs("LGP-RUN-2026-001")
        self.assertEqual([cost.kind for cost in costs], ["local_compute", "native_review"])

    def test_response_error_marks_run_failed(self):
        self.store.write_manifest(run_manifest(expected_item_count=1))
        self.store.append_raw_response(
            raw_response(error={"message": "Synthetic runtime error."})
        )
        manifest = self.store.finalize(
            "LGP-RUN-2026-001",
            expected_item_count=1,
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "failed")
        self.assertEqual(manifest.completed_item_count, 0)
        self.assertTrue(manifest.errors)

    def test_failed_run_is_recorded(self):
        self.store.write_manifest(run_manifest())
        self.store.append_raw_response(raw_response())
        manifest = self.store.mark_failed(
            "LGP-RUN-2026-001",
            {"message": "Synthetic inference error."},
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "failed")
        self.assertTrue(manifest.errors)
        self.assertEqual(manifest.completed_item_count, 1)
        self.assertEqual(manifest.wall_clock_seconds, 60.0)

    def test_incomplete_run_records_reason_and_finish_metadata(self):
        self.store.write_manifest(run_manifest(expected_item_count=2))
        self.store.append_raw_response(raw_response())
        manifest = self.store.mark_incomplete(
            "LGP-RUN-2026-001",
            "Synthetic missing item.",
            finished_at="2026-10-20T10:01:00+00:00",
        )
        self.assertEqual(manifest.run_status, "incomplete")
        self.assertEqual(manifest.completed_item_count, 1)
        self.assertEqual(manifest.wall_clock_seconds, 60.0)
        self.assertEqual(manifest.exclusions[0]["reason"], "Synthetic missing item.")
        with self.assertRaises(ValidationError):
            run_manifest(run_status="excluded")

    def test_reproducibility_checks_item_hash(self):
        item_path = self.root / "items.jsonl"
        item_path.write_text("synthetic item file\n", encoding="utf-8")
        manifest = run_manifest(item_file_sha256=sha256_file(item_path))
        self.assertTrue(self.store.verify_reproducibility(manifest, item_path))
        bad = run_manifest(item_file_sha256="b" * 64)
        with self.assertRaises(RunError):
            self.store.verify_reproducibility(bad, item_path)

    def test_reproducibility_checks_raw_response_model_revision(self):
        item_path = self.root / "items.jsonl"
        item_path.write_text("synthetic item file\n", encoding="utf-8")
        digest = sha256_file(item_path)
        manifest = run_manifest(
            item_file_sha256=digest,
            model_revision="0123456789abcdef",
        )
        write_jsonl(
            self.store.raw_path(manifest.run_id),
            [
                raw_response(
                    model_revision="0123456789abcdef",
                ).to_dict()
            ],
        )
        mismatched = run_manifest(
            item_file_sha256=digest,
            model_revision="fedcba9876543210",
        )
        with self.assertRaises(RunError):
            self.store.verify_reproducibility(mismatched, item_path)

    def test_raw_response_rejects_moving_revision(self):
        with self.assertRaises(ValidationError):
            raw_response(model_revision="latest")
        with self.assertRaises(ValidationError):
            raw_response(error="")

    def test_raw_response_token_counts_are_integers(self):
        with self.assertRaises(ValidationError):
            raw_response(prompt_tokens=1.5)


if __name__ == "__main__":
    unittest.main()
