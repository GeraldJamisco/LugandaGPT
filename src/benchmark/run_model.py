"""Run frozen benchmark items through a model and record its answers.

Runs on a GPU pod. Loads Sunflower-14B in 4-bit, optionally attaches a trained
LoRA adapter (--adapter), generates greedily, and writes one JSON line per item.
Heavy libraries import only inside run(), so --dry-run and tests work with no GPU.

  python -m benchmark.run_model --items data/benchmark/frozen/items.jsonl \
      --model-name base --output answers-base.jsonl
  python -m benchmark.run_model --items data/benchmark/frozen/items.jsonl \
      --adapter runs/sunflower-v0.2 --model-name v0.2 --output answers-v0.2.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

BASE_MODEL = "Sunbird/Sunflower-14B"


def read_items(paths, skip_multi_turn=True):
    """Read benchmark items from one or more JSONL files. Returns usable items."""
    items, seen = [], set()
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                it = json.loads(line)
                if it.get("excluded") is True or it.get("review_status") == "excluded":
                    continue
                if skip_multi_turn and it.get("turns"):
                    continue
                if not (it.get("prompt") or "").strip():
                    continue
                iid = it.get("id") or it.get("item_id")
                if not iid or iid in seen:
                    continue
                seen.add(iid)
                items.append({
                    "item_id": iid,
                    "category": it.get("category", ""),
                    "prompt": it["prompt"],
                    "expected_behavior": it.get("expected_behavior", ""),
                    "turns": it.get("turns", []),
                })
    return items


def build_messages(item):
    msgs = []
    for t in item.get("turns", []):
        role = t.get("role", "user")
        content = t.get("content", "")
        if content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": item["prompt"]})
    return msgs


def plan(args):
    items = read_items(args.items, skip_multi_turn=not args.include_multi_turn)
    cats = {}
    for it in items:
        cats[it["category"]] = cats.get(it["category"], 0) + 1
    return {"items": len(items), "by_category": cats,
            "model_name": args.model_name, "adapter": args.adapter,
            "base_model": BASE_MODEL, "output": args.output}


def run(args):
    info = plan(args)
    if args.dry_run:
        print(json.dumps(info, indent=1, ensure_ascii=False))
        print("\nDRY RUN ok. No model loaded.")
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_use_double_quant=True,
                             bnb_4bit_compute_dtype=torch.bfloat16)
    print(">> loading base model...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb, torch_dtype=torch.bfloat16, device_map="auto")
    if args.adapter:
        from peft import PeftModel
        print(">> attaching adapter:", args.adapter, flush=True)
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    def encode(msgs):
        r = None
        for kw in (dict(enable_thinking=False, return_dict=True), dict(return_dict=True), dict()):
            try:
                r = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                            return_tensors="pt", **kw)
                break
            except TypeError:
                continue
        return ({k: v.to(model.device) for k, v in r.items()}
                if hasattr(r, "keys") else {"input_ids": r.to(model.device)})

    items = read_items(args.items, skip_multi_turn=not args.include_multi_turn)
    out = Path(args.output)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for i, it in enumerate(items, 1):
            enc = encode(build_messages(it))
            plen = enc["input_ids"].shape[1]
            with torch.no_grad():
                g = model.generate(**enc, max_new_tokens=args.max_new_tokens,
                                   do_sample=False, pad_token_id=tok.eos_token_id)
            answer = tok.decode(g[0][plen:], skip_special_tokens=True).strip()
            rec = {"item_id": it["item_id"], "category": it["category"],
                   "prompt": it["prompt"], "expected_behavior": it["expected_behavior"],
                   "model": args.model_name, "answer": answer}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print("[%d/%d] %s" % (i, len(items), it["item_id"]), flush=True)
    print("Wrote", len(items), "answers to", out)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Run benchmark items through a model")
    p.add_argument("--items", nargs="+", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model-name", required=True, help="label stored with each answer, e.g. base or v0.2")
    p.add_argument("--adapter", default=None, help="path to a LoRA adapter, or omit for base")
    p.add_argument("--max-new-tokens", type=int, default=120)
    p.add_argument("--include-multi-turn", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return run(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
