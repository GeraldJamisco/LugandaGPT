"""Guarded QLoRA fine-tune of Sunflower-14B (Gate 6, budget D-021 = $20).

Runs on a rented GPU (RunPod), not on the owner's PC and not in the cloud
workspace. Heavy libraries (torch, transformers, peft, trl, bitsandbytes) are
imported only inside run_training(), after the config and data checks pass, so
--dry-run and the unit tests work on a plain Python with no GPU.

Typical use on the pod:
  python -m training.train_sunflower --train data/training/train-v0.1.jsonl --dry-run
  python -m training.train_sunflower --train data/training/train-v0.1.jsonl \
      --output runs/sunflower-v0.1 --confirm-approval D-021
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .errors import AuthorizationError, TrainingError
from .sunflower_config import build_config, RECOMMENDED_GPU_VRAM_GB
from .sunflower_data import load_training_rows, summarise


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_overrides(path):
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TrainingError("config file must be a JSON object")
    return data


def plan(args):
    """Validate config + data and return a plan dict. No heavy imports, no GPU."""
    overrides = _load_overrides(args.config)
    if args.epochs is not None:
        overrides["epochs"] = args.epochs
    if args.max_seq_len is not None:
        overrides["max_seq_len"] = args.max_seq_len
    cfg = build_config(overrides)
    rows = load_training_rows(args.train)
    summary = summarise(rows)
    return {
        "config": cfg,
        "train_file": str(args.train),
        "train_sha256": _sha256(args.train),
        "data_summary": summary,
        "recommended_gpu_vram_gb": RECOMMENDED_GPU_VRAM_GB,
        "decisions": ["D-020", "D-021", "D-022", "D-024", "D-025", "D-026"],
        "note": "Stop the pod when the run finishes (D-021). Launch is not approved by this run.",
    }


def run_training(args):
    the_plan = plan(args)
    if args.dry_run:
        print(json.dumps(the_plan, indent=1, ensure_ascii=False))
        print("\nDRY RUN ok. No model was loaded and no GPU time was used.")
        return 0

    if args.confirm_approval != "D-021":
        raise AuthorizationError(
            "a real run needs --confirm-approval D-021 (the owner's $20 approval)"
        )

    # --- Heavy imports happen only here, on the GPU box ---
    import torch  # noqa: F401
    from transformers import (  # noqa: F401
        AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset
    from trl import SFTTrainer

    if not torch.cuda.is_available():
        raise TrainingError("no CUDA GPU found; run this on a RunPod GPU pod")

    cfg = the_plan["config"]
    rows = load_training_rows(args.train)

    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], revision=cfg["revision"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def to_text(row):
        return {"text": tokenizer.apply_chat_template(
            row["messages"], tokenize=False, add_generation_prompt=False)}

    dataset = Dataset.from_list([to_text(r) for r in rows])

    compute_dtype = getattr(torch, "bfloat16")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=cfg["quantization"]["bnb_4bit_quant_type"],
        bnb_4bit_use_double_quant=cfg["quantization"]["bnb_4bit_use_double_quant"],
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"], revision=cfg["revision"],
        quantization_config=bnb, torch_dtype=compute_dtype, device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        task_type=cfg["lora"]["task_type"], r=cfg["lora"]["r"],
        lora_alpha=cfg["lora"]["alpha"], lora_dropout=cfg["lora"]["dropout"],
        bias=cfg["lora"]["bias"], target_modules=list(cfg["lora"]["target_modules"]),
    )
    model = get_peft_model(model, lora)
    resolved_rev = getattr(getattr(model, "config", None), "_commit_hash", cfg["revision"])

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    targs = TrainingArguments(
        output_dir=str(out), num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["per_device_batch_size"],
        gradient_accumulation_steps=cfg["grad_accum"],
        learning_rate=cfg["learning_rate"], warmup_ratio=cfg["warmup_ratio"],
        weight_decay=cfg["weight_decay"], lr_scheduler_type=cfg["lr_scheduler"],
        bf16=True, logging_steps=10, save_strategy="epoch", seed=cfg["seed"],
        report_to=[],
    )
    trainer = SFTTrainer(
        model=model, args=targs, train_dataset=dataset,
        dataset_text_field="text", max_seq_length=cfg["max_seq_len"],
        tokenizer=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))

    manifest = {
        **{k: the_plan[k] for k in ("train_file", "train_sha256", "data_summary")},
        "config": cfg, "resolved_revision": resolved_rev,
        "adapter_dir": str(out),
    }
    (out / "run-manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print("Training complete. Adapter saved to", out)
    print("REMINDER: stop the RunPod pod now (D-021).")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="QLoRA fine-tune of Sunflower-14B")
    p.add_argument("--train", default="data/training/train-v0.1.jsonl")
    p.add_argument("--output", default="runs/sunflower-v0.1")
    p.add_argument("--config", help="optional JSON file of hyper-parameter overrides")
    p.add_argument("--epochs", type=int)
    p.add_argument("--max-seq-len", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--confirm-approval", default="")
    args = p.parse_args(argv)
    try:
        return run_training(args)
    except TrainingError as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
