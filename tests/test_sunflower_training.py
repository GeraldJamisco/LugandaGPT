import json
import tempfile
import unittest
from pathlib import Path

from training.sunflower_config import build_config
from training.sunflower_data import load_training_rows, HELDOUT_PATTERN
from training.errors import ConfigError, DataError
from training import train_sunflower


def _write(lines):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for obj in lines:
        f.write(json.dumps(obj) + "\n")
    f.close()
    return f.name


def _row(uid="X-1", user="Say hi", asst="Ki kati", source="s"):
    return {"id": uid, "source": source,
            "messages": [{"role": "user", "content": user},
                         {"role": "assistant", "content": asst}]}


class ConfigTests(unittest.TestCase):
    def test_default_identity_pinned(self):
        cfg = build_config()
        self.assertEqual(cfg["base_model"], "Sunbird/Sunflower-14B")
        self.assertEqual(cfg["license"], "apache-2.0")

    def test_cannot_override_identity(self):
        with self.assertRaises(ConfigError):
            build_config({"base_model": "evil/model"})

    def test_budget_cap_enforced(self):
        with self.assertRaises(ConfigError):
            build_config({"approved_usd": 50})

    def test_unknown_field_rejected(self):
        with self.assertRaises(ConfigError):
            build_config({"nonsense": 1})


class DataTests(unittest.TestCase):
    def test_loads_good_rows(self):
        path = _write([_row(), _row("X-2")])
        self.assertEqual(len(load_training_rows(path)), 2)

    def test_rejects_heldout_hour(self):
        path = _write([_row(user="meeting at 9:00am tomorrow")])
        with self.assertRaises(DataError):
            load_training_rows(path)

    def test_rejects_credential(self):
        path = _write([_row(asst="token hf_" + "a" * 25)])
        with self.assertRaises(DataError):
            load_training_rows(path)

    def test_rejects_wrong_roles(self):
        bad = {"id": "B", "source": "s",
               "messages": [{"role": "assistant", "content": "x"},
                            {"role": "user", "content": "y"}]}
        path = _write([bad])
        with self.assertRaises(DataError):
            load_training_rows(path)

    def test_heldout_pattern_boundaries(self):
        self.assertTrue(HELDOUT_PATTERN.search("at 1:00pm"))
        self.assertFalse(HELDOUT_PATTERN.search("at 11:00am"))


class PlanTests(unittest.TestCase):
    def test_plan_has_sha_and_summary(self):
        path = _write([_row(source="rule"), _row("X-2", source="salt")])
        args = train_sunflower.main.__globals__["argparse"].Namespace(
            train=path, output="runs/x", config=None, epochs=None, max_seq_len=None)
        p = train_sunflower.plan(args)
        self.assertEqual(p["data_summary"]["rows"], 2)
        self.assertIn("train_sha256", p)
        self.assertEqual(len(p["train_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
