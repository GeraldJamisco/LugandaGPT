# LugandaGPT Project Reporter

The Project Reporter collects recorded project activity, writes a local
report, and can deliver that report to the private Telegram group. It runs
on this machine with Python 3.13 and the standard library only.

No trained LugandaGPT model exists. Every report describes recorded
project activity (commits, recorded test output, experiment log entries,
documented decisions). It is not an evaluation of any model.

The requirements are in `docs/PROJECT_REPORTER_SPEC.md`. This file is the
operating guide: how to run the reporter, how to confirm that a report
arrived, and what to do when delivery fails.

## Components

| Piece | File |
| --- | --- |
| Command line entry | `src\reporter\__main__.py` |
| Shared generate and deliver pipeline | `src\reporter\runner.py` |
| Report builder | `src\reporter\report.py` |
| Telegram client | `src\reporter\telegram_client.py` |
| Scheduler (in-process, disabled by default) | `src\reporter\scheduler.py` |
| Local dashboard | `src\reporter\dashboard.py`, `src\reporter\static\` |
| Local output (ignored by Git) | `reports\reporter\` |

## One-time setup in Windows CMD

Run every command from the repository root:

```bat
set PYTHONPATH=%CD%\src
python -m reporter status
```

`PYTHONPATH` is needed in each new CMD window because the package lives
under `src\`. `status` is read-only: it prints repository, phase, test,
experiment, spending, schedule, reporting and Telegram state, and never
contacts Telegram.

The bot credentials come from the environment and are never written to
source, state, logs, reports or messages:

```bat
set LUGANDAGPT_TELEGRAM_BOT_TOKEN=<bot token>
set LUGANDAGPT_TELEGRAM_CHAT_ID=<numeric chat id of the private group>
python -m reporter telegram check
```

`telegram check` calls getMe only. It sends no message and prints no
token. `set` lasts for the current window; `setx` keeps values for new
windows. Either way the values stay out of Git, and they must never be
pasted into a document, log, commit or chat.

## What is diagnostic and what is real

| Command | Sends a Telegram message | Writes a report |
| --- | --- | --- |
| `python -m reporter status` | no | no |
| `python -m reporter collect` | no | no |
| `python -m reporter telegram check` | no (getMe only) | no |
| `python -m reporter telegram test --get-me-only` | no | no |
| `python -m reporter telegram test` | one short test message | no |
| `python -m reporter report` | no | yes |
| `python -m reporter report --send` | the full report | yes |
| `python -m reporter deliver` | the full report, if one is waiting | no |
| `python -m reporter serve` | nothing on start | no |

`status` and `collect` are diagnostics. `report` writes the real report
file to `reports\reporter\archive\` and sends nothing. Only
`telegram test`, `report --send`, `deliver`, and the scheduler after it is
enabled can put a message in the group.

## Report content in Telegram

The delivered message is plain text with thirteen numbered sections:
executive summary, verified completed work, attempted or incomplete work,
recorded failures and collection warnings, human-reported activity, git
activity, recorded test results, experiments, blockers, next priorities,
verified spending, reporting and delivery health, and the local report
reference with the evidence index.

Nothing is shortened. A report that exceeds the 4096 character limit is
split into ordered parts, each labelled `part i of n` with the report id,
so the whole content reaches the phone. Missing data is shown as
unavailable, never as zero or an estimate.

Three things are kept deliberately separate in the text. The executive
summary answers what changed, what was completed, what remains incomplete,
the latest recorded test state, whether core research or model development
advanced, the Phase exit criteria verification, the next milestone and any
owner decisions. The reporting and delivery health section states only
what was observed when the report was generated; the outcome of the current
send is recorded afterwards in `state.json`, `delivery.log` and the
dashboard, never claimed inside the message itself. Working-tree changes are
listed as repository state, not classified as incomplete work.

### Test evidence

Test results come only from the JSON records in `reports\reporter\test_runs\`,
never from filename order and never parsed out of a summary sentence. Runs
are ordered by their own `recorded_at`. The report shows two lines:

- Latest run: the run with the newest recorded timestamp.
- Latest successful run: the newest run whose record passes.

They are kept apart so that a newer failing run is never reported as its own
older success. `tests_run` and `duration_seconds` are shown when present; a
missing field is printed as `test count unavailable` or
`duration unavailable`, not left out or estimated. A record without a usable
timestamp is counted separately and is not used as the latest run.

### Exit criteria verification

Each recorded exit criterion gets one of four statuses:

| Status | Meaning |
| --- | --- |
| verified complete | an owner verification record confirms it, with a note |
| incomplete | an automated check found a required artifact missing |
| needs review | automated evidence exists, but completion needs human judgement |
| not verified | no automated check is registered and no evidence is available |

Automated checks never mark a criterion complete on their own: files existing
is not proof that documentation is consistent or that no secret was ever
committed. A phase is marked complete only when every recorded criterion is
verified complete, and never when the criteria list is empty. When more than
one criterion is pending, the report states the available evidence does not
establish an ordering rather than inventing one.

Owner verification records are read from an optional, read-only file
`reports\reporter\exit_criteria_verification.json`. The reporter never writes
it. Its shape is:

```json
{
  "Phase 0": {
    "Documentation inventory complete and internally consistent.": {
      "status": "verified complete",
      "verified_at": "2026-10-19T00:00:00+00:00",
      "author": "Project Owner",
      "note": "Reviewed each file against the roadmap."
    }
  }
}
```

A record whose status is `verified complete` but has no note is downgraded to
`needs review`, so a status is never shown without supporting evidence.

## Proving delivery before enabling anything

```bat
python -m reporter telegram check
python -m reporter telegram test
python -m reporter report
python -m reporter report --send
```

You should see one test message, then the full report in the group. Both
the passed delivery test and at least one saved report are required
before scheduled reporting can be enabled; the enable command refuses to
run otherwise and prints which condition is missing.

## Dashboard

```bat
python -m reporter serve
```

Open `http://127.0.0.1:8765`. The action panel offers Generate report,
Retry delivery, Test Telegram delivery, Enable schedule and Disable
schedule. The "Latest report and delivery" card shows the last generation
result, the last delivery result with parts sent of parts total, and any
report still awaiting delivery.

