"""Command line tools for the Sunbird API connection.

    python -m sunbird_api check
    python -m sunbird_api chat "Translate from English to Luganda: Good morning"
    python -m sunbird_api translate-source --dry-run
    python -m sunbird_api translate-source --max-requests 400

Only project-authored English source text is ever sent. Teacher translations,
reviews, and account data are never read by this module. Output is machine
suggestions for comparison, not training data and not Studio submissions.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import (
    DEFAULT_MODEL,
    MODELS,
    SunbirdClient,
    SunbirdError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = "data/source/pilot-v1/translator_export.csv"
DEFAULT_OUTPUT = "data/machine/sunbird-suggestions.csv"
DEFAULT_LEDGER = "reports/sunbird/usage-ledger.jsonl"
DEFAULT_CAP = 25

# The Studio fields each suggestion is meant to be compared against.
FIELD_SOURCES = (
    ("source_context", "source_context_en"),
    ("prior_turns", "prior_turns_en"),
    ("source_prompt", "source_prompt_en"),
    ("reference_answer", "reference_answer_or_rubric_en"),
)
OUTPUT_COLUMNS = (
    "item_id",
    "field",
    "english",
    "sunbird_luganda",
    "model",
    "temperature",
    "finish_reason",
    "prompt_tokens",
    "completion_tokens",
    "created_utc",
    "machine_output",
    "review_status",
)


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _client_from_args(args):
    return SunbirdClient(
        request_cap=args.max_requests,
        ledger_path=PROJECT_ROOT / args.ledger,
    )


def _read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    needed = {"item_id"} | {column for _, column in FIELD_SOURCES}
    missing = needed - set(rows[0].keys() if rows else needed)
    if missing:
        raise SunbirdError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    return rows


def _turns(raw):
    try:
        turns = json.loads(raw)
    except ValueError:
        raise SunbirdError("prior_turns_en is not valid JSON") from None
    if not isinstance(turns, list) or not all(
        isinstance(t, dict) and isinstance(t.get("content"), str) for t in turns
    ):
        raise SunbirdError("prior_turns_en must be a list of turns with text content")
    return turns


def build_tasks(rows, only_ids=None, limit=None):
    """One task per item field that has English text. A task may need several requests."""
    tasks = []
    selected = [r for r in rows if not only_ids or r["item_id"] in only_ids]
    if limit is not None:
        selected = selected[:limit]
    for row in selected:
        for name, column in FIELD_SOURCES:
            text = (row.get(column) or "").strip()
            if not text:
                continue
            if name == "prior_turns":
                turns = _turns(text)
                tasks.append(
                    {"item_id": row["item_id"], "field": name, "english": text,
                     "turns": turns, "requests": len(turns)}
                )
            else:
                tasks.append(
                    {"item_id": row["item_id"], "field": name, "english": text,
                     "requests": 1}
                )
    return tasks


def _done_keys(path):
    if not path.is_file():
        return set()
    with open(path, newline="", encoding="utf-8") as handle:
        return {(r["item_id"], r["field"]) for r in csv.DictReader(handle)}


def _append_row(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.is_file()
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def _run_task(client, task, args):
    results = []
    if task["field"] == "prior_turns":
        translated = []
        for turn in task["turns"]:
            result = client.translate(
                turn["content"], model=args.model, temperature=args.temperature,
                max_tokens=args.max_tokens, purpose="translate-source:prior_turns",
            )
            results.append(result)
            translated.append({"role": turn.get("role", ""), "content": result.text})
        luganda = json.dumps(translated, ensure_ascii=False)
    else:
        result = client.translate(
            task["english"], model=args.model, temperature=args.temperature,
            max_tokens=args.max_tokens, purpose=f"translate-source:{task['field']}",
        )
        results.append(result)
        luganda = result.text
    finishes = sorted({r.finish_reason for r in results})
    return {
        "item_id": task["item_id"],
        "field": task["field"],
        "english": task["english"],
        "sunbird_luganda": luganda,
        "model": results[0].model,
        "temperature": args.temperature,
        "finish_reason": "|".join(finishes),
        "prompt_tokens": sum(r.usage.get("prompt_tokens", 0) for r in results),
        "completion_tokens": sum(r.usage.get("completion_tokens", 0) for r in results),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "machine_output": "true",
        "review_status": "unreviewed",
    }


def _check(args, client_factory):
    client = client_factory(args)
    info = client.check()
    _print(
        {
            "status": "token_valid",
            "username": info.get("username"),
            "fields_reported": sorted(info.keys()),
            "note": "token and email are never printed",
        }
    )
    return 0


def _chat(args, client_factory):
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    client = client_factory(args)
    result = client.chat(
        messages, model=args.model, temperature=args.temperature,
        max_tokens=args.max_tokens, purpose="chat",
    )
    _print(
        {
            "model": result.model,
            "finish_reason": result.finish_reason,
            "usage": result.usage,
            "text": result.text,
        }
    )
    return 0


def _translate_source(args, client_factory):
    input_path = PROJECT_ROOT / args.input
    output_path = PROJECT_ROOT / args.output
    only_ids = set(args.ids.split(",")) if args.ids else None
    tasks = build_tasks(_read_rows(input_path), only_ids=only_ids, limit=args.limit)
    done = _done_keys(output_path)
    pending = [t for t in tasks if (t["item_id"], t["field"]) not in done]
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "model": args.model,
        "tasks_total": len(tasks),
        "tasks_already_done": len(tasks) - len(pending),
        "tasks_pending": len(pending),
        "requests_pending": sum(t["requests"] for t in pending),
        "request_cap": args.max_requests,
    }
    if args.dry_run:
        _print({"status": "dry_run", "sent_anything": False, **summary})
        return 0
    if not pending:
        _print({"status": "nothing_to_do", **summary})
        return 0
    client = client_factory(args)
    written = 0
    stopped = "completed"
    for task in pending:
        if client.requests_made + task["requests"] > args.max_requests:
            stopped = "request_cap_reached"
            break
        try:
            row = _run_task(client, task, args)
        except SunbirdError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            stopped = "error"
            break
        _append_row(output_path, row)
        written += 1
    _print(
        {
            "status": stopped,
            "tasks_written_this_run": written,
            "requests_made": client.requests_made,
            "tasks_remaining": len(pending) - written,
            "machine_output_note": "suggestions only; not Studio submissions and not training data",
            **summary,
        }
    )
    return 2 if stopped == "error" else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m sunbird_api",
        description="Sunbird AI API tools. Credentials come from the environment.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
        p.add_argument("--temperature", type=float, default=0.3)
        p.add_argument("--max-tokens", type=int, default=512)
        p.add_argument("--max-requests", type=int, default=DEFAULT_CAP,
                       help="hard cap on requests this run (default %(default)s)")
        p.add_argument("--ledger", default=DEFAULT_LEDGER)

    check = sub.add_parser("check", help="verify the token without generating text")
    check.add_argument("--max-requests", type=int, default=DEFAULT_CAP)
    check.add_argument("--ledger", default=DEFAULT_LEDGER)
    check.set_defaults(handler=_check)

    chat = sub.add_parser("chat", help="send one prompt to Sunflower")
    chat.add_argument("prompt")
    chat.add_argument("--system")
    common(chat)
    chat.set_defaults(handler=_chat)

    ts = sub.add_parser(
        "translate-source",
        help="get Sunflower English-to-Luganda suggestions for the source records",
    )
    ts.add_argument("--input", default=DEFAULT_INPUT)
    ts.add_argument("--output", default=DEFAULT_OUTPUT)
    ts.add_argument("--ids", help="comma-separated item IDs, for example E-001,P-001")
    ts.add_argument("--limit", type=int, help="only the first N items")
    ts.add_argument("--dry-run", action="store_true", help="count work, send nothing")
    common(ts)
    ts.set_defaults(handler=_translate_source)
    return parser


def default_client_factory(args):
    return _client_from_args(args)


def main(argv=None, *, client_factory=default_client_factory):
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args, client_factory)
    except SunbirdError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
