"""Model, tokenizer, LoRA, and TRL construction.

Optional heavy packages are imported inside functions. A caller must pass the
authorization, data, and runtime preflight before any of these functions are
reached by the training command.
"""

import json
import math
import time
from pathlib import Path

from .constants import (
    PINNED_BASE_ID,
    PINNED_CHAT_TEMPLATE_SHA256,
    PINNED_END_OF_TURN_TOKEN_ID,
    PINNED_EOS_IDS,
    PINNED_LORA,
    PINNED_LORA_TARGETS,
    PINNED_PARAMETER_COUNT,
    PINNED_PARAMETERS,
    PINNED_PAD_TOKEN_ID,
)
from .errors import EnvironmentError, TrainingError
from .storage import sha256_text


def _import_torch():
    try:
        import torch
    except ImportError as error:
        raise EnvironmentError("PyTorch is not installed") from error
    return torch


def verify_tokenizer(tokenizer):
    template = getattr(tokenizer, "chat_template", None)
    if not isinstance(template, str) or not template:
        raise EnvironmentError("the tokenizer has no base chat template")
    actual_hash = sha256_text(template)
    if actual_hash != PINNED_CHAT_TEMPLATE_SHA256:
        raise EnvironmentError(
            "chat template SHA-256 does not match the pinned base: "
            f"{actual_hash}"
        )
    checks = {
        "pad_token_id": PINNED_PAD_TOKEN_ID,
        "eos_token_id": PINNED_EOS_IDS[0],
        "bos_token_id": 2,
    }
    for name, expected in checks.items():
        actual = getattr(tokenizer, name, None)
        if actual != expected:
            raise EnvironmentError(
                f"tokenizer {name} is {actual!r}; expected {expected!r}"
            )
    end_of_turn = tokenizer.convert_tokens_to_ids("<end_of_turn>")
    if end_of_turn != PINNED_END_OF_TURN_TOKEN_ID:
        raise EnvironmentError(
            "tokenizer <end_of_turn> id is "
            f"{end_of_turn!r}; expected {PINNED_END_OF_TURN_TOKEN_ID!r}"
        )
    return {
        "chat_template_sha256": actual_hash,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
        "bos_token_id": tokenizer.bos_token_id,
        "end_of_turn_token_id": end_of_turn,
        "vocab_size": len(tokenizer),
    }


def load_tokenizer(config, model_path=None, local_files_only=False):
    try:
        from transformers import AutoTokenizer
    except ImportError as error:
        raise EnvironmentError("Transformers is not installed") from error
    base = config["base_model"]
    source = str(model_path) if model_path else base["id"]
    kwargs = {
        "trust_remote_code": False,
        "use_fast": True,
        "local_files_only": local_files_only,
    }
    if model_path is None:
        kwargs["revision"] = base["revision"]
    try:
        tokenizer = AutoTokenizer.from_pretrained(source, **kwargs)
    except Exception as error:
        raise EnvironmentError(f"cannot load the pinned tokenizer: {error}") from error
    verify_tokenizer(tokenizer)
    return tokenizer


def _model_config_value(config, name):
    if hasattr(config, name):
        return getattr(config, name)
    text_config = getattr(config, "text_config", None)
    if text_config is not None and hasattr(text_config, name):
        return getattr(text_config, name)
    raise EnvironmentError(f"model config does not expose {name}")


def verify_model_pins(model):
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != PINNED_PARAMETER_COUNT:
        raise EnvironmentError(
            f"base model has {parameter_count} parameters; expected {PINNED_PARAMETER_COUNT}"
        )
    for name, expected in PINNED_PARAMETERS.items():
        actual = _model_config_value(model.config, name)
        if actual != expected:
            raise EnvironmentError(
                f"model config {name} is {actual!r}; expected {expected!r}"
            )
    eos = getattr(model.generation_config, "eos_token_id", None)
    if isinstance(eos, int):
        eos = [eos]
    if eos is None or tuple(eos) != PINNED_EOS_IDS:
        raise EnvironmentError(
            f"generation eos_token_id is {eos!r}; expected {list(PINNED_EOS_IDS)!r}"
        )
    return {
        "parameter_count": parameter_count,
        "config": {
            name: _model_config_value(model.config, name) for name in PINNED_PARAMETERS
        },
        "generation_eos_token_ids": list(PINNED_EOS_IDS),
    }


