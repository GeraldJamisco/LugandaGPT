"""Pilot file, provenance, split, and contamination tests."""

import copy
import tempfile
import unittest
from pathlib import Path

from training.data import load_pilot_dataset
from training.errors import DataError, ProvenanceError

from .training_support import (
    AS_OF,
    make_evaluation_records,
    make_pilot_splits,
    write_synthetic_project,
)


class SyntheticProjectTests(unittest.TestCase):
    def test_complete_synthetic_project_passes_without_tokenizer(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            dataset = load_pilot_dataset(
                project["config"],
                project_root=project["root"],
                require_complete=True,
                require_approved=True,
                as_of=AS_OF,
            )
            self.assertEqual(dataset.summary["counts"]["train"], 70)
            self.assertEqual(dataset.summary["counts"]["validation"], 15)
            self.assertEqual(dataset.summary["counts"]["heldout"], 15)
            self.assertEqual(dataset.summary["counts"]["evaluation"], 24)
            self.assertEqual(dataset.summary["audit"], {"required": 7, "covered": 7})
            self.assertIsNone(dataset.summary["token_checks"])
            self.assertEqual(
                set(dataset.hashes), {"train", "validation", "heldout", "evaluation"}
            )
            self.assertRegex(dataset.provenance_sha256, r"^[0-9a-f]{64}$")

    def test_missing_train_file(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            Path(project["paths"]["train"]).unlink()
            with self.assertRaises(DataError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_duplicate_id_across_splits(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            pilot["validation"][0]["pilot_id"] = pilot["train"][0]["pilot_id"]
            project = write_synthetic_project(temporary, pilot_splits=pilot)
            with self.assertRaises(DataError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_audit_shortfall(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            for record in pilot["train"][:7]:
                record["reviewers"] = [
                    review
                    for review in record["reviewers"]
                    if review["role"] != "audit"
                ]
            project = write_synthetic_project(temporary, pilot_splits=pilot)
            with self.assertRaises(DataError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_wrong_split_declaration(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            pilot["train"][0]["split"] = "validation"
            project = write_synthetic_project(temporary, pilot_splits=pilot)
            with self.assertRaises(DataError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_short_conversation_without_follow_up(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            target = next(
                record
                for record in pilot["train"]
                if record["capability"] == "short_conversation"
            )
            target["messages"] = target["messages"][:2]
            project = write_synthetic_project(temporary, pilot_splits=pilot)
            with self.assertRaises(DataError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )


class ContaminationTests(unittest.TestCase):
    def test_exact_duplicate_between_train_and_evaluation(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            evaluation = make_evaluation_records()
            evaluation[0]["messages"][0]["content"] = pilot["train"][0]["messages"][0][
                "content"
            ]
            project = write_synthetic_project(
                temporary,
                pilot_splits=pilot,
                evaluation_records=evaluation,
            )
            with self.assertRaises(DataError) as context:
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )
            self.assertIn("duplicate", str(context.exception).lower())

    def test_eight_gram_overlap_between_heldout_and_evaluation(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            pilot = make_pilot_splits()
            evaluation = make_evaluation_records()
            shared = " ".join(
                f"{message['role']} {message['content']}"
                for message in pilot["heldout"][0]["messages"]
            )
            evaluation[0]["messages"][0]["content"] = shared + " extra"
            project = write_synthetic_project(
                temporary,
                pilot_splits=pilot,
                evaluation_records=evaluation,
            )
            with self.assertRaises(DataError) as context:
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )
            self.assertIn("8-gram", str(context.exception))


class ProvenanceTests(unittest.TestCase):
    def test_unresolved_consent_blocks_training(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(
                temporary,
                provenance_overrides={
                    "consent": [
                        {
                            "reference": "CONSENT-001",
                            "teacher_id": "T-001",
                            "status": "pending",
                            "withdrawal_terms": "Synthetic term.",
                            "retention": "Temporary directory.",
                        }
                    ]
                },
            )
            with self.assertRaises(ProvenanceError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_config_hash_mismatch_blocks_training(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            config = copy.deepcopy(project["config"].data)
            config["dataset"]["split_hashes"]["train"] = "0" * 64
            with self.assertRaises(ProvenanceError):
                load_pilot_dataset(
                    config,
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_provenance_hash_mismatch_blocks_training(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            provenance = project["provenance_path"]
            text = provenance.read_text(encoding="utf-8")
            provenance.write_text(
                text.replace(
                    project["hashes"]["train"],
                    "1" * 64,
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ProvenanceError):
                load_pilot_dataset(
                    project["config"],
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_unapproved_version_blocks_training(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            config = copy.deepcopy(project["config"].data)
            config["dataset"]["version"] = "pilot-v1-unapproved"
            with self.assertRaises(ProvenanceError):
                load_pilot_dataset(
                    config,
                    project_root=project["root"],
                    as_of=AS_OF,
                )

    def test_pending_config_hash_blocks_training(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-data-") as temporary:
            project = write_synthetic_project(temporary)
            config = copy.deepcopy(project["config"].data)
            config["dataset"]["split_hashes"] = "pending"
            with self.assertRaises(ProvenanceError):
                load_pilot_dataset(
                    config,
                    project_root=project["root"],
                    as_of=AS_OF,
                )


if __name__ == "__main__":
    unittest.main()
