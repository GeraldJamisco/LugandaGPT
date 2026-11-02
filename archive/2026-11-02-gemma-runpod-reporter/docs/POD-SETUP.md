# Runpod Pod Setup and Cleanup Checklist

**Status:** preparation only. No Pod has been created. No package has been installed on a GPU host. No model or dataset has been downloaded for this gate.

This document is the operator checklist for the bounded Runpod RTX 4090 smoke test. It does not authorize the run. The owner must approve the exact configuration, data, translator and reviewer terms, dependency pins, and credit purchase before the first paid action. See `docs/DECISIONS.md` D-008 and `reports/RUNPOD-FIRST-GATE-REPORT.md`.

## Hard limits

| Limit | Value |
|---|---:|
| Total cash cap, including tax and fees | $20.00 |
| Proposed credit purchase | $10.00 |
| Hard credit stop | $8.00 consumed |
| Low-balance alert | $4.00 remaining |
| Hard runtime | 6 hours |
| Training optimizer-step cap | 30 |
| GPU | One Secure Cloud RTX 4090, 24 GB |
| Container disk | 30 GB |
| Volume disk | 20 GB, deleted with the Pod |
| Network volume | None |

Stop before paying if the tax-inclusive checkout total is above $20.00. Stop the run if the hourly console total is materially above $0.896849, if the GPU is not an RTX 4090, or if the approved prerequisites are missing.

## 1. Before creating the Pod

1. Confirm written owner approval for the exact run. The YAML file must still be at `configs/gemma3-1b-lora-smoke.yaml` and must match the approved hash.
2. Confirm the 100-example pilot and 24-item evaluation set exist as translated, native-reviewed Luganda data and pass training validation. The English source draft exists in `data/source/pilot-v1/`; it is not approved training data.
3. Confirm written translator and reviewer consent, licence, compensation, attribution, withdrawal, and retention terms. The owner reports that native speakers are available; the formal records do not exist at the time of preparation.
4. Confirm the Hugging Face account has accepted the Gemma terms and can access the gated base. Do not use an unofficial mirror.
5. Read the Runpod checkout total, including sales tax and any card fee. Do not use a prepaid card. The prepaid-card minimum is $100.
6. Disable auto-pay. Set the low-balance alert to $4.00 remaining. Do not create a network volume or a deploy-when-available subscription.
7. Recheck Secure Cloud capacity and the hourly summary. Stop if an RTX 4090 is not available. Do not substitute a different GPU without a new owner decision.

## 2. Create the Pod

1. Select Secure Cloud, one RTX 4090 24 GB, and an available region.
2. Select the official PyTorch CUDA template. Record the exact image tag or digest.
3. Set container disk to 30 GB and volume disk to 20 GB. Do not attach a network volume.
4. Add a dedicated SSH public key. Do not expose Jupyter publicly if the managed proxy is sufficient.
5. Record the Pod ID, region, host, image, start time, and console hourly total in the run record.
6. Start the Pod. Confirm the console shows the approved GPU and storage before doing work.

## 3. Install the pinned environment

Use Python 3.11. Do not install these packages into the local Windows environment. Do not let pip choose an unpinned Torch, Transformers, TRL, Datasets, or PEFT version. If `python3.11` is not present in the image, stop and choose an image that provides it. Do not silently use Python 3.12 or 3.13; the config pins 3.11 and `check_runtime` rejects other versions.

```bash
python3.11 --version
python3.11 -m venv /workspace/luganda-venv
source /workspace/luganda-venv/bin/activate
python -m pip --version
python -m pip install -r /workspace/LugandaGPT/requirements-training.txt
```

The requirements file pins direct dependencies only. It has not been resolved or tested on Linux. Record the full resolved set:

