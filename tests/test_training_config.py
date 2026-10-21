"""Configuration validation tests."""

import copy
import tempfile
import unittest
from pathlib import Path

from training.config import load_config, validate_config, validate_authorized_for_execution
from training.errors import AuthorizationError, ConfigError

from .training_support import BASE_CONFIG


def _base():
    return copy.deepcopy(load_config(BASE_CONFIG).data)


class CurrentConfigTests(unittest.TestCase):
    def test_current_config_is_structurally_valid(self):
        loaded = load_config(BASE_CONFIG)
        self.assertEqual(loaded["base_model"]["revision"], "dcc83ea841ab6100d6b47a070329e1ba4cf78752")
        self.assertEqual(loaded["lora"]["expected_trainable_parameters"], 13_045_760)
        self.assertEqual(loaded["dependencies"]["datasets"], "5.0.1")

    def test_current_config_is_not_authorized(self):
        loaded = load_config(BASE_CONFIG)
        with self.assertRaises(AuthorizationError):
            validate_authorized_for_execution(loaded)


class RejectionTests(unittest.TestCase):
    def test_unknown_field_rejected(self):
        data = _base()
        data["experiment"]["unexpected"] = True
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_missing_field_rejected(self):
        data = _base()
        del data["training"]["completion_only_loss"]
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_base_revision_change_rejected(self):
        data = _base()
        data["base_model"]["revision"] = "f" * 40
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_moving_revision_rejected(self):
        data = _base()
        data["base_model"]["revision"] = "main"
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_lora_shape_change_rejected(self):
        data = _base()
        data["lora"]["r"] = 8
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_lora_target_change_rejected(self):
        data = _base()
        data["lora"]["target_modules"] = ["q_proj", "v_proj"]
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_assistant_only_loss_rejected(self):
        data = _base()
        data["training"]["assistant_only_loss"] = True
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_packing_rejected(self):
        data = _base()
        data["dataset"]["packing"] = True
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_quantization_change_rejected(self):
        data = _base()
        data["quantization"]["quant_type"] = "fp4"
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_full_run_rejected(self):
        data = _base()
        data["experiment"]["full_run_authorized"] = True
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_execution_without_approval_rejected(self):
        data = _base()
        data["experiment"]["execution_authorized"] = True
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_budget_above_cap_rejected(self):
        data = _base()
        data["budget"]["cash_cap_usd"] = 20.01
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_budget_arithmetic_rejected(self):
        data = _base()
        data["budget"]["estimated_total_hourly_usd"] = 0.5
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_dependency_change_rejected(self):
        data = _base()
        data["dependencies"]["trl"] = "0.21.0"
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_dataset_path_escape_rejected(self):
        data = _base()
        data["dataset"]["train_path"] = "../outside.jsonl"
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_training_output_must_be_absolute(self):
        data = _base()
        data["training"]["output_dir"] = "runs/relative"
        with self.assertRaises(ConfigError):
            validate_config(data)

    def test_run_record_contradiction_rejected(self):
        data = _base()
        data["run_record"]["status"] = "completed"
        with self.assertRaises(ConfigError):
            validate_config(data)


class YamlSafetyTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-config-") as temporary:
            path = Path(temporary) / "duplicate.yaml"
            path.write_text("experiment: {}\nexperiment: {}\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_secret_is_rejected_before_schema(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-config-") as temporary:
            path = Path(temporary) / "secret.yaml"
            path.write_text(
                "token: hf_abcdefghijklmnopqrstuvwx\n", encoding="utf-8"
            )
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_non_mapping_config_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lugandagpt-config-") as temporary:
            path = Path(temporary) / "list.yaml"
            path.write_text("- item\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