The dashboard binds to 127.0.0.1 only. It returns report ids and masked
chat ids, never tokens or filesystem paths.

Keep the CMD window open: closing the browser does not stop the process.
`Ctrl+C` in that window stops it. No Windows service and no scheduled
task are created. `python -m reporter stop` sends a stop signal to a
`serve` process started earlier (it reads `reports\reporter\server.pid`).

## Confirming that a report arrived

- The group itself: each delivered report arrives as one or more messages
  headed `LugandaGPT Project Report` with its report id.
- Dashboard card "Latest report and delivery": delivered or failed, with
  time, source and part counts.
- `python -m reporter status`, field `reporting`: the same data as JSON.
- `reports\reporter\delivery.log`: one line per attempt, including
  transient retries and failures.
- `reports\reporter\state.json`, key `pending_delivery`: present while a
  saved report has not reached Telegram, cleared on success. The state
  file never holds credentials.

## When delivery fails

A failure leaves the saved report file untouched and records the report
as awaiting delivery with the error, the attempt count and the number of
parts already confirmed.

Retry without regenerating:

```bat
python -m reporter deliver
python -m reporter deliver --report-id RPT-20261019-192842-P8H
```

or press Retry delivery in the dashboard. A retry resumes after the last
part Telegram confirmed, so parts already in the group are not repeated.
A report id that is already recorded as delivered is never sent again;
the retry output says `duplicate send skipped`.

One known gap: if the process dies between Telegram accepting a message
and the state file being written, the next retry can repeat that one part
once. If the process crashed mid-delivery, look at the group before
retrying.

Common failure reasons:

| Message | Fix |
| --- | --- |
| `manual Telegram delivery test has not passed` | run `python -m reporter telegram test` |
| `no saved report is awaiting delivery` | run `python -m reporter report` |
| `Bad Request: chat not found` | chat id is wrong, or the bot is not in the group |
| `token is not configured` or invalid token | set the token variable again, then `telegram check` |
| `report generation failed` | the collector failed; the error and stage are printed, nothing was sent |

## Scheduled reporting

Disabled by default. Enabling requires both safety conditions: a passed
manual Telegram delivery test and at least one saved report.

```bat
python -m reporter schedule status
python -m reporter schedule enable
python -m reporter schedule disable
```

The dashboard buttons do the same. Slots are fixed wall-clock times in
East Africa Time: 06:00, 14:00 and 22:00 EAT (UTC+3), eight hours apart.

The scheduler runs inside the reporter process only. For scheduled
reports to happen the process must be running at the slot time and the
computer must be on. While the process is down nothing runs; when it
comes back, at most one catch-up run happens and any further missed slots
are counted in `last_result.missed_periods_skipped` instead of being
fired in a burst.

`schedule status` prints `last_result`, which records whether generation
succeeded and whether delivery succeeded: `generated`, `sent`,
`delivery_ok`, `delivery_error`, `delivery_parts_sent` and
`delivery_parts_total`. Delivery of a scheduled report still requires the
delivery test to have passed.

Restart `serve` after changing the code: a running process keeps the code
it loaded when it started.

## Where output lives

All paths are under `reports\reporter\`, which Git ignores:

| Path | Content |
| --- | --- |
| `archive\<id>.md` and `<id>.json` | report files, written once, never overwritten |
| `state.json` | schedule flag, delivery test state, last report, last delivery, pending delivery |
| `delivery.log` | one line per delivery or generation attempt |
| `test_runs\*.json` | recorded test output that reports are allowed to cite |
| `human_activity.json` | entries added with `add-activity` |
| `exit_criteria_verification.json` | optional owner verification records, read only, never written by the reporter |
| `server.pid` | pid of the running dashboard |

Reports cite only what is recorded in those files. If `test_runs` is
empty the report says test output is unavailable and claims no result. A
test record's count and duration are cited only when the JSON carries the
`tests_run` and `duration_seconds` fields.

## Tests

```bat
python -m unittest discover -s tests -t . -v
```

No test contacts Telegram: outbound HTTP is blocked inside the test base
class, and dashboard test servers bind their own free port instead of the
dashboard port. The latest recorded full run is
`reports\reporter\test_runs\2026-10-19-reporter-suite.json` (148 tests, OK).
The reporter cites whichever record has the newest `recorded_at`, so after
adding tests write a new record with `tests_run` and `duration_seconds` so
reports point at current evidence.

## Rules that still apply

`AGENTS.md` governs this tool like the rest of the repository: no paid
API calls or spending, no commits or pushes without approval, no
credentials in any file, and no claim that scheduled delivery works until
a real scheduled run has been observed end to end. Scheduled reporting
stays disabled until the project director enables it deliberately.
