"""Report construction: structured JSON plus a human readable Markdown file.

Every significant claim carries an evidence reference. Verified facts and
proposals are kept in separate sections, and an empty period is reported
as empty rather than padded.
"""

import json
from datetime import datetime, timedelta, timezone

from . import collect, config, events, redact, store, verify

TIMEZONE_NAME = config.REPORT_TZ_NAME


def _report_tz_iso(value):
    """Render a timestamp in project reporting time (EAT)."""
    parsed = _parse_timestamp(value) if not isinstance(value, datetime) else value
    if parsed is None:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(config.REPORT_TZ).isoformat(timespec="seconds")


def _parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def test_outcome(run):
    """Classify a recorded test run from its own fields only."""
    if not isinstance(run, dict):
        return "unknown"
    if run.get("status") == "unreadable":
        return "unverifiable"
    exit_code = run.get("exit_code")
    failures = run.get("failures")
    errors = run.get("errors")
    if isinstance(exit_code, int) and exit_code != 0:
        return "failed"
    if isinstance(failures, int) and failures > 0:
        return "failed"
    if isinstance(errors, int) and errors > 0:
        return "failed"
    if isinstance(exit_code, int) or isinstance(failures, int):
        return "passed"
    return "unknown"


def _recorded_int(record, *names):
    """A recorded integer field, or None. Booleans and text are not numbers."""
    for name in names:
        value = record.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def _recorded_duration(record, *names):
    for name in names:
        value = record.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None


def latest_test_evidence(tests):
    """Select the latest run by recorded timestamp, and the latest success.

    Ordering uses the run's own recorded_at, never the file name and never
    text inside the report. A run without a usable timestamp cannot be
    placed in time and is counted separately. The latest successful run is
    kept distinct from the latest run, so an older success is never shown as
    the latest result when a newer run failed.
    """
    runs = [run for run in (tests.get("runs") or []) if isinstance(run, dict)]
    dated = []
    undated = 0
    for run in runs:
        stamp = _parse_timestamp(run.get("recorded_at"))
        if stamp is None:
            undated += 1
        else:
            dated.append((stamp, run))
    dated.sort(key=lambda pair: pair[0])

    def summarize(run):
        if run is None:
            return None
        return {
            "file": run.get("file"),
            "recorded_at": run.get("recorded_at"),
            "outcome": test_outcome(run),
            "tests_run": _recorded_int(run, "tests_run", "tests"),
            "duration_seconds": _recorded_duration(run, "duration_seconds", "duration"),
            "exit_code": _recorded_int(run, "exit_code"),
            "failures": _recorded_int(run, "failures"),
            "errors": _recorded_int(run, "errors"),
            "command": run.get("command"),
        }

    latest = dated[-1][1] if dated else None
    latest_successful = None
    for _, run in reversed(dated):
        if test_outcome(run) == "passed":
            latest_successful = run
            break

    status = "available" if runs else "unavailable"
    return {
        "status": status,
        "reason": None if runs else (tests.get("reason") or "no recorded test output"),
        "source": tests.get("source"),
        "run_count": len(runs),
        "undated_count": undated,
        "latest_run": summarize(latest),
        "latest_successful_run": summarize(latest_successful),
        "latest_is_success": bool(
            latest is not None and test_outcome(latest) == "passed"
        ),
    }


def describe_test_run(summary, label=None):
    """One line describing a selected run, stating missing fields plainly."""
    if not summary:
        return "none recorded"
    parts = [
        f"{summary.get('file') or 'unnamed record'} recorded "
        f"{summary.get('recorded_at') or 'timestamp unavailable'}"
    ]
    parts.append(str(summary.get("outcome") or "unknown"))
    count = summary.get("tests_run")
    parts.append(f"{count} tests" if count is not None else "test count unavailable")
    duration = summary.get("duration_seconds")
    parts.append(
        f"{duration:g}s" if duration is not None else "duration unavailable"
    )
    line = ", ".join(parts)
    return f"{label}: {line}" if label else line


# Activity events describe work done in the period. Repository state,
# blockers and open decisions are reference facts and are counted separately,
# so "what changed" is not inflated by an uncommitted working tree.
ACTIVITY_KINDS = ("commit", "test_run", "experiment", "human_reported")

