"""Telegram Bot API access using only the Python standard library.

The bot token is read from the environment at call time and never written
to source, state, logs, reports or error messages. Every error string is
passed through redaction before it leaves this module.
"""

import json
import os
import re
import urllib.error
import urllib.request

from . import config, redact, store

TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_\-]{25,64}$")
CHAT_ID_RE = re.compile(r"^(?:-?\d{4,20}|@[A-Za-z0-9_]{5,32})$")


class TelegramError(RuntimeError):
    """Raised when the Telegram API cannot be reached or refuses a call."""


def _credentials():
    token = os.environ.get(config.TOKEN_ENV, "").strip()
    chat_id = os.environ.get(config.CHAT_ENV, "").strip()
    problems = []
    if not token:
        problems.append(f"{config.TOKEN_ENV} is not set in this environment")
    elif not TOKEN_RE.match(token):
        # The value is never echoed back, not even in this diagnostic.
        problems.append(
            f"{config.TOKEN_ENV} does not look like a Telegram bot token "
            "(expected digits, colon, then the token body)"
        )
    if not chat_id:
        problems.append(f"{config.CHAT_ENV} is not set in this environment")
    elif not CHAT_ID_RE.match(chat_id):
        problems.append(
            f"{config.CHAT_ENV} must be a numeric chat id or an @channelname, "
            "not a bot username"
        )
    elif chat_id.lstrip("@").lower() == config.BOT_USERNAME.lower():
        # A username is never a chat id, least of all the bot's own.
        problems.append(
            f"{config.CHAT_ENV} must be the destination channel or group id, "
            "not the bot username"
        )
    return {
        "token": token,
        "chat_id": chat_id,
        "token_configured": bool(token),
        "chat_id_configured": bool(chat_id),
        "problems": problems,
        "ready": not problems,
    }


def mask_chat_id(chat_id):
    """Show only the tail of a chat id so the dashboard leaks nothing."""
    if not chat_id:
        return None
    text = str(chat_id)
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[0]}{'*' * (len(text) - 4)}{text[-4:]}"


def status():
    """Safe configuration status for the dashboard and CLI."""
    creds = _credentials()
    state = store.read_state()
    telegram_state = state.get("telegram", {})
    return {
        "token_configured": creds["token_configured"],
        "chat_id_configured": creds["chat_id_configured"],
        "ready": creds["ready"],
        "problems": creds["problems"],
        "chat_id_masked": mask_chat_id(
            os.environ.get(config.CHAT_ENV, "").strip() or None
        ),
        "bot_username": telegram_state.get("bot_username"),
        "expected_bot_username": config.BOT_USERNAME,
        "delivery_test_passed": bool(telegram_state.get("delivery_test_passed")),
        "last_test_at": telegram_state.get("last_test_at"),
        "last_test_result": telegram_state.get("last_test_result"),
        "token_never_returned": True,
    }


def _post(method, payload, token=None, timeout=None):
    """POST to one Telegram method. Returns the parsed response dict."""
    token = token if token is not None else _credentials()["token"]
    if not token:
        raise TelegramError("bot token is not configured")
    url = f"{config.TELEGRAM_API}/bot{token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = timeout or config.HTTP_TIMEOUT_SECONDS
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            http_status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
        http_status = exc.code
    except urllib.error.URLError as exc:
        raise TelegramError(redact.redact(f"network error: {exc.reason}")) from None
    except TimeoutError:
        raise TelegramError("network error: request timed out") from None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TelegramError(
            redact.redact(
                f"unexpected response from Telegram (HTTP {http_status}): "
                f"{raw[:200]}"
            )
        ) from None
    if not isinstance(data, dict):
        raise TelegramError(f"unexpected response payload (HTTP {http_status})")
    data.setdefault("http_status", http_status)
    return data