def load_base_model(config, model_path=None, local_files_only=False):
    torch = _import_torch()
    try:
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    except ImportError as error:
        raise EnvironmentError("Transformers is not installed") from error
    if not torch.cuda.is_available():
        raise EnvironmentError("a CUDA GPU is required to load the 4-bit base")
    quantization = config["quantization"]
    quant_config = BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_storage=torch.uint8,
    )
    base = config["base_model"]
    source = str(model_path) if model_path else base["id"]
    kwargs = {
        "quantization_config": quant_config,
        "device_map": {"": torch.cuda.current_device()},
        "torch_dtype": torch.bfloat16,
        "trust_remote_code": False,
        "low_cpu_mem_usage": True,
        "local_files_only": local_files_only,
    }
    if model_path is None:
        kwargs["revision"] = base["revision"]
    try:
        model = AutoModelForCausalLM.from_pretrained(source, **kwargs)
    except Exception as error:
        raise EnvironmentError(f"cannot load the pinned base model: {error}") from error
    if not getattr(model, "is_loaded_in_4bit", False):
        raise EnvironmentError("the base model did not load in 4-bit mode")
    identity = verify_model_pins(model)
    model.config.use_cache = False
    return model, identity


def build_lora_config(config):
    try:
        from peft import LoraConfig, TaskType
    except ImportError as error:
        raise EnvironmentError("PEFT is not installed") from error
    lora = config["lora"]
    return LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora["r"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        bias=lora["bias"],
        target_modules=list(PINNED_LORA_TARGETS),
        use_dora=lora["use_dora"],
        use_rslora=lora["use_rslora"],
        init_lora_weights=lora["init_lora_weights"],
        modules_to_save=list(lora["modules_to_save"]),
    )


