"""Shared fixtures: isolate reporter paths in a temporary directory."""

import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from reporter import config


class ReporterPathTestCase(unittest.TestCase):
    """Point every reporter path at a temporary directory.

    Outbound HTTP is blocked by default as well. A test that needs the
    Telegram client's request code must mock urllib.request.urlopen (or
    telegram_client.send_message) itself, which replaces this guard.
    """

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory(prefix="lugandagpt-reporter-")
        root = Path(self._tmp.name)
        self.tmp_root = root
        self.archive_dir = root / "archive"
        self.test_runs_dir = root / "test_runs"
        self.state_file = root / "state.json"
        self.human_file = root / "human_activity.json"
        self.api_file = root / "api_usage.json"
        self.exit_criteria_file = root / "exit_criteria_verification.json"
        self.delivery_log = root / "delivery.log"
        self.patches = [
            mock.patch.object(config, "REPORTS_ROOT", root),
            mock.patch.object(config, "ARCHIVE_DIR", self.archive_dir),
            mock.patch.object(config, "TEST_RUNS_DIR", self.test_runs_dir),
            mock.patch.object(config, "STATE_FILE", self.state_file),
            mock.patch.object(config, "HUMAN_ACTIVITY_FILE", self.human_file),
            mock.patch.object(config, "API_USAGE_FILE", self.api_file),
            mock.patch.object(config, "EXIT_CRITERIA_FILE", self.exit_criteria_file),
            mock.patch.object(config, "DELIVERY_LOG", self.delivery_log),
            # A test must never reach Telegram for real.
            mock.patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("test attempted a real network call"),
            ),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def write_test_run(self, name, payload):
        self.test_runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.test_runs_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    @staticmethod
    def synthetic_data(**overrides):
        """Minimal collected-data shape with nothing assumed."""
        data = {
            "collected_at": "2026-10-19T00:00:00+00:00",
            "git": {
                "available": True,
                "error": None,
                "collected_at": "2026-10-19T00:00:00+00:00",
                "branch": "main",
                "head": None,
                "commits": [],
                "changes": [],
                "clean": True,
            },
            "tests": {
                "status": "unavailable",
                "reason": "no recorded test output files",
                "source": "reports/reporter/test_runs",
                "runs": [],
            },
            "experiments": {"status": "unavailable", "reason": "no entries", "entries": []},
            "roadmap": {
                "status": "available",
                "reason": None,
                "phases": [],
                "current_phase": None,
                "blockers": [],
                "upcoming": [],
            },
            "decisions": {"status": "available", "reason": None, "entries": [], "open": []},
            "human_activity": {"status": "unavailable", "reason": "none", "entries": []},
            "api_usage": {
                "status": "unavailable",
                "reason": "no verified billing or usage export present",
                "spend_usd": None,
                "source": None,
                "retrieved_at": None,
            },
            "warnings": [],
        }
        data.update(overrides)
        return data