def _raise_if_failed(response, stage):
    if response.get("ok"):
        return response
    description = str(response.get("description") or "unknown error")
    error_code = response.get("error_code")
    raise TelegramError(
        redact.redact(f"{stage} failed (code {error_code}): {description}")
    )


def get_me(timeout=None):
    """Verify which bot the configured token belongs to."""
    response = _post("getMe", {}, timeout=timeout)
    _raise_if_failed(response, "getMe")
    result = response.get("result") or {}
    return {
        "ok": True,
        "username": result.get("username"),
        "first_name": result.get("first_name"),
        "id": result.get("id"),
    }


def send_message(text, chat_id=None, timeout=None, token=None):
    """Send one plain-text message. Returns {'ok', 'message_id'}."""
    creds = _credentials()
    target = chat_id or creds["chat_id"]
    if not target:
        raise TelegramError(f"{config.CHAT_ENV} is not configured")
    if not isinstance(text, str) or not text.strip():
        raise TelegramError("refusing to send an empty message")
    if len(text) > config.TELEGRAM_MESSAGE_LIMIT:
        raise TelegramError(
            f"message is {len(text)} characters, above the "
            f"{config.TELEGRAM_MESSAGE_LIMIT} limit; split it first"
        )
    response = _post(
        "sendMessage",
        {"chat_id": target, "text": text},
        token=token,
        timeout=timeout,
    )
    _raise_if_failed(response, "sendMessage")
    return {"ok": True, "message_id": (response.get("result") or {}).get("message_id")}


def split_text(text, limit=None):
    """Split on line boundaries so nothing is silently dropped."""
    limit = limit or config.TELEGRAM_MESSAGE_LIMIT
    chunks = []
    current = ""
    for line in text.splitlines():
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _count(summary, key):
    value = summary.get(key)
    return len(value) if isinstance(value, list) else 0


def _add_items(add, items, labels=("evidence",), show_area=False):
    """Render report summary items, which are dicts, as short bullet lines."""
    for item in items or []:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            when = f" [{item['when']}]" if item.get("when") else ""
            area = (
                f"[{item['area']}] "
                if show_area and item.get("area")
                else ""
            )
            evidence = " / ".join(
                str(item.get(label)) for label in labels if item.get(label)
            )
            suffix = f" (evidence: {evidence})" if evidence else ""
            add(f"- {area}{text}{when}{suffix}" if text else "- (empty entry)")
        else:
            add(f"- {str(item).strip()}")


def _delivery_health():
    """Delivery and scheduling facts read from local state only."""
    state = store.read_state()
    schedule = state.get("schedule") or {}
    telegram_state = state.get("telegram") or {}
    return {
        "schedule_enabled": bool(schedule.get("enabled")),
        "interval_hours": schedule.get("interval_hours"),
        "next_run_at": schedule.get("next_run_at"),
        "last_attempt_at": schedule.get("last_attempt_at"),
        "last_result": schedule.get("last_result"),
        "delivery_test_passed": bool(telegram_state.get("delivery_test_passed")),
        "last_delivery": state.get("last_delivery") or None,
        "pending_delivery": state.get("pending_delivery") or None,
    }


