"""Dashboard tests: localhost binding, method and origin checks, traversal."""

import http.client
import json
import os
import threading
import unittest
from unittest import mock

from reporter import config, dashboard, store

from .support import ReporterPathTestCase

FAKE_TOKEN = "123456789:" + "A" * 35


class DashboardTestCase(ReporterPathTestCase):
    def setUp(self):
        super().setUp()
        # reuse_address=False: with SO_REUSEADDR on Windows, binding to port
        # 0 can hand back a port a live reporter already holds, and requests
        # then reach that process (real Telegram messages, real state writes).
        self.server = dashboard.create_server("127.0.0.1", 0, reuse_address=False)
        self.port = self.server.server_port
        self.assertNotEqual(self.port, config.DEFAULT_PORT)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        def shutdown():
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)

        self.addCleanup(shutdown)

    def request(self, method, path, body=None, headers=None, content_type="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = dict(headers or {})
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8") if not isinstance(body, (bytes, str)) else body
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            headers.setdefault("Content-Type", content_type)
            headers.setdefault("X-Reporter-Client", "local")
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8", "replace")
        status = response.status
        content_type_resp = response.getheader("Content-Type")
        conn.close()
        return status, data, content_type_resp


class StaticAndRouteTests(DashboardTestCase):
    def test_index_served_at_root(self):
        status, data, ctype = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("LugandaGPT Project Reporter", data)

    def test_static_assets_served(self):
        for name, expected in (("style.css", "text/css"), ("app.js", "javascript")):
            with self.subTest(name=name):
                status, data, ctype = self.request("GET", f"/static/{name}")
                self.assertEqual(status, 200)
                self.assertIn(expected, ctype)

    def test_unknown_static_path_traversal_is_not_found(self):
        for path in (
            "/static/../config.py",
            "/static/%2e%2e/config.py",
            "/static/..%2Fconfig.py",
            "/static/nonexistent.js",
        ):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 404)

    def test_unknown_endpoint_is_not_found(self):
        for path in ("/nope", "/api/unknown", "/api/report/generate"):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 404)

    def test_report_path_traversal_is_rejected(self):
        for path in (
            "/api/report/../../etc/passwd",
            "/api/report/%2e%2e%2f%2e%2e%2fetc",
            "/api/report/notareportid",
            "/api/report/RPT-20261019-080000-P8H/../../../secrets",
        ):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertIn(status, (400, 404))

    def test_methods_other_than_get_and_post_are_rejected(self):
        for method in ("PUT", "DELETE", "PATCH"):
            with self.subTest(method=method):
                status, _, _ = self.request(method, "/api/overview")
                self.assertEqual(status, 405)


