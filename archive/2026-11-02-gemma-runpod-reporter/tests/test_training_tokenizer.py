"""Tokenizer-only checks against the pinned local base tokenizer."""

import os
import tempfile
import unittest
from pathlib import Path

from training.config import load_config
from training.data import check_token_limits, expand_prompt_completion, load_pilot_dataset
from training.errors import DataError
from training.modeling import load_tokenizer, verify_tokenizer

from .training_support import AS_OF, BASE_CONFIG, valid_pilot_record, write_synthetic_project

DEFAULT_TOKENIZER = Path(r"D:\LugandaGPT\models\gemma-3-1b-it")
TOKENIZER_PATH = Path(os.environ.get("LUGANDAGPT_TOKENIZER_PATH", DEFAULT_TOKENIZER))


@unittest.skipUnless(
    (TOKENIZER_PATH / "tokenizer_config.json").is_file(),
    "pinned local tokenizer is not available",
)
class LocalTokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(BASE_CONFIG)
        cls.tokenizer = load_tokenizer(
            cls.config, model_path=TOKENIZER_PATH, local_files_only=True
        )

    def test_pinned_tokenizer_identity(self):
        identity = verify_tokenizer(self.tokenizer)
        self.assertEqual(
            identity["chat_template_sha256"],
            "7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4",
        )
        self.assertEqual(identity["eos_token_id"], 1)
        self.assertEqual(identity["end_of_turn_token_id"], 106)
        self.assertEqual(identity["pad_token_id"], 0)

    def test_synthetic_record_is_within_limits(self):
        record = valid_pilot_record()
        result = check_token_limits(record, self.tokenizer)
        self.assertEqual(result["assistant_turns"], 1)
        self.assertGreater(result["full_tokens"], 0)
        self.assertLessEqual(result["max_prompt_completion_tokens"], 512)

    def test_short_conversation_expands_each_assistant_turn(self):
        record = valid_pilot_record(capability="short_conversation")
        expanded = expand_prompt_completion(record)
        self.assertEqual(len(expanded), 2)
        self.assertEqual([item["turn_index"] for item in expanded], [1, 3])
        result = check_token_limits(record, self.tokenizer)
        self.assertEqual(result["assistant_turns"], 2)

    def test_over_limit_record_rejected(self):
        record = valid_pilot_record()
        record["messages"][0]["content"] = "word " * 700
        with self.assertRaises(DataError):
            check_token_limits(record, self.tokenizer)

    def test_full_synthetic_project_with_tokenizer(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-tokenizer-") as temporary:
            project = write_synthetic_project(temporary)
            dataset = load_pilot_dataset(
                project["config"],
                project_root=project["root"],
                require_complete=True,
                require_approved=True,
                tokenizer=self.tokenizer,
                require_token_checks=True,
                as_of=AS_OF,
            )
            checks = dataset.summary["token_checks"]
            self.assertEqual(checks["records_checked"], 124)
            self.assertEqual(checks["status"], "within_declared_limits")
            self.assertGreater(checks["assistant_turns"], 100)


if __name__ == "__main__":
    unittest.main()