```bash
python -m pip freeze > /workspace/pip-freeze.txt
python - <<'PY'
import torch, transformers, peft, accelerate, bitsandbytes, datasets, trl
import huggingface_hub, tokenizers, safetensors, sentencepiece
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
print("transformers", transformers.__version__)
print("peft", peft.__version__)
print("accelerate", accelerate.__version__)
print("bitsandbytes", bitsandbytes.__version__)
print("datasets", datasets.__version__)
print("trl", trl.__version__)
print("huggingface_hub", huggingface_hub.__version__)
print("tokenizers", tokenizers.__version__)
print("safetensors", safetensors.__version__)
print("sentencepiece", sentencepiece.__version__)
PY
```

Stop if any direct version differs from `configs/gemma3-1b-lora-smoke.yaml`. Do not patch around a version mismatch on the Pod.

## 4. Transfer code and protected data

1. Transfer `src/`, `configs/`, `tests/`, `requirements-training.txt`, the approved data files, and the provenance record.
2. Do not transfer the local virtual environment, `.git`, model weights, caches, credentials, or any unapproved data.
3. Do not clone an uncommitted public branch. The working tree is not committed.
4. Verify the SHA-256 of every transferred file against a local manifest.
5. Set `HF_TOKEN` through a Runpod secret or an interactive shell read. Never write it into the repository, YAML, command history, notebook, or log.

## 5. Model and tokenizer setup

Only after the owner approves the model download:

```bash
mkdir -p /workspace/models
hf download google/gemma-3-1b-it \
  --revision dcc83ea841ab6100d6b47a070329e1ba4cf78752 \
  --local-dir /workspace/models/gemma-3-1b-it
```

The download must use the gated Hugging Face account. If access fails, stop. Do not use a mirror.

Run from the project root:

```bash
export PYTHONPATH=/workspace/LugandaGPT/src
python -m training hash /workspace/models/gemma-3-1b-it/tokenizer_config.json
python -m training hash /workspace/models/gemma-3-1b-it/generation_config.json
```

The tokenizer check is implemented in `src/training/modeling.py`. It verifies:

- the base chat template SHA-256;
- pad token id 0;
- BOS token id 2;
- EOS token ids 1 and 106;
- the `<end_of_turn>` id 106;
- the tokenizer vocabulary length, reported for comparison with the model pin.

No model weights are loaded by the tokenizer check.

## 6. Local and Pod validation sequence

On the Pod, with the approved config and data in place:

```bash
python -m training validate-config configs/gemma3-1b-lora-smoke.yaml
python -m training validate-data configs/gemma3-1b-lora-smoke.yaml \
  --project-root . \
  --tokenizer-path /workspace/models/gemma-3-1b-it \
  --require-tokenizer
python -m training preflight configs/gemma3-1b-lora-smoke.yaml \
  --project-root . \
  --model-path /workspace/models/gemma-3-1b-it
```

`preflight` requires the config to be approved for execution and requires CUDA. If it returns `preflight_passed_except_model_load_and_one_step`, the base load, bitsandbytes layer, one-step backward pass, and adapter reload are still pending. Do not describe preflight as a full GPU test.

The training command performs the following before the optimizer loop:

1. authorization and exact Pod metadata check;
2. Python, package, CUDA, BF16, and RTX 4090 check;
3. tokenizer pin check;
4. complete data, provenance, review, deduplication, and tokenizer validation;
5. 4-bit base load and pin check;
6. one forward and backward pass with a finite-loss and gradient check.

Stop if any step fails. Do not set `execution_authorized` or `authorization_status` without written owner approval.

## 7. Training command and monitoring

```bash
python -m training train configs/gemma3-1b-lora-smoke.yaml \
  --project-root . \
  --model-path /workspace/models/gemma-3-1b-it \
  --output-dir /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM \
  --pod-id "$RUNPOD_POD_ID" \
  --region "<console region>" \
  --host "<console host>" \
  --image "<exact image tag or digest>"
```

Use the actual values, not placeholders. Checkpoint resume is deliberately disabled for this first gate. A retry is a new attempt in a new run directory, with the failure recorded.

Monitor the console and the log. Stop on any of these:

