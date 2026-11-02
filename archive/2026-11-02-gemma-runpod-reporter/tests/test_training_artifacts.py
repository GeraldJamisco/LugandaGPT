"""Artifact, manifest, and cost-record tests."""

import tempfile
import unittest
from pathlib import Path

from training.artifacts import (
    prepare_run_directory,
    read_run_manifest,
    record_final_cost,
    verify_artifact_inventory,
    write_artifact_inventory,
    write_run_manifest,
)
from training.errors import ArtifactError


class ArtifactTests(unittest.TestCase):
    def _manifest(self):
        return {
            "schema_version": 1,
            "status": "completed",
            "started_at_utc": "2026-10-21T10:00:00+00:00",
            "ended_at_utc": "2026-10-21T10:30:00+00:00",
        }

    def test_inventory_round_trip(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            (output / "adapter.bin").write_bytes(b"synthetic adapter")
            write_run_manifest(output, self._manifest())
            write_artifact_inventory(output)
            self.assertTrue(verify_artifact_inventory(output))
            self.assertEqual(
                read_run_manifest(output)["status"],
                "completed",
            )

    def test_tampered_file_detected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            artifact = output / "adapter.bin"
            artifact.write_bytes(b"original")
            write_run_manifest(output, self._manifest())
            write_artifact_inventory(output)
            artifact.write_bytes(b"changed")
            with self.assertRaises(ArtifactError):
                verify_artifact_inventory(output)

    def test_unlisted_file_detected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            (output / "adapter.bin").write_bytes(b"original")
            write_run_manifest(output, self._manifest())
            write_artifact_inventory(output)
            (output / "extra.bin").write_bytes(b"extra")
            with self.assertRaises(ArtifactError):
                verify_artifact_inventory(output)

    def test_tampered_manifest_detected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            write_run_manifest(output, self._manifest())
            path = output / "run_manifest.json"
            path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaises(ArtifactError):
                read_run_manifest(output)

    def test_cost_record_under_caps(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            write_run_manifest(output, self._manifest())
            record = record_final_cost(
                output,
                final_credit_charge_usd=5.38,
                final_cash_charge_usd=10.80,
                remaining_credit_usd=4.62,
                sales_tax_usd=0.80,
            )
            self.assertTrue(record["within_caps"])
            self.assertTrue(verify_artifact_inventory(output))
            manifest = read_run_manifest(output)
            self.assertEqual(manifest["cost"]["final_cash_charge_usd"], 10.80)
            self.assertTrue(manifest["final_billing_recorded"])

    def test_cost_record_above_credit_stop_is_recorded_as_breach(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            write_run_manifest(output, self._manifest())
            record = record_final_cost(
                output,
                final_credit_charge_usd=8.01,
                final_cash_charge_usd=8.01,
                remaining_credit_usd=1.99,
            )
            self.assertFalse(record["within_caps"])
            self.assertEqual(len(record["breaches"]), 1)
            self.assertTrue(verify_artifact_inventory(output))
            self.assertTrue(read_run_manifest(output)["final_billing_recorded"])

    def test_existing_run_directory_is_not_reused(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-artifacts-") as temporary:
            output = Path(temporary) / "run"
            prepare_run_directory({"training": {"output_dir": str(output)}})
            with self.assertRaises(ArtifactError):
                prepare_run_directory({"training": {"output_dir": str(output)}})


if __name__ == "__main__":
    unittest.main()
