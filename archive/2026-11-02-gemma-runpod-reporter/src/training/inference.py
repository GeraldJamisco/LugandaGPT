"""Post-training generation without scoring or benchmark claims.

The inference pass is separate from training. It records base, existing-adapter,
and new-adapter responses verbatim and prepares a blind review packet. It does
not call the benchmark scoring tools and does not create native reviews.
"""

import gc
import hashlib
import random
from pathlib import Path

from .artifacts import (
    read_run_manifest,
    utc_now,
    write_artifact_inventory,
    write_json_text,
    write_run_manifest,
)
from .config import load_config, validate_authorized_for_execution
from .constants import PINNED_LORA
from .data import load_pilot_dataset
from .environment import check_runtime
from .errors import AuthorizationError, ArtifactError, TrainingError
from .modeling import (
    generate_text,
    load_adapter_model,
    load_base_model,
    load_tokenizer,
)
from .storage import sha256_file, write_jsonl


def _load_authorized(config_path, project_root=None):
    loaded = load_config(config_path, project_root=project_root)
    try:
        validate_authorized_for_execution(loaded)
    except Exception as error:
        raise AuthorizationError(str(error)) from error
    return loaded


def _adapter_parameter_count(path):
    weights = Path(path) / "adapter_model.safetensors"
    if not weights.is_file():
        return None
    try:
        from safetensors import safe_open
    except ImportError as error:
        raise ArtifactError("safetensors is required to inspect an adapter") from error
    try:
        with safe_open(str(weights), framework="pt", device="cpu") as handle:
            return sum(handle.get_tensor(key).numel() for key in handle.keys())
    except Exception as error:
        raise ArtifactError(f"cannot inspect adapter weights: {error}") from error


def _adapter_hash(path):
    path = Path(path)
    if not path.is_dir():
        raise ArtifactError(f"adapter directory not found: {path}")
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            files.append((item.relative_to(path).as_posix(), sha256_file(item)))
    if not files:
        raise ArtifactError(f"adapter directory is empty: {path}")
    digest = hashlib.sha256()
    for relative, file_hash in files:
        digest.update(f"{relative}\0{file_hash}\n".encode("utf-8"))
    parameters = _adapter_parameter_count(path)
    value = {"sha256": digest.hexdigest(), "files": len(files)}
    if parameters is not None:
        value["parameters"] = parameters
    return value


def _prompt_before_final_assistant(record):
    messages = record["messages"]
    assistant_indices = [
        index for index, message in enumerate(messages) if message["role"] == "assistant"
    ]
    if not assistant_indices:
        raise TrainingError(
            f"{record.get('pilot_id') or record.get('eval_id')} has no assistant turn"
        )
    final = assistant_indices[-1]
    prompt = messages[:final]
    if not prompt or prompt[-1]["role"] != "user":
        raise TrainingError("inference prompt does not end with a user turn")
    return prompt


def load_inference_items(loaded, project_root=None, tokenizer=None):
    dataset = load_pilot_dataset(
        loaded,
        project_root=project_root,
        require_complete=True,
        require_approved=True,
        tokenizer=tokenizer,
        require_token_checks=True,
    )
    items = []
    for split, records in (
        ("heldout", dataset.heldout),
        ("evaluation", dataset.evaluation),
    ):
        for record in records:
            item_id = record.get("pilot_id") or record.get("eval_id")
            items.append(
                {
                    "item_id": item_id,
                    "split": split,
                    "capability": record["capability"],
                    "prompt": _prompt_before_final_assistant(record),
                }
            )
    return items, dataset


