"""Local-only WSGI application for LugandaGPT Translation Studio."""

import hmac
import json
import mimetypes
import re
import secrets
import traceback
from contextlib import closing
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from training.constants import CAPABILITIES, VALIDATION_CHECKS

from . import auth
from .db import (
    connect,
    get_item,
    get_meta,
    get_user,
    item_source,
    list_users,
    set_meta,
)
from .source_import import collection_counts, import_source, item_count
from .reward_rules import COMPLETED_REVIEW_CENTS, TRANSLATION_APPROVAL_CENTS
from .workflow import (
    DEFAULT_EXPORT_DIR,
    TRANSLATION_STATUSES,
    WorkflowError,
    admin_counts,
    admin_items,
    all_payables,
    all_translator_rewards,
    approve_dataset,
    assigned_items,
    assign_review,
    assign_translation,
    assignments_for_item,
    bulk_assign_review,
    bulk_assign_translation,
    dataset_blockers,
    export_review_csv,
    export_training_jsonl,
    is_reward_eligible,
    item_audit,
    next_translation_item,
    previous_translation_item,
    progress_counts,
    recent_audit,
    record_payment,
    resolution_history,
    resolve_dispute,
    review_history,
    reviewer_reward,
    revoke_dataset,
    return_translation,
    save_translation,
    submit_review,
    training_metadata_view,
    translation_view,
    translator_reward,
    update_training_metadata,
    validation_values,
    version_history,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"
MAX_BODY = 2_000_000
SESSION_COOKIE = "studio_session"
PREAUTH_COOKIE = "studio_preauth"

CAPABILITY_LABELS = {
    "formal_comprehension": "Reading and understanding",
    "formal_generation": "Writing in Luganda",
    "rewriting_formal_luganda": "Making an English passage more formal",
    "question_answering": "Answering a question",
    "instruction_following": "Following instructions",
    "short_conversation": "Understanding a conversation",
}
CAPABILITY_PURPOSE = {
    "formal_comprehension": "Read the English passage and answer or summarize it using only the information provided.",
    "formal_generation": "Write clear Luganda that meets the instruction and uses the right level of formality.",
    "rewriting_formal_luganda": "Keep the meaning while making the Luganda clearer and more formal.",
    "question_answering": "Answer the question in Luganda. If the information is missing, say so instead of guessing.",
    "instruction_following": "Follow every instruction, including the response language, length, format, tone, and content.",
    "short_conversation": "Use the earlier turns to answer the final turn naturally and consistently.",
}
STATUS_LABELS = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "ready_for_review": "Ready for review",
    "needs_revision": "Returned for correction",
    "under_dispute": "Needs owner resolution",
    "reviewed": "Reviewed",
    "not_ready": "Not ready for dataset",
    "approved_for_dataset": "Approved for dataset preparation",
    "cannot_assess": "Cannot assess yet",
    "approved": "Approved",
}
DECISION_LABELS = {
    "approved": "Approved",
    "needs_revision": "Needs revision",
    "cannot_assess": "Cannot assess yet",
}
ROLE_LABELS = {"admin": "Administrator", "translator": "Translator", "reviewer": "Reviewer"}
COLLECTION_LABELS = {"pilot": "Pilot example", "evaluation": "Evaluation item"}
PII_LABELS = {"none": "No personal data", "redacted": "Redacted", "needs_review": "Needs review"}
VALIDATION_LABELS = {
    "schema": "Schema and required fields",
    "language": "Language checked",
    "instruction_response": "Instruction and response checked",
    "duplicate": "Duplicate check",
    "contamination": "Contamination check",
    "pii": "Privacy check",
    "token_length": "Token length check",
    "review_complete": "Review complete",
}


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


class Response:
    def __init__(self, body=b"", status="200 OK", content_type="text/html; charset=utf-8", headers=None):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.headers = [
            ("Content-Type", content_type),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
            (
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
            ),
            ("Cache-Control", "no-store"),
        ]
        if headers:
            self.headers.extend(headers)
        self.headers.append(("Content-Length", str(len(self.body))))

    def with_cookie(self, name, value, max_age, http_only=True, secure=False):
        parts = [f"{name}={quote(value, safe='')}", "Path=/", "SameSite=Lax"]
        if http_only:
            parts.append("HttpOnly")
        if secure:
            parts.append("Secure")
        if max_age is not None:
            parts.append(f"Max-Age={int(max_age)}")
        self.headers.append(("Set-Cookie", "; ".join(parts)))
        return self


