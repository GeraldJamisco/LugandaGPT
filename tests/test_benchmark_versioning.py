"""Versioning, exclusion, and approval tests."""

import tempfile
import unittest
from pathlib import Path

from benchmark.errors import ApprovalError, ValidationError, WorkflowError
from benchmark.item import validate_item
from benchmark.storage import sha256_file, write_json, write_jsonl
from benchmark.versioning import (
    EDITORIAL,
    MAJOR,
    MINOR,
    ApprovalRecord,
    BenchmarkManifest,
    ExclusionRecord,
    NativeReviewSignoff,
    SourceException,
    assert_version_change_allowed,
    build_manifest,
    check_version_update,
    classify_change,
    compare_versions,
    hash_items,
    load_approved_benchmark,
    next_version,
    read_manifest,
    write_item_file,
    write_manifest,
)

from .benchmark_support import approval_for, base_item, evidence_for


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lugandagpt-benchmark-")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_draft_manifest_hash_matches_item_file(self):
        item = base_item()
        path = self.root / "items.jsonl"
        actual = write_item_file(path, [item], expected_version="0.1-draft")
        manifest = build_manifest(
            [item],
            version="0.1-draft",
            date="2026-10-20",
            changelog="Synthetic draft.",
        )
        self.assertEqual(manifest.item_file_sha256, actual)
        self.assertEqual(manifest.item_file_sha256, sha256_file(path))
        write_manifest(self.root / "manifest.json", manifest)
        self.assertEqual(read_manifest(self.root / "manifest.json").version, "0.1-draft")

    def test_approved_manifest_cannot_use_a_draft_version(self):
        item = base_item()
        with self.assertRaises(ApprovalError):
            BenchmarkManifest(
                version="0.1-draft",
                date="2026-10-20",
                changelog="Synthetic approval attempt.",
                item_file_sha256=hash_items([item]),
                status="approved",
                approval=approval_for([item], "1.0"),
            )

    def test_draft_manifest_rejects_approval(self):
        item = base_item()
        with self.assertRaises(ApprovalError):
            build_manifest(
                [item],
                version="0.1-draft",
                date="2026-10-20",
                changelog="Synthetic draft.",
                status="draft",
                approval=approval_for([item], "1.0"),
            )

    def test_source_exception_is_available_to_manifest_validation(self):
        item = base_item(
            source={
                "type": "other",
                "url": None,
                "licence": None,
                "inspiration": "Synthetic source-derived item.",
            }
        )
        exception = SourceException(
            item_id=item["id"],
            approved_by="Synthetic Project Owner",
            role="project_owner",
            date="2026-10-20",
            reason="Synthetic source exception for tests.",
        )
        with self.assertRaises(ValidationError):
            build_manifest(
                [item],
                version="0.1-draft",
                date="2026-10-20",
                changelog="Synthetic draft.",
            )
        manifest = build_manifest(
            [item],
            version="0.1-draft",
            date="2026-10-20",
            changelog="Synthetic draft.",
            source_exceptions={item["id"]: exception},
        )
        self.assertEqual(manifest.status, "draft")

    def test_draft_manifest_requires_a_draft_version(self):
        item = base_item()
        with self.assertRaises(ValidationError):
            BenchmarkManifest(
                version="1.0",
                date="2026-10-20",
                changelog="Synthetic draft.",
                item_file_sha256=hash_items([item]),
                status="draft",
            )

    def test_approved_manifest_requires_approved_items(self):
        item = base_item(benchmark_version="1.0", review_status="draft")
        with self.assertRaises(ApprovalError):
            build_manifest(
                [item],
                version="1.0",
                date="2026-10-20",
                changelog="Synthetic approval attempt.",
                status="approved",
                approval=approval_for([item], "1.0"),
            )

    def test_approved_manifest_round_trip(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        items = [item]
        evidence = {item["id"]: evidence_for(item, approve=True)}
        path = self.root / "items.jsonl"
        write_item_file(path, items, expected_version="1.0", evidence_by_id=evidence)
        manifest = build_manifest(
            items,
            version="1.0",
            date="2026-10-20",
            changelog="Synthetic approved benchmark.",
            status="approved",
            approval=approval_for(items, "1.0"),
            evidence_by_id=evidence,
        )
        write_manifest(self.root / "manifest.json", manifest)
        result = load_approved_benchmark(
            path, self.root / "manifest.json", evidence_by_id=evidence
        )
        self.assertEqual(result["manifest"].status, "approved")
        self.assertEqual(len(result["items"]), 1)

    def test_manifest_rejects_malformed_approval_lists(self):
        item = base_item(benchmark_version="1.0")
        manifest = BenchmarkManifest(
            version="1.0",
            date="2026-10-20",
            changelog="Synthetic approved benchmark.",
            item_file_sha256=hash_items([item]),
            status="approved",
            approval=approval_for([item], "1.0"),
        )
        value = manifest.to_dict()
        value["approval"]["native_review_signoff"]["reviewer_panel"] = "ab"
        path = self.root / "manifest.json"
        write_json(path, value)
        with self.assertRaises(ValidationError):
            read_manifest(path)

    def test_tampered_item_file_fails_approval_load(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        evidence = {item["id"]: evidence_for(item, approve=True)}
        path = self.root / "items.jsonl"
        write_item_file(path, [item], expected_version="1.0", evidence_by_id=evidence)
        manifest = build_manifest(
            [item],
            version="1.0",
            date="2026-10-20",
            changelog="Synthetic approved benchmark.",
            status="approved",
            approval=approval_for([item], "1.0"),
            evidence_by_id=evidence,
        )
        write_manifest(self.root / "manifest.json", manifest)
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(ApprovalError):
            load_approved_benchmark(path, self.root / "manifest.json", evidence_by_id=evidence)

    def test_approval_hash_mismatch_is_rejected(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        evidence = {item["id"]: evidence_for(item, approve=True)}
        approval = approval_for([item], "1.0")
        bad = ApprovalRecord(
            specification_version=approval.specification_version,
            benchmark_version=approval.benchmark_version,
            approved_by=approval.approved_by,
            role=approval.role,
            date=approval.date,
            scope=approval.scope,
            conditions=approval.conditions,
            item_file_sha256="b" * 64,
            item_ids=approval.item_ids,
            native_review_signoff=approval.native_review_signoff,
        )
        with self.assertRaises(ApprovalError):
            build_manifest(
                [item],
                version="1.0",
                date="2026-10-20",
                changelog="Synthetic approval.",
                status="approved",
                approval=bad,
                evidence_by_id=evidence,
            )

    def test_approval_must_list_every_item(self):
        first = base_item(benchmark_version="1.0", review_status="approved")
        second = base_item(
            id="LGP-BENCH-INSTRUCTION-002",
            benchmark_version="1.0",
            review_status="approved",
        )
        items = [first, second]
        evidence = {
            first["id"]: evidence_for(first, approve=True),
            second["id"]: evidence_for(second, approve=True),
        }
        base_approval = approval_for(items, "1.0")
        narrow = ApprovalRecord(
            specification_version=base_approval.specification_version,
            benchmark_version=base_approval.benchmark_version,
            approved_by=base_approval.approved_by,
            role=base_approval.role,
            date=base_approval.date,
            scope=base_approval.scope,
            conditions=base_approval.conditions,
            item_file_sha256=hash_items(items),
            item_ids=(first["id"],),
            native_review_signoff=NativeReviewSignoff(
                reviewer_panel=("reviewer-1", "reviewer-2"),
                calibration_date="2026-10-20",
                agreement_statistic="synthetic",
                items_reviewed=(first["id"],),
                signoff_date="2026-10-20",
            ),
        )
        with self.assertRaises(ApprovalError):
            build_manifest(
                items,
                version="1.0",
                date="2026-10-20",
                changelog="Synthetic approval.",
                status="approved",
                approval=narrow,
                evidence_by_id=evidence,
            )


class ExclusionTests(unittest.TestCase):
    def test_exclusion_requires_a_reason(self):
        with self.assertRaises(ValidationError):
            ExclusionRecord(
                exclusion_id="EX-001",
                item_id="LGP-BENCH-INSTRUCTION-001",
                version="0.1-draft",
                date="2026-10-20",
                actor="Synthetic Reviewer",
                reason="",
            )

    def test_excluded_item_needs_a_record(self):
        item = base_item(review_status="excluded")
        with self.assertRaises(ValidationError):
            validate_item(item)
        record = ExclusionRecord(
            exclusion_id="EX-001",
            item_id=item["id"],
            version=item["benchmark_version"],
            date="2026-10-20",
            actor="Synthetic Reviewer",
            reason="Synthetic exclusion reason.",
        )
        validate_item(item, evidence={"exclusion_record": record})

    def test_exclusion_record_needs_identity_version_actor_and_date(self):
        item = base_item(review_status="excluded")
        with self.assertRaises(ValidationError):
            validate_item(
                item,
                evidence={
                    "exclusion_record": {
                        "item_id": item["id"],
                        "reason": "Synthetic exclusion reason.",
                    }
                },
            )


class VersionChangeTests(unittest.TestCase):
    def test_compare_and_classify(self):
        old = [base_item()]
        new = [base_item(prompt="SYNTHETIC TEST DATA. A changed prompt.")]
        diff = compare_versions(old, new)
        self.assertEqual(diff["changed"], [old[0]["id"]])
        self.assertEqual(classify_change(old, new), MINOR)
        self.assertEqual(classify_change(old, old), EDITORIAL)
        self.assertEqual(
            classify_change(old, new, dimension_changed=True),
            MAJOR,
        )

    def test_next_version_rules(self):
        self.assertEqual(next_version("1.0", MINOR), "1.1")
        self.assertEqual(next_version("1.0", MAJOR), "2.0")
        self.assertEqual(next_version("1.0", EDITORIAL), "1.0")
        self.assertEqual(next_version("0.1-draft", MINOR), "0.2-draft")
        self.assertTrue(assert_version_change_allowed("1.0", "1.1", MINOR))
        self.assertTrue(assert_version_change_allowed("1.0", "2.0", MAJOR))
        with self.assertRaises(WorkflowError):
            assert_version_change_allowed("1.0", "2.0", MINOR)
        with self.assertRaises(WorkflowError):
            assert_version_change_allowed("1.0", "1.0", MINOR)

    def test_version_check_uses_the_previous_manifest_hash(self):
        item = base_item()
        changed = base_item(prompt="SYNTHETIC TEST DATA. Different baseline.")
        manifest = BenchmarkManifest(
            version="0.1-draft",
            date="2026-10-20",
            changelog="Synthetic draft.",
            item_file_sha256=hash_items([item]),
            status="draft",
        )
        with self.assertRaises(WorkflowError):
            check_version_update(manifest, [changed], [changed], "0.2-draft", MINOR)

    def test_approved_change_requires_a_new_version(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        changed = base_item(
            benchmark_version="1.0",
            review_status="approved",
            prompt="SYNTHETIC TEST DATA. Changed after freeze.",
        )
        approval = approval_for([item], "1.0")
        manifest = BenchmarkManifest(
            version="1.0",
            date="2026-10-20",
            changelog="Synthetic approved version.",
            item_file_sha256=hash_items([item]),
            status="approved",
            approval=approval,
        )
        with self.assertRaises(WorkflowError):
            check_version_update(manifest, [item], [changed], "1.0", MINOR)
        self.assertTrue(check_version_update(manifest, [item], [changed], "1.1", MINOR))
        self.assertTrue(
            check_version_update(
                manifest,
                [item],
                [changed],
                "2.0",
                MAJOR,
                dimension_changed=True,
            )
        )

    def test_signoff_requires_two_reviewers(self):
        with self.assertRaises(ValidationError):
            NativeReviewSignoff(
                reviewer_panel=("reviewer-1",),
                calibration_date="2026-10-20",
                agreement_statistic="synthetic",
                items_reviewed=("LGP-BENCH-INSTRUCTION-001",),
                signoff_date="2026-10-20",
            )

    def test_signoff_rejects_duplicate_reviewers_and_items(self):
        with self.assertRaises(ValidationError):
            NativeReviewSignoff(
                reviewer_panel=("reviewer-1", "reviewer-1"),
                calibration_date="2026-10-20",
                agreement_statistic="synthetic",
                items_reviewed=("LGP-BENCH-INSTRUCTION-001",),
                signoff_date="2026-10-20",
            )
        with self.assertRaises(ValidationError):
            NativeReviewSignoff(
                reviewer_panel=("reviewer-1", "reviewer-2"),
                calibration_date="2026-10-20",
                agreement_statistic="synthetic",
                items_reviewed=(
                    "LGP-BENCH-INSTRUCTION-001",
                    "LGP-BENCH-INSTRUCTION-001",
                ),
                signoff_date="2026-10-20",
            )

    def test_approval_rejects_a_draft_benchmark_version(self):
        with self.assertRaises(ValidationError):
            approval_for([base_item()], "0.1-draft")


if __name__ == "__main__":
    unittest.main()