def _generate_for_model(
    loaded,
    tokenizer,
    items,
    model_path,
    adapter_path,
    model_role,
    enforce_pinned_adapter,
):
    import torch

    model, model_identity = load_base_model(
        loaded,
        model_path=model_path,
        local_files_only=bool(model_path),
    )
    adapter_identity = None
    if adapter_path:
        adapter_identity = _adapter_hash(adapter_path)
        if enforce_pinned_adapter:
            expected = PINNED_LORA["expected_trainable_parameters"]
            actual = adapter_identity.get("parameters")
            if actual is not None and actual != expected:
                raise TrainingError(
                    f"new adapter has {actual} trainable parameters; expected {expected}"
                )
        model, config_identity = load_adapter_model(
            model,
            adapter_path,
            is_trainable=False,
            enforce_pinned_shape=enforce_pinned_adapter,
        )
        adapter_identity["config"] = config_identity
    outputs = []
    for item in items:
        generated = generate_text(
            model,
            tokenizer,
            item["prompt"],
            max_new_tokens=loaded["inference"]["max_new_tokens"],
            repetition_penalty=loaded["inference"]["repetition_penalty"],
            seed=loaded["inference"]["seed"],
        )
        outputs.append(
            {
                "item_id": item["item_id"],
                "split": item["split"],
                "capability": item["capability"],
                "prompt": item["prompt"],
                "model_role": model_role,
                "adapter_path": str(adapter_path) if adapter_path else None,
                "adapter_sha256": adapter_identity["sha256"] if adapter_identity else None,
                **generated,
            }
        )
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return outputs, {
        "model_role": model_role,
        "base_model": model_identity,
        "adapter": adapter_identity,
    }


def build_blind_packet(outputs, seed=42):
    """Create a deterministic A/B/C response packet and a separate key.

    This is preparation for native review. It is not evidence that a review
    happened.
    """
    grouped = {}
    for item in outputs:
        grouped.setdefault(item["item_id"], []).append(item)
    rng = random.Random(seed)
    packet = []
    key = {}
    for item_id in sorted(grouped):
        responses = grouped[item_id]
        if len(responses) != 3:
            raise TrainingError(
                f"blind packet needs three model responses for {item_id}; "
                f"found {len(responses)}"
            )
        roles = {response["model_role"] for response in responses}
        if roles != {"base", "existing_adapter", "new_adapter"}:
            raise TrainingError(
                f"blind packet has unexpected models for {item_id}: {sorted(roles)}"
            )
        rng.shuffle(responses)
        labels = ["A", "B", "C"]
        packet_item = {
            "item_id": item_id,
            "split": responses[0]["split"],
            "capability": responses[0]["capability"],
            "prompt": responses[0]["prompt"],
            "responses": [],
            "native_reviews": [],
            "review_status": "pending_native_review",
        }
        key[item_id] = {}
        for label, response in zip(labels, responses):
            packet_item["responses"].append(
                {
                    "label": label,
                    "output": response["output"],
                    "finish_reason": response["finish_reason"],
                }
            )
            key[item_id][label] = {
                "model_role": response["model_role"],
                "adapter_sha256": response["adapter_sha256"],
            }
        packet.append(packet_item)
    return packet, key