class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = unquote(environ.get("PATH_INFO", "/")) or "/"
        self.query = {
            key: values[-1]
            for key, values in parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).items()
        }
        self._form = None
        self._cookies = None

    def form(self):
        if self._form is not None:
            return self._form
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            raise HTTPError(413, "The submitted form is too large.")
        body = self.environ["wsgi.input"].read(length) if length else b""
        values = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        self._form = {key: items[-1] for key, items in values.items()}
        return self._form

    def cookie(self, name):
        if self._cookies is None:
            self._cookies = {}
            raw = self.environ.get("HTTP_COOKIE", "")
            if raw:
                jar = SimpleCookie()
                try:
                    jar.load(raw)
                    self._cookies = {key: morsel.value for key, morsel in jar.items()}
                except Exception:
                    self._cookies = {}
        return self._cookies.get(name)


def format_datetime(value):
    if not value:
        return "Not recorded"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y, %H:%M")
    except ValueError:
        return str(value)


def format_money_cents(value):
    cents = int(value)
    return f"${cents // 100}.{cents % 100:02d}"


def is_unresolved(value):
    if not isinstance(value, str):
        return True
    lowered = value.strip().casefold()
    return not lowered or any(
        marker in lowered for marker in ("pending", "tbd", "todo", "unresolved", "needs review")
    )


