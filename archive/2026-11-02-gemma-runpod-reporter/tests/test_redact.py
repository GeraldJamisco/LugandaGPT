"""Redaction tests: credential shapes never survive into output."""

import unittest

from reporter import redact


class RedactionTests(unittest.TestCase):
    def test_telegram_token_redacted(self):
        text = "token is 123456789:" + "A" * 35 + " ok"
        out = redact.redact(text)
        self.assertNotIn("A" * 35, out)
        self.assertIn(redact.REDACTED, out)

    def test_common_key_shapes_redacted(self):
        samples = [
            "sk-" + "a" * 30,
            "ghp_" + "b" * 30,
            "hf_" + "c" * 30,
            "AIza" + "d" * 30,
            "-----BEGIN RSA PRIVATE KEY-----",
        ]
        for sample in samples:
            with self.subTest(sample=sample[:12]):
                self.assertNotIn(sample, redact.redact(f"value {sample} end"))

    def test_assignment_style_secret_redacted(self):
        self.assertNotIn("supersecretvalue123", redact.redact('api_key="supersecretvalue123"'))

    def test_plain_text_untouched(self):
        text = "Roadmap phase 2 is blocked on phase 1 approval."
        self.assertEqual(redact.redact(text), text)

    def test_contains_secret_detects_token(self):
        self.assertTrue(redact.contains_secret("999999999:" + "Z" * 35))
        self.assertFalse(redact.contains_secret("no secrets here"))

    def test_configured_env_token_is_always_removed(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"LUGANDAGPT_TELEGRAM_BOT_TOKEN": "555555555:" + "C" * 35}):
            text = "leak " + "555555555:" + "C" * 35
            self.assertNotIn("C" * 35, redact.redact(text))
            self.assertTrue(redact.contains_secret(text))

    def test_redact_value_walks_nested_structures(self):
        payload = {
            "a": ["ok", "sk-" + "e" * 30],
            "b": {"c": ("fine", "ghp_" + "f" * 30)},
            "d": 5,
        }
        out = redact.redact_value(payload)
        self.assertNotIn("e" * 30, str(out))
        self.assertNotIn("f" * 30, str(out))
        self.assertEqual(out["d"], 5)


if __name__ == "__main__":
    unittest.main()