def _float_config(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingError(f"{field} is not numeric")
    if not math.isfinite(value):
        raise TrainingError(f"{field} is not finite")
    return float(value)


def build_sft_config(config, output_dir=None):
    try:
        from trl import SFTConfig
    except ImportError as error:
        raise EnvironmentError("TRL 0.20.0 is not installed") from error
    training = config["training"]
    dataset = config["dataset"]
    resolved_output = str(output_dir or training["output_dir"])
    kwargs = {
        "output_dir": resolved_output,
        "run_name": training["run_name"],
        "per_device_train_batch_size": training["per_device_train_batch_size"],
        "per_device_eval_batch_size": training["per_device_eval_batch_size"],
        "gradient_accumulation_steps": training["gradient_accumulation_steps"],
        "num_train_epochs": training["num_train_epochs"],
        "max_steps": training["max_steps"],
        "learning_rate": _float_config(training["learning_rate"], "learning_rate"),
        "lr_scheduler_type": training["lr_scheduler_type"],
        "warmup_ratio": _float_config(training["warmup_ratio"], "warmup_ratio"),
        "weight_decay": _float_config(training["weight_decay"], "weight_decay"),
        "max_grad_norm": _float_config(training["max_grad_norm"], "max_grad_norm"),
        "optim": training["optim"],
        "adam_beta1": _float_config(training["adam_beta1"], "adam_beta1"),
        "adam_beta2": _float_config(training["adam_beta2"], "adam_beta2"),
        "adam_epsilon": _float_config(training["adam_epsilon"], "adam_epsilon"),
        "bf16": training["bf16"],
        "fp16": training["fp16"],
        "tf32": training["tf32"],
        "bf16_full_eval": training["bf16_full_eval"],
        "gradient_checkpointing": training["gradient_checkpointing"],
        "gradient_checkpointing_kwargs": dict(
            training["gradient_checkpointing_kwargs"]
        ),
        "assistant_only_loss": training["assistant_only_loss"],
        "completion_only_loss": training["completion_only_loss"],
        "dataset_kwargs": dict(training["dataset_kwargs"]),
        "eval_strategy": training["eval_strategy"],
        "eval_steps": training["eval_steps"],
        "eval_on_start": training["eval_on_start"],
        "save_strategy": training["save_strategy"],
        "save_steps": training["save_steps"],
        "save_total_limit": training["save_total_limit"],
        "save_only_model": training["save_only_model"],
        "save_safetensors": training["save_safetensors"],
        "load_best_model_at_end": training["load_best_model_at_end"],
        "logging_steps": training["logging_steps"],
        "logging_first_step": training["logging_first_step"],
        "report_to": training["report_to"],
        "push_to_hub": training["push_to_hub"],
        "hub_model_id": training["hub_model_id"],
        "seed": training["seed"],
        "data_seed": training["data_seed"],
        "dataloader_num_workers": training["dataloader_num_workers"],
        "dataset_num_proc": training["dataset_num_proc"],
        "remove_unused_columns": training["remove_unused_columns"],
        "torch_compile": training["torch_compile"],
        "use_liger_kernel": training["use_liger_kernel"],
        "average_tokens_across_devices": training["average_tokens_across_devices"],
        "include_num_input_tokens_seen": training["include_num_input_tokens_seen"],
        "max_length": dataset["max_length"],
        "packing": dataset["packing"],
    }
    return SFTConfig(**kwargs)


def build_trainer(
    config,
    model,
    tokenizer,
    train_dataset,
    eval_dataset,
    output_dir=None,
):
    try:
        from peft import PeftModel
        from trl import SFTTrainer
    except ImportError as error:
        raise EnvironmentError("TRL or PEFT is not installed") from error
    args = build_sft_config(config, output_dir=output_dir)
    try:
        trainer = SFTTrainer(
            model=model,
            args=args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            processing_class=tokenizer,
            peft_config=build_lora_config(config),
        )
    except Exception as error:
        raise TrainingError(f"cannot construct the SFT trainer: {error}") from error
    if not isinstance(trainer.model, PeftModel):
        raise TrainingError("SFTTrainer did not apply a PEFT adapter")
    if not getattr(trainer.model, "is_loaded_in_4bit", False):
        raise TrainingError("the trainer model is not in 4-bit mode")
    trainable = sum(
        parameter.numel()
        for parameter in trainer.model.parameters()
        if parameter.requires_grad
    )
    expected = config["lora"]["expected_trainable_parameters"]
    if trainable != expected:
        raise TrainingError(
            f"LoRA adapter has {trainable} trainable parameters; expected {expected}"
        )
    return trainer


def one_step_check(trainer):
    """Run one forward and backward pass without updating the optimizer."""
    torch = _import_torch()
    try:
        dataloader = trainer.get_train_dataloader()
        batch = next(iter(dataloader))
        inputs = trainer._prepare_inputs(batch)
        trainer.model.train()
        trainer.model.zero_grad(set_to_none=True)
        started = time.monotonic()
        outputs = trainer.model(**inputs)
        loss = outputs.loss
        if loss is None or not torch.isfinite(loss):
            raise TrainingError("one-step check produced a non-finite loss")
        trainer.accelerator.backward(loss)
        grad_count = sum(
            1
            for parameter in trainer.model.parameters()
            if parameter.requires_grad and parameter.grad is not None
        )
        if grad_count == 0:
            raise TrainingError("one-step check produced no gradients")
        trainer.model.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
    except RuntimeError as error:
        if "out of memory" in str(error).lower():
            raise EnvironmentError(
                "one-step check ran out of GPU memory; stop the run"
            ) from error
        raise
    tokens = int(inputs.get("attention_mask", inputs["input_ids"]).sum().item())
    return {
        "loss": float(loss.detach().float().item()),
        "batch_tokens": tokens,
        "gradient_tensors": grad_count,
        "seconds": round(time.monotonic() - started, 4),
        "step": 0,
    }


def verify_adapter_identity(adapter_path, expected_trainable=None, enforce_pinned_shape=True):
    path = Path(adapter_path)
    config_path = path / "adapter_config.json"
    if not config_path.is_file():
        raise TrainingError(f"adapter_config.json is missing from {path}")
    try:
        adapter_config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TrainingError(f"cannot read adapter config: {error}") from error
    base = adapter_config.get("base_model_name_or_path")
    if not isinstance(base, str) or not base:
        raise TrainingError("adapter config has no base_model_name_or_path")
    if base != PINNED_BASE_ID and "gemma-3-1b-it" not in Path(base).name:
        raise TrainingError(
            f"adapter base model {base!r} does not identify the pinned Gemma 3 1B base"
        )
    expected = expected_trainable or PINNED_LORA["expected_trainable_parameters"]
    if enforce_pinned_shape:
        for key in ("r", "lora_alpha", "lora_dropout"):
            if key in adapter_config:
                expected_key = {"r": "r", "lora_alpha": "alpha", "lora_dropout": "dropout"}[key]
                if adapter_config[key] != PINNED_LORA[expected_key]:
                    raise TrainingError(
                        f"adapter {key} is {adapter_config[key]!r}; "
                        f"expected {PINNED_LORA[expected_key]!r}"
                    )
    return {
        "base_model_name_or_path": base,
        "r": adapter_config.get("r"),
        "lora_alpha": adapter_config.get("lora_alpha"),
        "lora_dropout": adapter_config.get("lora_dropout"),
        "expected_trainable_parameters": expected,
    }


def load_adapter_model(
    base_model,
    adapter_path,
    is_trainable=False,
    enforce_pinned_shape=True,
):
    try:
        from peft import PeftModel
    except ImportError as error:
        raise EnvironmentError("PEFT is not installed") from error
    identity = verify_adapter_identity(
        adapter_path, enforce_pinned_shape=enforce_pinned_shape
    )
    try:
        model = PeftModel.from_pretrained(
            base_model, str(adapter_path), is_trainable=is_trainable
        )
    except Exception as error:
        raise TrainingError(f"cannot load adapter {adapter_path}: {error}") from error
    model.eval()
    return model, identity


def save_adapter_and_tokenizer(trainer, tokenizer, output_dir):
    output = Path(output_dir)
    final = output / "final_adapter"
    if final.exists() and any(final.iterdir()):
        raise TrainingError(f"refusing to overwrite a non-empty adapter directory: {final}")
    final.mkdir(parents=True, exist_ok=True)
    try:
        trainer.save_model(str(final))
        trainer.save_state()
        tokenizer.save_pretrained(str(final))
    except Exception as error:
        raise TrainingError(f"cannot save the adapter or tokenizer: {error}") from error
    if not (final / "adapter_config.json").is_file():
        raise TrainingError("saved adapter has no adapter_config.json")
    if not (final / "tokenizer_config.json").is_file():
        raise TrainingError("saved tokenizer has no tokenizer_config.json")
    return final


def generate_text(
    model,
    tokenizer,
    messages,
    *,
    max_new_tokens=256,
    repetition_penalty=1.0,
    seed=42,
):
    torch = _import_torch()
    from transformers import set_seed

    set_seed(seed)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = tokenizer(
        prompt,
        add_special_tokens=False,
        return_tensors="pt",
        truncation=False,
    )
    device = next(model.parameters()).device
    input_ids = encoded["input_ids"].to(device)
    attention_mask = encoded["attention_mask"].to(device)
    started = time.monotonic()
    model.eval()
    with torch.inference_mode():
        output = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=repetition_penalty,
            pad_token_id=PINNED_PAD_TOKEN_ID,
            eos_token_id=list(PINNED_EOS_IDS),
        )
    generated_ids = output[0][input_ids.shape[-1] :].tolist()
    finish_reason = "length"
    if generated_ids and generated_ids[-1] in PINNED_EOS_IDS:
        finish_reason = "eos"
    raw = tokenizer.decode(generated_ids, skip_special_tokens=False)
    text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    return {
        "rendered_prompt": prompt,
        "output": text,
        "raw_output": raw,
        "prompt_tokens": int(input_ids.shape[-1]),
        "completion_tokens": len(generated_ids),
        "finish_reason": finish_reason,
        "latency_ms": round((time.monotonic() - started) * 1000, 3),
    }


def peak_vram_gb():
    torch = _import_torch()
    if not torch.cuda.is_available():
        return None
    return round(torch.cuda.max_memory_allocated(0) / (1024**3), 3)
