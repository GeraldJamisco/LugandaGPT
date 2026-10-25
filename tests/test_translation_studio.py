"""End-to-end tests for the local LugandaGPT Translation Studio."""

import io
import json
import re
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from training.pilot import validate_pilot_record

from translation_studio import auth
from translation_studio.app import StudioApp
from translation_studio.db import SCHEMA, connect, init_db, item_source
from translation_studio.source_import import import_source
from translation_studio.workflow import (
    WorkflowError,
    approve_dataset,
    assign_review,
    assign_translation,
    build_training_record,
    export_review_csv,
    export_training_jsonl,
    get_translation,
    resolve_dispute,
    record_payment,
    review_history,
    reviewer_reward,
    reward_summary,
    return_translation,
    save_translation,
    submit_review,
    translator_reward,
    update_training_metadata,
    version_history,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"
UNICODE_TEXT = "TEST-Ŋŋ-ʼ-okulaba"


class Response:
    def __init__(self, status_code, headers, body):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.text = body.decode("utf-8", errors="replace")
        self.json = None
        try:
            self.json = json.loads(self.text)
        except json.JSONDecodeError:
            pass


class Client:
    def __init__(self, app):
        self.app = app
        self.cookies = {}
        self.csrf = None

    def _request(self, method, path, data=None, follow=False, add_csrf=True):
        if add_csrf and method == "POST" and self.csrf and "csrf_token" not in (data or {}):
            data = dict(data or {})
            data["csrf_token"] = self.csrf
        body = urlencode(data or {}).encode("utf-8")
        parsed = urlsplit(path)
        cookie_header = "; ".join(f"{key}={value}" for key, value in self.cookies.items())
        environ = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": parsed.path,
            "QUERY_STRING": parsed.query,
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "HTTP_HOST": "testserver",
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_COOKIE": cookie_header,
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(body),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        chunks = self.app(environ, start_response)
        response_body = b"".join(chunks)
        status_code = int(captured["status"].split(" ", 1)[0])
        response = Response(status_code, captured["headers"], response_body)
        for name, value in captured["headers"]:
            if name.lower() != "set-cookie":
                continue
            pair = value.split(";", 1)[0]
            if "=" not in pair:
                continue
            cookie_name, cookie_value = pair.split("=", 1)
            if "max-age=0" in value.lower():
                self.cookies.pop(cookie_name, None)
            else:
                self.cookies[cookie_name] = unquote(cookie_value)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        if csrf:
            self.csrf = csrf.group(1)
        if follow and status_code in (301, 302, 303, 307, 308):
            location = dict(captured["headers"]).get("Location", "/")
            return self._request("GET", urljoin(path, location), follow=True)
        return response

    def get(self, path, follow=True):
        return self._request("GET", path, follow=follow)

    def post(self, path, data=None, follow=False, add_csrf=True):
        return self._request("POST", path, data, follow=follow, add_csrf=add_csrf)

    def login(self, username, password):
        page = self.get("/login")
        token = re.search(r'name="preauth_token" value="([^"]+)"', page.text)
        if not token:
            raise AssertionError("login page did not include a preauth token")
        response = self.post(
            "/login",
            {
                "preauth_token": token.group(1),
                "username": username,
                "password": password,
                "next": "/home",
            },
            follow=True,
            add_csrf=False,
        )
        if response.status_code != 200 or "/login" in response.text:
            raise AssertionError(f"login failed with {response.status_code}")
        return response


class StudioTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="lugandagpt-studio-")
        self.db_path = Path(self.temporary.name) / "studio.sqlite3"
        self.export_dir = Path(self.temporary.name) / "exports"
        with closing(connect(self.db_path)) as connection:
            init_db(connection)
            self.admin_id, self.admin_public = auth.create_user(
                connection, "owner", "Project Owner", "admin", "owner-password-123"
            )
            self.translator_id, self.translator_public = auth.create_user(
                connection, "translator", "Teacher One", "translator", "teacher-password-123"
            )
            self.reviewer_id, self.reviewer_public = auth.create_user(
                connection, "reviewer", "Teacher Two", "reviewer", "review-password-123"
            )
            self.reviewer2_id, self.reviewer2_public = auth.create_user(
                connection, "reviewer2", "Teacher Three", "reviewer", "review2-password-123"
            )
            import_source(connection, SOURCE, actor_id=self.admin_id)
            assign_translation(connection, "P-001", self.translator_id, self.admin_id)
            assign_translation(connection, "P-002", self.translator_id, self.admin_id)
            assign_translation(connection, "P-085", self.translator_id, self.admin_id)
        self.app = StudioApp(db_path=self.db_path, source_path=SOURCE, export_dir=self.export_dir)
        self.translator_client = Client(self.app)
        self.translator_client.login("translator", "teacher-password-123")
        self.admin_client = Client(self.app)
        self.admin_client.login("owner", "owner-password-123")
        self.reviewer_client = Client(self.app)
        self.reviewer_client.login("reviewer", "review-password-123")
        self.reviewer2_client = Client(self.app)
        self.reviewer2_client.login("reviewer2", "review2-password-123")

    def tearDown(self):
        self.temporary.cleanup()

    def p001_data(self, response=UNICODE_TEXT):
        return {
            "context_lg": "TEST-Ŋŋ- context",
            "prompt_lg": "TEST-Ŋŋ- prompt",
            "response_lg": response,
            "notes": "Synthetic test note only.",
        }

    def save_and_submit(self, item_id="P-001", data=None):
        data = data or self.p001_data()
        response = self.translator_client.post(f"/work/{item_id}", {**data, "action": "save"})
        self.assertEqual(response.status_code, 302)
        self.translator_client.get(f"/work/{item_id}")
        response = self.translator_client.post(f"/work/{item_id}", {**data, "action": "submit"})
        self.assertEqual(response.status_code, 302)

    def complete_review(self, item_id="P-001", reviewer_client=None, reviewer_id=None, decision="approved"):
        reviewer_client = reviewer_client or self.reviewer_client
        reviewer_id = reviewer_id or self.reviewer_id
        with closing(connect(self.db_path)) as connection:
            assign_review(connection, item_id, reviewer_id, self.admin_id)
        page = reviewer_client.get(f"/review/{item_id}")
        self.assertEqual(page.status_code, 200)
        response = reviewer_client.post(
            f"/review/{item_id}",
            {
                "decision": decision,
                "comments": "Synthetic review comment for tests.",
                "suggested_correction": "Synthetic suggestion." if decision == "needs_revision" else "",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_import_is_idempotent_and_preserves_source(self):
        with closing(connect(self.db_path)) as connection:
            before = item_source(
                connection.execute("SELECT * FROM items WHERE item_id = 'P-001'").fetchone()
            )
            before_hashes = {
                row["item_id"]: row["source_sha256"]
                for row in connection.execute("SELECT item_id, source_sha256 FROM items")
            }
            result = import_source(connection, SOURCE, actor_id=self.admin_id)
            self.assertEqual(result["inserted"], 0)
            self.assertEqual(result["skipped"], 124)
            self.assertEqual(connection.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"], 124)
            collections = {
                row["collection"]: row["count"]
                for row in connection.execute(
                    "SELECT collection, COUNT(*) AS count FROM items GROUP BY collection"
                )
            }
            self.assertEqual(collections, {"evaluation": 24, "pilot": 100})
            ids = {
                row["item_id"]
                for row in connection.execute("SELECT item_id FROM items").fetchall()
            }
            self.assertIn("P-001", ids)
            self.assertIn("P-100", ids)
            self.assertIn("E-001", ids)
            self.assertIn("E-024", ids)
            save_translation(
                connection,
                "P-001",
                self.translator_id,
                "ctx",
                [],
                "prompt",
                "response",
                "",
                submit=False,
            )
            after = item_source(
                connection.execute("SELECT * FROM items WHERE item_id = 'P-001'").fetchone()
            )
            self.assertEqual(before, after)
            after_hashes = {
                row["item_id"]: row["source_sha256"]
                for row in connection.execute("SELECT item_id, source_sha256 FROM items")
            }
            self.assertEqual(before_hashes, after_hashes)

    def test_admin_assignment_route_and_validation_blockers(self):
        page = self.admin_client.get("/admin/assign")
        self.assertEqual(page.status_code, 200)
        response = self.admin_client.post(
            "/admin/assign",
            {
                "assignment_type": "translation",
                "user_id": self.translator_id,
                "collection": "pilot",
                "limit": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            assigned = connection.execute(
                "SELECT item_id FROM assignments WHERE user_id = ? AND assignment_type = 'translation'",
                (self.translator_id,),
            ).fetchall()
            self.assertEqual(len(assigned), 4)
            with self.assertRaises(WorkflowError):
                approve_dataset(connection, "P-001", self.admin_id)
            with self.assertRaises(WorkflowError):
                export_training_jsonl(connection, self.admin_id, self.export_dir)
            with self.assertRaises(WorkflowError):
                approve_dataset(connection, "E-001", self.admin_id)
            metadata = update_training_metadata(
                connection,
                "P-001",
                self.admin_id,
                {
                    "licence": "LIC-TEST-001",
                    "licence_status": "recorded",
                    "consent_ref": "CONSENT-TEST-001",
                    "consent_status": "not_recorded",
                    "pii_check": "none",
                    "contamination_notes": "Synthetic checks completed for tests.",
                },
            )
            self.assertIsNone(metadata)
            row = connection.execute(
                "SELECT * FROM training_metadata WHERE item_id = 'P-001'"
            ).fetchone()
            self.assertEqual(row["licence_status"], "recorded")
            self.assertEqual(row["consent_status"], "not_recorded")

    def test_teacher_sees_source_and_conversation_without_technical_labels(self):
        page = self.translator_client.get("/work/P-001")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Using only the notice", page.text)
        self.assertIn("central library", page.text)
        self.assertIn("Question about the passage", page.text)
        self.assertIn(
            "Translate the passage into natural Luganda. Keep the facts that the question asks about.",
            page.text,
        )
        self.assertIn("Translate the question into Luganda.", page.text)
        self.assertIn("Question or message in Luganda", page.text)
        self.assertIn("Answer in Luganda", page.text)
        self.assertNotIn("formal_comprehension", page.text)
        self.assertNotIn("proposed_split", page.text)
        conversation = self.translator_client.get("/work/P-085")
        self.assertEqual(conversation.status_code, 200)
        self.assertIn("Earlier request", conversation.text)
        self.assertIn("Earlier reply", conversation.text)
        self.assertLess(conversation.text.index("Is the workshop on Tuesday?"), conversation.text.index("Yes, the workshop is on Tuesday at nine in the morning."))
        self.assertLess(conversation.text.index("Yes, the workshop is on Tuesday at nine in the morning."), conversation.text.index("Actually, the message now says ten."))

    def test_task_categories_show_their_actual_source_parts(self):
        with closing(connect(self.db_path)) as connection:
            for item_id in ("P-018", "P-035", "P-052", "P-069"):
                assign_translation(connection, item_id, self.translator_id, self.admin_id)
        cases = (
            ("P-001", ("Question about the passage", "Passage translated into Luganda", "Translate the question into Luganda.", "Answer the question in natural Luganda.")),
            ("P-018", ("English instruction", "Instruction in Luganda", "Write the text requested by the English instruction in Luganda.")),
            ("P-035", ("What to do with the text", "Original English text to rewrite", "Original text translated into Luganda", "Formal rewrite in Luganda")),
            ("P-052", ("English question", "Question or message in Luganda", "Answer the question in natural Luganda using the English details provided.")),
            ("P-069", ("English instruction", "Instruction in Luganda", "Carry out the English instruction in Luganda.")),
            ("P-085", ("Latest message in English", "Earlier messages translated into Luganda", "Reply to the latest message in natural Luganda.")),
        )
        for item_id, expected_texts in cases:
            page = self.translator_client.get(f"/work/{item_id}")
            self.assertEqual(page.status_code, 200, item_id)
            for text in expected_texts:
                self.assertIn(text, page.text, (item_id, text))
            self.assertIn('name="prompt_lg"', page.text, item_id)
            self.assertIn('name="response_lg"', page.text, item_id)
            self.assertIn('class="badge badge-gold">Required</span>', page.text, item_id)
        generation = self.translator_client.get("/work/P-018")
        self.assertNotIn('name="context_lg"', generation.text)
        self.assertNotIn('name="turn_0"', generation.text)
        conversation = self.translator_client.get("/work/P-085")
        self.assertIn('name="turn_0"', conversation.text)
        self.assertIn("Illustration only", generation.text)
        self.assertIn("20 chickens and sells 5", generation.text)
        self.assertIn("15 chickens", generation.text)
        self.assertIn("This example is not part of the dataset", generation.text)
        self.assertIn("<details", generation.text)
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            assign_review(connection, "P-001", self.reviewer_id, self.admin_id)
        review = self.reviewer_client.get("/review/P-001")
        self.assertIn("English passage to translate", review.text)
        self.assertIn("Question about the passage", review.text)
        self.assertIn("Passage translated into Luganda", review.text)
        self.assertIn("Answer in Luganda", review.text)

    def test_source_prompt_and_response_fields_remain_required_for_valid_examples(self):
        page = self.translator_client.get("/work/P-001")
        self.assertIn('name="prompt_lg"', page.text)
        self.assertIn('name="response_lg"', page.text)
        submitted = self.translator_client.post(
            "/work/P-001",
            {"context_lg": "TEST-Ŋŋ- context", "action": "submit"},
        )
        self.assertEqual(submitted.status_code, 400)
        page_after = self.translator_client.get("/work/P-001")
        self.assertIn("Translate the question into Luganda.", page_after.text)

    def test_unicode_save_and_reload(self):
        data = self.p001_data(UNICODE_TEXT)
        response = self.translator_client.post("/work/P-001", {**data, "action": "save"})
        self.assertEqual(response.status_code, 302)
        page = self.translator_client.get("/work/P-001")
        self.assertIn(UNICODE_TEXT, page.text)
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-001")
            self.assertEqual(translation["response_lg"], UNICODE_TEXT)

    def test_partial_autosave_and_submit_guard(self):
        page = self.translator_client.get("/work/P-001")
        self.assertIn("data-autosave-url", page.text)
        response = self.translator_client.post(
            "/work/P-001/autosave",
            {"response_lg": "partial draft only"},
            follow=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "saved")
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-001")
            self.assertEqual(translation["status"], "in_progress")
            self.assertEqual(translation["response_lg"], "partial draft only")
        reloaded = self.translator_client.get("/work/P-001")
        self.assertIn("partial draft only", reloaded.text)
        self.assertIn("recovery-banner", reloaded.text)
        rejected = self.translator_client.post(
            "/work/P-001",
            {"response_lg": "partial draft only", "action": "submit"},
        )
        self.assertEqual(rejected.status_code, 400)
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-001")
            self.assertEqual(translation["status"], "in_progress")
        js = self.translator_client.get("/static/studio.js")
        self.assertIn("localStorage", js.text)
        self.assertIn("beforeunload", js.text)

    def test_status_transitions_and_review_cannot_overwrite(self):
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-001")
            self.assertEqual(translation["status"], "ready_for_review")
            self.assertEqual(translation["version"], 1)
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-001")
            self.assertEqual(translation["status"], "reviewed")
            self.assertEqual(translation["version"], 1)
            reviews = review_history(connection, "P-001")
            self.assertEqual(len(reviews), 1)
        dashboard = self.reviewer_client.get("/review")
        self.assertIn("Reviewed", dashboard.text)
        self.assertNotIn("Open review", dashboard.text)
        forbidden = self.reviewer_client.post(
            "/work/P-001",
            {**self.p001_data("attempted overwrite"), "action": "save"},
        )
        self.assertEqual(forbidden.status_code, 403)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-001")["response_lg"], UNICODE_TEXT)
        second_review = self.reviewer_client.post(
            "/review/P-001",
            {"decision": "approved", "comments": "A second attempt."},
        )
        self.assertEqual(second_review.status_code, 400)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(len(review_history(connection, "P-001")), 1)

    def test_access_control_and_self_review_guard(self):
        self.assertEqual(self.translator_client.get("/admin").status_code, 403)
        self.assertEqual(self.translator_client.get("/review").status_code, 403)
        self.assertEqual(self.reviewer_client.get("/work").status_code, 403)
        self.assertEqual(self.translator_client.get("/work/P-003").status_code, 403)
        self.assertEqual(self.translator_client.get("/register").status_code, 404)
        with closing(connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO assignments(item_id, user_id, assignment_type, created_by, created_at)
                VALUES ('P-001', ?, 'review', ?, '2026-10-23T00:00:00+00:00')
                """,
                (self.translator_id, self.admin_id),
            )
            connection.commit()
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            with self.assertRaises(WorkflowError):
                submit_review(connection, "P-001", self.translator_id, "approved", "Self review")
        csrf_missing = self.translator_client.post(
            "/work/P-001",
            {"response_lg": "no csrf", "action": "save"},
            add_csrf=False,
        )
        self.assertEqual(csrf_missing.status_code, 400)

    def test_second_review_disagreement_and_version_history(self):
        self.save_and_submit("P-002", {
            "context_lg": "TEST-Ŋŋ- context",
            "prompt_lg": "TEST-Ŋŋ- prompt",
            "response_lg": "TEST-Ŋŋ- first version",
            "notes": "",
        })
        self.complete_review("P-002", self.reviewer_client, self.reviewer_id, "approved")
        self.complete_review("P-002", self.reviewer2_client, self.reviewer2_id, "needs_revision")
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-002")
            self.assertEqual(translation["status"], "under_dispute")
            self.assertEqual(translation["resolution_required"], 1)
            versions = version_history(connection, "P-002")
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0]["response_lg"], "TEST-Ŋŋ- first version")
        page = self.admin_client.get("/admin/items/P-002")
        self.assertEqual(page.status_code, 200)
        response = self.admin_client.post(
            "/admin/items/P-002",
            {
                "action": "resolve",
                "decision": "needs_revision",
                "notes": "Synthetic owner resolution for tests.",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-002")["status"], "needs_revision")
        self.translator_client.get("/work/P-002")
        response = self.translator_client.post(
            "/work/P-002",
            {
                "context_lg": "TEST-Ŋŋ- context",
                "prompt_lg": "TEST-Ŋŋ- prompt",
                "response_lg": "TEST-Ŋŋ- second version",
                "notes": "",
                "action": "submit",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            translation = get_translation(connection, "P-002")
            self.assertEqual(translation["version"], 2)
            versions = version_history(connection, "P-002")
            self.assertEqual(len(versions), 2)
            self.assertEqual(versions[-1]["response_lg"], "TEST-Ŋŋ- first version")
            self.assertEqual(versions[0]["response_lg"], "TEST-Ŋŋ- second version")

    def test_dataset_approval_requires_separate_consent_status(self):
        self.save_and_submit()
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            values = {
                "licence": "LIC-TEST-001",
                "licence_status": "recorded",
                "consent_ref": "CONSENT-TEST-001",
                "consent_status": "not_recorded",
                "pii_check": "none",
                "contamination_notes": "Synthetic checks completed for tests.",
            }
            for name in (
                "schema",
                "language",
                "instruction_response",
                "duplicate",
                "contamination",
                "pii",
                "token_length",
                "review_complete",
            ):
                values[f"validation_{name}"] = True
            update_training_metadata(connection, "P-001", self.admin_id, values)
            with self.assertRaises(WorkflowError):
                approve_dataset(connection, "P-001", self.admin_id)
            values["consent_status"] = "recorded"
            update_training_metadata(connection, "P-001", self.admin_id, values)
            approve_dataset(connection, "P-001", self.admin_id)
            row = connection.execute(
                "SELECT * FROM training_metadata WHERE item_id = 'P-001'"
            ).fetchone()
            self.assertEqual(row["dataset_status"], "approved_for_dataset")
            self.assertEqual(get_translation(connection, "P-001")["status"], "reviewed")

    def test_owner_can_resolve_disagreement_as_approved(self):
        self.save_and_submit(
            "P-002",
            {
                "context_lg": "TEST-Ŋŋ- context",
                "prompt_lg": "TEST-Ŋŋ- prompt",
                "response_lg": "TEST-Ŋŋ- response",
                "notes": "",
            },
        )
        self.complete_review("P-002", self.reviewer_client, self.reviewer_id, "approved")
        self.complete_review("P-002", self.reviewer2_client, self.reviewer2_id, "needs_revision")
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-002")["status"], "under_dispute")
        page = self.admin_client.get("/admin/items/P-002")
        self.assertEqual(page.status_code, 200)
        response = self.admin_client.post(
            "/admin/items/P-002",
            {
                "action": "resolve",
                "decision": "approved",
                "notes": "Synthetic owner resolution in favour of approval.",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-002")["status"], "reviewed")
            values = {
                "licence": "LIC-TEST-001",
                "licence_status": "recorded",
                "consent_ref": "CONSENT-TEST-001",
                "consent_status": "recorded",
                "pii_check": "none",
                "contamination_notes": "Synthetic checks completed for tests.",
            }
            for name in (
                "schema",
                "language",
                "instruction_response",
                "duplicate",
                "contamination",
                "pii",
                "token_length",
                "review_complete",
            ):
                values[f"validation_{name}"] = True
            update_training_metadata(connection, "P-002", self.admin_id, values)
            approve_dataset(connection, "P-002", self.admin_id)

    def test_home_template_tolerates_missing_reward_context(self):
        html = self.app.templates.get_template("home.html").render(
            user={
                "role": "translator",
                "display_name": "Teacher One",
                "public_id": "T-001",
            },
            counts={
                "waiting": 0,
                "saved": 0,
                "returned": 0,
                "ready": 0,
                "total": 0,
            },
            next_item=None,
            meta={},
            current_path="/home",
            notice=None,
            error=None,
            errors=[],
            csrf_token="test-token",
        )
        self.assertIn("reward dashboard is not loaded", html)

    def test_reward_summary_math(self):
        self.assertEqual(reward_summary(0, 20)["accrued_cents"], 0)
        self.assertEqual(reward_summary(10, 20)["accrued_cents"], 200)
        self.assertEqual(reward_summary(50, 20)["accrued_cents"], 1000)
        self.assertEqual(reward_summary(100, 20)["accrued_cents"], 2000)
        self.assertEqual(reward_summary(10, 20)["accrued_usd"], Decimal("2.00"))
        self.assertEqual(reward_summary(100, 20)["accrued_usd"], Decimal("20.00"))

    def test_reward_counts_only_approved_work_and_admin_sees_it(self):
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(translator_reward(connection, self.translator_id)["approved_count"], 0)
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            pending = translator_reward(connection, self.translator_id)
            self.assertEqual(pending["approved_count"], 0)
            self.assertEqual(pending["pending_count"], 1)
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            reward = translator_reward(connection, self.translator_id)
            self.assertEqual(reward["approved_count"], 1)
            self.assertEqual(reward["accrued_cents"], 20)
            self.assertEqual(reward["accrued_usd"], Decimal("0.20"))
        page = self.translator_client.get("/rewards")
        self.assertEqual(page.status_code, 200)
        self.assertIn("$0.20", page.text)
        self.assertIn("Translation P-001", page.text)
        self.assertIn("Payment status", page.text)
        self.assertIn("unpaid", page.text)
        dashboard = self.translator_client.get("/home")
        self.assertIn("Pending approval", dashboard.text)
        self.assertIn("Revision requested, not yet approved", dashboard.text)
        admin_page = self.admin_client.get("/admin")
        self.assertEqual(admin_page.status_code, 200)
        self.assertIn("Contributor rewards", admin_page.text)
        self.assertIn("$0.20", admin_page.text)

    def test_revision_request_earns_review_reward_but_not_translation_reward(self):
        self.save_and_submit()
        self.complete_review(decision="needs_revision")
        with closing(connect(self.db_path)) as connection:
            translator = translator_reward(connection, self.translator_id)
            reviewer = reviewer_reward(connection, self.reviewer_id)
            self.assertEqual(translator["approved_count"], 0)
            self.assertEqual(translator["revision_count"], 1)
            self.assertEqual(reviewer["review_count"], 1)
            self.assertEqual(reviewer["accrued_cents"], 20)

    def test_cannot_assess_review_is_rewarded_without_approving_translation(self):
        self.save_and_submit()
        self.complete_review(decision="cannot_assess")
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(reviewer_reward(connection, self.reviewer_id)["accrued_cents"], 20)
            self.assertEqual(translator_reward(connection, self.translator_id)["accrued_cents"], 0)

    def test_dispute_resolution_records_translation_reward_once(self):
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            assign_review(connection, "P-001", self.reviewer_id, self.admin_id)
            assign_review(connection, "P-001", self.reviewer2_id, self.admin_id)
            submit_review(connection, "P-001", self.reviewer_id, "approved", "First review approved.")
            self.assertEqual(translator_reward(connection, self.translator_id)["approved_count"], 0)
            submit_review(connection, "P-001", self.reviewer2_id, "needs_revision", "Please correct this issue.")
            self.assertEqual(get_translation(connection, "P-001")["status"], "under_dispute")
            self.assertEqual(translator_reward(connection, self.translator_id)["approved_count"], 0)
            resolve_dispute(connection, "P-001", self.admin_id, "approved", "The owner accepted the correction.")
            self.assertEqual(translator_reward(connection, self.translator_id)["accrued_cents"], 20)
            self.assertEqual(reviewer_reward(connection, self.reviewer_id)["accrued_cents"], 20)
            self.assertEqual(reviewer_reward(connection, self.reviewer2_id)["accrued_cents"], 20)

    def test_reward_history_is_private_to_each_contributor(self):
        with closing(connect(self.db_path)) as connection:
            other_translator_id, _ = auth.create_user(
                connection, "translator_two", "Teacher Four", "translator", "teacher4-password-123"
            )
            assign_translation(connection, "P-018", other_translator_id, self.admin_id)
        self.save_and_submit()
        self.complete_review()
        other_client = Client(self.app)
        other_client.login("translator_two", "teacher4-password-123")
        other_client.post(
            "/work/P-018",
            {"prompt_lg": "Other prompt", "response_lg": "Other response", "action": "submit"},
        )
        with closing(connect(self.db_path)) as connection:
            assign_review(connection, "P-018", self.reviewer2_id, self.admin_id)
        reviewer_two_client = Client(self.app)
        reviewer_two_client.login("reviewer2", "review2-password-123")
        reviewer_two_client.post(
            "/review/P-018",
            {"decision": "approved", "comments": "Other contributor review."},
        )
        translator_page = self.translator_client.get("/rewards")
        other_translator_page = other_client.get("/rewards")
        reviewer_page = self.reviewer_client.get("/rewards")
        reviewer_two_page = reviewer_two_client.get("/rewards")
        self.assertIn("Translation P-001", translator_page.text)
        self.assertNotIn("Translation P-018", translator_page.text)
        self.assertIn("Translation P-018", other_translator_page.text)
        self.assertNotIn("Translation P-001", other_translator_page.text)
        self.assertIn("Translation P-001", reviewer_page.text)
        self.assertNotIn("Translation P-018", reviewer_page.text)
        self.assertIn("Translation P-018", reviewer_two_page.text)
        self.assertNotIn("Translation P-001", reviewer_two_page.text)

    def test_schema_migration_backfills_verifiable_work_and_payment_cents(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-reward-migration-") as temporary:
            legacy_path = Path(temporary) / "legacy.sqlite3"
            with closing(connect(legacy_path)) as connection:
                legacy_schema = SCHEMA.replace(
                    "    amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_cents >= 0),\n", ""
                )
                legacy_schema = re.sub(
                    r"CREATE TABLE IF NOT EXISTS reward_earnings \(.*?"
                    r"CREATE INDEX IF NOT EXISTS reward_earnings_recipient_idx\n"
                    r"    ON reward_earnings\(recipient_id, recipient_role, earned_at, id\);\n",
                    "",
                    legacy_schema,
                    flags=re.S,
                )
                connection.executescript(legacy_schema)
                owner_id, _ = auth.create_user(connection, "legacy_owner", "Owner", "admin", "owner-password-123")
                translator_id, _ = auth.create_user(
                    connection, "legacy_translator", "Translator", "translator", "translator-password-123"
                )
                reviewer_id, _ = auth.create_user(
                    connection, "legacy_reviewer", "Reviewer", "reviewer", "reviewer-password-123"
                )
                import_source(connection, SOURCE, actor_id=owner_id)
                assign_translation(connection, "P-001", translator_id, owner_id)
                save_translation(
                    connection, "P-001", translator_id, "Context", [], "Question", "Answer", "", submit=True
                )
                assign_review(connection, "P-001", reviewer_id, owner_id)
                connection.execute(
                    "INSERT INTO reviews(item_id, reviewer_id, translation_version, decision, comments, "
                    "suggested_correction, created_at) VALUES (?, ?, 1, 'approved', '', '', ?)",
                    ("P-001", reviewer_id, "2026-01-02T10:00:00+00:00"),
                )
                connection.execute(
                    "UPDATE translations SET status = 'reviewed' WHERE item_id = 'P-001'"
                )
                connection.execute(
                    """
                    INSERT INTO translation_versions(
                        item_id, version, translator_id, context_lg, turns_lg, prompt_lg,
                        response_lg, notes, submitted_at
                    )
                    SELECT item_id, 2, translator_id, context_lg, turns_lg, prompt_lg,
                           response_lg, notes, '2026-01-04T10:00:00+00:00'
                    FROM translations WHERE item_id = 'P-001'
                    """
                )
                connection.execute(
                    "UPDATE translations SET status = 'ready_for_review', version = 2, "
                    "submitted_at = '2026-01-04T10:00:00+00:00' WHERE item_id = 'P-001'"
                )
                connection.execute(
                    "INSERT INTO reward_payments(recipient_id, recipient_role, amount_usd, work_count, note, "
                    "paid_at, created_by, created_at) VALUES (?, 'reviewer', 0.20, 1, 'Legacy reference', ?, ?, ?)",
                    (reviewer_id, "2026-01-03T10:00:00+00:00", owner_id, "2026-01-03T10:00:00+00:00"),
                )
                connection.commit()
                init_db(connection)
                self.assertEqual(
                    translator_reward(connection, translator_id)["accrued_cents"], 20
                )
                self.assertEqual(
                    translator_reward(connection, translator_id)["approved_items"][0]["translation_version"],
                    1,
                )
                reviewer_reward_data = reviewer_reward(connection, reviewer_id)
                self.assertEqual(reviewer_reward_data["accrued_cents"], 20)
                self.assertEqual(reviewer_reward_data["paid_cents"], 20)
                self.assertEqual(reviewer_reward_data["reviews"][0]["payment_status"], "paid")
                self.assertEqual(reviewer_reward_data["reviews"][0]["payment_references"], ["Legacy reference"])
                init_db(connection)
                self.assertEqual(reviewer_reward(connection, reviewer_id)["review_count"], 1)

    def test_schema_migration_retries_payment_conversion_when_cents_column_exists(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-partial-reward-migration-") as temporary:
            with closing(connect(Path(temporary) / "partial.sqlite3")) as connection:
                init_db(connection)
                owner_id, _ = auth.create_user(
                    connection, "partial_owner", "Owner", "admin", "owner-password-123"
                )
                reviewer_id, _ = auth.create_user(
                    connection, "partial_reviewer", "Reviewer", "reviewer", "reviewer-password-123"
                )
                connection.execute(
                    "INSERT INTO reward_payments(recipient_id, recipient_role, amount_usd, amount_cents, "
                    "work_count, note, paid_at, created_by, created_at) "
                    "VALUES (?, 'reviewer', 0.20, 0, 1, 'Legacy payment', ?, ?, ?)",
                    (reviewer_id, "2026-01-03T10:00:00+00:00", owner_id, "2026-01-03T10:00:00+00:00"),
                )
                connection.commit()

                init_db(connection)

                payment = connection.execute(
                    "SELECT amount_cents FROM reward_payments WHERE recipient_id = ?", (reviewer_id,)
                ).fetchone()
                self.assertEqual(payment["amount_cents"], 20)
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM reward_payments").fetchone()[0], 1
                )
                connection.execute(
                    "INSERT INTO reward_payments(recipient_id, recipient_role, amount_usd, amount_cents, "
                    "work_count, note, paid_at, created_by, created_at) "
                    "VALUES (?, 'reviewer', 0.30, 20, 1, 'Inconsistent payment', ?, ?, ?)",
                    (reviewer_id, "2026-01-04T10:00:00+00:00", owner_id, "2026-01-04T10:00:00+00:00"),
                )
                connection.commit()
                with self.assertRaisesRegex(RuntimeError, "inconsistent dollar and cent amounts"):
                    init_db(connection)
                self.assertEqual(
                    connection.execute(
                        "SELECT amount_cents FROM reward_payments WHERE note = 'Inconsistent payment'"
                    ).fetchone()[0],
                    20,
                )

    def test_repeated_review_and_reapproval_do_not_duplicate_earnings(self):
        self.save_and_submit()
        self.complete_review()
        repeated = self.reviewer_client.post(
            "/review/P-001",
            {"decision": "approved", "comments": "Duplicate attempt."},
        )
        self.assertEqual(repeated.status_code, 400)
        with closing(connect(self.db_path)) as connection:
            return_translation(connection, "P-001", self.admin_id, "Correction after approval.")
            self.assertEqual(translator_reward(connection, self.translator_id)["approved_count"], 1)
        resubmitted = self.translator_client.post(
            "/work/P-001", {**self.p001_data("Corrected Luganda reply."), "action": "submit"}
        )
        self.assertEqual(resubmitted.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            submit_review(connection, "P-001", self.reviewer_id, "approved", "Approved again.")
            self.assertEqual(translator_reward(connection, self.translator_id)["approved_count"], 1)
            self.assertEqual(reviewer_reward(connection, self.reviewer_id)["review_count"], 2)

    def test_reviewer_cannot_approve_missing_background_passage(self):
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            connection.execute("UPDATE translations SET context_lg = '' WHERE item_id = 'P-001'")
            connection.commit()
            assign_review(connection, "P-001", self.reviewer_id, self.admin_id)
        page = self.reviewer_client.get("/review/P-001")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Required background passage missing", page.text)
        response = self.reviewer_client.post(
            "/review/P-001",
            {"decision": "approved", "comments": "This should not be allowed."},
        )
        self.assertEqual(response.status_code, 400)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-001")["status"], "ready_for_review")
            self.assertEqual(reviewer_reward(connection, self.reviewer_id)["review_count"], 0)

    def test_admin_can_return_submitted_work_for_correction(self):
        self.save_and_submit()
        page = self.admin_client.get("/admin/items/P-001")
        self.assertEqual(page.status_code, 200)
        response = self.admin_client.post(
            "/admin/items/P-001",
            {
                "action": "return_translation",
                "reason": "Please complete the Luganda background passage and check the assistant reply.",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(get_translation(connection, "P-001")["status"], "needs_revision")
        translator_page = self.translator_client.get("/work/P-001")
        self.assertEqual(translator_page.status_code, 200)
        self.assertIn("Passage translated into Luganda", translator_page.text)

    def test_reviewer_reward_and_payment_clearing(self):
        self.save_and_submit()
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            reward = reviewer_reward(connection, self.reviewer_id)
            self.assertEqual(reward["review_count"], 1)
            self.assertEqual(reward["accrued_cents"], 20)
            self.assertEqual(reward["available_cents"], 20)
            self.assertEqual(reward["paid_cents"], 0)
        page = self.admin_client.get("/admin/payments")
        self.assertEqual(page.status_code, 200)
        response = self.admin_client.post(
            "/admin/payments",
            {
                "recipient_id": self.reviewer_id,
                "role": "reviewer",
                "amount": "0.20",
                "note": "Synthetic reviewer payment for tests.",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            reward = reviewer_reward(connection, self.reviewer_id)
            self.assertEqual(reward["paid_cents"], 20)
            self.assertEqual(reward["available_cents"], 0)
            self.assertEqual(len(reward["payments"]), 1)
            with self.assertRaises(WorkflowError):
                record_payment(
                    connection,
                    self.reviewer_id,
                    "reviewer",
                    "0.01",
                    "Overpay attempt",
                    self.admin_id,
                )
        rewards_page = self.reviewer_client.get("/rewards")
        self.assertIn("Payment reference: Synthetic reviewer payment for tests.", rewards_page.text)
        self.assertIn("Paid", rewards_page.text)
        self.assertIn("$0.20 paid", rewards_page.text)
        self.save_and_submit(
            "P-002",
            {
                "context_lg": "TEST-Ŋŋ- context",
                "prompt_lg": "TEST-Ŋŋ- prompt",
                "response_lg": "TEST-Ŋŋ- response",
                "notes": "",
            },
        )
        self.complete_review("P-002", self.reviewer_client, self.reviewer_id, "approved")
        with closing(connect(self.db_path)) as connection:
            reward = reviewer_reward(connection, self.reviewer_id)
            self.assertEqual(reward["review_count"], 2)
            self.assertEqual(reward["accrued_cents"], 40)
            self.assertEqual(reward["paid_cents"], 20)
            self.assertEqual(reward["available_cents"], 20)

    def test_translator_payment_clearing(self):
        self.save_and_submit()
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            reward = translator_reward(connection, self.translator_id)
            self.assertEqual(reward["available_cents"], 20)
        response = self.admin_client.post(
            "/admin/payments",
            {
                "recipient_id": self.translator_id,
                "role": "translator",
                "amount": "0.20",
                "note": "Synthetic translator payment for tests.",
            },
        )
        self.assertEqual(response.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            reward = translator_reward(connection, self.translator_id)
            self.assertEqual(reward["paid_cents"], 20)
            self.assertEqual(reward["available_cents"], 0)
            self.assertEqual(len(reward["payments"]), 1)
        rewards_page = self.translator_client.get("/rewards")
        self.assertIn("Payment recorded", rewards_page.text)

    def test_partial_payment_uses_integer_cents_and_shows_reference(self):
        self.save_and_submit()
        self.complete_review()
        first_payment = self.admin_client.post(
            "/admin/payments",
            {
                "recipient_id": self.translator_id,
                "role": "translator",
                "amount": "0.05",
                "note": "Synthetic partial payment.",
            },
        )
        self.assertEqual(first_payment.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            reward = translator_reward(connection, self.translator_id)
            self.assertEqual(reward["paid_cents"], 5)
            self.assertEqual(reward["available_cents"], 15)
            self.assertEqual(reward["approved_items"][0]["payment_status"], "partially paid")
            payment = reward["payments"][0]
            self.assertEqual(payment["amount_cents"], 5)
            self.assertEqual(payment["amount_usd"], Decimal("0.05"))
        page = self.translator_client.get("/rewards")
        self.assertIn("Partially paid", page.text)
        self.assertIn("Synthetic partial payment", page.text)
        cleared = self.admin_client.post(
            "/admin/payments",
            {
                "recipient_id": self.translator_id,
                "role": "translator",
                "amount": "0.15",
                "note": "Synthetic final payment.",
            },
        )
        self.assertEqual(cleared.status_code, 302)
        with closing(connect(self.db_path)) as connection:
            reward = translator_reward(connection, self.translator_id)
            self.assertEqual(reward["paid_cents"], 20)
            self.assertEqual(reward["available_cents"], 0)
            self.assertEqual(reward["approved_items"][0]["payment_status"], "paid")

    def test_training_export_validates_and_excludes_evaluation(self):
        self.save_and_submit()
        self.complete_review()
        with closing(connect(self.db_path)) as connection:
            metadata = {
                "licence": "LIC-TEST-001",
                "licence_status": "recorded",
                "consent_ref": "CONSENT-TEST-001",
                "consent_status": "recorded",
                "pii_check": "none",
                "contamination_notes": "Synthetic exact and 8-word checks completed for tests.",
            }
            for name in (
                "schema",
                "language",
                "instruction_response",
                "duplicate",
                "contamination",
                "pii",
                "token_length",
                "review_complete",
            ):
                metadata[f"validation_{name}"] = True
            update_training_metadata(connection, "P-001", self.admin_id, metadata)
            approve_dataset(connection, "P-001", self.admin_id)
            with self.assertRaises(WorkflowError):
                build_training_record(connection, "E-001")
            jsonl_path, manifest_path, manifest = export_training_jsonl(
                connection, self.admin_id, self.export_dir
            )
            self.assertFalse(manifest["training_authorized"])
            self.assertTrue(manifest["evaluation_excluded"])
            records = [
                json.loads(line)
                for line in jsonl_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["pilot_id"], "P-001")
            self.assertEqual(records[0]["messages"][-2]["role"], "user")
            self.assertIn("TEST-Ŋŋ- context", records[0]["messages"][-2]["content"])
            self.assertIn("TEST-Ŋŋ- prompt", records[0]["messages"][-2]["content"])
            validate_pilot_record(records[0], expected_split="train")
            self.assertFalse(any(record["pilot_id"].startswith("E-") for record in records))
            csv_path, count = export_review_csv(connection, self.admin_id, self.export_dir)
            self.assertEqual(count, 124)

    def test_admin_pages_render_and_mobile_assets_exist(self):
        self.save_and_submit()
        with closing(connect(self.db_path)) as connection:
            assign_review(connection, "P-001", self.reviewer_id, self.admin_id)
        for path in (
            "/admin",
            "/admin/users",
            "/admin/assign",
            "/admin/items",
            "/admin/items/P-001",
            "/admin/export",
            "/admin/audit",
            "/review",
            "/review/P-001",
        ):
            response = self.admin_client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(
                '<aside class="admin-sidebar" aria-label="Administration">',
                response.text,
                path,
            )
        self.assertEqual(self.translator_client.get("/progress").status_code, 200)
        page = self.translator_client.get("/home")
        self.assertIn("width=device-width", page.text)
        css = self.translator_client.get("/static/studio.css")
        self.assertIn("@media (max-width: 680px)", css.text)
        self.assertIn("overflow-x: auto", css.text)
        self.assertIn("position: sticky", css.text)
        self.assertIn(".teacher-work-aside", css.text)
        background = self.translator_client.get("/static/Background_img.png")
        self.assertEqual(background.status_code, 200)
        self.assertTrue(background.body.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
