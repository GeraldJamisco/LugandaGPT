"""Pinned configuration for the Sunflower-14B QLoRA fine-tune (Gate 6, D-021).

Importing this module imports nothing heavy. It only defines the approved
training identity and validates a config against it, so the base model,
adapter shape, and budget cannot drift silently between runs.

Facts confirmed from the Hugging Face model card on 2026-11-04:
  base_model : Sunbird/Sunflower-14B  (gated; owner granted access)
  built on   : Qwen/Qwen3-14B
  size       : ~15B parameters, BF16
  licence    : apache-2.0  (permits commercial use of the weights)
"""

from .errors import ConfigError

# --- Approved, pinned identity -------------------------------------------------
BASE_MODEL = "Sunbird/Sunflower-14B"
ARCHITECTURE = "qwen3"
LICENSE = "apache-2.0"
# The exact commit is pinned at run time to whatever the hub resolves and is
# recorded in the manifest. A specific revision may be set here once chosen.
DEFAULT_REVISION = "main"

# QLoRA 4-bit load (bitsandbytes).
QUANTIZATION = {
    "load_in_4bit": True,
    "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_use_double_quant": True,
    "bnb_4bit_compute_dtype": "bfloat16",
}

# LoRA adapter shape. Target modules are the Qwen3 attention and MLP projections.
LORA = {
    "task_type": "CAUSAL_LM",
    "r": 16,
    "alpha": 32,
    "dropout": 0.05,
    "bias": "none",
    "target_modules": (
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ),
}

# Training hyper-parameters the owner approved as the default first run.
DEFAULTS = {
    "max_seq_len": 1024,
    "epochs": 1,
    "per_device_batch_size": 1,
    "grad_accum": 16,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.03,
    "weight_decay": 0.0,
    "lr_scheduler": "cosine",
    "seed": 7,
}

# Budget guard. D-021 approved $20 total and no more. A config asking to spend
# more than this is rejected unless the owner records a new decision.
MAX_APPROVED_USD = 20.0

# Recommended GPU: a 24 GB card (e.g. RTX 4090 / A5000) fits 14B in 4-bit.
RECOMMENDED_GPU_VRAM_GB = 24


def build_config(overrides=None):
    """Return the full config dict, pinned identity plus defaults, with overrides
    applied only to the hyper-parameters (never to identity)."""
    cfg = {
        "base_model": BASE_MODEL,
        "architecture": ARCHITECTURE,
        "license": LICENSE,
        "revision": DEFAULT_REVISION,
        "quantization": dict(QUANTIZATION),
        "lora": {**LORA, "target_modules": list(LORA["target_modules"])},
        **DEFAULTS,
        "approved_usd": MAX_APPROVED_USD,
    }
    for key, value in (overrides or {}).items():
        if key in ("base_model", "architecture", "license", "lora", "quantization"):
            raise ConfigError("pinned identity cannot be overridden", field=key)
        if key not in cfg:
            raise ConfigError("unknown config field", field=key)
        cfg[key] = value
    validate_config(cfg)
    return cfg


def validate_config(cfg):
    if cfg.get("base_model") != BASE_MODEL:
        raise ConfigError(f"base_model must be {BASE_MODEL}", field="base_model")
    if cfg.get("license") != LICENSE:
        raise ConfigError("license drift from the pinned Apache-2.0", field="license")
    if cfg.get("lora", {}).get("r") != LORA["r"]:
        raise ConfigError("LoRA rank drift from approved shape", field="lora.r")
    approved = float(cfg.get("approved_usd", 0))
    if approved > MAX_APPROVED_USD:
        raise ConfigError(
            f"approved_usd {approved} exceeds the D-021 cap of {MAX_APPROVED_USD}",
            field="approved_usd",
        )
    for field in ("epochs", "per_device_batch_size", "grad_accum", "max_seq_len"):
        if int(cfg.get(field, 0)) <= 0:
            raise ConfigError("must be a positive integer", field=field)
    return True