def build_report_document(report, report_file=None, health=None):
    """The full report as plain Telegram-sized source text.

    Plain text is deliberate: the client sends no parse mode, so no markup
    escaping can corrupt a message. The result may exceed the per-message
    limit; split_report_parts() divides it into labelled parts instead of
    shortening it.
    """
    from . import report as report_mod

    report_id = report.get("report_id", "unknown")
    report_file = report_file or f"{report_id}.md"
    summary = report.get("summary", {}) or {}
    git = report.get("git", {}) or {}
    tests = report.get("tests", {}) or {}
    experiments = report.get("experiments", {}) or {}
    roadmap = report.get("roadmap", {}) or {}
    spending = report.get("api_spending", {}) or {}
    # Prefer the state observed when this report was generated, so the
    # document never presents a later delivery outcome as its own status.
    health = health or report.get("reporting") or _delivery_health()
    lines = []
    add = lines.append

    add("LugandaGPT Project Report")
    add(f"Report ID: {report_id}")
    add(f"Reporting period: {report['period']['start']} to {report['period']['end']}")
    add(
        "Window covered: "
        + report_mod.period_summary_text(report.get("period") or {})
    )
    add(f"Generated: {report['generated_at']} ({report.get('timezone', 'EAT')})")
    add("Project stage: foundation and research. No trained LugandaGPT model exists.")
    add("")
    add("1) Executive summary")
    executive = report.get("executive_summary") or {}
    if executive:
        for label, key in (
            ("What changed", "changed"),
            ("Completed", "completed"),
            ("Remains incomplete", "incomplete"),
            ("Software verification", "software_verification"),
            ("Core research and model development", "core_research"),
            ("Phase exit criteria", "phase_verification"),
            ("Most important next milestone", "next_milestone"),
            ("Owner decisions needed", "owner_decisions"),
        ):
            add(f"{label}: {executive.get(key)}")
    else:
        add(report.get("activity_note", ""))
        add(
            f"Verified completed: {_count(summary, 'verified_completed')} | "
            f"Attempted or incomplete: {_count(summary, 'attempted_or_incomplete')} | "
            f"Failures or warnings: {_count(summary, 'failed_or_unavailable')} | "
            f"Human reported: {_count(summary, 'human_reported')}"
        )
    add(
        f"Counts: verified completed {_count(summary, 'verified_completed')}, "
        f"attempted or incomplete {_count(summary, 'attempted_or_incomplete')}, "
        f"failures or warnings {_count(summary, 'failed_or_unavailable')}, "
        f"human reported {_count(summary, 'human_reported')}"
    )
    add(
        f"New activity events: {report.get('new_activity_count', 0)} | "
        f"Already reported: {report.get('duplicate_event_count', 0)}"
    )
    add("")
    add("2) Verified completed work")
    _add_items(add, summary.get("verified_completed"), show_area=True)
    if not summary.get("verified_completed"):
        add("- None recorded in this period.")
    add("")
    add("3) Attempted or incomplete work")
    _add_items(add, summary.get("attempted_or_incomplete"))
    if not summary.get("attempted_or_incomplete"):
        add("- None recorded in this period.")
    repository_state = report.get("repository_state") or {}
    if repository_state.get("changed_file_count"):
        add(
            f"Note: {repository_state['changed_file_count']} uncommitted "
            "working-tree change(s) are repository state (section 6), not "
            "incomplete tasks."
        )
    add("")
    add("4) Recorded failures and collection warnings")
    _add_items(add, summary.get("failed_or_unavailable"))
    if not summary.get("failed_or_unavailable"):
        add("- None recorded in this period.")
    add("")
    add("5) Human-reported activity")
    _add_items(add, summary.get("human_reported"))
    if not summary.get("human_reported"):
        add("- None recorded in this period.")
    add("")
    add("6) Git activity and working-tree status")
    if git.get("available"):
        head = git.get("head") or {}
        add(f"Branch: {git.get('branch')}")
        if head.get("sha"):
            add(
                f"Head: {str(head.get('sha'))[:12]} {head.get('subject')} "
                f"({head.get('author')}, {head.get('authored_at')})"
            )
        if git.get("clean"):
            add("Working tree: clean")
        else:
            add(f"Working tree: {git.get('changed_file_count')} changed file(s)")
            for path in git.get("changed_files", []):
                add(f"- {path}")
            add(
                "Note: an uncommitted change is repository state at collection "
                "time; it is not classified as an incomplete task."
            )
    else:
        add(f"Unavailable: {git.get('error') or 'Git activity could not be collected'}.")
    add("")
    add("7) Recorded test results")
    add(f"Status: {tests.get('status', 'unavailable')}")
    add(f"Source: {tests.get('source', 'unavailable')}")
    evidence = report.get("test_evidence") or {}
    runs = tests.get("runs") or []
    if runs:
        add(
            "Latest run: "
            + str(report_mod.describe_test_run(evidence.get("latest_run")))
        )
        add(
            "Latest successful run: "
            + str(report_mod.describe_test_run(evidence.get("latest_successful_run")))
        )
        if evidence.get("undated_count"):
            add(
                f"{evidence['undated_count']} recorded run(s) have no usable "
                "timestamp and cannot be ordered."
            )
        for run in runs:
            add(
                f"- {run.get('file')}: {report_mod.test_outcome(run)} "
                f"(command: {run.get('command', 'unrecorded')}, "
                f"recorded: {run.get('recorded_at', 'unknown')})"
            )
        add(
            "Note: recorded tests verify software behaviour only; they do not "
            "measure Luganda language quality."
        )
    else:
        add(
            f"Unavailable: {tests.get('reason') or 'no recorded test output'}. "
            "No test result is claimed."
        )
    add("")
    add("8) Experiments and recorded results")
    add(f"Status: {experiments.get('status', 'unavailable')}")
    entries = experiments.get("entries") or []
    if entries:
        for entry in entries:
            add(f"- {entry.get('id')}: {entry.get('title')} (evidence: {entry.get('evidence')})")
            fields = entry.get("fields") or {}
            for key, value in fields.items():
                add(f"  {key}: {value}")
            if not fields:
                add("  No recorded result fields; no result is claimed.")
    else:
        add(
            f"Unavailable: {experiments.get('reason') or 'no experiment records'}. "
            "No experiment is claimed as run."
        )
    add("")
    add("9) Blockers and outstanding decisions")
    _add_items(add, report.get("blockers"))
    if not report.get("blockers"):
        add("- No documented blockers open in the roadmap or decision log.")
    add("")
    add("10) Next priorities (roadmap)")
    current = roadmap.get("current_phase")
    if current:
        add(
            f"Current phase: Phase {current.get('number')}: {current.get('title')} "
            f"(status: {current.get('status')})"
        )
    else:
        add("Current phase: not determinable from the roadmap records.")
    for phase in roadmap.get("upcoming") or []:
        add(f"Upcoming: Phase {phase.get('number')}: {phase.get('title')} (status: {phase.get('status')})")
    grouped = {}
    for step in report.get("next_steps") or []:
        grouped.setdefault(step.get("kind") or "proposal", []).append(step)
    for kind, heading in (
        (
            "mandatory",
            "Mandatory exit criteria for the current phase (each shown with its "
            "verification status)",
        ),
        ("approval", "Needs the project owner's decision or approval"),
        ("optional", "Optional improvements, not required by the roadmap"),
        ("proposal", "Proposals, not verified work"),
        ("information", "Information only"),
    ):
        steps = grouped.get(kind) or []
        if not steps:
            continue
        add(f"{heading}:")
        for step in steps:
            if kind == "mandatory":
                status = step.get("status_label") or "not verified"
                evidence_text = (
                    "; ".join(step.get("evidence") or []) or "evidence unavailable"
                )
                add(
                    f"- [{status}] {step.get('text')} "
                    f"(evidence: {evidence_text}; basis: {step.get('basis')})"
                )
            else:
                add(f"- {step.get('text')} (basis: {step.get('basis')})")
    add("")
    add("11) Verified spending")
    if spending.get("status") == "available":
        add(
            f"{spending.get('spend_usd')} USD from {spending.get('source')} "
            f"(retrieved {spending.get('retrieved_at')})"
        )
    else:
        add(
            f"Unavailable: {spending.get('note') or 'no verified usage data'}. "
            "No zero and no estimate is assumed."
        )
    add("")
    add("12) Reporting and delivery health")
    observed_at = health.get("observed_at") or report.get("generated_at")
    add(
        f"State observed at generation ({observed_at}), before this message "
        "was sent:"
    )
    if health.get("schedule_enabled"):
        add(
            f"Scheduling: ENABLED, every {health.get('interval_hours')}h at the "
            "06:00, 14:00 and 22:00 EAT slots; next run "
            f"{health.get('next_run_at') or 'unknown'}"
        )
    else:
        add(
            "Scheduling: disabled; reports are generated on demand or by the "
            "running reporter process"
        )
    add(
        "Telegram delivery test: "
        + ("passed" if health.get("delivery_test_passed") else "not passed")
    )
    last_delivery = health.get("last_delivery") or {}
    if last_delivery:
        if last_delivery.get("ok"):
            add(
                f"Last delivery before this run: report "
                f"{last_delivery.get('report_id')} at {last_delivery.get('at')} "
                f"delivered ({last_delivery.get('source')})"
            )
        else:
            add(
                f"Last delivery before this run: report "
                f"{last_delivery.get('report_id')} at {last_delivery.get('at')} "
                f"FAILED: {last_delivery.get('error') or last_delivery.get('reason')}"
            )
    else:
        add("Last delivery before this run: none recorded")
    pending = health.get("pending_delivery") or {}
    if pending:
        add(
            f"Awaiting delivery before this run: report {pending.get('report_id')} "
            f"since {pending.get('since')} (last error: {pending.get('last_error')})"
        )
    else:
        add("Awaiting delivery before this run: none")
    add(
        "This report's delivery: not claimed here. Telegram confirms the send "
        "after this message leaves, and the outcome is then recorded in "
        "reports/reporter/state.json (last_delivery), "
        "reports/reporter/delivery.log and the dashboard delivery status."
    )
    add("")
    add("13) Saved local report and evidence")
    add(f"Markdown: reports/reporter/archive/{report_file}")
    add(f"JSON: reports/reporter/archive/{report_id}.json")
    evidence = report.get("evidence") or []
    if evidence:
        add("Evidence index:")
        for item in evidence:
            add(f"- {item.get('claim')}: {item.get('source')}")
    else:
        add("Evidence index: no verified claims recorded in this period.")
    add(report.get("model_status") or "No trained LugandaGPT model exists.")
    return "\n".join(lines)


