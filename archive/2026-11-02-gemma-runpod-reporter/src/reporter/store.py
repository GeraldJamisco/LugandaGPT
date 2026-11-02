"""Local report archive and state persistence.

Reports are written once and never overwritten. All writes go through a
temporary file and os.replace so a crash cannot leave a half written
report. State holds scheduling flags only; it never holds credentials.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone

from . import config, redact

REPORT_ID_PATTERN = re.compile(r"^RPT-\d{8}-\d{6}-P\d{1,2}H(-\d+)?$")
_LOCK = threading.Lock()


def default_state():
    # Empty dicts are the "nothing recorded yet" form. Dicts (not None) are
    # used so that read_state() can merge stored values over these defaults.
    return {
        "schedule": {
            "enabled": False,
            "interval_hours": config.DEFAULT_INTERVAL_HOURS,
            "last_attempt_at": None,
            "next_run_at": None,
            "last_result": None,
        },
        "telegram": {
            "delivery_test_passed": False,
            "last_test_at": None,
            "last_test_result": None,
            "chat_id_masked": None,
            "bot_username": None,
        },
        "last_delivered_report_id": None,
        "last_report": {},
        "last_delivery": {},
        "pending_delivery": {},
    }


def is_valid_report_id(report_id):
    return isinstance(report_id, str) and bool(REPORT_ID_PATTERN.match(report_id))


def _write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_state():
    if not config.STATE_FILE.exists():
        return default_state()
    try:
        data = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_state()
    if not isinstance(data, dict):
        return default_state()
    state = default_state()
    for key in state:
        if isinstance(data.get(key), dict):
            state[key].update(data[key])
    if isinstance(data.get("last_delivered_report_id"), str):
        state["last_delivered_report_id"] = data["last_delivered_report_id"]
    return state


def write_state(state):
    with _LOCK:
        _write_json_atomic(config.STATE_FILE, redact.redact_value(state))


def report_paths(report_id):
    if not is_valid_report_id(report_id):
        raise ValueError(f"invalid report id: {report_id!r}")
    return (
        config.ARCHIVE_DIR / f"{report_id}.json",
        config.ARCHIVE_DIR / f"{report_id}.md",
    )


def report_exists(report_id):
    json_path, _ = report_paths(report_id)
    return json_path.exists()


def save_report(report, markdown_text):
    """Store a report. Refuses to overwrite an existing report id.

    Returns (path_json, created) where created is False when the report
    was already stored, which keeps repeated runs duplicate free.
    """
    report_id = report["report_id"]
    json_path, md_path = report_paths(report_id)
    with _LOCK:
        if json_path.exists():
            return json_path, False
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(json_path, report)
        tmp_md = md_path.with_suffix(".md.tmp")
        tmp_md.write_text(markdown_text, encoding="utf-8")
        os.replace(tmp_md, md_path)
    return json_path, True


def list_reports(limit=50):
    """Report metadata, newest first. Reads stored files only."""
    if not config.ARCHIVE_DIR.exists():
        return []
    items = []
    for path in sorted(config.ARCHIVE_DIR.glob("RPT-*.json")):
        if not is_valid_report_id(path.stem):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        summary = data.get("summary", {})
        items.append(
            {
                "report_id": data.get("report_id", path.stem),
                "generated_at": data.get("generated_at"),
                "period": data.get("period"),
                "activity": data.get("activity_note"),
                "new_events": len(summary.get("verified_completed", [])),
                "has_markdown": (config.ARCHIVE_DIR / f"{path.stem}.md").exists(),
            }
        )
    # Report ids encode the period end, so sorting by id keeps history in
    # period order even when generation timestamps collide.
    items.sort(key=lambda item: item["report_id"], reverse=True)
    return items[:limit]


def load_report_json(report_id):
    json_path, _ = report_paths(report_id)
    if not json_path.exists():
        raise FileNotFoundError(report_id)
    return json.loads(json_path.read_text(encoding="utf-8"))


def load_report_markdown(report_id):
    _, md_path = report_paths(report_id)
    if not md_path.exists():
        raise FileNotFoundError(report_id)
    return md_path.read_text(encoding="utf-8")


def previous_event_ids(limit=40, exclude_report_id=None):
    """Event ids already reported, used to deduplicate the next report."""
    seen = set()
    for meta in list_reports(limit=limit):
        if exclude_report_id and meta["report_id"] == exclude_report_id:
            continue
        try:
            data = load_report_json(meta["report_id"])
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            continue
        for event in data.get("events", []):
            if event.get("previously_reported") or event.get("duplicate_in_report"):
                continue
            if event.get("id"):
                seen.add(event["id"])
    return seen


def append_delivery_log(message):
    """Append a delivery line. Redacted before it touches the disk."""
    config.REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _LOCK:
        with config.DELIVERY_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {redact.redact(str(message))}\n")


def read_delivery_log(limit=20):
    if not config.DELIVERY_LOG.exists():
        return []
    lines = config.DELIVERY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def append_human_activity(text, author=None):
    """Add a human-entered activity record. Returns the stored entry."""
    text = str(text).strip()
    if not text:
        raise ValueError("activity text is empty")
    if config.HUMAN_ACTIVITY_FILE.exists():
        try:
            data = json.loads(config.HUMAN_ACTIVITY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = []
        if not isinstance(data, list):
            data = []
    else:
        data = []
    entry = {
        "id": f"human-{len(data) + 1}",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text": redact.redact(text),
        "author": author,
    }
    data.append(entry)
    _write_json_atomic(config.HUMAN_ACTIVITY_FILE, data)
    return entry
