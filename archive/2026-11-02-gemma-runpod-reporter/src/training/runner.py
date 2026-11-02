"""Guarded orchestration for the bounded smoke test.

The order is intentional: authorization, runtime, tokenizer, data, duplicate
and contamination checks, one forward/backward pass, and only then training.
No bypass flag exists.
"""

import datetime as _datetime
import logging
import math
import time
import traceback
from pathlib import Path

from .artifacts import (
    export_checkpoint_manifest,
    export_config_snapshot,
    export_environment,
    prepare_run_directory,
    utc_now,
    write_artifact_inventory,
    write_json_text,
    write_run_manifest,
)
from .config import load_config, validate_authorized_for_execution
from .data import expand_split, load_pilot_dataset
from .environment import (
    check_runtime,
    collect_code_manifest,
    collect_git_record,
)
from .errors import AuthorizationError, DataError, EnvironmentError, TrainingError
from .modeling import (
    build_trainer,
    load_base_model,
    load_tokenizer,
    one_step_check,
    peak_vram_gb,
    save_adapter_and_tokenizer,
)


def _require_run_metadata(pod_id, region, host, image):
    values = {"pod_id": pod_id, "region": region, "host": host, "image": image}
    for field, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise TrainingError(f"--{field.replace('_', '-')} is required for a paid run")
        stripped = value.strip()
        lowered = stripped.casefold()
        if stripped.startswith("<") and stripped.endswith(">"):
            raise TrainingError(f"{field} is still a placeholder: {value!r}")
        if lowered in {
            "any_available_record_actual",
            "record_actual_at_launch",
            "record_exact_at_launch",
            "pending",
        }:
            raise TrainingError(f"{field} is still a placeholder: {value!r}")
    return values


def _load_authorized_config(config_path, project_root=None):
    loaded = load_config(config_path, project_root=project_root)
    try:
        validate_authorized_for_execution(loaded)
    except Exception as error:
        raise AuthorizationError(str(error)) from error
    return loaded


def _load_tokenizer_for_config(loaded, tokenizer_path=None, model_path=None):
    path = tokenizer_path or model_path
    return load_tokenizer(
        loaded,
        model_path=path,
        local_files_only=bool(path),
    )


def preflight(
    config_path,
    project_root=None,
    tokenizer_path=None,
    model_path=None,
):
    """Run every non-training check that does not load the base model."""
    loaded = _load_authorized_config(config_path, project_root)
    runtime = check_runtime(loaded, require_gpu=True)
    tokenizer = _load_tokenizer_for_config(
        loaded, tokenizer_path=tokenizer_path, model_path=model_path
    )
    dataset = load_pilot_dataset(
        loaded,
        project_root=project_root,
        require_complete=True,
        require_approved=True,
        tokenizer=tokenizer,
        require_token_checks=True,
    )
    return {
        "status": "preflight_passed_except_model_load_and_one_step",
        "config_sha256": loaded.sha256,
        "runtime": runtime,
        "tokenizer": {
            "chat_template_sha256": loaded["tokenizer"]["chat_template_sha256"],
            "eos_token_ids": list(loaded["tokenizer"]["generation_eos_token_ids"]),
        },
        "dataset": dataset.summary,
        "pending": [
            "base model load at the pinned revision",
            "4-bit layer forward pass",
            "one-step forward and backward pass",
            "adapter save and reload",
        ],
    }


def _prepare_datasets(records_train, records_validation):
    try:
        from datasets import Dataset
    except ImportError as error:
        raise EnvironmentError("Datasets is not installed") from error
    train_rows = expand_split(records_train)
    validation_rows = expand_split(records_validation)
    if not train_rows or not validation_rows:
        raise DataError("training and validation expansions must not be empty")
    return Dataset.from_list(train_rows), Dataset.from_list(validation_rows)


def _estimate_cost_so_far(started_monotonic, hourly_usd):
    hours = (time.monotonic() - started_monotonic) / 3600.0
    return hours, hours * hourly_usd


