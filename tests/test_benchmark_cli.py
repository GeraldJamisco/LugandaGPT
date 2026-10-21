"""CLI tests for local validation commands."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from benchmark.cli import main
from benchmark.storage import write_json, write_jsonl
from benchmark.versioning import build_manifest, write_item_file, write_manifest

from .benchmark_support import base_item, evidence_for, run_manifest


FIXTURE = Path(__file__).parent / "fixtures" / "benchmark" / "synthetic_items.jsonl"


class CliTests(unittest.TestCase):
    def test_validate_synthetic_fixture(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["validate", str(FIXTURE), "--version", "0.1-draft"])
        self.assertEqual(code, 0)
        self.assertIn("OK: 1 item", output.getvalue())

    def test_validate_rejects_malformed_file(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            path = Path(temporary) / "bad.jsonl"
            path.write_text("{\"id\": \"not-an-item\"}\n", encoding="utf-8")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main(["validate", str(path), "--version", "0.1-draft"])
            self.assertEqual(code, 2)
            self.assertIn("ERROR", error.getvalue())

    def test_reviewed_item_requires_evidence(self):
        item = base_item(review_status="native_reviewed")
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            path = Path(temporary) / "items.jsonl"
            write_jsonl(path, [item])
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main(["validate", str(path), "--version", "0.1-draft"])
            self.assertEqual(code, 2)
            self.assertIn("review evidence", error.getvalue())

    def test_approved_manifest_with_evidence(self):
        item = base_item(benchmark_version="1.0", review_status="approved")
        evidence = evidence_for(item, approve=True)
        evidence_json = {
            key: [record.to_dict() for record in value]
            if isinstance(value, list)
            else value.to_dict()
            for key, value in evidence.items()
        }
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            root = Path(temporary)
            item_path = root / "items.jsonl"
            write_item_file(
                item_path,
                [item],
                expected_version="1.0",
                evidence_by_id={item["id"]: evidence},
            )
            manifest = build_manifest(
                [item],
                version="1.0",
                date="2026-10-20",
                changelog="Synthetic approved benchmark.",
                status="approved",
                approval=evidence["approval_record"],
                evidence_by_id={item["id"]: evidence},
            )
            manifest_path = root / "manifest.json"
            write_manifest(manifest_path, manifest)
            evidence_path = root / "evidence.json"
            write_json(evidence_path, {item["id"]: evidence_json})
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "validate",
                        str(item_path),
                        "--version",
                        "1.0",
                        "--manifest",
                        str(manifest_path),
                        "--evidence",
                        str(evidence_path),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("Approved benchmark verified", output.getvalue())

    def test_validate_run_returns_nonzero_for_failed_run(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            path = Path(temporary) / "run_manifest.json"
            manifest = run_manifest(
                run_status="failed",
                finished_at="2026-10-20T10:01:00+00:00",
                errors=({"message": "Synthetic failure."},),
            )
            write_json(path, manifest.to_dict())
            error = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
                code = main(["validate-run", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("not a completed evaluation", error.getvalue())

    def test_hash_command(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["hash", str(FIXTURE)])
        self.assertEqual(code, 0)
        self.assertEqual(len(output.getvalue().strip()), 64)


if __name__ == "__main__":
    unittest.main()
