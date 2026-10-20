"""Activity collection from verified project sources.

Nothing here infers success. Test results come only from recorded output
files, experiment entries only from the experiment log file, and spending
is unavailable unless a real billing export is present.
"""

import json
import re
from datetime import datetime, timezone

from . import config

PHASE_HEADING = re.compile(r"^##\s+Phase\s+(\d+)\s*(.*?)\s*$")
STATUS_LINE = re.compile(r"\*\*Status:\*\*\s*(.*)$")
BOLD_HEADING = re.compile(r"^\*\*(.+?)\*\*:?\s*$")
DECISION_HEADING = re.compile(r"^##\s+(D-\d{3})\s*(.*?)\s*$")
EXPERIMENT_HEADING = re.compile(r"^###\s+(EXP-[A-Za-z0-9_\-]+)\s*(.*?)\s*$")
FIELD_LINE = re.compile(r"^-\s+\*\*(.+?):\*\*\s*(.*)$")
LEADING_PUNCTUATION = re.compile(r"^[\s\u2010-\u2015\-:]+")
TEMPLATE_ID = "EXP-YYYY-NNN"


def _clean_title(text):
    """Drop separator punctuation left behind by the heading format."""
    return LEADING_PUNCTUATION.sub("", str(text).strip()).strip()


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _display_path(path):
    """Repo relative path when possible, directory name otherwise."""
    try:
        return str(path.relative_to(config.REPO_ROOT))
    except ValueError:
        return path.name


def _iter_lines_stripping_fences(lines):
    """Yield lines outside fenced code blocks, so templates are ignored."""
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line


# --- tests -------------------------------------------------------------


def collect_tests():
    """Read recorded test output. Never infers a pass from test files."""
    if not config.TEST_RUNS_DIR.exists():
        return {
            "status": "unavailable",
            "reason": "no recorded test output directory",
            "source": _display_path(config.TEST_RUNS_DIR),
            "runs": [],
        }
    runs = []
    for path in sorted(config.TEST_RUNS_DIR.glob("*.json")):
        raw = _read_text(path)
        if raw is None:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            runs.append(
                {
                    "file": path.name,
                    "status": "unreadable",
                    "reason": "recorded output is not valid JSON",
                }
            )
            continue
        if not isinstance(record, dict):
            continue
        record = dict(record)
        record["file"] = path.name
        runs.append(record)
    if not runs:
        return {
            "status": "unavailable",
            "reason": "no recorded test output files",
            "source": _display_path(config.TEST_RUNS_DIR),
            "runs": [],
        }
    return {
        "status": "available",
        "reason": None,
        "source": _display_path(config.TEST_RUNS_DIR),
        "runs": runs,
    }


# --- experiments -------------------------------------------------------


def collect_experiments():
    raw = _read_text(config.EXPERIMENT_LOG)
    if raw is None:
        return {"status": "unavailable", "reason": "experiment log missing", "entries": []}
    entries = []
    current = None
    lines = _iter_lines_stripping_fences(raw.splitlines())
    for line in lines:
        heading = EXPERIMENT_HEADING.match(line)
        if heading:
            if current:
                entries.append(current)
            exp_id = heading.group(1)
            if exp_id == TEMPLATE_ID:
                current = None
                continue
            current = {
                "id": exp_id,
                "title": _clean_title(heading.group(2)),
                "fields": {},
                "evidence": f"docs/EXPERIMENT_LOG.md",
            }
            continue
        if current is None:
            continue
        field = FIELD_LINE.match(line)
        if field:
            current["fields"][field.group(1).strip()] = field.group(2).strip()
    if current:
        entries.append(current)
    if not entries:
        return {
            "status": "unavailable",
            "reason": "no experiment records exist in the log",
            "entries": [],
        }
    return {"status": "available", "reason": None, "entries": entries}


# --- roadmap -----------------------------------------------------------


def collect_roadmap():
    raw = _read_text(config.ROADMAP_FILE)
    if raw is None:
        return {
            "status": "unavailable",
            "reason": "roadmap file missing",
            "phases": [],
            "current_phase": None,
            "blockers": [],
            "upcoming": [],
        }
    phases = []
    current = None
    collecting_exit_criteria = False
    for line in raw.splitlines():
        heading = PHASE_HEADING.match(line)
        if heading:
            if current:
                phases.append(current)
            current = {
                "number": int(heading.group(1)),
                "title": _clean_title(heading.group(2)),
                "status": None,
                "exit_criteria": [],
                "evidence": f"docs/ROADMAP.md (Phase {heading.group(1)})",
            }
            collecting_exit_criteria = False
            continue
        if current is None:
            continue
        status = STATUS_LINE.search(line)
        if status and current["status"] is None:
            current["status"] = status.group(1).strip().strip("*").strip()
        section = BOLD_HEADING.match(line.strip())
        if section:
            # Only the exit criteria block is collected: it is the recorded
            # definition of what the phase still requires.
            collecting_exit_criteria = (
                section.group(1).strip().lower() == "exit criteria"
            )
            continue
        if collecting_exit_criteria and line.strip().startswith("- "):
            criterion = line.strip()[2:].strip()
            if criterion:
                current["exit_criteria"].append(criterion)
    if current:
        phases.append(current)

    current_phase = None
    blockers = []
    upcoming = []
    for phase in phases:
        status = (phase["status"] or "").lower()
        if "in progress" in status and current_phase is None:
            current_phase = phase
        if status.startswith("blocked") or status.startswith("conditional"):
            blockers.append(
                {
                    "kind": "roadmap",
                    "text": f"Phase {phase['number']}: {phase['title']} is {phase['status']}",
                    "evidence": phase["evidence"],
                }
            )
        if "not started" in status:
            upcoming.append(phase)
    return {
        "status": "available",
        "reason": None,
        "phases": phases,
        "current_phase": current_phase,
        "blockers": blockers,
        "upcoming": upcoming,
    }


