# Training Sunflower-14B on RunPod (Gate 6, budget D-021 = $20)

This is the runbook for the first QLoRA fine-tune. It runs on a **rented RunPod
GPU**, not on the owner's PC (no GPU) and not in the cloud workspace. The script
is `src/training/train_sunflower.py`.

Confirmed facts (HF model card, 2026-11-04): base `Sunbird/Sunflower-14B`, built
on Qwen3-14B, ~15B params, BF16, licence **apache-2.0**. Owner has been granted
gated access.

## Before you rent anything

1. The data imbalance: `train-v0.1.jsonl` is ~99% SALT translation pairs and only
   ~96 examples target our weak areas. Rebuild with the small sets weighted up
   first, e.g. repeat the rule and native data so they are not drowned out:
   ```
   PYTHONPATH=src python -m training_data.build --repeat-native 20 --repeat-rule 10
   ```
   (Numbers to be chosen with the group once set 2 is in.)
2. Make sure your Hugging Face token (read) is ready. It is a secret: never put it
   in a file in the repo, a commit, or chat. On the pod you set it as an
   environment variable only.

## On RunPod

1. Create a pod with a **24 GB GPU** (RTX 4090 or A5000 is enough for 14B in
   4-bit) and a PyTorch template. Community cloud is cheapest.
2. In the pod terminal:
   ```
   git clone <your repo url> LugandaGPT && cd LugandaGPT
   pip install torch transformers peft trl datasets bitsandbytes accelerate
   export HF_TOKEN=***your token***      # not stored anywhere in the repo
   huggingface-cli login --token "$HF_TOKEN"
   ```
3. Copy your prepared `data/training/train-v0.1.jsonl` to the pod (it is git-ignored,
   so scp/upload it, or rebuild it on the pod from the committed source data).
4. **Dry run first** — this uses no GPU time and checks the config and data:
   ```
   PYTHONPATH=src python -m training.train_sunflower \
       --train data/training/train-v0.1.jsonl --dry-run
   ```
5. **Real run** — needs the owner's approval flag:
   ```
   PYTHONPATH=src python -m training.train_sunflower \
       --train data/training/train-v0.1.jsonl \
       --output runs/sunflower-v0.1 --confirm-approval D-021
   ```
6. When it finishes, the LoRA adapter and `run-manifest.json` are in
   `runs/sunflower-v0.1`. Download that folder (it is small, tens of MB).
7. **Stop the pod immediately** (D-021). A pod left running keeps charging.

## Cost

A 24 GB community GPU is roughly $0.35–0.45/hr. One epoch on the current data is
expected to take a small number of hours, well under the $20 cap. The dry run
prints the plan; the real run prints a reminder to stop the pod.

## What this run does NOT do

- It does not approve serving, hosting, or launch (those are Gate 8 / D-026).
- It does not claim the model is better than Sunflower. That is decided only after
  the frozen benchmark is run on the new adapter and the native group scores it
  blind (Gate 7).
