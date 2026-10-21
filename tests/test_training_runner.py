"""Guarded runner and modeling-construction tests that do not load weights."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from training.config import load_config
from training.environment import check_runtime, installed_versions
from training.errors import AuthorizationError, EnvironmentError, TrainingError
from training.inference import _adapter_hash, _prompt_before_final_assistant, build_blind_packet
from training.modeling import build_lora_config, build_sft_config, verify_adapter_identity
from training.runner import _require_run_metadata, preflight

from .training_support import BASE_CONFIG, valid_pilot_record


class EnvironmentTests(unittest.TestCase):
    def test_current_environment_is_not_the_pinned_pod(self):
        versions = installed_versions()
        self.assertIsNone(versions["datasets"])
        self.assertIsNone(versions["trl"])
        with self.assertRaises(EnvironmentError):
            check_runtime(load_config(BASE_CONFIG), require_gpu=True)

    def test_run_metadata_placeholders_rejected(self):
        with self.assertRaises(TrainingError):
            _require_run_metadata("pod-123", "any_available_record_actual", "host", "image")
        with self.assertRaises(TrainingError):
            _require_run_metadata("pod-123", "region", "host", "record_exact_at_launch")
        with self.assertRaises(TrainingError):
            _require_run_metadata("pod-123", "<console region>", "host", "image")
        values = _require_run_metadata("pod-123", "US-KS-2", "host.example", "image@sha256:abc")
        self.assertEqual(values["pod_id"], "pod-123")


class ConstructionTests(unittest.TestCase):
    def test_lora_config_matches_pins(self):
        config = load_config(BASE_CONFIG)
        lora = build_lora_config(config)
        self.assertEqual(lora.r, 16)
        self.assertEqual(lora.lora_alpha, 32)
        self.assertEqual(
            set(lora.target_modules),
            {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"},
        )
        self.assertFalse(lora.use_dora)
        self.assertFalse(lora.use_rslora)

    @unittest.skipIf(
        importlib.util.find_spec("trl") is not None,
        "TRL is installed; this assertion is for the preparation environment",
    )
    def test_sft_config_requires_trl(self):
        with self.assertRaises(EnvironmentError):
            build_sft_config(load_config(BASE_CONFIG))

    def test_preflight_stops_before_runtime_when_unauthorized(self):
        with self.assertRaises(AuthorizationError):
            preflight(BASE_CONFIG)

    def test_adapter_identity_checks_base_and_shape(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-adapter-") as temporary:
            path = Path(temporary)
            (path / "adapter_config.json").write_text(
                json.dumps(
                    {
                        "base_model_name_or_path": "google/gemma-3-1b-it",
                        "r": 16,
                        "lora_alpha": 32,
                        "lora_dropout": 0.05,
                    }
                ),
                encoding="utf-8",
            )
            identity = verify_adapter_identity(path)
            self.assertEqual(identity["r"], 16)
            (path / "adapter_config.json").write_text(
                json.dumps(
                    {
                        "base_model_name_or_path": "other/model",
                        "r": 16,
                        "lora_alpha": 32,
                        "lora_dropout": 0.05,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(TrainingError):
                verify_adapter_identity(path)

    def test_adapter_hash_is_tree_stable(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-adapter-") as temporary:
            path = Path(temporary)
            (path / "adapter_config.json").write_text("{}", encoding="utf-8")
            (path / "adapter_model.bin").write_bytes(b"weights")
            first = _adapter_hash(path)
            second = _adapter_hash(path)
            self.assertEqual(first, second)
            self.assertEqual(first["files"], 2)


class InferencePreparationTests(unittest.TestCase):
    def test_prompt_excludes_final_assistant_turn(self):
        record = valid_pilot_record()
        prompt = _prompt_before_final_assistant(record)
        self.assertEqual(len(prompt), 1)
        self.assertEqual(prompt[-1]["role"], "user")

    def test_short_conversation_prompt_keeps_prior_turns(self):
        record = valid_pilot_record(capability="short_conversation")
        prompt = _prompt_before_final_assistant(record)
        self.assertEqual(len(prompt), 3)
        self.assertEqual([item["role"] for item in prompt], ["user", "assistant", "user"])

    def test_blind_packet_has_no_model_identity(self):
        outputs = [
            {
                "item_id": "P-001",
                "split": "heldout",
                "capability": "formal_comprehension",
                "prompt": [{"role": "user", "content": "x"}],
                "model_role": role,
                "adapter_sha256": None,
                "output": role,
                "finish_reason": "eos",
            }
            for role in ("base", "existing_adapter", "new_adapter")
        ]
        packet, key = build_blind_packet(outputs, seed=42)
        self.assertEqual(len(packet), 1)
        self.assertEqual(len(packet[0]["responses"]), 3)
        for response in packet[0]["responses"]:
            self.assertNotIn("model_role", response)
            self.assertIn(response["label"], {"A", "B", "C"})
        self.assertEqual(set(key["P-001"]), {"A", "B", "C"})


if __name__ == "__main__":
    unittest.main()
