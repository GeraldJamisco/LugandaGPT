"""Strict loading and validation of the training configuration.

The YAML file is a controlled experiment record, not a place to discover
defaults. Missing values, unknown values, duplicate YAML keys, and values
that differ from the pinned base or approved bound are errors.
"""

import datetime as _datetime
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

import yaml

from .constants import (
    CASH_CAP_USD,
    CONTAINER_DISK_HOURLY_USD,
    EVALUATION_TOTAL,
    GPU_HOURLY_USD,
    HARD_CREDIT_STOP_USD,
    HARD_RUNTIME_HOURS,
    HOURLY_TOTAL_USD,
    LOW_BALANCE_ALERT_USD,
    MAX_STEPS,
    PINNED_BASE_ID,
    PINNED_BASE_REVISION,
    PINNED_CHAT_TEMPLATE_SHA256,
    PINNED_DEPENDENCIES,
    PINNED_END_OF_TURN_TOKEN_ID,
    PINNED_EOS_IDS,
    PINNED_EOS_TOKEN_ID,
    PINNED_LORA,
    PINNED_LORA_TARGETS,
    PINNED_PARAMETER_COUNT,
    PINNED_PARAMETERS,
    PINNED_PAD_TOKEN_ID,
    PINNED_TOKENIZER_REVISION,
    SIX_HOUR_TOTAL_USD,
    SPLIT_COUNTS,
    TRAINING_MAX_LENGTH,
    VOLUME_DISK_HOURLY_USD,
)
from .errors import AuthorizationError, ConfigError
from .storage import sha256_file