class StudioApp:
    def __init__(self, db_path=None, source_path=None, export_dir=None):
        self.db_path = db_path
        self.source_path = Path(source_path or DEFAULT_SOURCE)
        self.export_dir = Path(export_dir or DEFAULT_EXPORT_DIR)
        self.templates = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.templates.globals.update(
            capability_label=lambda value: CAPABILITY_LABELS.get(value, value),
            capability_purpose=lambda value: CAPABILITY_PURPOSE.get(value, ""),
            status_label=lambda value: STATUS_LABELS.get(value, value),
            decision_label=lambda value: DECISION_LABELS.get(value, value),
            role_label=lambda value: ROLE_LABELS.get(value, value),
            collection_label=lambda value: COLLECTION_LABELS.get(value, value),
            pii_label=lambda value: PII_LABELS.get(value, value),
            format_datetime=format_datetime,
            format_money_cents=format_money_cents,
            translation_reward_rate_cents=TRANSLATION_APPROVAL_CENTS,
            review_reward_rate_cents=COMPLETED_REVIEW_CENTS,
            is_unresolved=is_unresolved,
            validation_checks=VALIDATION_CHECKS,
            validation_labels=VALIDATION_LABELS,
            capabilities=CAPABILITIES,
        )

    def __call__(self, environ, start_response):
        request = Request(environ)
        session = None
        try:
            if request.path == "/favicon.ico":
                start_response("302 Found", [("Location", "/static/favicon.svg")])
                return [b""]
            if request.path.startswith("/static/"):
                return self._static(request, start_response)
            with closing(connect(self.db_path)) as connection:
                token = request.cookie(SESSION_COOKIE)
                session = auth.get_session(connection, token)
                response = self._dispatch(connection, request, session)
            start_response(response.status, response.headers)
            return [response.body]
        except HTTPError as error:
            response = self._error_response(session, error.status, error.message)
        except Exception:
            traceback.print_exc()
            response = self._error_response(
                session,
                500,
                "Something went wrong. Your saved work was not changed. If this happened after a code update, stop and restart the local server.",
            )
        start_response(response.status, response.headers)
        return [response.body]

    def _static(self, request, start_response):
        relative = request.path[len("/static/") :]
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            raise HTTPError(404, "File not found.")
        if not candidate.is_file():
            raise HTTPError(404, "File not found.")
        mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        body = candidate.read_bytes()
        start_response(
            "200 OK",
            [
                ("Content-Type", mime),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-cache"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
        return [body]

    def _dispatch(self, connection, request, session):
        if request.path == "/login":
            if request.method == "GET":
                return self._login_page(connection, request, session)
            if request.method == "POST":
                return self._login_submit(connection, request)
            raise HTTPError(405, "Method not allowed.")
        if not session:
            target = request.path
            return self._redirect(f"/login?next={quote(target, safe='/')}")
        if request.method == "POST":
            form = request.form()
            if not hmac.compare_digest(form.get("csrf_token", ""), session["csrf_token"]):
                raise HTTPError(400, "The form expired. Reload the page and try again.")
        user = session
        if request.path == "/":
            return self._redirect("/home")
        if request.path == "/logout" and request.method == "POST":
            auth.delete_session(connection, request.cookie(SESSION_COOKIE), user["user_id"])
            return self._redirect("/login").with_cookie(SESSION_COOKIE, "", 0)
        if request.path == "/home":
            return self._home(connection, request, user)
        if request.path == "/work":
            return self._work_dashboard(connection, request, user)
        match = re.fullmatch(r"/work/([PE]-\d{3})/autosave", request.path)
        if match:
            if request.method == "POST":
                return self._work_autosave(connection, request, user, match.group(1))
            raise HTTPError(405, "Method not allowed.")
        match = re.fullmatch(r"/work/([PE]-\d{3})", request.path)
        if match:
            if request.method == "GET":
                return self._work_item(connection, request, user, match.group(1))
            if request.method == "POST":
                return self._work_save(connection, request, user, match.group(1))
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/progress":
            return self._progress(connection, request, user)
        if request.path == "/rewards":
            return self._rewards(connection, request, user)
        if request.path == "/review":
            return self._review_dashboard(connection, request, user)
        match = re.fullmatch(r"/review/([PE]-\d{3})", request.path)
        if match:
            if request.method == "GET":
                return self._review_item(connection, request, user, match.group(1))
            if request.method == "POST":
                return self._review_submit(connection, request, user, match.group(1))
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/admin":
            return self._admin(connection, request, user)
        if request.path == "/admin/users":
            if request.method == "GET":
                return self._admin_users(connection, request, user)
            if request.method == "POST":
                return self._admin_users_create(connection, request, user)
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/admin/assign":
            if request.method == "GET":
                return self._admin_assign(connection, request, user)
            if request.method == "POST":
                return self._admin_assign_submit(connection, request, user)
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/admin/items":
            return self._admin_items(connection, request, user)
        match = re.fullmatch(r"/admin/items/([PE]-\d{3})", request.path)
        if match:
            if request.method == "GET":
                return self._admin_item(connection, request, user, match.group(1))
            if request.method == "POST":
                return self._admin_item_submit(connection, request, user, match.group(1))
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/admin/import" and request.method == "POST":
            return self._admin_import(connection, request, user)
        if request.path == "/admin/export":
            if request.method == "GET":
                return self._admin_export(connection, request, user)
            if request.method == "POST":
                return self._admin_export_submit(connection, request, user)
            raise HTTPError(405, "Method not allowed.")
        if request.path == "/admin/audit":
            return self._admin_audit(connection, request, user)
        if request.path == "/admin/payments":
            if request.method == "GET":
                return self._admin_payments(connection, request, user)
            if request.method == "POST":
                return self._admin_payments_submit(connection, request, user)
            raise HTTPError(405, "Method not allowed.")
        raise HTTPError(404, "Page not found.")

    def _require_user(self, user):
        if not user:
            raise HTTPError(401, "Please sign in.")

    def _require_admin(self, user):
        self._require_user(user)
        if user["role"] != "admin":
            raise HTTPError(403, "Only an administrator can open this page.")

    def _require_translator(self, user):
        self._require_user(user)
        if user["role"] != "translator":
            raise HTTPError(403, "This page is for translators.")

    def _require_reviewer(self, user):
        self._require_user(user)
        if user["role"] not in ("reviewer", "admin"):
            raise HTTPError(403, "This page is for reviewers.")

    def _redirect(self, location):
        return Response(b"", "302 Found", headers=[("Location", location)])

    def _json_response(self, value, status="200 OK"):
        return Response(
            json.dumps(value, ensure_ascii=False, sort_keys=True),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def _render(self, connection, request, user, template, context=None, status="200 OK"):
        context = dict(context or {})
        session = user
        csrf_token = session["csrf_token"] if session else context.get("preauth_token", "")
        context.setdefault("user", dict(user) if user else None)
        context.setdefault("csrf_token", csrf_token)
        context.setdefault("current_path", request.path)
        context.setdefault("notice", request.query.get("notice"))
        context.setdefault("error", None)
        context.setdefault("errors", [])
        context.setdefault(
            "meta",
            {
                "source_imported_at": get_meta(connection, "last_import_at"),
                "source_dataset_name": get_meta(connection, "source_dataset_name"),
            },
        )
        body = self.templates.get_template(template).render(**context)
        return Response(body, status=status)

    def _error_response(self, user, status, message):
        reasons = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            413: "Payload Too Large",
            500: "Internal Server Error",
        }
        return Response(
            self.templates.get_template("error.html").render(
                user=dict(user) if user else None,
                csrf_token=user["csrf_token"] if user else "",
                current_path="",
                status=status,
                message=message,
                notice=None,
                error=None,
                errors=[],
                meta={},
            ),
            status=f"{status} {reasons.get(status, 'Error')}",
        )

    def _login_page(self, connection, request, session):
        if session:
            return self._redirect("/home")
        token = request.cookie(PREAUTH_COOKIE) or secrets.token_urlsafe(32)
        response = self._render(
            connection,
            request,
            None,
            "login.html",
            {"preauth_token": token, "next": request.query.get("next", "")},
        )
        return response.with_cookie(PREAUTH_COOKIE, token, 3600)

    def _login_submit(self, connection, request):
        form = request.form()
        cookie = request.cookie(PREAUTH_COOKIE) or ""
        if not cookie or not hmac.compare_digest(form.get("preauth_token", ""), cookie):
            raise HTTPError(400, "The sign-in form expired. Reload the page and try again.")
        user = auth.authenticate(connection, form.get("username", ""), form.get("password", ""))
        if not user:
            token = secrets.token_urlsafe(32)
            response = self._render(
                connection,
                request,
                None,
                "login.html",
                {
                    "preauth_token": token,
                    "error": "The username or password was not recognized.",
                    "username": form.get("username", ""),
                    "next": form.get("next", ""),
                },
                status="200 OK",
            )
            return response.with_cookie(PREAUTH_COOKIE, token, 3600)
        token, _csrf = auth.create_session(connection, user["id"])
        target = form.get("next") or "/home"
        if not target.startswith("/") or target.startswith("//"):
            target = "/home"
        response = self._redirect(target)
        response.with_cookie(SESSION_COOKIE, token, auth.SESSION_HOURS * 3600)
        response.with_cookie(PREAUTH_COOKIE, "", 0)
        return response

    def _home(self, connection, request, user):
        reward = None
        rewards = None
        if user["role"] == "translator":
            counts = progress_counts(connection, user["user_id"], "translator")
            next_item = next_translation_item(connection, user["user_id"])
            reward = translator_reward(connection, user["user_id"])
        elif user["role"] == "reviewer":
            counts = progress_counts(connection, user["user_id"], "reviewer")
            next_item = None
            reward = reviewer_reward(connection, user["user_id"])
        else:
            counts = admin_counts(connection)
            next_item = None
            rewards = all_translator_rewards(connection)
        return self._render(
            connection,
            request,
            user,
            "home.html",
            {
                "counts": counts,
                "next_item": next_item,
                "item_count": item_count(connection),
                "collections": collection_counts(connection),
                "reward": reward,
                "rewards": rewards,
            },
        )

    def _work_dashboard(self, connection, request, user):
        self._require_translator(user)
        status = request.query.get("status", "")
        query = request.query.get("q", "").strip()
        rows = assigned_items(connection, user["user_id"], "translation", query, status)
        counts = progress_counts(connection, user["user_id"], "translator")
        items = []
        for index, row in enumerate(rows, 1):
            source = item_source(row)
            items.append(
                {
                    "row": row,
                    "source": source,
                    "number": index,
                    "total": len(rows),
                }
            )
        return self._render(
            connection,
            request,
            user,
            "dashboard.html",
            {
                "counts": counts,
                "items": items,
                "query": query,
                "status": status,
                "status_options": TRANSLATION_STATUSES,
                "next_item": next_translation_item(connection, user["user_id"]),
                "reward": translator_reward(connection, user["user_id"]),
            },
        )

    def _work_item_context(self, connection, request, user, item_id, form_values=None, error=None):
        item = get_item(connection, item_id)
        if not item:
            raise HTTPError(404, "Example not found.")
        if user["role"] == "translator" and not workflow_is_assigned(
            connection, item_id, user["user_id"], "translation"
        ):
            raise HTTPError(403, "This example is not assigned to you.")
        source = item_source(item)
        translation = translation_view(connection, item_id)
        metadata = training_metadata_view(connection, item_id)
        reviews = review_history(connection, item_id)
        resolutions = resolution_history(connection, item_id)
        source_turns = source.get("conversation_turns") or []
        if form_values is None:
            form_values = {
                "context_lg": translation["context_lg"] if translation else "",
                "turns": translation["turns"] if translation else ["" for _ in source_turns],
                "prompt_lg": translation["prompt_lg"] if translation else "",
                "response_lg": translation["response_lg"] if translation else "",
                "notes": translation["notes"] if translation else "",
            }
        status = translation["status"] if translation else "not_started"
        editable = (
            user["role"] == "translator"
            and status in ("not_started", "in_progress", "needs_revision")
            and metadata["dataset_status"] != "approved_for_dataset"
        )
        assigned_rows = assigned_items(connection, user["user_id"], "translation") if user["role"] == "translator" else []
        ids = [row["item_id"] for row in assigned_rows]
        number = ids.index(item_id) + 1 if item_id in ids else 1
        return {
            "item": item,
            "source": source,
            "translation": translation,
            "metadata": metadata,
            "reviews": reviews,
            "resolutions": resolutions,
            "form_values": form_values,
            "status": status,
            "editable": editable,
            "number": number,
            "total": len(ids) if ids else 1,
            "previous_id": previous_translation_item(connection, user["user_id"], item_id)
            if user["role"] == "translator"
            else None,
            "next_id": next_translation_item(connection, user["user_id"], item_id)
            if user["role"] == "translator"
            else None,
            "error": error,
        }

    def _work_item(self, connection, request, user, item_id):
        if user["role"] not in ("translator", "admin"):
            raise HTTPError(403, "This page is for translators.")
        context = self._work_item_context(connection, request, user, item_id)
        return self._render(connection, request, user, "work_item.html", context)

    def _work_save(self, connection, request, user, item_id):
        self._require_translator(user)
        form = request.form()
        action = form.get("action", "save")
        turns = []
        item = get_item(connection, item_id)
        if not item:
            raise HTTPError(404, "Example not found.")
        source = item_source(item)
        for index in range(len(source.get("conversation_turns") or [])):
            turns.append(form.get(f"turn_{index}", ""))
        values = {
            "context_lg": form.get("context_lg", ""),
            "turns": turns,
            "prompt_lg": form.get("prompt_lg", ""),
            "response_lg": form.get("response_lg", ""),
            "notes": form.get("notes", ""),
        }
        try:
            save_translation(
                connection,
                item_id,
                user["user_id"],
                values["context_lg"],
                values["turns"],
                values["prompt_lg"],
                values["response_lg"],
                values["notes"],
                submit=action in ("submit", "mark_ready"),
            )
        except WorkflowError as error:
            context = self._work_item_context(
                connection, request, user, item_id, form_values=values, error=error
            )
            return self._render(
                connection,
                request,
                user,
                "work_item.html",
                context,
                status="400 Bad Request",
            )
        if action == "save_next":
            next_id = next_translation_item(connection, user["user_id"], item_id)
            if next_id:
                return self._redirect(f"/work/{next_id}?notice=Progress+saved.")
            return self._redirect("/work?notice=Progress+saved.+There+is+no+next+example.")
        if action in ("submit", "mark_ready"):
            return self._redirect(f"/work/{item_id}?notice=Sent+for+review.")
        return self._redirect(f"/work/{item_id}?notice=Progress+saved.")

    def _work_autosave(self, connection, request, user, item_id):
        self._require_translator(user)
        form = request.form()
        item = get_item(connection, item_id)
        if not item:
            return self._json_response(
                {"status": "error", "message": "Example not found."},
                status="404 Not Found",
            )
        source = item_source(item)
        turns = [
            form.get(f"turn_{index}", "")
            for index in range(len(source.get("conversation_turns") or []))
        ]
        try:
            translation = save_translation(
                connection,
                item_id,
                user["user_id"],
                form.get("context_lg", ""),
                turns,
                form.get("prompt_lg", ""),
                form.get("response_lg", ""),
                form.get("notes", ""),
                submit=False,
            )
        except WorkflowError as error:
            return self._json_response(
                {
                    "status": "error",
                    "message": str(error),
                    "errors": error.errors,
                },
                status="409 Conflict",
            )
        return self._json_response(
            {
                "status": "saved",
                "saved_at": translation["updated_at"],
                "translation_status": translation["status"],
                "version": translation["version"],
            }
        )

    def _progress(self, connection, request, user):
        self._require_translator(user)
        rows = assigned_items(connection, user["user_id"], "translation")
        items = []
        for row in rows:
            source = item_source(row)
            items.append({"row": row, "source": source})
        counts = progress_counts(connection, user["user_id"], "translator")
        reward = translator_reward(connection, user["user_id"])
        return self._render(
            connection,
            request,
            user,
            "progress.html",
            {"counts": counts, "items": items, "reward": reward},
        )

    def _rewards(self, connection, request, user):
        if user["role"] == "translator":
            reward = translator_reward(connection, user["user_id"])
        elif user["role"] == "reviewer":
            reward = reviewer_reward(connection, user["user_id"])
        else:
            raise HTTPError(403, "Rewards are shown on translator and reviewer accounts.")
        return self._render(
            connection,
            request,
            user,
            "rewards.html",
            {"reward": reward},
        )

    def _review_dashboard(self, connection, request, user):
        self._require_reviewer(user)
        if user["role"] == "admin":
            rows = [row for row in admin_items(connection) if row["translation_status"]]
            counts = {
                "total": len(rows),
                "waiting": sum(1 for row in rows if row["translation_status"] == "ready_for_review"),
                "completed": sum(1 for row in rows if row["translation_status"] == "reviewed"),
            }
        else:
            rows = assigned_items(connection, user["user_id"], "review")
            counts = progress_counts(connection, user["user_id"], "reviewer")
        reward = reviewer_reward(connection, user["user_id"]) if user["role"] == "reviewer" else None
        items = []
        for row in rows:
            my_review = None
            if user["role"] == "reviewer":
                my_review = next(
                    (
                        review
                        for review in review_history(connection, row["item_id"])
                        if review["reviewer_id"] == user["user_id"]
                        and review["translation_version"] == row["translation_version"]
                    ),
                    None,
                )
            items.append(
                {
                    "row": row,
                    "source": item_source(row),
                    "my_review": my_review,
                }
            )
        return self._render(
            connection,
            request,
            user,
            "review_dashboard.html",
            {"counts": counts, "items": items, "reward": reward},
        )

    def _review_item_context(self, connection, request, user, item_id, form_values=None, error=None):
        item = get_item(connection, item_id)
        if not item:
            raise HTTPError(404, "Example not found.")
        if user["role"] == "reviewer" and not workflow_is_assigned(
            connection, item_id, user["user_id"], "review"
        ):
            raise HTTPError(403, "This example is not assigned to you for review.")
        translation = translation_view(connection, item_id)
        if not translation:
            raise HTTPError(404, "There is no translation to review.")
        translator = get_user(connection, translation["translator_id"])
        translation["translator_public_id"] = translator["public_id"] if translator else ""
        translation["translator_name"] = translator["display_name"] if translator else ""
        source = item_source(item)
        metadata = training_metadata_view(connection, item_id)
        reviews = review_history(connection, item_id)
        my_review = next(
            (
                row
                for row in reviews
                if row["reviewer_id"] == user["user_id"]
                and row["translation_version"] == translation["version"]
            ),
            None,
        )
        can_review = (
            user["role"] == "reviewer"
            and workflow_is_assigned(connection, item_id, user["user_id"], "review")
            and translation["status"] in ("ready_for_review", "reviewed")
            and not my_review
            and metadata["dataset_status"] != "approved_for_dataset"
            and user["user_id"] != translation["translator_id"]
        )
        show_other_reviews = user["role"] == "admin" or bool(my_review)
        visible_reviews = reviews if show_other_reviews else []
        return {
            "item": item,
            "source": source,
            "translation": translation,
            "metadata": metadata,
            "reviews": visible_reviews,
            "all_review_count": len(reviews),
            "my_review": my_review,
            "can_review": can_review,
            "form_values": form_values
            or {"decision": "", "comments": "", "suggested_correction": ""},
            "error": error,
        }

    def _review_item(self, connection, request, user, item_id):
        context = self._review_item_context(connection, request, user, item_id)
        return self._render(connection, request, user, "review_item.html", context)

    def _review_submit(self, connection, request, user, item_id):
        self._require_reviewer(user)
        if user["role"] != "reviewer":
            raise HTTPError(403, "Administrators resolve reviews but do not submit them.")
        form = request.form()
        values = {
            "decision": form.get("decision", ""),
            "comments": form.get("comments", ""),
            "suggested_correction": form.get("suggested_correction", ""),
        }
        try:
            submit_review(
                connection,
                item_id,
                user["user_id"],
                values["decision"],
                values["comments"],
                values["suggested_correction"],
            )
        except WorkflowError as error:
            context = self._review_item_context(
                connection, request, user, item_id, form_values=values, error=error
            )
            return self._render(
                connection,
                request,
                user,
                "review_item.html",
                context,
                status="400 Bad Request",
            )
        return self._redirect(f"/review/{item_id}?notice=Review+recorded.")

    def _admin(self, connection, request, user):
        self._require_admin(user)
        import_result = None
        raw = get_meta(connection, "last_import_result")
        if raw:
            try:
                import_result = json.loads(raw)
            except json.JSONDecodeError:
                import_result = None
        return self._render(
            connection,
            request,
            user,
            "admin.html",
            {
                "counts": admin_counts(connection),
                "import_result": import_result,
                "audit": recent_audit(connection, 15),
                "source_imported_at": get_meta(connection, "last_import_at"),
                "source_dataset_name": get_meta(connection, "source_dataset_name"),
                "rewards": all_translator_rewards(connection),
            },
        )

    def _admin_users(self, connection, request, user):
        self._require_admin(user)
        return self._render(
            connection,
            request,
            user,
            "admin_users.html",
            {"users": list_users(connection)},
        )

    def _admin_users_create(self, connection, request, user):
        self._require_admin(user)
        form = request.form()
        try:
            auth.create_user(
                connection,
                form.get("username", ""),
                form.get("display_name", ""),
                form.get("role", ""),
                form.get("password", ""),
                actor_id=user["user_id"],
            )
        except auth.AuthError as error:
            return self._render(
                connection,
                request,
                user,
                "admin_users.html",
                {
                    "users": list_users(connection),
                    "error": str(error),
                    "form": form,
                },
                status="400 Bad Request",
            )
        return self._redirect("/admin/users?notice=User+created.")

    def _admin_assign(self, connection, request, user):
        self._require_admin(user)
        users = list_users(connection)
        return self._render(
            connection,
            request,
            user,
            "admin_assign.html",
            {
                "users": users,
                "translators": [row for row in users if row["role"] == "translator"],
                "reviewers": [row for row in users if row["role"] == "reviewer"],
                "counts": admin_counts(connection),
            },
        )

    def _admin_assign_submit(self, connection, request, user):
        self._require_admin(user)
        form = request.form()
        assignment_type = form.get("assignment_type", "")
        try:
            user_id = int(form.get("user_id", "0"))
        except ValueError:
            user_id = 0
        collection = form.get("collection") or None
        capability = form.get("capability") or None
        try:
            limit = int(form.get("limit", "10"))
        except ValueError:
            limit = 10
        limit = max(1, min(limit, 200))
        try:
            if assignment_type == "translation":
                assigned = bulk_assign_translation(
                    connection, user_id, user["user_id"], collection, limit, capability
                )
            elif assignment_type == "review":
                assigned = bulk_assign_review(
                    connection, user_id, user["user_id"], collection, limit, capability
                )
            else:
                raise WorkflowError("Choose translation or review work.")
        except WorkflowError as error:
            return self._render(
                connection,
                request,
                user,
                "admin_assign.html",
                {
                    "users": list_users(connection),
                    "translators": [row for row in list_users(connection) if row["role"] == "translator"],
                    "reviewers": [row for row in list_users(connection) if row["role"] == "reviewer"],
                    "counts": admin_counts(connection),
                    "error": str(error),
                },
                status="400 Bad Request",
            )
        return self._redirect(f"/admin/assign?notice=Assigned+{len(assigned)}+items.")

    def _admin_items(self, connection, request, user):
        self._require_admin(user)
        collection = request.query.get("collection") or None
        status = request.query.get("status") or None
        dataset = request.query.get("dataset") or None
        query = request.query.get("q", "").strip() or None
        rows = admin_items(connection, collection, status, dataset, query)
        items = [{"row": row, "source": item_source(row)} for row in rows]
        return self._render(
            connection,
            request,
            user,
            "admin_items.html",
            {
                "items": items,
                "collection": collection or "",
                "status": status or "",
                "dataset": dataset or "",
                "query": query or "",
            },
        )

    def _admin_item_context(self, connection, request, user, item_id, metadata_form=None, error=None):
        item = get_item(connection, item_id)
        if not item:
            raise HTTPError(404, "Example not found.")
        source = item_source(item)
        translation = translation_view(connection, item_id)
        metadata = training_metadata_view(connection, item_id)
        blockers = dataset_blockers(connection, item_id, source, translation, metadata)
        default_metadata_form = {
            "licence": metadata["licence"],
            "licence_status": metadata["licence_status"],
            "consent_ref": metadata["consent_ref"],
            "consent_status": metadata["consent_status"],
            "pii_check": metadata["pii_check"],
            "contamination_notes": metadata["contamination_notes"],
            **{
                f"validation_{name}": bool(validation_values(metadata).get(name))
                for name in VALIDATION_CHECKS
            },
        }
        if metadata_form:
            default_metadata_form.update(metadata_form)
        versions = []
        for row in version_history(connection, item_id):
            version = dict(row)
            try:
                version["turns"] = json.loads(version["turns_lg"] or "[]")
            except json.JSONDecodeError:
                version["turns"] = []
            versions.append(version)
        return {
            "item": item,
            "source": source,
            "translation": translation,
            "metadata": metadata,
            "validation": validation_values(metadata),
            "blockers": blockers,
            "reviews": review_history(connection, item_id),
            "versions": versions,
            "resolutions": resolution_history(connection, item_id),
            "assignments": assignments_for_item(connection, item_id),
            "audit": item_audit(connection, item_id),
            "reward_eligible": is_reward_eligible(connection, item_id),
            "metadata_form": default_metadata_form,
            "error": error,
            "users": list_users(connection),
        }

    def _admin_item(self, connection, request, user, item_id):
        self._require_admin(user)
        return self._render(
            connection,
            request,
            user,
            "admin_item.html",
            self._admin_item_context(connection, request, user, item_id),
        )

    def _admin_item_submit(self, connection, request, user, item_id):
        self._require_admin(user)
        form = request.form()
        action = form.get("action", "")
        try:
            if action == "metadata":
                update_training_metadata(connection, item_id, user["user_id"], form)
                return self._redirect(f"/admin/items/{item_id}?notice=Dataset+preparation+fields+saved.")
            if action == "approve":
                approve_dataset(connection, item_id, user["user_id"])
                return self._redirect(f"/admin/items/{item_id}?notice=Approved+for+dataset+preparation.")
            if action == "revoke":
                revoke_dataset(connection, item_id, user["user_id"])
                return self._redirect(f"/admin/items/{item_id}?notice=Dataset+approval+revoked.")
            if action == "return_translation":
                return_translation(
                    connection,
                    item_id,
                    user["user_id"],
                    form.get("reason", ""),
                )
                return self._redirect(f"/admin/items/{item_id}?notice=Returned+to+the+translator+for+correction.")
            if action == "resolve":
                resolve_dispute(
                    connection,
                    item_id,
                    user["user_id"],
                    form.get("decision", ""),
                    form.get("notes", ""),
                )
                return self._redirect(f"/admin/items/{item_id}?notice=Disagreement+resolved.")
            if action == "assign_translation":
                assign_translation(connection, item_id, int(form.get("user_id", "0")), user["user_id"])
                return self._redirect(f"/admin/items/{item_id}?notice=Translator+assigned.")
            if action == "assign_review":
                assign_review(connection, item_id, int(form.get("user_id", "0")), user["user_id"])
                return self._redirect(f"/admin/items/{item_id}?notice=Reviewer+assigned.")
            raise WorkflowError("Unknown administrator action.")
        except (WorkflowError, ValueError) as error:
            context = self._admin_item_context(
                connection, request, user, item_id, metadata_form=form, error=error
            )
            return self._render(
                connection,
                request,
                user,
                "admin_item.html",
                context,
                status="400 Bad Request",
            )

    def _admin_import(self, connection, request, user):
        self._require_admin(user)
        try:
            result = import_source(connection, self.source_path, actor_id=user["user_id"])
        except Exception as error:
            result = {"status": "failed", "message": str(error), "conflicts": []}
        set_meta(connection, "last_import_result", json.dumps(result, ensure_ascii=False))
        connection.commit()
        return self._redirect("/admin?notice=Source+import+finished.")

    def _admin_export(self, connection, request, user):
        self._require_admin(user)
        approved = admin_items(connection, dataset_status="approved_for_dataset")
        return self._render(
            connection,
            request,
            user,
            "admin_export.html",
            {"approved_count": len(approved)},
        )

    def _admin_export_submit(self, connection, request, user):
        self._require_admin(user)
        form = request.form()
        action = form.get("action", "")
        try:
            if action == "csv":
                collection = form.get("collection") or None
                if collection == "all":
                    collection = None
                path, count = export_review_csv(
                    connection, user["user_id"], self.export_dir, collection
                )
                return self._download(path)
            if action == "training":
                path, manifest_path, manifest = export_training_jsonl(
                    connection, user["user_id"], self.export_dir
                )
                return self._download(path)
            raise WorkflowError("Choose an export type.")
        except WorkflowError as error:
            return self._render(
                connection,
                request,
                user,
                "admin_export.html",
                {
                    "approved_count": len(admin_items(connection, dataset_status="approved_for_dataset")),
                    "error": str(error),
                    "errors": error.errors,
                },
                status="400 Bad Request",
            )

    def _download(self, path):
        path = Path(path)
        data = path.read_bytes()
        return Response(
            data,
            status="200 OK",
            content_type="application/octet-stream",
            headers=[("Content-Disposition", f'attachment; filename="{path.name}"')],
        )

    def _admin_audit(self, connection, request, user):
        self._require_admin(user)
        return self._render(
            connection,
            request,
            user,
            "admin_audit.html",
            {"audit": recent_audit(connection, 200)},
        )

    def _admin_payments(self, connection, request, user):
        self._require_admin(user)
        return self._render(
            connection,
            request,
            user,
            "admin_payments.html",
            {"payables": all_payables(connection)},
        )

    def _admin_payments_submit(self, connection, request, user):
        self._require_admin(user)
        form = request.form()
        try:
            recipient_id = int(form.get("recipient_id", "0"))
        except ValueError:
            recipient_id = 0
        role = form.get("role", "")
        try:
            record_payment(
                connection,
                recipient_id,
                role,
                form.get("amount", ""),
                form.get("note", ""),
                user["user_id"],
            )
        except WorkflowError as error:
            return self._render(
                connection,
                request,
                user,
                "admin_payments.html",
                {
                    "payables": all_payables(connection),
                    "error": str(error),
                    "errors": error.errors,
                },
                status="400 Bad Request",
            )
        return self._redirect("/admin/payments?notice=Payment+cleared+and+recorded.")


def workflow_is_assigned(connection, item_id, user_id, assignment_type):
    from .workflow import is_assigned

    return is_assigned(connection, item_id, user_id, assignment_type)


def create_app(db_path=None, source_path=None, export_dir=None):
    return StudioApp(db_path, source_path, export_dir)