# --- decisions ---------------------------------------------------------


def collect_decisions():
    raw = _read_text(config.DECISIONS_FILE)
    if raw is None:
        return {"status": "unavailable", "reason": "decision log missing", "entries": []}
    entries = []
    current = None
    for line in raw.splitlines():
        heading = DECISION_HEADING.match(line)
        if heading:
            if current:
                entries.append(current)
            current = {
                "id": heading.group(1),
                "title": _clean_title(heading.group(2)),
                "status": None,
                "evidence": f"docs/DECISIONS.md ({heading.group(1)})",
            }
            continue
        if current is None:
            continue
        if line.startswith("**Status:**") and current["status"] is None:
            current["status"] = line.split(":", 1)[1].strip().strip("*").strip().rstrip(".")
    if current:
        entries.append(current)
    open_entries = [e for e in entries if (e["status"] or "").lower() == "open"]
    return {"status": "available", "reason": None, "entries": entries, "open": open_entries}


# --- human entered activity -------------------------------------------


def collect_human_activity():
    if not config.HUMAN_ACTIVITY_FILE.exists():
        return {"status": "unavailable", "reason": "no human activity file", "entries": []}
    raw = _read_text(config.HUMAN_ACTIVITY_FILE)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"status": "unavailable", "reason": "human activity file unreadable", "entries": []}
    if not isinstance(data, list):
        return {"status": "unavailable", "reason": "human activity file malformed", "entries": []}
    entries = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "id": item.get("id") or f"human-{index + 1}",
                "text": str(item.get("text", "")).strip(),
                "recorded_at": item.get("recorded_at"),
                "author": item.get("author"),
                "source": "human-entered",
            }
        )
    if not entries:
        return {"status": "unavailable", "reason": "no human activity entries", "entries": []}
    return {"status": "available", "reason": None, "entries": entries}


# --- API usage ---------------------------------------------------------


def collect_api_usage():
    """Spend is unavailable unless a real export exists. Never assumes 0."""
    if not config.API_USAGE_FILE.exists():
        return {
            "status": "unavailable",
            "reason": "no verified billing or usage export present",
            "spend_usd": None,
            "source": None,
            "retrieved_at": None,
        }
    raw = _read_text(config.API_USAGE_FILE)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {
            "status": "unavailable",
            "reason": "usage export unreadable",
            "spend_usd": None,
            "source": None,
            "retrieved_at": None,
        }
    if not isinstance(data, dict) or not data.get("source") or not data.get("retrieved_at"):
        return {
            "status": "unavailable",
            "reason": "usage export missing source or retrieval timestamp",
            "spend_usd": None,
            "source": None,
            "retrieved_at": None,
        }
    spend = data.get("spend_usd")
    if not isinstance(spend, (int, float)) or isinstance(spend, bool):
        return {
            "status": "unavailable",
            "reason": "usage export has no numeric spend value",
            "spend_usd": None,
            "source": str(data.get("source")),
            "retrieved_at": str(data.get("retrieved_at")),
        }
    return {
        "status": "available",
        "reason": None,
        "spend_usd": spend,
        "source": str(data.get("source")),
        "retrieved_at": str(data.get("retrieved_at")),
    }


# --- aggregate ---------------------------------------------------------


def collect_all(commit_limit=10):
    """Collect every source. Returns warnings instead of raising."""
    from . import gitcollect

    warnings = []
    git = gitcollect.collect(commit_limit=commit_limit)
    if not git["available"]:
        warnings.append({"source": "git", "error": git["error"]})

    collected = {
        "collected_at": _now_iso(),
        "git": git,
        "tests": collect_tests(),
        "experiments": collect_experiments(),
        "roadmap": collect_roadmap(),
        "decisions": collect_decisions(),
        "human_activity": collect_human_activity(),
        "api_usage": collect_api_usage(),
        "warnings": warnings,
    }
    return collected
