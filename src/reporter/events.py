"""Stable event identifiers and deduplication across consecutive reports."""

from . import redact


def build_events(data):
    """Turn collected activity into events with stable ids and evidence.

    An id is derived from the underlying record (commit sha, file name,
    experiment id, entry id), never from the report timestamp, so the same
    activity keeps the same id in every later report.
    """
    events = []

    git = data.get("git") or {}
    if git.get("available"):
        for commit in git.get("commits", []):
            events.append(
                {
                    "id": f"commit:{commit['sha']}",
                    "kind": "commit",
                    "label": commit["subject"],
                    "timestamp": commit["authored_at"],
                    "evidence": f"git commit {commit['sha'][:12]} ({commit['author']})",
                }
            )
        for change in git.get("changes", []):
            events.append(
                {
                    "id": f"change:{change['index_status']}{change['worktree_status']}:{change['path']}",
                    "kind": "working_tree_change",
                    "label": f"{change['path']} [{change['index_status']}{change['worktree_status']}]",
                    "timestamp": None,
                    "evidence": "git status --porcelain",
                }
            )

    tests = data.get("tests") or {}
    if tests.get("status") == "available":
        for run in tests.get("runs", []):
            events.append(
                {
                    "id": f"test:{run.get('file') or run.get('id') or 'unknown'}",
                    "kind": "test_run",
                    "label": run.get("summary") or run.get("command") or run.get("file"),
                    "timestamp": run.get("recorded_at"),
                    "evidence": f"{tests.get('source')}/{run.get('file', '')}".rstrip("/"),
                }
            )

    experiments = data.get("experiments") or {}
    for entry in experiments.get("entries", []):
        events.append(
            {
                "id": f"experiment:{entry['id']}",
                "kind": "experiment",
                "label": entry.get("title") or entry["id"],
                "timestamp": entry.get("fields", {}).get("Date"),
                "evidence": entry.get("evidence", "docs/EXPERIMENT_LOG.md"),
            }
        )

    human = data.get("human_activity") or {}
    for entry in human.get("entries", []):
        events.append(
            {
                "id": f"human:{entry['id']}",
                "kind": "human_reported",
                "label": entry.get("text"),
                "timestamp": entry.get("recorded_at"),
                "evidence": "human-entered activity record",
            }
        )

    decisions = data.get("decisions") or {}
    for entry in decisions.get("open", []):
        events.append(
            {
                "id": f"decision-open:{entry['id']}",
                "kind": "open_decision",
                "label": f"{entry['id']} {entry['title']} is still Open",
                "timestamp": None,
                "evidence": entry.get("evidence", "docs/DECISIONS.md"),
            }
        )

    roadmap = data.get("roadmap") or {}
    for blocker in roadmap.get("blockers", []):
        events.append(
            {
                "id": f"blocker:{blocker['text']}",
                "kind": "blocker",
                "label": blocker["text"],
                "timestamp": None,
                "evidence": blocker.get("evidence", "docs/ROADMAP.md"),
            }
        )

    for event in events:
        event["label"] = redact.redact(str(event.get("label") or ""))
        event["evidence"] = redact.redact(str(event.get("evidence") or ""))
    return events


def mark_duplicates(events, prior_ids):
    """Flag events already reported. Returns (new_events, duplicate_events)."""
    prior_ids = prior_ids or set()
    new_events = []
    duplicate_events = []
    seen_in_report = set()
    for event in events:
        already_reported = event["id"] in prior_ids
        repeated_here = event["id"] in seen_in_report
        event["previously_reported"] = already_reported
        event["duplicate_in_report"] = repeated_here
        if already_reported or repeated_here:
            duplicate_events.append(event)
        else:
            new_events.append(event)
        seen_in_report.add(event["id"])
    return new_events, duplicate_events
