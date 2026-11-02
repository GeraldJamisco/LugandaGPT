"""Read-only Git inspection.

Only whitelisted, read-only subcommands may run. Shell execution is never
used, arguments are never built from dashboard input, and no state changing
subcommand (commit, checkout, reset, push, pull, stash, merge, tag) can be
invoked through this module.
"""

import json
import subprocess
from datetime import datetime, timezone

from . import config

READ_ONLY_SUBCOMMANDS = frozenset(
    {"status", "log", "rev-parse", "branch", "diff", "show", "ls-files", "remote", "config"}
)
FORBIDDEN = frozenset(
    {
        "commit",
        "checkout",
        "clone",
        "reset",
        "push",
        "pull",
        "fetch",
        "merge",
        "rebase",
        "stash",
        "tag",
        "cherry-pick",
        "revert",
        "mv",
        "rm",
        "clean",
        "apply",
        "am",
        "gc",
    }
)
FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


class GitError(RuntimeError):
    """Raised when a disallowed or failing Git call is attempted."""


def _git(args, cwd=None, timeout=20):
    """Run a whitelisted read-only Git command and return stdout."""
    if not args:
        raise GitError("empty git invocation")
    subcommand = args[0]
    if subcommand in FORBIDDEN:
        raise GitError(f"refusing state-changing git subcommand: {subcommand}")
    if subcommand not in READ_ONLY_SUBCOMMANDS:
        raise GitError(f"git subcommand not whitelisted: {subcommand}")
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd or config.GIT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git command timed out after {timeout}s") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise GitError(f"git {subcommand} exited {completed.returncode}: {detail[:400]}")
    return completed.stdout


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty(error=None):
    return {
        "available": False,
        "error": error,
        "collected_at": _now_iso(),
        "branch": None,
        "head": None,
        "commits": [],
        "changes": [],
        "clean": None,
    }


def collect(commit_limit=10, cwd=None):
    """Collect branch, recent commits and working tree status.

    Returns a dict with available=False and an error message when Git
    information cannot be read. Never raises for a broken repository.
    """
    try:
        status = _git(["status", "--porcelain=v1", "-b"], cwd=cwd)
    except GitError as exc:
        return _empty(str(exc))

    lines = status.splitlines()
    branch = None
    changes = []
    if lines and lines[0].startswith("## "):
        header = lines[0][3:]
        branch = header.split("...")[0].strip() or None
        body = lines[1:]
    else:
        body = lines
    for line in body:
        if len(line) < 4:
            continue
        changes.append(
            {
                "index_status": line[0],
                "worktree_status": line[1],
                "path": line[3:],
            }
        )

    commits = []
    head = None
    try:
        fmt = FIELD_SEP.join(["%H", "%s", "%an", "%aI"]) + RECORD_SEP
        raw = _git(
            ["log", f"-n{int(commit_limit)}", f"--format={fmt}"],
            cwd=cwd,
        )
        for record in raw.split(RECORD_SEP):
            record = record.strip("\n")
            if not record:
                continue
            parts = record.split(FIELD_SEP)
            if len(parts) != 4:
                continue
            commits.append(
                {
                    "sha": parts[0],
                    "subject": parts[1],
                    "author": parts[2],
                    "authored_at": parts[3],
                }
            )
    except GitError as exc:
        return _empty(str(exc))

    if commits:
        head = commits[0]

    return {
        "available": True,
        "error": None,
        "collected_at": _now_iso(),
        "branch": branch,
        "head": head,
        "commits": commits,
        "changes": changes,
        "clean": len(changes) == 0,
    }


def describe(cwd=None):
    """Compact Git summary used by the CLI. Read-only like collect()."""
    data = collect(cwd=cwd)
    if not data["available"]:
        return json.dumps({"available": False, "error": data["error"]}, indent=2)
    return json.dumps(data, indent=2)