class OverviewTests(DashboardTestCase):
    def test_overview_returns_verified_sources(self):
        status, data, _ = self.request("GET", "/api/overview")
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertTrue(payload["ok"])
        overview = payload["overview"]
        for key in (
            "repo",
            "phase",
            "blockers",
            "milestones",
            "tests",
            "experiments",
            "api_spending",
            "schedule",
            "reporting",
            "telegram",
            "reports",
            "timeline",
            "public_drafts",
            "model_status",
        ):
            self.assertIn(key, overview)
        self.assertIn("No trained LugandaGPT model exists", overview["model_status"])
        self.assertFalse(overview["schedule"]["enabled"])

    def test_overview_never_returns_a_token(self):
        with mock.patch.dict(os.environ, {config.TOKEN_ENV: FAKE_TOKEN}):
            status, data, _ = self.request("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertNotIn(FAKE_TOKEN, data)
        self.assertIn('"token_configured": true', data)

    def test_telegram_status_endpoint_hides_credentials(self):
        with mock.patch.dict(os.environ, {config.TOKEN_ENV: FAKE_TOKEN}):
            status, data, _ = self.request("GET", "/api/telegram/status")
        self.assertEqual(status, 200)
        self.assertNotIn(FAKE_TOKEN, data)
        self.assertIn("token_never_returned", data)


class WriteRequestGuardTests(DashboardTestCase):
    def test_foreign_origin_is_rejected(self):
        status, data, _ = self.request(
            "POST",
            "/api/schedule",
            body={"enabled": True},
            headers={"Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertFalse(json.loads(data)["ok"])

    def test_browser_like_request_without_local_marker_is_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body = json.dumps({"enabled": True}).encode("utf-8")
        conn.request(
            "POST",
            "/api/schedule",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        response.read()
        conn.close()
        self.assertEqual(response.status, 403)

    def test_local_origin_is_accepted(self):
        status, data, _ = self.request(
            "POST",
            "/api/schedule",
            body={"enabled": False},
            headers={"Origin": f"http://127.0.0.1:{self.port}"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data)["ok"])

    def test_invalid_host_header_is_rejected(self):
        status, _, _ = self.request(
            "GET", "/api/overview", headers={"Host": "evil.example"}
        )
        self.assertEqual(status, 403)

    def test_wrong_content_type_is_rejected(self):
        status, _, _ = self.request(
            "POST",
            "/api/schedule",
            body='{"enabled": true}',
            content_type="text/plain",
        )
        self.assertEqual(status, 415)

    def test_invalid_payload_values_are_rejected(self):
        status, data, _ = self.request(
            "POST", "/api/schedule", body={"enabled": "yes"}
        )
        self.assertEqual(status, 400)
        self.assertIn("boolean", json.loads(data)["error"])

    def test_unexpected_fields_are_rejected(self):
        status, data, _ = self.request(
            "POST", "/api/schedule", body={"enabled": True, "cmd": "rm -rf /"}
        )
        self.assertEqual(status, 400)
        self.assertIn("unexpected fields", json.loads(data)["error"])

    def test_oversized_body_is_rejected_before_reading(self):
        blob = json.dumps({"enabled": True, "pad": "x" * (config.MAX_POST_BODY_BYTES + 10)})
        status, _, _ = self.request("POST", "/api/schedule", body=blob)
        self.assertEqual(status, 413)

    def test_malformed_json_is_rejected(self):
        status, _, _ = self.request("POST", "/api/schedule", body="{not json")
        self.assertEqual(status, 400)

    def test_only_approved_write_endpoints_exist(self):
        self.assertEqual(
            set(dashboard.POST_ROUTES),
            {
                "/api/report/generate",
                "/api/report/deliver",
                "/api/telegram/test",
                "/api/schedule",
            },
        )
        for payload in dashboard.ALLOWED_BODY_KEYS.values():
            self.assertLessEqual(len(payload), 1)


class ActionTests(DashboardTestCase):
    def test_generate_report_action_creates_a_report(self):
        status, data, _ = self.request("POST", "/api/report/generate", body={})
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertTrue(payload["ok"])
        report_id = payload["result"]["report_id"]
        self.assertTrue(store.is_valid_report_id(report_id))
        self.assertTrue((self.archive_dir / f"{report_id}.json").exists())

    def test_generated_report_is_fetchable_by_id(self):
        _, data, _ = self.request("POST", "/api/report/generate", body={})
        report_id = json.loads(data)["result"]["report_id"]
        status, body, ctype = self.request("GET", f"/api/report/{report_id}/markdown")
        self.assertEqual(status, 200)
        self.assertIn("text/markdown", ctype)
        self.assertIn("# LugandaGPT Project Reporter", body)
        status, _, _ = self.request("GET", f"/api/report/{report_id}")
        self.assertEqual(status, 200)

    def test_schedule_enable_refused_without_delivery_test(self):
        status, data, _ = self.request("POST", "/api/schedule", body={"enabled": True})
        self.assertEqual(status, 409)
        payload = json.loads(data)
        self.assertFalse(payload["ok"])
        self.assertTrue(any("delivery test" in str(x) for x in [payload.get("result", {}).get("reason")]))
        self.assertFalse(store.read_state()["schedule"]["enabled"])

    def test_telegram_test_action_without_credentials_fails_cleanly(self):
        with mock.patch.dict(
            os.environ, {config.TOKEN_ENV: "", config.CHAT_ENV: ""}
        ), mock.patch.object(
            __import__("urllib.request", fromlist=["urlopen"]),
            "urlopen",
            side_effect=AssertionError("network used"),
        ) as opened:
            status, data, _ = self.request("POST", "/api/telegram/test", body={})
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["result"]["stage"], "configuration")
        opened.assert_not_called()

    def test_generate_action_reports_a_generation_failure(self):
        with mock.patch.object(
            dashboard.runner.report_mod,
            "generate_report",
            side_effect=RuntimeError("collector exploded"),
        ):
            status, data, _ = self.request("POST", "/api/report/generate", body={})
        self.assertEqual(status, 500)
        payload = json.loads(data)
        self.assertFalse(payload["ok"])
        self.assertIn("collector exploded", payload["error"])
        self.assertEqual(payload["result"]["stage"], "generate")

    def test_deliver_action_without_anything_to_send_is_not_found(self):
        status, data, _ = self.request("POST", "/api/report/deliver", body={})
        self.assertEqual(status, 404)
        payload = json.loads(data)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["result"]["stage"], "select")
        self.assertIn("reporting", payload)

    def test_deliver_action_rejects_an_invalid_report_id(self):
        status, data, _ = self.request(
            "POST", "/api/report/deliver", body={"report_id": "../etc"}
        )
        self.assertEqual(status, 400)

    def test_deliver_action_sends_the_saved_report(self):
        _, data, _ = self.request("POST", "/api/report/generate", body={})
        report_id = json.loads(data)["result"]["report_id"]
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        store.write_state(state)

        with mock.patch.object(
            dashboard.telegram_client,
            "send_report",
            return_value={
                "ok": True,
                "message_ids": [7],
                "attempts": 1,
                "parts_sent": 1,
                "parts_total": 1,
            },
        ):
            status, data, _ = self.request("POST", "/api/report/deliver", body={})
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["report_id"], report_id)
        reporting = payload["reporting"]
        self.assertTrue(reporting["last_delivery"]["ok"])
        self.assertIsNone(reporting["awaiting_delivery"])
        self.assertEqual(reporting["last_delivered_report_id"], report_id)

        # A second retry must not send the same report again.
        with mock.patch.object(dashboard.telegram_client, "send_report") as send:
            status, data, _ = self.request("POST", "/api/report/deliver", body={})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data)["result"].get("duplicate"))
        send.assert_not_called()

    def test_deliver_action_reports_a_delivery_failure(self):
        _, data, _ = self.request("POST", "/api/report/generate", body={})
        report_id = json.loads(data)["result"]["report_id"]
        state = store.read_state()
        state["telegram"]["delivery_test_passed"] = True
        store.write_state(state)

        with mock.patch.object(
            dashboard.telegram_client,
            "send_report",
            return_value={
                "ok": False,
                "error": "sendMessage failed (code 400): Bad Request: chat not found",
                "attempts": 2,
                "parts_sent": 0,
                "parts_total": 2,
            },
        ):
            status, data, _ = self.request("POST", "/api/report/deliver", body={})
        self.assertEqual(status, 409)
        payload = json.loads(data)
        self.assertFalse(payload["ok"])
        self.assertIn("chat not found", payload["result"]["error"])
        reporting = payload["reporting"]
        self.assertEqual(reporting["awaiting_delivery"]["report_id"], report_id)
        self.assertFalse(reporting["last_delivery"]["ok"])
        # The saved report still exists and was not modified.
        self.assertTrue(store.report_exists(report_id))


if __name__ == "__main__":
    unittest.main()