def _make_guard(base_sft_config):
    try:
        from transformers import TrainerCallback
    except ImportError as error:
        raise EnvironmentError("Transformers is not installed") from error

    class RunGuard(TrainerCallback):
        def __init__(self):
            self.started = time.monotonic()
            self.hours = 0.0
            self.estimated_cost = 0.0
            self.limit_reason = None
            self.nonfinite_loss = None
            self.last_step = 0

        def _check(self, control):
            self.hours, self.estimated_cost = _estimate_cost_so_far(
                self.started, base_sft_config["budget"]["estimated_total_hourly_usd"]
            )
            if self.limit_reason:
                control.should_training_stop = True
            if self.hours >= base_sft_config["budget"]["hard_runtime_hours"]:
                self.limit_reason = "runtime_cap_reached"
                control.should_training_stop = True
            if self.estimated_cost >= base_sft_config["budget"]["hard_credit_stop_usd"]:
                self.limit_reason = "credit_stop_reached"
                control.should_training_stop = True

        def on_step_end(self, args, state, control, **kwargs):
            self.last_step = int(state.global_step)
            self._check(control)
            return control

        def on_log(self, args, state, control, logs=None, **kwargs):
            loss = (logs or {}).get("loss")
            if loss is not None:
                try:
                    finite = math.isfinite(float(loss))
                except (TypeError, ValueError):
                    finite = False
                if not finite:
                    self.nonfinite_loss = loss
                    self.limit_reason = "nonfinite_loss"
                    control.should_training_stop = True
            self._check(control)
            return control

        def on_evaluate(self, args, state, control, **kwargs):
            self._check(control)
            return control

    return RunGuard


def _write_failure(output_dir, manifest, error):
    manifest["status"] = "failed"
    manifest["ended_at_utc"] = utc_now()
    started = _datetime.datetime.fromisoformat(
        manifest["started_at_utc"].replace("Z", "+00:00")
    )
    ended = _datetime.datetime.fromisoformat(
        manifest["ended_at_utc"].replace("Z", "+00:00")
    )
    manifest["runtime_seconds"] = round((ended - started).total_seconds(), 3)
    manifest["errors"].append(
        {"type": type(error).__name__, "message": str(error)[:4000]}
    )
    log_path = Path(output_dir) / "logs" / "failure.txt"
    log_path.write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
    try:
        export_checkpoint_manifest(output_dir)
        write_run_manifest(output_dir, manifest)
        write_artifact_inventory(output_dir)
    except Exception:
        # The original failure is more useful than a failure while recording it.
        pass


