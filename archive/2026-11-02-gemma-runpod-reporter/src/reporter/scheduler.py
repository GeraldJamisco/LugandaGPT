"""Eight hour scheduler.

Runs inside the reporter process: no Windows service, no scheduled task and
no system-level change. Disabled by default, and enabling is refused until
the owner has both passed the manual Telegram delivery test and generated a
report, so the first scheduled run never fires into an unverified setup.
"""

import threading
from datetime import datetime, timedelta, timezone

from . import config, store

JOB_LOCK = threading.Lock()


def _parse_iso(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def advance_next_run(previous_next, now, interval_hours):
    """Keep the cadence strictly increasing so a restart causes one
    catch-up run, never a burst of backlogged runs.

    Returns (next_run, missed_periods).
    """
    interval = timedelta(hours=interval_hours)
    base = previous_next or now
    nxt = base + interval
    missed = 0
    while nxt <= now:
        nxt += interval
        missed += 1
    return nxt, missed


def next_boundary(now=None, hours=None):
    """Next scheduled slot in East Africa Time (06:00, 14:00, 22:00).

    Slots are fixed wall-clock times in EAT, so reports land on a stable
    eight-hour cadence instead of drifting with the computer's clock.
    """
    hours = tuple(sorted(hours or config.SCHEDULE_HOURS_EAT))
    current = (now or datetime.now(timezone.utc)).astimezone(config.REPORT_TZ)
    base_date = current.date()
    candidates = []
    for day_offset in (0, 1):
        day = base_date + timedelta(days=day_offset)
        for hour in hours:
            candidate = datetime(day.year, day.month, day.day, hour, tzinfo=config.REPORT_TZ)
            if candidate > current:
                candidates.append(candidate)
    return min(candidates)


def count_missed_boundaries(previous_next, now, hours=None):
    """How many scheduled slots lie at or before 'now' (the first of them
    is the run that is due, the rest are skipped catch-up windows)."""
    if previous_next is None:
        return 0
    count = 0
    cursor = previous_next
    while cursor <= now and count < 100:
        count += 1
        cursor = next_boundary(cursor, hours=hours)
    return count


def schedule_status():
    state = store.read_state()
    schedule = state.get("schedule", {})
    now = datetime.now(timezone.utc)
    next_run = _parse_iso(schedule.get("next_run_at"))
    return {
        "enabled": bool(schedule.get("enabled")),
        "interval_hours": int(schedule.get("interval_hours") or config.DEFAULT_INTERVAL_HOURS),
        "timezone": config.REPORT_TZ_NAME,
        "slots_eat": ", ".join(
            f"{hour:02d}:00" for hour in sorted(config.SCHEDULE_HOURS_EAT)
        )
        + " EAT",
        "last_attempt_at": schedule.get("last_attempt_at"),
        "next_run_at": schedule.get("next_run_at"),
        "due_now": bool(next_run and now >= next_run and schedule.get("enabled")),
        "last_result": schedule.get("last_result"),
        "delivery_test_passed": bool(
            state.get("telegram", {}).get("delivery_test_passed")
        ),
        "runs_in_process_only": True,
        "system_task_created": False,
    }


def set_enabled(enabled, now=None):
    """Persist the schedule flag.

    Enabling requires both safety conditions: a passed manual Telegram
    delivery test and at least one saved report.
    """
    enabled = bool(enabled)
    state = store.read_state()
    schedule = state["schedule"]
    if enabled:
        problems = []
        if not state.get("telegram", {}).get("delivery_test_passed"):
            problems.append("manual Telegram delivery test has not passed")
        if not store.list_reports(limit=1):
            problems.append("no saved report exists yet, generate a manual report first")
        if problems:
            return {
                "ok": False,
                "enabled": False,
                "reason": "; ".join(problems) + "; automatic reporting stays disabled",
            }
    schedule["enabled"] = enabled
    if enabled:
        now = now or datetime.now(timezone.utc)
        schedule["next_run_at"] = next_boundary(now).isoformat(timespec="seconds")
    else:
        schedule["next_run_at"] = None
    store.write_state(state)
    return {"ok": True, "enabled": enabled, "next_run_at": schedule["next_run_at"]}


def run_due_job(job_fn):
    """Run one job. Returns ok=False when a previous job still holds the
    lock, which prevents overlapping reporting jobs."""
    if not JOB_LOCK.acquire(blocking=False):
        return {"ok": False, "ran": False, "reason": "previous reporting job still running"}
    try:
        outcome = job_fn()
        return {"ok": True, "ran": True, "outcome": outcome}
    except Exception as exc:  # noqa: BLE001 - scheduler must keep running
        store.append_delivery_log(f"reporting job failed: {type(exc).__name__}: {exc}")
        return {"ok": False, "ran": True, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        JOB_LOCK.release()


class Scheduler(threading.Thread):
    """Background loop that checks for due work on every tick."""

    def __init__(self, job_fn, tick_seconds=30.0):
        super().__init__(name="reporter-scheduler", daemon=True)
        self.job_fn = job_fn
        self.tick_seconds = tick_seconds
        self._stop_event = threading.Event()

    def stop(self, timeout=5.0):
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=timeout)

    def tick(self, now=None):
        state = store.read_state()
        schedule = state.get("schedule", {})
        if not schedule.get("enabled"):
            return {"ran": False, "reason": "scheduling disabled"}
        now = now or datetime.now(timezone.utc)
        next_run = _parse_iso(schedule.get("next_run_at"))
        if next_run is None:
            schedule["next_run_at"] = next_boundary(now).isoformat(timespec="seconds")
            state["schedule"] = schedule
            store.write_state(state)
            return {"ran": False, "reason": "no next run recorded, schedule repaired"}
        if now < next_run:
            return {"ran": False, "reason": "not due"}

        outcome = run_due_job(self.job_fn)
        missed = count_missed_boundaries(next_run, now)
        new_next = next_boundary(now)
        state = store.read_state()
        schedule = state.get("schedule", {})
        schedule["last_attempt_at"] = now.astimezone(config.REPORT_TZ).isoformat(
            timespec="seconds"
        )
        schedule["next_run_at"] = new_next.isoformat(timespec="seconds")
        inner = outcome.get("outcome") or {}
        delivery = inner.get("delivery") or {}
        schedule["last_result"] = {
            "ran": outcome.get("ran"),
            "ok": bool(outcome.get("ok")) and bool(inner.get("ok", True)),
            "stage": inner.get("stage"),
            "error": outcome.get("error") or inner.get("error"),
            "reason": outcome.get("reason") or delivery.get("reason"),
            "missed_periods_skipped": max(0, missed - 1),
            "summary": inner.get("activity_note"),
            "report_id": inner.get("report_id"),
            "generated": bool(inner.get("report_id")),
            "sent": inner.get("sent"),
            "delivery_ok": delivery.get("ok"),
            "delivery_error": delivery.get("error"),
            "delivery_duplicate_skipped": bool(delivery.get("duplicate")),
            "delivery_parts_sent": delivery.get("parts_sent"),
            "delivery_parts_total": delivery.get("parts_total"),
        }
        state["schedule"] = schedule
        store.write_state(state)
        return {"ran": outcome.get("ran"), "outcome": outcome, "next_run_at": schedule["next_run_at"]}

    def run(self):
        while not self._stop_event.wait(self.tick_seconds):
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - never kill the loop
                store.append_delivery_log(
                    f"scheduler tick error: {type(exc).__name__}: {exc}"
                )