NEXT_STEP_LABELS = {
    "mandatory": "mandatory for this phase; completion not verified",
    "approval": "needs owner decision or approval",
    "optional": "optional; not required by the roadmap",
    "information": "information only",
}


def next_step_label(step):
    """Label a next-priority item from its kind, with a legacy fallback."""
    kind = step.get("kind")
    if kind == "mandatory" and step.get("status_label"):
        return f"mandatory for this phase; status: {step['status_label']}"
    if kind in NEXT_STEP_LABELS:
        return NEXT_STEP_LABELS[kind]
    return "verified basis" if step.get("verified") else "proposal, needs approval"


def _duration_text(seconds):
    """Human wording for how long the reporting window actually covers."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "less than a minute"
    minutes = seconds // 60
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} hours {minutes} minutes"
    if hours:
        return f"{hours} hours"
    return f"{minutes} minutes"


def period_summary_text(period):
    """Describe the window that was covered, not the nominal cadence.

    An on-demand report between two scheduled slots covers only the time
    since the previous report, so it must never read as a full interval.
    """
    interval = period.get("interval_hours")
    covered = period.get("covered_text") or "an unrecorded duration"
    mode = period.get("mode")
    if mode == "scheduled":
        return f"{covered} covered, scheduled report"
    if mode == "on-demand":
        return (
            f"{covered} covered, on-demand report, not a full "
            f"{interval}h scheduled period"
        )
    return f"{interval}h interval (reporting mode not recorded)"


def _reporting_snapshot(state, observed_at):
    """Delivery and scheduling facts as observed when this report was built.

    Captured at generation time on purpose. A delivery outcome can only be
    known after Telegram confirms the send, so it is recorded separately in
    state and must not be presented as part of this report's own state.
    """
    schedule = state.get("schedule") or {}
    telegram_state = state.get("telegram") or {}
    return {
        "observed_at": observed_at,
        "schedule_enabled": bool(schedule.get("enabled")),
        "interval_hours": schedule.get("interval_hours"),
        "next_run_at": schedule.get("next_run_at"),
        "last_attempt_at": schedule.get("last_attempt_at"),
        "last_result": schedule.get("last_result"),
        "delivery_test_passed": bool(telegram_state.get("delivery_test_passed")),
        "last_delivery": state.get("last_delivery") or None,
        "pending_delivery": state.get("pending_delivery") or None,
    }


def build_report(
    data=None,
    period_start=None,
    period_end=None,
    interval_hours=config.DEFAULT_INTERVAL_HOURS,
    source=None,
):
    """Build a report dictionary. Does not write anything to disk."""
    data = data if data is not None else collect.collect_all()
    if not isinstance(period_end, datetime):
        period_end = datetime.now(timezone.utc)
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    # Report ids use project reporting time so the id matches the stamped
    # period end the owner reads (EAT, UTC+3).
    id_stamp = period_end.astimezone(config.REPORT_TZ)
    if period_start is None:
        previous = None
        for meta in store.list_reports(limit=1):
            previous = _parse_timestamp(meta.get("generated_at"))
        period_start = previous or (period_end - timedelta(hours=interval_hours))

    period_start_dt = _parse_timestamp(period_start) or period_end
    if period_start_dt.tzinfo is None:
        period_start_dt = period_start_dt.replace(tzinfo=timezone.utc)
    coverage_seconds = int((period_end - period_start_dt).total_seconds())
    if coverage_seconds < 0:
        coverage_seconds = 0
    period_mode = "scheduled" if source == "scheduler" else "on-demand"

    prior_ids = store.previous_event_ids(exclude_report_id=None)
    all_events = events.build_events(data)
    new_events, duplicate_events = events.mark_duplicates(all_events, prior_ids)

    git = data.get("git") or {}
    tests = data.get("tests") or {}
    experiments = data.get("experiments") or {}
    roadmap = data.get("roadmap") or {}
    decisions = data.get("decisions") or {}
    human = data.get("human_activity") or {}
    api_usage = data.get("api_usage") or {}

    verified_completed = []
    attempted = []
    failed = []
    human_reported = []
    evidence = []

    for event in new_events:
        if event["kind"] == "commit":
            item = {
                "text": f"Commit: {event['label']}",
                "when": event["timestamp"],
                "evidence": event["evidence"],
                "area": "repository change",
            }
            verified_completed.append(item)
            evidence.append({"claim": item["text"], "source": item["evidence"]})
        elif event["kind"] == "test_run":
            run = next(
                (r for r in tests.get("runs", []) if r.get("file") and r.get("file") in event["evidence"]),
                None,
            )
            outcome = test_outcome(run)
            if outcome == "passed":
                item = {
                    "text": event["label"] or "Recorded test run",
                    "when": event["timestamp"],
                    "evidence": event["evidence"],
                    "area": "test verification",
                }
                verified_completed.append(item)
                evidence.append({"claim": item["text"], "source": item["evidence"]})
            elif outcome == "failed":
                failed.append(
                    {
                        "text": event["label"] or "Recorded test run reported failures",
                        "when": event["timestamp"],
                        "evidence": event["evidence"],
                    }
                )
            else:
                attempted.append(
                    {
                        "text": f"Test output recorded without a verifiable outcome: {event['label']}",
                        "when": event["timestamp"],
                        "evidence": event["evidence"],
                    }
                )
        elif event["kind"] == "experiment":
            verified_completed.append(
                {
                    "text": f"Experiment record present: {event['label']}",
                    "when": event["timestamp"],
                    "evidence": event["evidence"],
                    "area": "research record",
                }
            )
            evidence.append({"claim": event["label"], "source": event["evidence"]})
        elif event["kind"] == "human_reported":
            human_reported.append(
                {
                    "text": event["label"],
                    "when": event["timestamp"],
                    "evidence": event["evidence"],
                }
            )

    # Working-tree changes are repository state, not evidence of unfinished
    # work. They are recorded in their own section and never counted as
    # attempted or incomplete tasks.
    changed_files = git.get("changes") if git.get("available") else []
    repository_state = {
        "available": bool(git.get("available")),
        "branch": git.get("branch"),
        "clean": git.get("clean"),
        "changed_file_count": len(changed_files or []),
        "changed_files": changed_files or [],
        "note": (
            "Working-tree changes are a snapshot of repository state at "
            "collection time. An uncommitted change is not classified as an "
            "attempted or incomplete task."
        ),
    }

    for warning in data.get("warnings", []):
        failed.append(
            {
                "text": f"Collection warning from {warning.get('source')}: {warning.get('error')}",
                "when": None,
                "evidence": "collector warning",
            }
        )

    for run in tests.get("runs", []):
        if run.get("status") == "unreadable":
            failed.append(
                {
                    "text": f"Recorded test output unreadable: {run.get('file')}",
                    "when": run.get("recorded_at"),
                    "evidence": f"{tests.get('source')}/{run.get('file', '')}".rstrip("/"),
                }
            )

    blockers = list(roadmap.get("blockers", []))
    for entry in decisions.get("open", []):
        blockers.append(
            {
                "kind": "open_decision",
                "text": f"{entry['id']} {entry['title']} is Open",
                "evidence": entry["evidence"],
            }
        )

    if (
        not verified_completed
        and not human_reported
        and not attempted
        and not failed
        and not experiments.get("entries")
    ):
        activity_note = (
            "No meaningful activity recorded in this period. "
            "Sources checked: git log and status, test output records, "
            "experiment log, human activity records."
        )
    else:
        parts = []
        if verified_completed:
            parts.append(f"{len(verified_completed)} verified completed item(s)")
        if attempted:
            parts.append(f"{len(attempted)} attempted or incomplete item(s)")
        if failed:
            parts.append(f"{len(failed)} failure(s) or collection warning(s)")
        if human_reported:
            parts.append(f"{len(human_reported)} human-entered item(s)")
        activity_note = "Activity in this period: " + ", ".join(parts) + "."

    spending = {
        "status": api_usage.get("status", "unavailable"),
        "spend_usd": api_usage.get("spend_usd"),
        "source": api_usage.get("source"),
        "retrieved_at": api_usage.get("retrieved_at"),
        "note": api_usage.get("reason")
        or f"Verified from {api_usage.get('source')}",
    }

    generated_at = datetime.now(config.REPORT_TZ).isoformat(timespec="seconds")
    state = store.read_state()
    reporting_snapshot = _reporting_snapshot(state, generated_at)

    new_activity_events = [
        event for event in new_events if event["kind"] in ACTIVITY_KINDS
    ]
    activity_counts = {
        kind: sum(1 for event in new_activity_events if event["kind"] == kind)
        for kind in ACTIVITY_KINDS
    }

    current_phase = roadmap.get("current_phase") or {}
    exit_criteria = current_phase.get("exit_criteria") or []
    verification_context = data.get("verification_context")
    if verification_context is None:
        verification_context = (
            verify.build_context(data=data) if exit_criteria else {}
        )
    verification_records = verify.verify_criteria(exit_criteria, verification_context)
    verification_summary = verify.summarize(verification_records)
    verification_priority = verify.highest_priority(verification_records)
    test_evidence = latest_test_evidence(tests)
    open_decisions = [item for item in blockers if item.get("kind") == "open_decision"]
    approval_blockers = [
        item
        for item in roadmap.get("blockers", [])
        if "approval" in str(item.get("text", "")).lower()
    ]

    next_steps = []
    for record in verification_records:
        next_steps.append(
            {
                "text": f"Phase {current_phase.get('number')} exit criterion: "
                f"{record['criterion'].rstrip('.')}.",
                "basis": current_phase.get("evidence") or "docs/ROADMAP.md",
                "verified": record["status"] == verify.STATUS_VERIFIED_COMPLETE,
                "kind": "mandatory",
                "status": record["status"],
                "status_label": record["status_label"],
                "evidence": record["evidence"],
                "evidence_available": record["evidence_available"],
                "reason": record["reason"],
            }
        )
    if current_phase and not exit_criteria:
        next_steps.append(
            {
                "text": (
                    f"Continue Phase {current_phase.get('number')}: "
                    f"{current_phase.get('title')} "
                    f"(status: {current_phase.get('status')}); the roadmap "
                    "records no exit criteria for it."
                ),
                "basis": current_phase.get("evidence") or "docs/ROADMAP.md",
                "verified": True,
                "kind": "mandatory",
            }
        )
    for item in open_decisions:
        next_steps.append(
            {
                "text": item["text"],
                "basis": item["evidence"],
                "verified": True,
                "kind": "approval",
            }
        )
    for item in approval_blockers:
        next_steps.append(
            {
                "text": item["text"],
                "basis": item["evidence"],
                "verified": True,
                "kind": "approval",
            }
        )
    if tests.get("status") != "available":
        next_steps.append(
            {
                "text": "Record real test output in reports/reporter/test_runs/ before any test result is reported.",
                "basis": "test output is currently unavailable",
                "verified": False,
                "kind": "information",
            }
        )
    if spending["status"] != "available":
        next_steps.append(
            {
                "text": "Supply a provider billing export to enable verified spending reports.",
                "basis": api_usage.get("reason", "usage data unavailable"),
                "verified": False,
                "kind": "optional",
            }
        )
    if not state["schedule"].get("enabled"):
        next_steps.append(
            {
                "text": (
                    "Scheduled reporting is disabled; enabling it requires the "
                    "owner's decision."
                ),
                "basis": "reports/reporter/state.json schedule.enabled is false",
                "verified": True,
                "kind": "approval",
            }
        )
    if not new_activity_events:
        next_steps.append(
            {
                "text": (
                    "No new activity was recorded this period; confirm that work "
                    "is being committed or recorded."
                ),
                "basis": "no new activity events collected this period",
                "verified": False,
                "kind": "information",
            }
        )

    if new_activity_events:
        described = ", ".join(
            f"{count} {kind.replace('_', ' ')}"
            for kind, count in activity_counts.items()
            if count
        )
        changed_summary = (
            f"{len(new_activity_events)} new activity item(s) recorded: "
            f"{described}."
        )
    else:
        changed_summary = (
            "No new activity was recorded in this period; previously reported "
            "items are not counted again."
        )

    if verified_completed:
        completed_summary = (
            f"{len(verified_completed)} verified item(s), listed in section 2."
        )
    else:
        completed_summary = "No verified completion was recorded in this period."

    incomplete_bits = []
    if attempted:
        incomplete_bits.append(
            f"{len(attempted)} item(s) recorded without a verifiable outcome"
        )
    if failed:
        incomplete_bits.append(
            f"{len(failed)} failure(s) or collection warning(s)"
        )
    incomplete_summary = (
        "; ".join(incomplete_bits) + "."
        if incomplete_bits
        else "No incomplete task or failure was recorded in this period."
    )
    if repository_state["changed_file_count"]:
        incomplete_summary += (
            f" {repository_state['changed_file_count']} uncommitted "
            "working-tree change(s) are repository state, not incomplete work."
        )
    if blockers:
        incomplete_summary += (
            f" {len(blockers)} documented blocker(s) or open decision(s) "
            "remain (section 9)."
        )

    if activity_counts["experiment"]:
        core_summary = (
            f"Experiment evidence was recorded in this period "
            f"({activity_counts['experiment']} record(s)); only the results "
            "stated in docs/EXPERIMENT_LOG.md are claimed. No trained model "
            "exists."
        )
    else:
        core_summary = (
            "No research result was recorded: no experiment or evaluation "
            "result in this period. Repository changes, recorded tests and "
            "reporter work do not measure Luganda language quality, so no "
            "capability advance is claimed. No trained model exists."
        )

    latest_run = test_evidence.get("latest_run")
    latest_ok = test_evidence.get("latest_successful_run")
    if latest_run is None:
        software_verification = (
            "No test run is recorded, so no test result is claimed. Recorded "
            "tests verify software only and do not measure Luganda language "
            "quality."
        )
    else:
        software_verification = (
            "Latest recorded test run: " + describe_test_run(latest_run) + "."
        )
        if latest_run["outcome"] == "passed":
            software_verification += " It is the latest run and it passed."
        elif latest_ok is None:
            software_verification += (
                " It is the latest run and it did not pass; no successful run "
                "is recorded."
            )
        else:
            software_verification += (
                " It is the latest run and it did not pass; the latest "
                "successful run predates it and is not the latest run."
            )
        if latest_ok is not None and latest_ok["file"] != latest_run["file"]:
            software_verification += (
                " Latest successful run: " + describe_test_run(latest_ok) + "."
            )
        if test_evidence.get("undated_count"):
            software_verification += (
                f" {test_evidence['undated_count']} recorded run(s) have no "
                "usable timestamp and cannot be placed in time."
            )
        software_verification += (
            " Recorded tests verify software only; they do not measure Luganda "
            "language quality."
        )

    if not verification_records:
        phase_verification = (
            "No recorded phase exit criteria are available to verify, so no "
            "phase completion is claimed."
        )
    else:
        phase_label = (
            f"Phase {current_phase.get('number')}"
            if current_phase
            else "Current phase"
        )
        counts = verification_summary["counts"]
        parts = [
            f"{verification_summary['verified_complete']} of "
            f"{verification_summary['total']} verified complete"
        ]
        for status in (
            verify.STATUS_INCOMPLETE,
            verify.STATUS_NEEDS_REVIEW,
            verify.STATUS_NOT_VERIFIED,
        ):
            if counts.get(status):
                parts.append(f"{counts[status]} {verify.STATUS_LABELS[status]}")
        phase_verification = (
            f"{phase_label} exit criteria: " + ", ".join(parts) + "."
        )
        if verification_priority["criterion"]:
            phase_verification += (
                f" Highest-priority criterion: "
                f"{verification_priority['criterion']} "
                f"({verification_priority['basis']})."
            )
        else:
            basis = verification_priority["basis"]
            phase_verification += f" {basis[0].upper()}{basis[1:]}."
        if verification_summary["phase_complete"]:
            phase_verification += (
                " Every recorded exit criterion is verified complete."
            )
        else:
            phase_verification += (
                f" {phase_label} is not complete: completion requires every "
                "recorded exit criterion to be verified complete."
            )

    if current_phase and verification_records:
        phase_label = (
            f"Phase {current_phase.get('number')}: {current_phase.get('title')}"
        )
        next_milestone = (
            f"{phase_label} remains in progress: "
            f"{verification_summary['verified_complete']} of "
            f"{verification_summary['total']} recorded exit criteria are "
            "verified complete."
        )
        if verification_priority["criterion"]:
            next_milestone += (
                f" Address first: {verification_priority['criterion']} "
                f"({verification_priority['basis']})."
            )
        else:
            next_milestone += f" {verification_priority['basis'][0].upper()}"
            next_milestone += f"{verification_priority['basis'][1:]}."
    elif current_phase:
        next_milestone = (
            f"Continue Phase {current_phase.get('number')}: "
            f"{current_phase.get('title')} "
            f"(status: {current_phase.get('status')}); the roadmap records no "
            "exit criteria for it."
        )
    elif roadmap.get("upcoming"):
        first = roadmap["upcoming"][0]
        next_milestone = (
            f"Start Phase {first.get('number')}: {first.get('title')}."
        )
    else:
        next_milestone = "Not determinable from docs/ROADMAP.md."

    decision_texts = [
        str(item["text"]).strip().rstrip(".; ") for item in open_decisions
    ]
    decision_texts += [
        str(item["text"]).strip().rstrip(".; ") for item in approval_blockers
    ]
    owner_decisions = (
        "Owner decision required: " + "; ".join(decision_texts) + "."
        if decision_texts
        else "No owner decision is recorded as open."
    )

    executive_summary = {
        "changed": changed_summary,
        "completed": completed_summary,
        "incomplete": incomplete_summary,
        "software_verification": software_verification,
        "core_research": core_summary,
        "phase_verification": phase_verification,
        "next_milestone": next_milestone,
        "owner_decisions": owner_decisions,
    }

    report = {
        "report_id": f"RPT-{id_stamp:%Y%m%d}-{id_stamp:%H%M%S}-P{int(interval_hours)}H",
        "schema_version": 1,
        "period": {
            "start": _report_tz_iso(period_start),
            "end": _report_tz_iso(period_end),
            "interval_hours": int(interval_hours),
            "mode": period_mode,
            "source": source,
            "covered_seconds": coverage_seconds,
            "covered_text": _duration_text(coverage_seconds),
        },
        "generated_at": generated_at,
        "timezone": TIMEZONE_NAME,
        "timezone_note": (
            "Report timestamps are East Africa Time (UTC+3, no daylight saving). "
            "Git evidence keeps the offset recorded by Git."
        ),
        "git": {
            "available": git.get("available", False),
            "error": git.get("error"),
            "branch": git.get("branch"),
            "head": git.get("head"),
            "clean": git.get("clean"),
            "changed_file_count": len(git.get("changes", [])),
            "changed_files": git.get("changes", []),
        },
        "repository_state": repository_state,
        "activity_note": activity_note,
        "summary": {
            "verified_completed": verified_completed,
            "attempted_or_incomplete": attempted,
            "failed_or_unavailable": failed,
            "human_reported": human_reported,
        },
        "events": all_events,
        "new_event_count": len(new_events),
        "new_activity_count": len(new_activity_events),
        "duplicate_event_count": len(duplicate_events),
        "tests": tests,
        "test_evidence": test_evidence,
        "experiments": experiments,
        "roadmap": {
            "current_phase": roadmap.get("current_phase"),
            "phases": roadmap.get("phases", []),
            "upcoming": roadmap.get("upcoming", []),
        },
        "phase_verification": {
            "phase": current_phase.get("number") if current_phase else None,
            "title": current_phase.get("title") if current_phase else None,
            "summary": verification_summary,
            "priority": verification_priority,
            "criteria": verification_records,
        },
        "decisions": {
            "open": decisions.get("open", []),
            "total": len(decisions.get("entries", [])),
        },
        "blockers": blockers,
        "api_spending": spending,
        "evidence": evidence,
        "next_steps": next_steps,
        "executive_summary": executive_summary,
        "reporting": reporting_snapshot,
        "warnings": data.get("warnings", []),
        "model_status": "No trained LugandaGPT model exists. This report does not evaluate a model.",
    }
    return redact.redact_value(report)


def render_markdown(report):
    """Render the report dictionary as a readable Markdown document."""
    lines = []
    add = lines.append
    add("# LugandaGPT Project Reporter")
    add("")
    add(f"**Report ID:** `{report['report_id']}`  ")
    add(
        f"**Period:** {report['period']['start']} to {report['period']['end']} "
        f"({period_summary_text(report['period'])})  "
    )
    add(f"**Generated:** {report['generated_at']} ({report['timezone']})")
    add("")
    add(f"**Activity:** {report['activity_note']}")
    add("")

    executive = report.get("executive_summary") or {}
    if executive:
        add("## Executive summary")
        add("")
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
            add(f"- **{label}:** {executive.get(key)}")
        add("")

    git = report["git"]
    add("## Repository state")
    add("")
    if git["available"]:
        head = git.get("head") or {}
        add(f"- Branch: `{git.get('branch')}`")
        if head:
            add(
                f"- Latest commit: `{head.get('sha', '')[:12]}` {head.get('subject')} "
                f"({head.get('author')}, {head.get('authored_at')})"
            )
        add(f"- Working tree: {'clean' if git.get('clean') else 'has uncommitted changes'}")
        repository_state = report.get("repository_state") or {}
        if repository_state.get("changed_file_count"):
            add(f"- Note: {repository_state.get('note')}")
    else:
        add(f"- Git unavailable: {git.get('error')}")
    add("")

    summary = report["summary"]
    add("## Verified completed work")
    add("")
    if summary["verified_completed"]:
        for item in summary["verified_completed"]:
            when = f" [{item['when']}]" if item.get("when") else ""
            area = f"[{item['area']}] " if item.get("area") else ""
            add(f"- {area}{item['text']}{when} (evidence: {item['evidence']})")
    else:
        add("- None recorded in this period.")
    add("")

    add("## Attempted or incomplete work")
    add("")
    if summary["attempted_or_incomplete"]:
        for item in summary["attempted_or_incomplete"]:
            add(f"- {item['text']} (evidence: {item['evidence']})")
    else:
        add("- None recorded in this period.")
    repository_state = report.get("repository_state") or {}
    if repository_state.get("changed_file_count"):
        add(
            f"- Note: {repository_state['changed_file_count']} uncommitted "
            "working-tree change(s) are repository state (see Repository state), "
            "not incomplete tasks."
        )
    add("")

    add("## Failures and collection warnings")
    add("")
    if summary["failed_or_unavailable"]:
        for item in summary["failed_or_unavailable"]:
            add(f"- {item['text']} (evidence: {item['evidence']})")
    else:
        add("- None recorded in this period.")
    add("")

    add("## Human-reported activity")
    add("")
    if summary["human_reported"]:
        for item in summary["human_reported"]:
            when = f" [{item['when']}]" if item.get("when") else ""
            add(f"- {item['text']}{when} (source: {item['evidence']})")
    else:
        add("- None recorded in this period.")
    add("")

    tests = report["tests"]
    test_evidence = report.get("test_evidence") or {}
    add("## Tests")
    add("")
    if tests.get("status") == "available":
        add(f"Recorded output from `{tests.get('source')}`:")
        add(f"- Latest run: {describe_test_run(test_evidence.get('latest_run'))}")
        add(
            "- Latest successful run: "
            f"{describe_test_run(test_evidence.get('latest_successful_run'))}"
        )
        if test_evidence.get("undated_count"):
            add(
                f"- {test_evidence['undated_count']} recorded run(s) have no "
                "usable timestamp and cannot be ordered."
            )
        for run in tests.get("runs", []):
            outcome = test_outcome(run)
            add(
                f"- `{run.get('file')}`: {outcome}"
                f" (command: {run.get('command', 'unrecorded')}, "
                f"recorded {run.get('recorded_at', 'unknown')})"
            )
        add(
            "- Note: recorded tests verify software behaviour only; they do not "
            "measure Luganda language quality."
        )
    else:
        add(f"Unavailable: {tests.get('reason')}. No test result is claimed.")
    add("")

    experiments = report["experiments"]
    add("## Experiments")
    add("")
    if experiments.get("status") == "available":
        for entry in experiments.get("entries", []):
            add(f"- {entry['id']}: {entry.get('title')} (evidence: {entry['evidence']})")
    else:
        add(f"Unavailable: {experiments.get('reason')}. No experiment is claimed as run.")
    add("")

    add("## Decisions and blockers")
    add("")
    if report["blockers"]:
        for blocker in report["blockers"]:
            add(f"- {blocker['text']} (evidence: {blocker['evidence']})")
    else:
        add("- No documented blockers open in the roadmap or decision log.")
    add("")

    add("## Roadmap")
    add("")
    current = report["roadmap"]["current_phase"]
    if current:
        add(f"- Current phase: Phase {current['number']}: {current['title']} ({current['status']})")
    else:
        add("- Current phase: not determinable from the roadmap records.")
    for phase in report["roadmap"]["phases"]:
        add(f"- Phase {phase['number']}: {phase['title']} (status: {phase['status']})")
    add("")

    verification = report.get("phase_verification") or {}
    records = verification.get("criteria") or []
    add("## Phase exit criteria verification")
    add("")
    if not records:
        add(
            "- No recorded phase exit criteria are available to verify, so no "
            "phase completion is claimed."
        )
    else:
        summary = verification.get("summary") or {}
        label = (
            f"Phase {verification['phase']}: {verification['title']}"
            if verification.get("phase") is not None
            else "Current phase"
        )
        add(
            f"- {label}: {summary.get('verified_complete', 0)} of "
            f"{summary.get('total', 0)} recorded exit criteria verified complete "
            f"({'phase marked complete' if summary.get('phase_complete') else 'phase not complete'})."
        )
        for record in records:
            evidence = (
                "; ".join(record["evidence"])
                if record.get("evidence")
                else "evidence unavailable"
            )
            add(
                f"- [{record['status_label']}] {record['criterion']} "
                f"(evidence: {evidence}; {record['reason']})"
            )
    add("")

    add("## Verified spending")
    add("")
    spend = report["api_spending"]
    if spend["status"] == "available":
        add(
            f"- {spend['spend_usd']} USD from {spend['source']} "
            f"(retrieved {spend['retrieved_at']})"
        )
    else:
        add(f"- Unavailable: {spend['note']}. No zero or estimate is assumed.")
    add("")

    add("## Next priorities (roadmap requirements, options and approvals)")
    add("")
    for step in report["next_steps"]:
        extras = ""
        if step.get("evidence"):
            extras += "; evidence: " + "; ".join(step["evidence"])
        elif step.get("kind") == "mandatory":
            extras += "; evidence unavailable"
        add(
            f"- {step['text']} "
            f"({next_step_label(step)}; basis: {step['basis']}{extras})"
        )
    add("")

    add("## Evidence index")
    add("")
    if report["evidence"]:
        for item in report["evidence"]:
            add(f"- {item['claim']}: {item['source']}")
    else:
        add("- No verified claims recorded in this period.")
    add("")

    if report["warnings"]:
        add("## Warnings")
        add("")
        for warning in report["warnings"]:
            add(f"- {warning.get('source')}: {warning.get('error')}")
        add("")

    add("---")
    add("")
    add(
        "Facts in this report come from the sources cited above. "
        "Mandatory items are roadmap requirements, each shown with its "
        "verification status and evidence; approval items need the project "
        "owner's decision. "
        + report["model_status"]
    )
    add("")
    return redact.redact("\n".join(lines))


def generate_report(data=None, period_start=None, period_end=None, save=True, **kwargs):
    """Build, render and optionally store a report.

    Returns (report, markdown, created). created is False when a report
    with this id already exists, so history is never overwritten.
    """
    report = build_report(
        data=data, period_start=period_start, period_end=period_end, **kwargs
    )
    markdown = render_markdown(report)
    created = False
    if save:
        _, created = store.save_report(report, markdown)
    return report, markdown, created


def report_as_json(report):
    """Serialize a report. Used by the API and by tests."""
    return json.dumps(report, indent=2, ensure_ascii=False)