def run_training(
    config_path,
    *,
    project_root=None,
    model_path=None,
    tokenizer_path=None,
    output_dir=None,
    pod_id=None,
    region=None,
    host=None,
    image=None,
    resume_from_checkpoint=None,
):
    """Execute the authorized smoke test and return the run directory.

    Callers must not invoke this without project-director authorization. The
    function itself also enforces the config flags before loading any model.
    """
    loaded = _load_authorized_config(config_path, project_root)
    _require_run_metadata(pod_id, region, host, image)
    if resume_from_checkpoint or loaded["training"]["resume_from_checkpoint"]:
        raise TrainingError(
            "checkpoint resume is disabled for this first gate; record a new "
            "attempt with a new run directory instead"
        )
    runtime = check_runtime(loaded, require_gpu=True)
    tokenizer = _load_tokenizer_for_config(
        loaded, tokenizer_path=tokenizer_path, model_path=model_path
    )
    dataset = load_pilot_dataset(
        loaded,
        project_root=project_root,
        require_complete=True,
        require_approved=True,
        tokenizer=tokenizer,
        require_token_checks=True,
    )
    output = prepare_run_directory(loaded, output_dir=output_dir)
    started_at = utc_now()
    manifest = {
        "schema_version": 1,
        "experiment_id": loaded["experiment"]["id"],
        "experiment_name": loaded["experiment"]["name"],
        "approval_reference": loaded["experiment"]["approval_reference"],
        "config_path": str(loaded.path),
        "config_sha256": loaded.sha256,
        "status": "started",
        "started_at_utc": started_at,
        "ended_at_utc": None,
        "runtime_seconds": None,
        "gpu_hours": None,
        "base_model": {
            "id": loaded["base_model"]["id"],
            "revision": loaded["base_model"]["revision"],
            "parameter_count": loaded["base_model"]["parameter_count"],
        },
        "tokenizer": {
            "revision": loaded["tokenizer"]["revision"],
            "chat_template_sha256": loaded["tokenizer"]["chat_template_sha256"],
            "eos_token_ids": list(loaded["tokenizer"]["generation_eos_token_ids"]),
        },
        "quantization": dict(loaded["quantization"]),
        "lora": {
            "config": dict(loaded["lora"]),
            "expected_trainable_parameters": loaded["lora"][
                "expected_trainable_parameters"
            ],
            "actual_trainable_parameters": None,
        },
        "dataset": {
            "version": loaded["dataset"]["version"],
            "counts": dataset.summary["counts"],
            "hashes": dict(dataset.hashes),
            "provenance_sha256": dataset.provenance_sha256,
            "summary": dataset.summary,
            "reviewed": True,
        },
        "environment": runtime,
        "hardware": {
            "provider": loaded["hardware"]["provider"],
            "cloud": loaded["hardware"]["cloud"],
            "gpu": runtime.get("gpu_name"),
            "gpu_total_memory_gb": runtime.get("gpu_total_memory_gb"),
            "peak_vram_gb": None,
            "pod_id": pod_id,
            "region": region,
            "host": host,
            "image": image,
            "driver_version": None,
            "cuda_version": runtime.get("cuda"),
        },
        "training": {
            "output_dir": str(output),
            "run_name": loaded["training"]["run_name"],
            "max_steps": loaded["training"]["max_steps"],
            "resume_from_checkpoint": resume_from_checkpoint,
            "arguments": None,
            "log_history": None,
        },
        "preflight": {},
        "artifacts": {},
        "errors": [],
        "cost": None,
        "final_billing_recorded": False,
        "notes": [
            "This manifest records one smoke-test attempt. It is not a benchmark result.",
            "Final billing and Pod termination must be recorded by the operator.",
        ],
    }
    export_config_snapshot(output, loaded)
    export_environment(
        output,
        runtime_record=runtime,
        code_manifest=collect_code_manifest(loaded.project_root),
        git_record=collect_git_record(loaded.project_root),
    )
    write_run_manifest(output, manifest)

    logger = logging.getLogger("lugandagpt.training")
    logger.setLevel(logging.INFO)
    log_file = output / "logs" / "train.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(file_handler)
    logger.propagate = False

    guard_class = _make_guard(loaded)
    guard = guard_class()
    try:
        import torch

        torch.cuda.reset_peak_memory_stats()
        model, identity = load_base_model(
            loaded,
            model_path=model_path,
            local_files_only=bool(model_path),
        )
        manifest["base_model"].update(identity)
        train_dataset, eval_dataset = _prepare_datasets(
            dataset.train, dataset.validation
        )
        trainer = build_trainer(
            loaded,
            model,
            tokenizer,
            train_dataset,
            eval_dataset,
            output_dir=str(output),
        )
        manifest["lora"]["actual_trainable_parameters"] = sum(
            parameter.numel()
            for parameter in trainer.model.parameters()
            if parameter.requires_grad
        )
        manifest["training"]["arguments"] = trainer.args.to_dict()
        manifest["hardware"]["peak_vram_gb"] = peak_vram_gb()
        step_check = one_step_check(trainer)
        manifest["preflight"]["one_step"] = step_check
        manifest["hardware"]["peak_vram_gb"] = peak_vram_gb()
        write_run_manifest(output, manifest)
        logger.info("One-step check passed: %s", step_check)
        logger.info("Starting training with max_steps=%s", loaded["training"]["max_steps"])
        trainer.train()
        manifest["training"]["log_history"] = trainer.state.log_history
        write_json_text(
            output / "logs" / "trainer_log_history.json",
            trainer.state.log_history,
        )
        if guard.limit_reason:
            raise TrainingError(f"training stopped by guard: {guard.limit_reason}")
        if guard.nonfinite_loss is not None:
            raise TrainingError("training produced a non-finite loss")
        if trainer.state.global_step < 1:
            raise TrainingError("training completed without an optimizer step")
        manifest["hardware"]["peak_vram_gb"] = peak_vram_gb()
        final_adapter = save_adapter_and_tokenizer(trainer, tokenizer, output)
        checkpoints = export_checkpoint_manifest(output)
        manifest["artifacts"]["final_adapter"] = str(final_adapter.relative_to(output))
        manifest["artifacts"]["checkpoints"] = [
            checkpoint["name"] for checkpoint in checkpoints
        ]
        manifest["status"] = "completed"
        manifest["ended_at_utc"] = utc_now()
        started = _datetime.datetime.fromisoformat(
            manifest["started_at_utc"].replace("Z", "+00:00")
        )
        ended = _datetime.datetime.fromisoformat(
            manifest["ended_at_utc"].replace("Z", "+00:00")
        )
        manifest["runtime_seconds"] = round((ended - started).total_seconds(), 3)
        manifest["gpu_hours"] = round(manifest["runtime_seconds"] / 3600.0, 6)
        write_run_manifest(output, manifest)
        write_artifact_inventory(output)
        logger.info("Training completed and artifacts were written to %s", output)
        return output
    except BaseException as error:
        _write_failure(output, manifest, error)
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(error, TrainingError):
            raise
        raise TrainingError(f"training failed: {error}") from error
    finally:
        logger.removeHandler(file_handler)
        file_handler.close()