- runtime reaches 6 hours;
- credits consumed reach $8;
- balance falls below the $4 alert;
- loss is NaN or non-finite;
- CUDA out of memory is not resolved by the pre-approved fallback;
- a data, tokenizer, revision, or package check fails;
- the process hangs for more than 10 minutes;
- the operator cannot monitor the run.

The runner writes a run manifest, config snapshot, environment freeze, GPU and host records, code hashes, dataset hashes, training arguments, logs, checkpoints, and a final adapter. It does not merge the adapter into the base.

## 8. Inference

After a completed training run, with both the existing translation adapter and the saved new adapter available:

```bash
python -m training infer /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM/config.snapshot.yaml \
  --run-dir /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM \
  --new-adapter /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM/final_adapter \
  --existing-adapter /workspace/adapters/existing-translation-adapter \
  --project-root /workspace/LugandaGPT \
  --model-path /workspace/models/gemma-3-1b-it
```

Use the frozen `config.snapshot.yaml` from the completed run, not the working config. The inference command requires the snapshot hash to match the training manifest. If the working config changes after training, inference refuses it.

The inference command requires the training run to be completed, checks that the supplied new adapter matches the run's saved adapter, checks current config and dataset hashes, and runs the base, existing adapter, and new adapter on the held-out and evaluation prompts. It writes raw outputs, a blind review packet, and a separate key. It does not score the outputs and does not create native reviews.

## 9. Export and cleanup

1. Run `python -m training verify-artifacts <run-dir>` on the Pod.
2. Export the adapter, tokenizer, run manifest, config snapshot, environment freeze, logs, checkpoint manifest, raw outputs, and checksums.
3. Copy the export to local or approved storage. Open at least one adapter file and one log locally.
4. Verify the copied run directory again with `verify-artifacts`.
5. Terminate the Pod. Do not stop it and leave the volume billed.
6. Confirm the Pod, volume disk, and any network volume are gone.
7. Read the final billing page. Record the final credit charge, final cash charge, remaining credit, sales tax, and payment fee:

```bash
python -m training record-cost <run-dir> \
  --final-credit-charge <actual credits consumed> \
  --final-cash-charge <actual cash paid> \
  --remaining-credit <actual remaining credit> \
  --sales-tax <actual tax> \
  --payment-fee <actual fee> \
  --notes "Final Runpod billing after termination"
```

The cost record must normally remain at or below $20 cash and $8 of consumed credits. The tool records the actual values even when a limit is exceeded, sets `within_caps=false`, and lists the breach. If that happens, stop, preserve the record, and report the breach. Do not hide it by editing the record.

8. Remove the local copy of the Hugging Face token from the Pod before termination where practical.
9. Do not add a completed experiment record to `docs/EXPERIMENT_LOG.md` unless a run actually completed.

## 10. Failure handling

| Failure | Action |
|---|---|
| No RTX 4090 capacity | Stop. Do not substitute. |
| Checkout total above $20 | Do not pay. |
| Price above the approved hourly basis | Recalculate and stop if the caps are not met. |
| Gated model access fails | Stop. Do not use a mirror. |
| Dependency mismatch | Stop. Do not mix versions. |
| One-step check OOM | Stop. A pre-approved max-length reduction to 768 is possible only with a recorded config change and fresh preflight. |
| Loss is non-finite | Stop. Do not continue training. |
| Data validation fails | Stop. Do not patch data on the Pod. |
| Adapter reload or inference fails | Stop. Preserve logs and terminate. |
| Cost or time cap reached | Stop, export if possible, then terminate. |
| Operator must leave | Do not start, or terminate. |

## 11. Current blockers

- No Runpod account, payment method, credits, or tax-inclusive checkout total.
- No verified live RTX 4090 capacity.
- The English source draft exists, but no Luganda translations or second-speaker native reviews exist.
- No Luganda provenance record, formal consent, compensation schedule, licence, or retention terms exist.
- No GPU runtime check, bitsandbytes training test, one-step test, VRAM measurement, or adapter reload.
- No final Runpod billing record because no Pod has run.

The required status remains `BLOCKED: OWNER DECISION OR PREREQUISITE REQUIRED`.
