"""Local dashboard: stdlib HTTP server bound to localhost.

Read-only with respect to project code. No endpoint executes commands,
no endpoint accepts a filesystem path, and mutating endpoints require a
matching origin plus an explicit content type.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from . import collect, config, redact, report, runner, scheduler, store, telegram_client

REPORT_ID_RE = re.compile(r"^[A-Za-z0-9\-]+$")
REPORT_ROUTE_RE = re.compile(r"^/api/report/([A-Za-z0-9\-]+)(/markdown)?$")
STATIC_ROUTE_RE = re.compile(r"^/static/([A-Za-z0-9\.\-_]+)$")

GET_ROUTES = (
    "/",
    "/api/overview",
    "/api/reports",
    "/api/report/<id>",
    "/api/report/<id>/markdown",
    "/api/schedule",
    "/api/telegram/status",
)
POST_ROUTES = (
    "/api/report/generate",
    "/api/report/deliver",
    "/api/telegram/test",
    "/api/schedule",
)
ALLOWED_BODY_KEYS = {
    "/api/report/generate": set(),
    "/api/report/deliver": {"report_id"},
    "/api/telegram/test": set(),
    "/api/schedule": {"enabled"},
}
LOCAL_CLIENT_HEADER = "X-Reporter-Client"


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def overview():
    """Everything the dashboard shows, assembled from verified sources."""
    data = collect.collect_all(commit_limit=10)
    roadmap = data.get("roadmap", {})
    git = data.get("git", {})
    reports = store.list_reports(limit=10)

    timeline = []
    if reports:
        try:
            latest = store.load_report_json(reports[0]["report_id"])
            timeline = [
                {
                    "id": event.get("id"),
                    "kind": event.get("kind"),
                    "label": event.get("label"),
                    "timestamp": event.get("timestamp"),
                    "evidence": event.get("evidence"),
                    "previously_reported": event.get("previously_reported"),
                }
                for event in latest.get("events", [])[:30]
            ]
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            timeline = []

    return {
        "generated_at": _now_iso(),
        "model_status": (
            "No trained LugandaGPT model exists. "
            "This dashboard does not evaluate a model."
        ),
        "repo": {
            "available": git.get("available"),
            "error": git.get("error"),
            "branch": git.get("branch"),
            "head": git.get("head"),
            "clean": git.get("clean"),
            "changed_file_count": len(git.get("changes", [])),
            "changed_files": git.get("changes", []),
        },
        "phase": {
            "current": roadmap.get("current_phase"),
            "all": roadmap.get("phases", []),
        },
        "blockers": data.get("decisions", {}).get("open", [])
        + roadmap.get("blockers", []),
        "milestones": roadmap.get("upcoming", []),
        "tests": data.get("tests"),
        "experiments": data.get("experiments"),
        "api_spending": data.get("api_usage"),
        "human_activity": data.get("human_activity"),
        "schedule": scheduler.schedule_status(),
        "reporting": runner.reporting_status(),
        "telegram": telegram_client.status(),
        "reports": reports,
        "timeline": timeline,
        "delivery_log": store.read_delivery_log(limit=10),
        "public_drafts": {
            "status": "not implemented (Stage E of docs/PROJECT_REPORTER_SPEC.md)"
        },
        "warnings": data.get("warnings", []),
    }


class ReporterHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "LugandaGPTReporter/0.1"

    # --- response helpers -------------------------------------------------

    def log_message(self, fmt, *args):
        line = fmt % args
        sys.stderr.write(f"[reporter] {redact.redact(line)}\n")

    def _send(self, status, body, content_type):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload, status=200):
        self._send(
            status,
            json.dumps(payload, indent=2, ensure_ascii=False),
            "application/json; charset=utf-8",
        )

    def _error(self, status, message):
        self._send_json({"ok": False, "error": message}, status=status)

    # --- request guards ---------------------------------------------------

    def _host_allowed(self):
        host = (self.headers.get("Host") or "").strip().lower()
        allowed = {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
            "127.0.0.1",
            "localhost",
        }
        return host in allowed

    def _origin_allowed(self):
        origin = self.headers.get("Origin")
        if origin:
            return origin.rstrip("/") in self.server.allowed_origins
        # Browsers always send Origin on cross-site writes; a client that
        # omits it must identify itself explicitly.
        return (self.headers.get(LOCAL_CLIENT_HEADER) or "").strip() == "local"

    def _read_json_body(self):
        length = self.headers.get("Content-Length")
        if length is None:
            self._error(400, "missing Content-Length")
            return None
        try:
            size = int(length)
        except ValueError:
            self._error(400, "invalid Content-Length")
            return None
        if size > config.MAX_POST_BODY_BYTES:
            self._error(413, "request body too large")
            return None
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if content_type != "application/json":
            self._error(415, "Content-Type must be application/json")
            return None
        raw = self.rfile.read(size)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(400, "body is not valid JSON")
            return None
        if not isinstance(payload, dict):
            self._error(400, "body must be a JSON object")
            return None
        return payload

    # --- GET --------------------------------------------------------------

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._host_allowed():
            self._error(403, "invalid Host header")
            return
        path = unquote(urlsplit(self.path).path)

        if path == "/":
            self._serve_static("index.html")
            return
        static_match = STATIC_ROUTE_RE.match(path)
        if static_match:
            self._serve_static(static_match.group(1))
            return

        if path == "/api/overview":
            self._send_json({"ok": True, "overview": overview()})
            return
        if path == "/api/reports":
            self._send_json({"ok": True, "reports": store.list_reports(limit=100)})
            return
        if path == "/api/schedule":
            self._send_json({"ok": True, "schedule": scheduler.schedule_status()})
            return
        if path == "/api/telegram/status":
            self._send_json({"ok": True, "telegram": telegram_client.status()})
            return

        report_match = REPORT_ROUTE_RE.match(path)
        if report_match:
            report_id = report_match.group(1)
            if not store.is_valid_report_id(report_id):
                # Anything that is not shaped like a stored report id,
                # including traversal attempts, is simply not found.
                self._error(404, "report not found")
                return
            try:
                if report_match.group(2):
                    body = store.load_report_markdown(report_id)
                    self._send(200, body, "text/markdown; charset=utf-8")
                else:
                    self._send_json(
                        {"ok": True, "report": store.load_report_json(report_id)}
                    )
            except (FileNotFoundError, ValueError):
                self._error(404, "report not found")
            return

        self._error(404, "unknown endpoint")

    def _serve_static(self, name):
        if name not in config.STATIC_FILES:
            self._error(404, "not found")
            return
        path = config.STATIC_DIR / name
        try:
            body = path.read_bytes()
        except OSError:
            self._error(404, "not found")
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(path.suffix, "application/octet-stream")
        self._send(200, body, content_type)

    # --- POST -------------------------------------------------------------

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._host_allowed():
            self._error(403, "invalid Host header")
            return
        path = unquote(urlsplit(self.path).path)
        if path not in POST_ROUTES:
            self._error(404, "unknown endpoint")
            return
        if not self._origin_allowed():
            self._error(403, "origin not allowed")
            return

        payload = self._read_json_body()
        if payload is None:
            return
        unexpected = set(payload) - ALLOWED_BODY_KEYS[path]
        if unexpected:
            self._error(400, f"unexpected fields: {', '.join(sorted(unexpected))}")
            return

        if path == "/api/report/generate":
            result = runner.run_once(send=False, source="dashboard")
            if not result.get("ok", True):
                self._send_json(
                    {"ok": False, "error": result.get("error"), "result": result},
                    status=500,
                )
                return
            self._send_json({"ok": True, "result": result, "reporting": runner.reporting_status()})
            return

        if path == "/api/report/deliver":
            report_id = payload.get("report_id")
            if report_id is not None:
                if not isinstance(report_id, str) or not store.is_valid_report_id(report_id):
                    self._error(400, "invalid report id")
                    return
            outcome = runner.retry_delivery(report_id=report_id, source="dashboard")
            status = 200 if outcome.get("ok") else 409
            if outcome.get("stage") == "select":
                status = 404
            self._send_json(
                {
                    "ok": bool(outcome.get("ok")),
                    "result": outcome,
                    "reporting": runner.reporting_status(),
                },
                status=status,
            )
            return

        if path == "/api/telegram/test":
            try:
                outcome = telegram_client.run_delivery_test()
            except Exception as exc:  # noqa: BLE001
                self._error(500, f"delivery test failed: {type(exc).__name__}")
                return
            self._send_json({"ok": bool(outcome.get("ok")), "result": outcome})
            return

        if path == "/api/schedule":
            enabled = payload.get("enabled")
            if not isinstance(enabled, bool):
                self._error(400, "'enabled' must be a boolean")
                return
            outcome = scheduler.set_enabled(enabled)
            self._send_json(
                {
                    "ok": bool(outcome.get("ok")),
                    "result": outcome,
                    "schedule": scheduler.schedule_status(),
                },
                status=200 if outcome.get("ok") else 409,
            )
            return

        self._error(404, "unknown endpoint")

    def do_PUT(self):  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self):  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self):  # noqa: N802
        self._method_not_allowed()

    def _method_not_allowed(self):
        if not self._host_allowed():
            self._error(403, "invalid Host header")
            return
        self.send_response(405)
        self.send_header("Allow", "GET, POST")
        self.send_header("Content-Length", "0")
        self.end_headers()


class DashboardServer(ThreadingHTTPServer):
    # SO_REUSEADDR is on by default here so restarting the reporter quickly
    # does not fail on a lingering socket. On Windows that same flag lets a
    # second process bind a port that is already in use, so tests and other
    # throwaway servers pass reuse_address=False and can never steal the
    # live reporter's port.
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, reuse_address=True):
        self.allow_reuse_address = bool(reuse_address)
        super().__init__(address, ReporterHandler)
        host, port = self.server_address[0], self.server_port
        self.allowed_origins = {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            f"http://[{host}]:{port}",
        }


def create_server(host=None, port=None, reuse_address=True):
    host = host or config.DEFAULT_HOST
    # port 0 means "any free port" and must survive, not fall back to the
    # default: falling back here made throwaway servers bind the live
    # reporter's port instead of their own.
    port = config.DEFAULT_PORT if port is None else int(port)
    return DashboardServer((host, port), reuse_address=reuse_address)


def serve(host=None, port=None):
    """Start the dashboard and block until interrupted."""
    config.ensure_dirs()
    server = create_server(host, port)
    url = f"http://127.0.0.1:{server.server_port}/"
    config.PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    thread = scheduler.Scheduler(runner_job, tick_seconds=30.0)
    thread.start()
    print(f"LugandaGPT Project Reporter listening on {url}")
    schedule = scheduler.schedule_status()
    print(
        "Automatic reporting: "
        + (
            f"enabled, next run {schedule['next_run_at']} ({schedule['timezone']})"
            if schedule["enabled"]
            else "disabled until the owner enables it"
        )
    )
    print("Keep this process running for scheduled reports; closing the browser does not stop it.")
    print("Stop with Ctrl+C.")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nStopping reporter.")
    finally:
        thread.stop()
        server.server_close()
        try:
            config.PID_FILE.unlink()
        except OSError:
            pass


def runner_job():
    """Scheduler callback: generate a report and deliver it when approved."""
    return runner.run_once(send=True, source="scheduler")