PART_HEADER_MARGIN = 120


def split_report_parts(document, report_id, limit=None):
    """Divide a report into ordered, labelled parts. Nothing is dropped."""
    limit = limit or config.TELEGRAM_MESSAGE_LIMIT
    body_limit = max(200, limit - PART_HEADER_MARGIN)
    chunks = split_text(document, limit=body_limit)
    total = len(chunks)
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        if total == 1:
            parts.append(chunk)
            continue
        header = (
            f"LugandaGPT Project Report (part {index} of {total})\n"
            f"Report: {report_id}"
        )
        parts.append(f"{header}\n{chunk}")
    return parts


def run_delivery_test(send_real_message=True, timeout=None):
    """Config check, getMe, then one short test message to the chat id.

    Records the outcome in local state. Never stores the token, and never
    reports success without a successful API response.
    """
    state = store.read_state()
    creds = _credentials()
    if not creds["ready"]:
        return {"ok": False, "stage": "configuration", "problems": creds["problems"]}

    try:
        me = get_me(timeout=timeout)
    except TelegramError as exc:
        record = {"ok": False, "stage": "getMe", "error": str(exc)}
        state["telegram"]["last_test_result"] = record
        state["telegram"]["delivery_test_passed"] = False
        store.write_state(state)
        return record

    if config.BOT_USERNAME and me.get("username") != config.BOT_USERNAME:
        record = {
            "ok": False,
            "stage": "getMe",
            "error": (
                f"configured token belongs to @{me.get('username')}, "
                f"expected @{config.BOT_USERNAME}"
            ),
        }
        state["telegram"]["last_test_result"] = record
        state["telegram"]["delivery_test_passed"] = False
        store.write_state(state)
        return record

    if not send_real_message:
        return {"ok": True, "stage": "getMe", "bot_username": me.get("username")}

    message = (
        "LugandaGPT Project Reporter delivery test.\n"
        "This destination was configured by the project owner.\n"
        "If you can read this, private channel delivery works."
    )
    try:
        outcome = send_message(message, timeout=timeout)
    except TelegramError as exc:
        record = {"ok": False, "stage": "sendMessage", "error": str(exc)}
        state["telegram"]["last_test_result"] = record
        state["telegram"]["delivery_test_passed"] = False
        store.write_state(state)
        store.append_delivery_log(f"delivery test failed at sendMessage: {exc}")
        return record

    record = {
        "ok": True,
        "stage": "sendMessage",
        "bot_username": me.get("username"),
        "message_id": outcome.get("message_id"),
        "chat_id_masked": mask_chat_id(creds["chat_id"]),
    }
    state["telegram"]["delivery_test_passed"] = True
    state["telegram"]["last_test_result"] = record
    state["telegram"]["bot_username"] = me.get("username")
    state["telegram"]["chat_id_masked"] = mask_chat_id(creds["chat_id"])
    from datetime import datetime, timezone

    state["telegram"]["last_test_at"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    store.write_state(state)
    store.append_delivery_log(
        f"delivery test succeeded: bot @{me.get('username')}, "
        f"message_id {outcome.get('message_id')}"
    )
    return record


def send_report(report, report_file, retries=2, retry_sleep=None, timeout=None,
                skip_parts=0):
    """Send the full report content, split into labelled parts.

    Retries are bounded per part and only cover transient network errors.
    skip_parts resumes a delivery whose earlier parts Telegram already
    confirmed, so a retry never repeats a message that went out.
    """
    report_id = report.get("report_id", "unknown")
    document = build_report_document(report, report_file=report_file)
    parts = split_report_parts(document, report_id)
    total = len(parts)
    try:
        skip = max(0, min(int(skip_parts or 0), total))
    except (TypeError, ValueError):
        skip = 0
    if skip >= total:
        # Marking this delivered would claim success Telegram never gave us.
        message = (
            "delivery state is inconsistent: every part is marked sent but "
            "Telegram never confirmed success; check the chat by hand"
        )
        store.append_delivery_log(f"report {report_id}: {message}")
        return {
            "ok": False,
            "error": message,
            "attempts": 0,
            "parts_sent": total,
            "parts_total": total,
            "needs_manual_check": True,
        }

    message_ids = []
    attempts = 0
    for index in range(skip, total):
        text = parts[index]
        attempt = 0
        delivered = False
        last_error = None
        while attempt <= retries:
            attempt += 1
            attempts += 1
            try:
                outcome = send_message(text, timeout=timeout)
                message_ids.append(outcome.get("message_id"))
                delivered = True
                break
            except TelegramError as exc:
                last_error = str(exc)
                transient = "network error" in last_error or "timed out" in last_error
                if transient and attempt <= retries:
                    delay = 5 * attempt
                    store.append_delivery_log(
                        f"report {report_id} part {index + 1}/{total} attempt "
                        f"{attempt} failed transiently, retrying in {delay}s: "
                        f"{last_error}"
                    )
                    if retry_sleep:
                        retry_sleep(delay)
                    else:
                        import time

                        time.sleep(delay)
                else:
                    break
        if not delivered:
            store.append_delivery_log(
                f"report {report_id} part {index + 1}/{total} delivery failed "
                f"after {attempts} attempt(s): {last_error}"
            )
            return {
                "ok": False,
                "error": redact.redact(last_error or "unknown"),
                "attempts": attempts,
                "parts_sent": index,
                "parts_total": total,
            }
    store.append_delivery_log(
        f"report {report_id} delivered: {total} part(s), message ids {message_ids}"
    )
    return {
        "ok": True,
        "message_ids": message_ids,
        "attempts": attempts,
        "parts_sent": total,
        "parts_total": total,
    }