STEMMING_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECRET_RE = re.compile(
    r"(?i)\b(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|"
    r"api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+)\b"
)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConfigError(
                f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class LoadedConfig:
    data: Mapping[str, Any]
    path: Path
    project_root: Path
    sha256: str

    def __getitem__(self, key):
        return self.data[key]

    def section(self, key):
        return self.data[key]


def _mapping(value, field):
    if not isinstance(value, Mapping):
        raise ConfigError("must be an object", field)
    return value


def _keys(value, field, required, optional=()):
    allowed = set(required) | set(optional)
    missing = sorted(set(required) - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ConfigError(f"missing required fields: {missing}", field)
    if unknown:
        raise ConfigError(f"unknown fields: {unknown}", field)
    return value


def _string(value, field, allow_empty=False):
    if not isinstance(value, str):
        raise ConfigError("must be a string", field)
    if not allow_empty and not value.strip():
        raise ConfigError("must not be empty", field)
    return value


def _stem(value, field):
    _string(value, field)
    if not STEMMING_RE.match(value):
        raise ConfigError("must be a short identifier using letters, digits, _ or -", field)
    return value


def _bool(value, field):
    if not isinstance(value, bool):
        raise ConfigError("must be true or false", field)
    return value


def _integer(value, field, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError("must be an integer", field)
    if minimum is not None and value < minimum:
        raise ConfigError(f"must be at least {minimum}", field)
    if maximum is not None and value > maximum:
        raise ConfigError(f"must be at most {maximum}", field)
    return value


def _number(value, field, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError("must be a number", field)
    if minimum is not None and value < minimum:
        raise ConfigError(f"must be at least {minimum}", field)
    if maximum is not None and value > maximum:
        raise ConfigError(f"must be at most {maximum}", field)
    return float(value)


def _enum(value, field, choices):
    _string(value, field)
    if value not in choices:
        raise ConfigError(f"must be one of {tuple(choices)}", field)
    return value


def _date(value, field):
    if isinstance(value, _datetime.datetime):
        return value.date()
    if isinstance(value, _datetime.date):
        return value
    _string(value, field)
    if not ISO_DATE_RE.match(value):
        raise ConfigError("must use YYYY-MM-DD", field)
    try:
        return _datetime.date.fromisoformat(value)
    except ValueError as error:
        raise ConfigError(f"is not a valid date: {error}", field) from error


def _sha256(value, field, allow_pending=False):
    if allow_pending and value == "pending":
        return value
    _string(value, field)
    if not SHA256_RE.match(value):
        raise ConfigError("must be a lowercase SHA-256 digest", field)
    return value


def _revision(value, field):
    _string(value, field)
    if value.strip().lower() in {"main", "master", "latest", "head"}:
        raise ConfigError("must be a pinned commit, not a moving branch", field)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise ConfigError("must be a full hexadecimal commit revision", field)
    return value


def _relative_path(value, field):
    _string(value, field)
    normalized = value.replace("\\", "/")
    if PurePosixPath(normalized).is_absolute() or PureWindowsPath(normalized).is_absolute():
        raise ConfigError("must be relative to the project root", field)
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise ConfigError("must not contain . or .. path segments", field)
    return "/".join(parts)


def _absolute_path(value, field):
    _string(value, field)
    normalized = value.replace("\\", "/")
    if not (normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized)):
        raise ConfigError("must be an absolute run path", field)
    if ".." in normalized.split("/"):
        raise ConfigError("must not contain .. path segments", field)
    return normalized


def _list_of_strings(value, field, allow_empty=True):
    if not isinstance(value, list):
        raise ConfigError("must be a list", field)
    if not allow_empty and not value:
        raise ConfigError("must not be empty", field)
    for index, item in enumerate(value):
        _string(item, f"{field}[{index}]")
    return value


def _exact(value, expected, field):
    if value != expected:
        raise ConfigError(f"must be {expected!r}, found {value!r}", field)
    return value


def load_config(path, project_root=None):
    """Load and validate one YAML config without touching data or models."""
    config_path = Path(path).resolve()
    if not config_path.is_file():
        raise ConfigError(f"configuration file not found: {config_path}")
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"cannot read configuration: {error}") from error
    if SECRET_RE.search(text):
        raise ConfigError("configuration appears to contain a secret; remove it")
    try:
        loader = _UniqueKeyLoader(text)
        try:
            data = loader.get_single_data()
        finally:
            loader.dispose()
    except yaml.YAMLError as error:
        raise ConfigError(f"invalid YAML: {error}") from error
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    loaded = LoadedConfig(
        data=data,
        path=config_path,
        project_root=root,
        sha256=sha256_file(config_path),
    )
    validate_config(loaded)
    return loaded


def validate_config(config):
    if isinstance(config, LoadedConfig):
        data = config.data
    elif isinstance(config, Mapping):
        data = config
    else:
        raise ConfigError("configuration must be a YAML object")
    data = _mapping(data, "config")
    _keys(
        data,
        "config",
        required=(
            "experiment",
            "base_model",
            "tokenizer",
            "quantization",
            "lora",
            "dataset",
            "training",
            "inference",
            "hardware",
            "budget",
            "artifacts",
            "run_record",
            "dependencies",
        ),
        optional=("notes",),
    )

    _validate_experiment(_mapping(data["experiment"], "experiment"))
    _validate_base_model(_mapping(data["base_model"], "base_model"))
    _validate_tokenizer(_mapping(data["tokenizer"], "tokenizer"))
    _validate_quantization(_mapping(data["quantization"], "quantization"))
    _validate_lora(_mapping(data["lora"], "lora"))
    _validate_dataset(_mapping(data["dataset"], "dataset"))
    _validate_training(_mapping(data["training"], "training"))
    _validate_inference(_mapping(data["inference"], "inference"))
    _validate_hardware(_mapping(data["hardware"], "hardware"))
    _validate_budget(_mapping(data["budget"], "budget"))
    _validate_artifacts(_mapping(data["artifacts"], "artifacts"))
    _validate_run_record(_mapping(data["run_record"], "run_record"))
    _validate_dependencies(_mapping(data["dependencies"], "dependencies"))
    if "notes" in data:
        notes = data["notes"]
        if not isinstance(notes, list):
            raise ConfigError("must be a list", "notes")
        for index, note in enumerate(notes):
            _string(note, f"notes[{index}]")
    return True


def _validate_experiment(value):
    _keys(
        value,
        "experiment",
        required=(
            "id",
            "name",
            "date_prepared",
            "status",
            "authorization_status",
            "execution_authorized",
            "approval_reference",
            "approval_scope",
            "existing_adapter_role",
            "full_run_authorized",
        ),
    )
    _stem(value["id"], "experiment.id")
    _stem(value["name"], "experiment.name")
    _date(value["date_prepared"], "experiment.date_prepared")
    status = _enum(
        value["status"],
        "experiment.status",
        ("proposed", "approved", "running", "completed", "failed"),
    )
    authorization = _enum(
        value["authorization_status"],
        "experiment.authorization_status",
        (
            "proposed",
            "authorized_in_principle_subject_to_prerequisites",
            "approved",
            "withdrawn",
        ),
    )
    execution = _bool(value["execution_authorized"], "experiment.execution_authorized")
    _string(value["approval_reference"], "experiment.approval_reference")
    _string(value["approval_scope"], "experiment.approval_scope")
    _exact(
        value["existing_adapter_role"],
        "translation_baseline_only",
        "experiment.existing_adapter_role",
    )
    _exact(value["full_run_authorized"], False, "experiment.full_run_authorized")
    if execution:
        if status != "approved" or authorization != "approved":
            raise ConfigError(
                "execution requires experiment.status=approved and "
                "authorization_status=approved",
                "experiment.execution_authorized",
            )
    elif authorization == "approved" and status == "proposed":
        raise ConfigError(
            "authorization_status=approved is inconsistent with status=proposed",
            "experiment.authorization_status",
        )


def _validate_base_model(value):
    _keys(
        value,
        "base_model",
        required=(
            "id",
            "revision",
            "gated",
            "license",
            "parameter_count",
            "hidden_size",
            "num_hidden_layers",
            "vocab_size",
            "context_limit",
            "weight_dtype",
        ),
    )
    _exact(value["id"], PINNED_BASE_ID, "base_model.id")
    _exact(value["revision"], PINNED_BASE_REVISION, "base_model.revision")
    _bool(value["gated"], "base_model.gated")
    _string(value["license"], "base_model.license")
    _exact(value["parameter_count"], PINNED_PARAMETER_COUNT, "base_model.parameter_count")
    for key, expected in PINNED_PARAMETERS.items():
        _exact(value[key], expected, f"base_model.{key}")
    _exact(value["weight_dtype"], "bfloat16", "base_model.weight_dtype")


def _validate_tokenizer(value):
    _keys(
        value,
        "tokenizer",
        required=(
            "revision",
            "chat_template_sha256",
            "pad_token",
            "pad_token_id",
            "bos_token_id",
            "eos_token",
            "eos_token_id",
            "end_of_turn_token",
            "end_of_turn_token_id",
            "generation_eos_token_ids",
            "add_special_tokens",
            "trust_remote_code",
        ),
    )
    _exact(value["revision"], PINNED_TOKENIZER_REVISION, "tokenizer.revision")
    _exact(
        value["chat_template_sha256"],
        PINNED_CHAT_TEMPLATE_SHA256,
        "tokenizer.chat_template_sha256",
    )
    _exact(value["pad_token"], "<pad>", "tokenizer.pad_token")
    _exact(value["pad_token_id"], PINNED_PAD_TOKEN_ID, "tokenizer.pad_token_id")
    _exact(value["bos_token_id"], 2, "tokenizer.bos_token_id")
    _exact(value["eos_token"], "<eos>", "tokenizer.eos_token")
    _exact(value["eos_token_id"], PINNED_EOS_TOKEN_ID, "tokenizer.eos_token_id")
    _exact(value["end_of_turn_token"], "<end_of_turn>", "tokenizer.end_of_turn_token")
    _exact(
        value["end_of_turn_token_id"],
        PINNED_END_OF_TURN_TOKEN_ID,
        "tokenizer.end_of_turn_token_id",
    )
    eos_ids = value["generation_eos_token_ids"]
    if not isinstance(eos_ids, list) or tuple(eos_ids) != PINNED_EOS_IDS:
        raise ConfigError(
            f"must be exactly {list(PINNED_EOS_IDS)}", "tokenizer.generation_eos_token_ids"
        )
    _exact(value["add_special_tokens"], False, "tokenizer.add_special_tokens")
    _exact(value["trust_remote_code"], False, "tokenizer.trust_remote_code")


def _validate_quantization(value):
    _keys(
        value,
        "quantization",
        required=(
            "load_in_4bit",
            "quant_type",
            "double_quant",
            "compute_dtype",
            "quant_storage",
            "use_cpu",
        ),
    )
    _exact(value["load_in_4bit"], True, "quantization.load_in_4bit")
    _exact(value["quant_type"], "nf4", "quantization.quant_type")
    _exact(value["double_quant"], True, "quantization.double_quant")
    _exact(value["compute_dtype"], "bfloat16", "quantization.compute_dtype")
    _exact(value["quant_storage"], "uint8", "quantization.quant_storage")
    _exact(value["use_cpu"], False, "quantization.use_cpu")


def _validate_lora(value):
    _keys(
        value,
        "lora",
        required=(
            "task_type",
            "r",
            "alpha",
            "dropout",
            "bias",
            "target_modules",
            "use_dora",
            "use_rslora",
            "init_lora_weights",
            "modules_to_save",
            "expected_trainable_parameters",
        ),
    )
    for key, expected in PINNED_LORA.items():
        actual = value[key]
        if key == "modules_to_save":
            _exact(actual, expected, f"lora.{key}")
        elif key == "dropout":
            _exact(float(actual), float(expected), f"lora.{key}")
        else:
            _exact(actual, expected, f"lora.{key}")
    targets = value["target_modules"]
    _list_of_strings(targets, "lora.target_modules", allow_empty=False)
    if len(targets) != len(set(targets)) or set(targets) != set(PINNED_LORA_TARGETS):
        raise ConfigError(
            f"must contain each of {list(PINNED_LORA_TARGETS)} exactly once",
            "lora.target_modules",
        )


def _validate_split_hashes(value):
    if value == "pending":
        return
    value = _mapping(value, "dataset.split_hashes")
    _keys(
        value,
        "dataset.split_hashes",
        required=("train", "validation", "heldout", "evaluation"),
    )
    for key, digest in value.items():
        _sha256(digest, f"dataset.split_hashes.{key}", allow_pending=True)


def _validate_dataset(value):
    _keys(
        value,
        "dataset",
        required=(
            "raw_format",
            "training_view",
            "version",
            "provenance_path",
            "split_hashes",
            "train_path",
            "validation_path",
            "heldout_path",
            "evaluation_path",
            "max_train_examples",
            "max_validation_examples",
            "max_heldout_examples",
            "max_evaluation_items",
            "expand_assistant_turns",
            "max_length",
            "non_conversation_max_tokens",
            "conversation_max_tokens",
            "packing",
            "shuffle_train",
            "seed",
            "deduplicate",
            "contamination_check",
            "native_review_required",
            "teacher_consent_required",
            "licence_record_required",
        ),
    )
    _exact(value["raw_format"], "messages", "dataset.raw_format")
    _exact(
        value["training_view"],
        "conversational_prompt_completion",
        "dataset.training_view",
    )
    _string(value["version"], "dataset.version")
    _relative_path(value["provenance_path"], "dataset.provenance_path")
    _validate_split_hashes(value["split_hashes"])
    for key in ("train_path", "validation_path", "heldout_path", "evaluation_path"):
        _relative_path(value[key], f"dataset.{key}")
    expected_counts = {
        "max_train_examples": SPLIT_COUNTS["train"],
        "max_validation_examples": SPLIT_COUNTS["validation"],
        "max_heldout_examples": SPLIT_COUNTS["heldout"],
        "max_evaluation_items": EVALUATION_TOTAL,
    }
    for key, expected in expected_counts.items():
        _exact(value[key], expected, f"dataset.{key}")
    _exact(value["expand_assistant_turns"], True, "dataset.expand_assistant_turns")
    _exact(value["max_length"], TRAINING_MAX_LENGTH, "dataset.max_length")
    _exact(value["non_conversation_max_tokens"], 512, "dataset.non_conversation_max_tokens")
    _exact(value["conversation_max_tokens"], 1024, "dataset.conversation_max_tokens")
    _exact(value["packing"], False, "dataset.packing")
    _exact(value["shuffle_train"], True, "dataset.shuffle_train")
    _exact(value["seed"], 42, "dataset.seed")
    _exact(value["deduplicate"], True, "dataset.deduplicate")
    _exact(value["contamination_check"], "exact_and_8gram", "dataset.contamination_check")
    for key in (
        "native_review_required",
        "teacher_consent_required",
        "licence_record_required",
    ):
        _exact(value[key], True, f"dataset.{key}")


def _validate_training(value):
    _keys(
        value,
        "training",
        required=(
            "framework",
            "framework_version",
            "output_dir",
            "run_name",
            "per_device_train_batch_size",
            "per_device_eval_batch_size",
            "gradient_accumulation_steps",
            "effective_batch_size",
            "num_train_epochs",
            "max_steps",
            "learning_rate",
            "lr_scheduler_type",
            "warmup_ratio",
            "weight_decay",
            "max_grad_norm",
            "optim",
            "adam_beta1",
            "adam_beta2",
            "adam_epsilon",
            "bf16",
            "fp16",
            "tf32",
            "bf16_full_eval",
            "gradient_checkpointing",
            "gradient_checkpointing_kwargs",
            "assistant_only_loss",
            "completion_only_loss",
            "dataset_kwargs",
            "eval_strategy",
            "eval_steps",
            "eval_on_start",
            "save_strategy",
            "save_steps",
            "save_total_limit",
            "save_only_model",
            "save_safetensors",
            "load_best_model_at_end",
            "logging_steps",
            "logging_first_step",
            "report_to",
            "push_to_hub",
            "hub_model_id",
            "resume_from_checkpoint",
            "seed",
            "data_seed",
            "dataloader_num_workers",
            "dataset_num_proc",
            "remove_unused_columns",
            "torch_compile",
            "use_liger_kernel",
            "average_tokens_across_devices",
            "include_num_input_tokens_seen",
        ),
    )
    _exact(value["framework"], "trl.SFTTrainer", "training.framework")
    _exact(value["framework_version"], PINNED_DEPENDENCIES["trl"], "training.framework_version")
    _absolute_path(value["output_dir"], "training.output_dir")
    _stem(value["run_name"], "training.run_name")
    _exact(value["per_device_train_batch_size"], 1, "training.per_device_train_batch_size")
    _exact(value["per_device_eval_batch_size"], 1, "training.per_device_eval_batch_size")
    _exact(value["gradient_accumulation_steps"], 8, "training.gradient_accumulation_steps")
    _exact(value["effective_batch_size"], 8, "training.effective_batch_size")
    if value["effective_batch_size"] != (
        value["per_device_train_batch_size"] * value["gradient_accumulation_steps"]
    ):
        raise ConfigError(
            "must equal batch size times gradient accumulation",
            "training.effective_batch_size",
        )
    _exact(value["num_train_epochs"], 3, "training.num_train_epochs")
    _exact(value["max_steps"], MAX_STEPS, "training.max_steps")
    _exact(float(value["learning_rate"]), 0.0002, "training.learning_rate")
    _exact(value["lr_scheduler_type"], "cosine", "training.lr_scheduler_type")
    _exact(float(value["warmup_ratio"]), 0.05, "training.warmup_ratio")
    _exact(float(value["weight_decay"]), 0.01, "training.weight_decay")
    _exact(float(value["max_grad_norm"]), 0.3, "training.max_grad_norm")
    _exact(value["optim"], "paged_adamw_8bit", "training.optim")
    _exact(float(value["adam_beta1"]), 0.9, "training.adam_beta1")
    _exact(float(value["adam_beta2"]), 0.999, "training.adam_beta2")
    _exact(float(value["adam_epsilon"]), 1e-8, "training.adam_epsilon")
    _exact(value["bf16"], True, "training.bf16")
    _exact(value["fp16"], False, "training.fp16")
    _exact(value["tf32"], False, "training.tf32")
    _exact(value["bf16_full_eval"], True, "training.bf16_full_eval")
    _exact(value["gradient_checkpointing"], True, "training.gradient_checkpointing")
    gc_kwargs = _mapping(value["gradient_checkpointing_kwargs"], "training.gradient_checkpointing_kwargs")
    _keys(
        gc_kwargs,
        "training.gradient_checkpointing_kwargs",
        required=("use_reentrant",),
    )
    _exact(gc_kwargs["use_reentrant"], False, "training.gradient_checkpointing_kwargs.use_reentrant")
    _exact(value["assistant_only_loss"], False, "training.assistant_only_loss")
    _exact(value["completion_only_loss"], True, "training.completion_only_loss")
    dataset_kwargs = _mapping(value["dataset_kwargs"], "training.dataset_kwargs")
    _keys(
        dataset_kwargs,
        "training.dataset_kwargs",
        required=(),
        optional=("add_special_tokens", "skip_prepare_dataset"),
    )
    for key, item in dataset_kwargs.items():
        _bool(item, f"training.dataset_kwargs.{key}")
    _exact(value["eval_strategy"], "steps", "training.eval_strategy")
    _exact(value["eval_steps"], 10, "training.eval_steps")
    _exact(value["eval_on_start"], True, "training.eval_on_start")
    _exact(value["save_strategy"], "steps", "training.save_strategy")
    _exact(value["save_steps"], 10, "training.save_steps")
    _exact(value["save_total_limit"], 3, "training.save_total_limit")
    _exact(value["save_only_model"], False, "training.save_only_model")
    _exact(value["save_safetensors"], True, "training.save_safetensors")
    _exact(value["load_best_model_at_end"], False, "training.load_best_model_at_end")
    _exact(value["logging_steps"], 1, "training.logging_steps")
    _exact(value["logging_first_step"], True, "training.logging_first_step")
    _exact(value["report_to"], "none", "training.report_to")
    _exact(value["push_to_hub"], False, "training.push_to_hub")
    _exact(value["hub_model_id"], None, "training.hub_model_id")
    if value["resume_from_checkpoint"] is not None:
        _absolute_path(value["resume_from_checkpoint"], "training.resume_from_checkpoint")
    _exact(value["seed"], 42, "training.seed")
    _exact(value["data_seed"], 42, "training.data_seed")
    _exact(value["dataloader_num_workers"], 2, "training.dataloader_num_workers")
    _exact(value["dataset_num_proc"], 2, "training.dataset_num_proc")
    _exact(value["remove_unused_columns"], True, "training.remove_unused_columns")
    _exact(value["torch_compile"], False, "training.torch_compile")
    _exact(value["use_liger_kernel"], False, "training.use_liger_kernel")
    _exact(
        value["average_tokens_across_devices"],
        True,
        "training.average_tokens_across_devices",
    )
    _exact(
        value["include_num_input_tokens_seen"],
        True,
        "training.include_num_input_tokens_seen",
    )


def _validate_inference(value):
    _keys(
        value,
        "inference",
        required=(
            "do_sample",
            "max_new_tokens",
            "repetition_penalty",
            "batch_size",
            "seed",
            "compare_models",
            "existing_adapter_path",
            "new_adapter_path",
            "record_raw_outputs",
            "record_finish_reason",
            "native_reviewers_per_response",
            "adjudicator_required",
            "blind_model_identity",
            "randomize_response_order",
            "call_results_benchmark_scores",
        ),
    )
    _exact(value["do_sample"], False, "inference.do_sample")
    _exact(value["max_new_tokens"], 256, "inference.max_new_tokens")
    _exact(float(value["repetition_penalty"]), 1.0, "inference.repetition_penalty")
    _exact(value["batch_size"], 1, "inference.batch_size")
    _exact(value["seed"], 42, "inference.seed")
    _exact(
        value["compare_models"],
        ["base", "existing_adapter", "new_adapter"],
        "inference.compare_models",
    )
    for key in ("existing_adapter_path", "new_adapter_path"):
        if value[key] is not None:
            _string(value[key], f"inference.{key}")
    _exact(value["record_raw_outputs"], True, "inference.record_raw_outputs")
    _exact(value["record_finish_reason"], True, "inference.record_finish_reason")
    _exact(value["native_reviewers_per_response"], 2, "inference.native_reviewers_per_response")
    _exact(value["adjudicator_required"], True, "inference.adjudicator_required")
    _exact(value["blind_model_identity"], True, "inference.blind_model_identity")
    _exact(value["randomize_response_order"], True, "inference.randomize_response_order")
    _exact(
        value["call_results_benchmark_scores"],
        False,
        "inference.call_results_benchmark_scores",
    )


def _validate_hardware(value):
    _keys(
        value,
        "hardware",
        required=(
            "provider",
            "cloud",
            "gpu",
            "gpu_count",
            "vram_gb",
            "cpu_and_ram",
            "container_disk_gb",
            "volume_disk_gb",
            "network_volume",
            "region",
            "image",
            "python",
            "cuda",
        ),
    )
    if str(value["provider"]).lower() != "runpod":
        raise ConfigError("must be Runpod for this gate", "hardware.provider")
    _exact(value["cloud"], "Secure Cloud", "hardware.cloud")
    _exact(value["gpu"], "NVIDIA GeForce RTX 4090", "hardware.gpu")
    _exact(value["gpu_count"], 1, "hardware.gpu_count")
    _exact(value["vram_gb"], 24, "hardware.vram_gb")
    _string(value["cpu_and_ram"], "hardware.cpu_and_ram")
    _exact(value["container_disk_gb"], 30, "hardware.container_disk_gb")
    _exact(value["volume_disk_gb"], 20, "hardware.volume_disk_gb")
    _exact(value["network_volume"], False, "hardware.network_volume")
    _string(value["region"], "hardware.region")
    _string(value["image"], "hardware.image")
    _exact(value["python"], "3.11", "hardware.python")
    _string(value["cuda"], "hardware.cuda")


def _validate_budget(value):
    _keys(
        value,
        "budget",
        required=(
            "cash_cap_usd",
            "cash_cap_includes",
            "credit_purchase_usd",
            "require_tax_inclusive_charge_at_or_below_cap",
            "gpu_hourly_usd",
            "container_disk_hourly_usd",
            "volume_disk_hourly_usd",
            "estimated_total_hourly_usd",
            "estimated_six_hour_usd",
            "hard_runtime_hours",
            "hard_credit_stop_usd",
            "low_balance_alert_usd",
            "auto_pay",
            "prepaid_card_allowed",
            "prepaid_card_minimum_usd",
            "unattended_run_allowed",
            "retry_limit",
            "native_authoring_and_review_in_cap",
        ),
    )
    cash_cap = _number(value["cash_cap_usd"], "budget.cash_cap_usd", 0)
    if cash_cap > CASH_CAP_USD:
        raise ConfigError(f"must not exceed ${CASH_CAP_USD:.2f}", "budget.cash_cap_usd")
    includes = _list_of_strings(value["cash_cap_includes"], "budget.cash_cap_includes", allow_empty=False)
    expected_includes = {"compute", "storage", "sales_tax", "payment_fees"}
    if set(includes) != expected_includes:
        raise ConfigError(f"must include {sorted(expected_includes)}", "budget.cash_cap_includes")
    credit = _number(value["credit_purchase_usd"], "budget.credit_purchase_usd", 0)
    if credit > cash_cap:
        raise ConfigError("must not exceed the cash cap", "budget.credit_purchase_usd")
    _exact(
        value["require_tax_inclusive_charge_at_or_below_cap"],
        True,
        "budget.require_tax_inclusive_charge_at_or_below_cap",
    )
    gpu = _number(value["gpu_hourly_usd"], "budget.gpu_hourly_usd", 0)
    container = _number(
        value["container_disk_hourly_usd"], "budget.container_disk_hourly_usd", 0
    )
    volume = _number(value["volume_disk_hourly_usd"], "budget.volume_disk_hourly_usd", 0)
    total = _number(value["estimated_total_hourly_usd"], "budget.estimated_total_hourly_usd", 0)
    _exact(float(gpu), GPU_HOURLY_USD, "budget.gpu_hourly_usd")
    _exact(
        float(container),
        CONTAINER_DISK_HOURLY_USD,
        "budget.container_disk_hourly_usd",
    )
    _exact(float(volume), VOLUME_DISK_HOURLY_USD, "budget.volume_disk_hourly_usd")
    if abs(total - (gpu + container + volume)) > 0.000001:
        raise ConfigError(
            "must equal GPU plus container disk plus volume disk",
            "budget.estimated_total_hourly_usd",
        )
    if abs(total - HOURLY_TOTAL_USD) > 0.000001:
        raise ConfigError(f"must be {HOURLY_TOTAL_USD}", "budget.estimated_total_hourly_usd")
    six_hour = _number(value["estimated_six_hour_usd"], "budget.estimated_six_hour_usd", 0)
    if abs(six_hour - total * 6) > 0.01 or abs(six_hour - SIX_HOUR_TOTAL_USD) > 0.01:
        raise ConfigError(
            "must agree with six hours at the hourly total and the report",
            "budget.estimated_six_hour_usd",
        )
    runtime = _number(value["hard_runtime_hours"], "budget.hard_runtime_hours", 0)
    if runtime > HARD_RUNTIME_HOURS:
        raise ConfigError("must not exceed the approved runtime cap", "budget.hard_runtime_hours")
    credit_stop = _number(value["hard_credit_stop_usd"], "budget.hard_credit_stop_usd", 0)
    _exact(float(credit_stop), HARD_CREDIT_STOP_USD, "budget.hard_credit_stop_usd")
    if credit_stop > credit:
        raise ConfigError("must not exceed the purchased credit", "budget.hard_credit_stop_usd")
    alert = _number(value["low_balance_alert_usd"], "budget.low_balance_alert_usd", 0)
    _exact(float(alert), LOW_BALANCE_ALERT_USD, "budget.low_balance_alert_usd")
    if alert >= credit_stop:
        raise ConfigError(
            "must be lower than the hard credit stop", "budget.low_balance_alert_usd"
        )
    _exact(value["auto_pay"], False, "budget.auto_pay")
    _exact(value["prepaid_card_allowed"], False, "budget.prepaid_card_allowed")
    _exact(value["prepaid_card_minimum_usd"], 100.0, "budget.prepaid_card_minimum_usd")
    _exact(value["unattended_run_allowed"], False, "budget.unattended_run_allowed")
    retries = _integer(value["retry_limit"], "budget.retry_limit", 0, 1)
    _exact(retries, 1, "budget.retry_limit")
    _exact(
        value["native_authoring_and_review_in_cap"],
        False,
        "budget.native_authoring_and_review_in_cap",
    )


def _validate_artifacts(value):
    required = (
        "export_adapter",
        "export_tokenizer",
        "export_training_config",
        "export_environment_freeze",
        "export_raw_model_outputs",
        "export_native_review_records",
        "export_checksums",
        "export_cost_record",
        "export_before_terminate",
        "terminate_after_export",
        "leave_stopped_pod",
        "leave_network_volume",
    )
    _keys(value, "artifacts", required=required)
    for key in required:
        _bool(value[key], f"artifacts.{key}")
    for key in (
        "export_adapter",
        "export_tokenizer",
        "export_training_config",
        "export_environment_freeze",
        "export_raw_model_outputs",
        "export_native_review_records",
        "export_checksums",
        "export_cost_record",
        "export_before_terminate",
        "terminate_after_export",
    ):
        _exact(value[key], True, f"artifacts.{key}")
    _exact(value["leave_stopped_pod"], False, "artifacts.leave_stopped_pod")
    _exact(value["leave_network_volume"], False, "artifacts.leave_network_volume")


def _nullable_string(value, field):
    if value is not None:
        _string(value, field)


def _nullable_number(value, field):
    if value is not None:
        _number(value, field, 0)


def _nullable_timestamp(value, field):
    if value is None:
        return None
    _string(value, field)
    try:
        parsed = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigError(f"is not an ISO timestamp: {error}", field) from error
    if parsed.tzinfo is None:
        raise ConfigError("must include a timezone offset", field)
    return parsed


def _validate_run_record(value):
    fields = (
        "status",
        "pod_id",
        "region",
        "host",
        "image_digest",
        "started_at_utc",
        "ended_at_utc",
        "runtime_seconds",
        "gpu_hours",
        "peak_vram_gb",
        "final_credit_charge_usd",
        "final_cash_charge_usd",
        "remaining_credit_usd",
        "driver_version",
        "cuda_version",
        "training_log_path",
        "checkpoint_manifest_path",
        "artifact_manifest_path",
    )
    _keys(value, "run_record", required=fields)
    status = _enum(
        value["status"],
        "run_record.status",
        ("not_run", "started", "completed", "failed", "incomplete", "excluded"),
    )
    for key in (
        "pod_id",
        "region",
        "host",
        "image_digest",
        "driver_version",
        "cuda_version",
        "training_log_path",
        "checkpoint_manifest_path",
        "artifact_manifest_path",
    ):
        _nullable_string(value[key], f"run_record.{key}")
    for key in ("started_at_utc", "ended_at_utc"):
        _nullable_timestamp(value[key], f"run_record.{key}")
    if value["started_at_utc"] and value["ended_at_utc"]:
        started = _datetime.datetime.fromisoformat(
            value["started_at_utc"].replace("Z", "+00:00")
        )
        ended = _datetime.datetime.fromisoformat(
            value["ended_at_utc"].replace("Z", "+00:00")
        )
        if ended < started:
            raise ConfigError("must not be earlier than started_at_utc", "run_record.ended_at_utc")
    for key in (
        "runtime_seconds",
        "gpu_hours",
        "peak_vram_gb",
        "final_credit_charge_usd",
        "final_cash_charge_usd",
        "remaining_credit_usd",
    ):
        _nullable_number(value[key], f"run_record.{key}")
    if status == "not_run":
        populated = [
            key
            for key in fields
            if key != "status" and value[key] is not None
        ]
        if populated:
            raise ConfigError(
                f"must have null runtime fields while status=not_run: {populated}",
                "run_record",
            )
    if status == "completed" and value["ended_at_utc"] is None:
        raise ConfigError("completed runs require an end time", "run_record.ended_at_utc")


def _validate_dependencies(value):
    required = tuple(PINNED_DEPENDENCIES) + ("cuda", "driver")
    _keys(value, "dependencies", required=required)
    for key, expected in PINNED_DEPENDENCIES.items():
        _exact(value[key], expected, f"dependencies.{key}")
    _string(value["cuda"], "dependencies.cuda")
    _string(value["driver"], "dependencies.driver")


def validate_authorized_for_execution(loaded):
    data = loaded.data
    if data["experiment"]["execution_authorized"] is not True:
        raise AuthorizationError(
            "experiment.execution_authorized is false; "
            "the configuration is not approved for a run"
        )
    if data["experiment"]["status"] != "approved":
        raise AuthorizationError(
            "experiment.status must be approved before execution"
        )
    if data["experiment"]["authorization_status"] != "approved":
        raise AuthorizationError(
            "experiment.authorization_status must be approved before execution"
        )
    if data["experiment"]["full_run_authorized"] is not False:
        raise AuthorizationError("this gate does not authorize a full run")
    return True
