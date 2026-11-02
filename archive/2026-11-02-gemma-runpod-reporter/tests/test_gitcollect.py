"""Git collection tests: real repository, unavailable Git, read-only guard."""

import subprocess
import unittest
from unittest import mock

from reporter import config, gitcollect


class RealRepositoryTests(unittest.TestCase):
    def test_collects_from_real_repository(self):
        data = gitcollect.collect(cwd=config.GIT_DIR)
        self.assertTrue(data["available"], msg=data.get("error"))
        self.assertIsInstance(data["branch"], str)
        self.assertTrue(data["branch"])
        self.assertGreater(len(data["commits"]), 0)
        self.assertIn("sha", data["commits"][0])
        self.assertIsInstance(data["clean"], bool)
        self.assertIsInstance(data["changes"], list)

    def test_head_matches_first_commit_in_log(self):
        data = gitcollect.collect(cwd=config.GIT_DIR)
        self.assertTrue(data["available"])
        self.assertEqual(data["head"]["sha"], data["commits"][0]["sha"])


class UnavailableGitTests(unittest.TestCase):
    def test_missing_git_binary_is_reported_not_raised(self):
        with mock.patch.object(
            subprocess, "run", side_effect=FileNotFoundError("git")
        ):
            data = gitcollect.collect(cwd=config.GIT_DIR)
        self.assertFalse(data["available"])
        self.assertIn("not found", data["error"])
        self.assertEqual(data["commits"], [])

    def test_failing_git_is_reported_not_raised(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        with mock.patch.object(subprocess, "run", return_value=completed):
            data = gitcollect.collect(cwd=config.GIT_DIR)
        self.assertFalse(data["available"])
        self.assertIn("not a git repository", data["error"])

    def test_timeout_is_reported_not_raised(self):
        with mock.patch.object(
            subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=20)
        ):
            data = gitcollect.collect(cwd=config.GIT_DIR)
        self.assertFalse(data["available"])
        self.assertIn("timed out", data["error"])


class ReadOnlyGuardTests(unittest.TestCase):
    def test_refuses_state_changing_subcommands(self):
        for args in (
            ["commit", "-m", "x"],
            ["push", "origin", "main"],
            ["checkout", "-b", "x"],
            ["reset", "--hard"],
            ["pull"],
        ):
            with self.subTest(args=args):
                with self.assertRaises(gitcollect.GitError):
                    gitcollect._git(args)

    def test_refuses_non_whitelisted_subcommands(self):
        with self.assertRaises(gitcollect.GitError):
            gitcollect._git(["symbolic-ref", "HEAD"])

    def test_subprocess_is_never_run_through_a_shell(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        with mock.patch.object(subprocess, "run", return_value=completed) as run:
            gitcollect._git(["status", "--porcelain"])
        _, kwargs = run.call_args
        self.assertFalse(kwargs.get("shell"))
        self.assertIsInstance(run.call_args.args[0], list)


if __name__ == "__main__":
    unittest.main()
