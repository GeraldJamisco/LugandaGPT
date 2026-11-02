"""CLI tests for local validation and guarded commands."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from training.cli import main

from .training_support import BASE_CONFIG, write_synthetic_project


class CliTests(unittest.TestCase):
    def _call(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validate_config(self):
        code, output, _ = self._call(["validate-config", str(BASE_CONFIG)])
        self.assertEqual(code, 0)
        value = json.loads(output)
        self.assertEqual(value["status"], "config_valid")
        self.assertFalse(value["execution_authorized"])

    def test_validate_data_current_config_is_blocked(self):
        code, _, error = self._call(["validate-data", str(BASE_CONFIG)])
        self.assertEqual(code, 2)
        self.assertIn("unapproved", error)

    def test_train_is_blocked_before_any_run_directory(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            output = Path(temporary) / "should-not-exist"
            code, _, error = self._call(
                [
                    "train",
                    str(BASE_CONFIG),
                    "--pod-id",
                    "pod-test",
                    "--region",
                    "region-test",
                    "--host",
                    "host-test",
                    "--image",
                    "image-test",
                    "--output-dir",
                    str(output),
                ]
            )
            self.assertEqual(code, 2)
            self.assertIn("execution_authorized", error)
            self.assertFalse(output.exists())

    def test_there_is_no_preflight_bypass_flag(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "train",
                        str(BASE_CONFIG),
                        "--pod-id",
                        "pod-test",
                        "--region",
                        "region-test",
                        "--host",
                        "host-test",
                        "--image",
                        "image-test",
                        "--skip-preflight",
                    ]
                )
        self.assertEqual(context.exception.code, 2)

    def test_hash_command(self):
        code, output, _ = self._call(["hash", str(BASE_CONFIG)])
        self.assertEqual(code, 0)
        value = json.loads(output)
        self.assertEqual(len(value["sha256"]), 64)

    def test_validate_synthetic_data_without_tokenizer(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-cli-") as temporary:
            project = write_synthetic_project(temporary)
            code, output, error = self._call(
                [
                    "validate-data",
                    str(project["config_path"]),
                    "--project-root",
                    str(project["root"]),
                ]
            )
            self.assertEqual(code, 0, error)
            value = json.loads(output)
            self.assertEqual(value["status"], "data_valid")
            self.assertEqual(value["counts"]["train"], 70)
            self.assertIsNone(value["token_checks"])


if __name__ == "__main__":
    unittest.main()