def run_inference(
    config_path,
    *,
    run_dir,
    new_adapter,
    existing_adapter,
    project_root=None,
    model_path=None,
    tokenizer_path=None,
):
    loaded = _load_authorized(config_path, project_root)
    run_path = Path(run_dir).resolve()
    manifest = read_run_manifest(run_path)
    if manifest.get("status") != "completed":
        raise TrainingError(
            "inference requires a completed training run manifest; "
            f"current status is {manifest.get('status')!r}"
        )
    if manifest.get("config_sha256") != loaded.sha256:
        raise TrainingError(
            "the inference config does not match the config recorded by the "
            "completed training run"
        )
    root = Path(project_root or Path.cwd()).resolve()
    new_value = new_adapter or loaded["inference"]["new_adapter_path"]
    existing_value = existing_adapter or loaded["inference"]["existing_adapter_path"]
    if not new_value or not existing_value:
        raise TrainingError(
            "both --new-adapter and --existing-adapter are required for the "
            "three-model comparison"
        )
    new_adapter = Path(new_value)
    existing_adapter = Path(existing_value)
    if not new_adapter.is_absolute():
        new_adapter = (root / new_adapter).resolve()
    if not existing_adapter.is_absolute():
        existing_adapter = (root / existing_adapter).resolve()
    if not new_adapter.is_dir() or not existing_adapter.is_dir():
        raise TrainingError("both adapter directories must exist")
    if new_adapter == existing_adapter:
        raise TrainingError("the new and existing adapter paths must be distinct")
    runtime = check_runtime(loaded, require_gpu=True)
    tokenizer = load_tokenizer(
        loaded,
        model_path=tokenizer_path or model_path,
        local_files_only=bool(tokenizer_path or model_path),
    )
    items, dataset = load_inference_items(
        loaded, project_root=project_root, tokenizer=tokenizer
    )
    if len(items) != 39:
        raise TrainingError(f"expected 39 held-out plus evaluation items, found {len(items)}")
    recorded_dataset = manifest.get("dataset", {})
    if recorded_dataset.get("hashes") != dict(dataset.hashes):
        raise TrainingError(
            "the current data hashes do not match the completed training run"
        )
    if recorded_dataset.get("provenance_sha256") != dataset.provenance_sha256:
        raise TrainingError(
            "the current provenance hash does not match the completed training run"
        )
    final_adapter_value = manifest.get("artifacts", {}).get("final_adapter")
    if not final_adapter_value:
        raise TrainingError("the training manifest does not record a final adapter")
    final_adapter = (run_path / final_adapter_value).resolve()
    try:
        final_adapter.relative_to(run_path)
    except ValueError as error:
        raise TrainingError("the recorded final adapter path escapes the run") from error
    if not final_adapter.is_dir():
        raise TrainingError(
            f"the recorded final adapter is missing: {final_adapter}"
        )
    new_hash = _adapter_hash(new_adapter)
    trained_hash = _adapter_hash(final_adapter)
    if new_hash["sha256"] != trained_hash["sha256"]:
        raise TrainingError(
            "the supplied new adapter is not the adapter saved by the training run"
        )
    existing_hash = _adapter_hash(existing_adapter)
    if existing_hash["sha256"] == new_hash["sha256"]:
        raise TrainingError("the existing adapter is identical to the new adapter")
    inference_dir = run_path / "inference"
    if inference_dir.exists() and any(inference_dir.iterdir()):
        raise ArtifactError(
            f"inference directory already exists and is not empty: {inference_dir}"
        )
    inference_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    model_records = []
    for role, adapter, enforce in (
        ("base", None, False),
        ("existing_adapter", existing_adapter, False),
        ("new_adapter", new_adapter, True),
    ):
        generated, record = _generate_for_model(
            loaded,
            tokenizer,
            items,
            model_path,
            adapter,
            role,
            enforce,
        )
        outputs.extend(generated)
        model_records.append(record)
    write_jsonl(inference_dir / "raw_outputs.jsonl", outputs)
    packet, key = build_blind_packet(outputs, seed=loaded["inference"]["seed"])
    write_json_text(inference_dir / "blind_review_packet.json", packet)
    write_json_text(inference_dir / "blind_key.json", key)
    inference_manifest = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": "completed",
        "training_run_manifest": str(run_path / "run_manifest.json"),
        "config_sha256": loaded.sha256,
        "dataset_hashes": dict(dataset.hashes),
        "dataset_provenance_sha256": dataset.provenance_sha256,
        "item_count": len(items),
        "items": {
            "heldout": len(dataset.heldout),
            "evaluation": len(dataset.evaluation),
        },
        "models": model_records,
        "generation": {
            "do_sample": False,
            "max_new_tokens": loaded["inference"]["max_new_tokens"],
            "repetition_penalty": loaded["inference"]["repetition_penalty"],
            "seed": loaded["inference"]["seed"],
            "eos_token_ids": loaded["tokenizer"]["generation_eos_token_ids"],
        },
        "native_review": {
            "status": "pending",
            "reviewers_per_response": loaded["inference"][
                "native_reviewers_per_response"
            ],
            "adjudicator_required": loaded["inference"]["adjudicator_required"],
            "blind_model_identity": loaded["inference"]["blind_model_identity"],
            "randomized_response_order": loaded["inference"][
                "randomize_response_order"
            ],
        },
        "scoring": {
            "status": "not_scored",
            "benchmark_scores_called": False,
            "reason": "Native review is required before any quality claim.",
        },
        "environment": runtime,
    }
    write_json_text(inference_dir / "inference_manifest.json", inference_manifest)
    manifest["inference"] = {
        "status": "completed",
        "directory": "inference",
        "manifest": "inference/inference_manifest.json",
        "raw_outputs": "inference/raw_outputs.jsonl",
        "blind_review_packet": "inference/blind_review_packet.json",
        "native_review_status": "pending",
        "scoring_status": "not_scored",
        "models": [item["model_role"] for item in model_records],
    }
    write_run_manifest(run_path, manifest)
    write_artifact_inventory(run_path)
    return inference_dir
