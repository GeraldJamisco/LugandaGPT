"""Single shared path for generating a report and delivering it.

Used by the CLI, the dashboard and the scheduler so that every route runs
the same read-only collection, the same storage rules and the same
duplicate-delivery guard. A generation failure is recorded and returned,
never hidden behind a report that pretends to be a success.
"""

from datetime import datetime, timezone

from . import config, redact, report as report_mod, store, telegram_client


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_last_report(entry):
    state = store.read_state()
    state["last_report"] = entry
    store.write_state(state)


def _record_delivery(rep, outcome, source):
    """Persist what actually happened to one delivery attempt.

    A failure leaves the saved report untouched and records it as awaiting
    delivery so the owner can retry without regenerating anything.
    """
    state = store.read_state()
    entry = {
        "report_id": rep["report_id"],
        "ok": bool(outcome.get("ok")),
        "at": _now_iso(),
        "source": source,
        "error": outcome.get("error"),
        "reason": outcome.get("reason"),
        "attempts": outcome.get("attempts"),
        "parts_sent": outcome.get("parts_sent"),
        "parts_total": outcome.get("parts_total"),
        "message_ids": outcome.get("message_ids"),
    }
    state["last_delivery"] = entry
    if entry["ok"]:
        state["last_delivered_report_id"] = rep["report_id"]
        state["pending_delivery"] = {}
        store.write_state(state)
        return entry
    pending = state.get("pending_delivery") or {}
    retrying = pending.get("report_id") == rep["report_id"]
    state["pending_delivery"] = {
        "report_id": rep["report_id"],
        "since": pending.get("since") if retrying else entry["at"],
        "last_try": entry["at"],
        "attempts": (int(pending.get("attempts") or 0) + 1) if retrying else 1,
        "last_error": outcome.get("error") or outcome.get("reason"),
        "parts_sent": outcome.get("parts_sent"),
        "parts_total": outcome.get("parts_total"),
    }
    store.write_state(state)
    return entry


def deliver_report(rep, source="manual", skip_parts=0):
    """Deliver one report, skipping a report id that already went out.

    This is the duplicate-delivery guard that keeps restarts and repeated
    scheduler ticks from spamming the channel. Failures never touch the
    saved report itself.
    """
    state = store.read_state()
    telegram_state = state.get("telegram", {})
    if not telegram_state.get("delivery_test_passed"):
        reason = "manual Telegram delivery test has not passed; nothing sent"
        store.append_delivery_log(
            f"{source}: report {rep['report_id']} not sent, {reason}"
        )
        outcome = {"ok": False, "reason": reason, "error": None, "blocked": True}
        _record_delivery(rep, outcome, source)
        return outcome

    if state.get("last_delivered_report_id") == rep["report_id"]:
        return {
            "ok": True,
            "reason": "report already delivered, duplicate send skipped",
            "duplicate": True,
        }

    outcome = telegram_client.send_report(
        rep, f"{rep['report_id']}.md", skip_parts=skip_parts
    )
    _record_delivery(rep, outcome, source)
    return outcome


def run_once(send=False, source="manual", interval_hours=None, data=None,
             period_start=None, period_end=None):
    """Generate one report, optionally delivering it to Telegram.

    send=True only attempts delivery when the owner has passed the manual
    delivery test. A report already delivered is never sent twice.
    """
    interval_hours = interval_hours or config.DEFAULT_INTERVAL_HOURS
    try:
        rep, markdown, created = report_mod.generate_report(
            data=data,
            interval_hours=interval_hours,
            period_start=period_start,
            period_end=period_end,
            source=source,
        )
    except Exception as exc:  # collection or storage failure, not a report
        error = redact.redact(f"{type(exc).__name__}: {exc}")
        store.append_delivery_log(f"{source}: report generation failed: {error}")
        _write_last_report(
            {"report_id": None, "ok": False, "error": error,
             "source": source, "at": _now_iso()}
        )
        return {
            "ok": False,
            "stage": "generate",
            "error": error,
            "source": source,
            "report_id": None,
            "created": False,
            "activity_note": None,
            "generated_at": None,
            "sent": False,
            "delivery": {"ok": False, "reason": "report generation failed; nothing was sent"},
        }

    result = {
        "ok": True,
        "stage": "generate",
        "source": source,
        "report_id": rep["report_id"],
        "created": created,
        "activity_note": rep["activity_note"],
        "generated_at": rep["generated_at"],
        "sent": False,
        "delivery": None,
    }
    _write_last_report(
        {
            "report_id": rep["report_id"],
            "ok": True,
            "created": created,
            "generated_at": rep["generated_at"],
            "source": source,
            "activity_note": rep["activity_note"],
            "at": _now_iso(),
        }
    )
    if not send:
        result["delivery"] = {"ok": None, "reason": "delivery not requested"}
        return result

    outcome = deliver_report(rep, source=source)
    result["delivery"] = outcome
    result["sent"] = bool(outcome.get("ok")) and not outcome.get("duplicate")
    return result


def retry_delivery(report_id=None, source="retry"):
    """Deliver a saved report again without regenerating or overwriting it.

    Defaults to whatever report is awaiting delivery. Already-delivered
    report ids are skipped by the same duplicate guard.
    """
    state = store.read_state()
    pending = state.get("pending_delivery") or {}
    last_report = state.get("last_report") or {}
    target = report_id or pending.get("report_id") or last_report.get("report_id")
    if not target:
        return {
            "ok": False,
            "stage": "select",
            "reason": "no saved report is awaiting delivery; generate a report first",
        }
    if not store.is_valid_report_id(target):
        return {"ok": False, "stage": "select", "reason": "invalid report id"}
    try:
        rep = store.load_report_json(target)
    except FileNotFoundError:
        return {
            "ok": False,
            "stage": "select",
            "reason": "saved report not found; nothing to retry",
        }
    except ValueError:
        return {
            "ok": False,
            "stage": "select",
            "reason": "saved report could not be read; nothing sent",
        }
    skip = pending.get("parts_sent") if pending.get("report_id") == target else 0
    outcome = deliver_report(rep, source=source, skip_parts=int(skip or 0))
    result = {"report_id": target, **outcome}
    result.setdefault("stage", "delivery")
    return result


def reporting_status():
    """Safe summary of the latest report and delivery for dashboard and CLI."""
    state = store.read_state()
    reports = store.list_reports(limit=1000)
    pending = state.get("pending_delivery") or {}
    return {
        "latest_saved_report_id": reports[0]["report_id"] if reports else None,
        "saved_report_count": len(reports),
        "last_report": state.get("last_report") or None,
        "last_delivery": state.get("last_delivery") or None,
        "last_delivered_report_id": state.get("last_delivered_report_id"),
        "awaiting_delivery": pending or None,
        "delivery_test_passed": bool(
            (state.get("telegram") or {}).get("delivery_test_passed")
        ),
    }


def record_activity(text, author=None):
    """Record a human-entered activity entry, redacted on the way in."""
    entry = store.append_human_activity(text, author=author)
    store.append_delivery_log(f"human activity recorded: {entry['id']}")
    return entry
