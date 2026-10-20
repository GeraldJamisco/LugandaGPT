"""Command line entry point: python -m reporter <command>.

Collection commands are read-only. Network calls to Telegram happen only for
the owner-requested commands: telegram check, telegram test, report --send,
deliver and the scheduler once it is enabled.
"""

import argparse
import json
import os
import sys

from . import collect, config, report, runner, scheduler, store, telegram_client
from . import dashboard as dashboard_mod


def _print(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_serve(args):
    dashboard_mod.serve(host=args.host, port=args.port)
    return 0


def cmd_report(args):
    result = runner.run_once(send=args.send, source="cli")
    _print(result)
    if not result.get("ok", True):
        return 1
    if args.send and result.get("delivery") and not result["delivery"].get("ok"):
        return 1
    return 0


def cmd_deliver(args):
    outcome = runner.retry_delivery(report_id=args.report_id, source="cli")
    _print({"ok": bool(outcome.get("ok")), "result": outcome})
    return 0 if outcome.get("ok") else 1


def cmd_status(args):
    overview = dashboard_mod.overview()
    _print(
        {
            "repo": overview["repo"],
            "phase": overview["phase"]["current"],
            "tests": overview["tests"]["status"],
            "experiments": overview["experiments"]["status"],
            "api_spending": overview["api_spending"]["status"],
            "schedule": overview["schedule"],
            "reporting": overview["reporting"],
            "telegram": overview["telegram"],
            "reports": len(overview["reports"]),
            "model_status": overview["model_status"],
        }
    )
    return 0


def cmd_collect(args):
    _print(collect.collect_all(commit_limit=args.commits))
    return 0


def cmd_telegram_check(args):
    status = telegram_client.status()
    if not status["ready"]:
        _print({"ok": False, "stage": "configuration", "problems": status["problems"]})
        return 1
    try:
        me = telegram_client.get_me()
    except telegram_client.TelegramError as exc:
        _print({"ok": False, "stage": "getMe", "error": str(exc)})
        return 1
    matches = me.get("username") == config.BOT_USERNAME
    _print(
        {
            "ok": matches,
            "stage": "getMe",
            "bot_username": me.get("username"),
            "expected_bot_username": config.BOT_USERNAME,
            "matches_expected": matches,
        }
    )
    return 0 if matches else 1


def cmd_telegram_test(args):
    if args.get_me_only:
        outcome = telegram_client.run_delivery_test(send_real_message=False)
    else:
        outcome = telegram_client.run_delivery_test()
    _print(outcome)
    return 0 if outcome.get("ok") else 1


def cmd_schedule(args):
    if args.action == "status":
        _print(scheduler.schedule_status())
        return 0
    outcome = scheduler.set_enabled(args.action == "enable")
    _print(outcome)
    return 0 if outcome.get("ok") else 1


def cmd_add_activity(args):
    entry = runner.record_activity(args.text, author=args.author)
    _print({"ok": True, "entry": entry})
    return 0


def cmd_stop(args):
    if not config.PID_FILE.exists():
        print("Reporter is not running (no pid file).")
        return 1
    raw = config.PID_FILE.read_text(encoding="utf-8").strip()
    if not raw.isdigit():
        print("pid file is malformed; not stopping anything.")
        return 1
    pid = int(raw)
    if pid == os.getpid():
        print("Refusing to stop the current process.")
        return 1
    try:
        os.kill(pid, signal_term())
    except ProcessLookupError:
        print(f"No process with pid {pid}.")
        config.PID_FILE.unlink()
        return 1
    except PermissionError:
        print(f"No permission to stop pid {pid}.")
        return 1
    print(f"Sent stop signal to pid {pid}.")
    return 0


def signal_term():
    import signal

    return signal.SIGTERM


def build_parser():
    parser = argparse.ArgumentParser(
        prog="reporter",
        description=(
            "LugandaGPT Project Reporter: read-only activity collection, "
            "local reports, local dashboard and opt-in Telegram delivery."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="run the local dashboard")
    serve.add_argument("--host", default=config.DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    serve.set_defaults(func=cmd_serve)

    rep = sub.add_parser("report", help="generate one report now")
    rep.add_argument(
        "--send",
        action="store_true",
        help="also deliver to Telegram; requires a passed delivery test",
    )
    rep.set_defaults(func=cmd_report)

    dlv = sub.add_parser(
        "deliver",
        help="retry delivery of a saved report without regenerating it",
    )
    dlv.add_argument(
        "--report-id",
        default=None,
        help="saved report to deliver; defaults to the report awaiting delivery",
    )
    dlv.set_defaults(func=cmd_deliver)

    status = sub.add_parser("status", help="print a compact status summary")
    status.set_defaults(func=cmd_status)

    col = sub.add_parser("collect", help="print collected activity as JSON")
    col.add_argument("--commits", type=int, default=10)
    col.set_defaults(func=cmd_collect)

    tg = sub.add_parser("telegram", help="Telegram verification (manual)")
    tg_sub = tg.add_subparsers(dest="telegram_action")
    check = tg_sub.add_parser("check", help="call getMe and verify the bot username")
    check.set_defaults(func=cmd_telegram_check)
    test = tg_sub.add_parser("test", help="send one short test message")
    test.add_argument("--get-me-only", action="store_true")
    test.set_defaults(func=cmd_telegram_test)
    tg.set_defaults(func=cmd_telegram_check)

    sched = sub.add_parser("schedule", help="show or toggle automatic reporting")
    sched.add_argument("action", choices=["status", "enable", "disable"])
    sched.set_defaults(func=cmd_schedule)

    activity = sub.add_parser("add-activity", help="record a human-entered activity")
    activity.add_argument("text")
    activity.add_argument("--author")
    activity.set_defaults(func=cmd_add_activity)

    stop = sub.add_parser("stop", help="stop a dashboard started by 'serve'")
    stop.set_defaults(func=cmd_stop)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        if getattr(args, "command", None) == "telegram":
            args.func = cmd_telegram_check
        else:
            parser.print_help()
            return 0
    config.ensure_dirs()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
