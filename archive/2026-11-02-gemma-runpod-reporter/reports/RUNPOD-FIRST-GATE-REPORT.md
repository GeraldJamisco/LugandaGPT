# Runpod First-Gate Preparation Report: Gemma 3 1B LoRA Smoke Test

**Status:** BLOCKED: OWNER DECISION OR PREREQUISITE REQUIRED

**Date:** 2026-10-21

**Prepared by:** DeepSeek, engineering agent

**Owner:** Project Director

**Approval reference:** `docs/DECISIONS.md`, D-008. The full 1,000 to 1,500 example run is not approved.

**Scope:** Prepare the first bounded fine-tuning gate for LugandaGPT using Approach B, a fresh LoRA adapter from the pinned `google/gemma-3-1b-it` base, on a Runpod RTX 4090. The report covers provider price and availability, account and payment requirements, full expected cost, the $20 cap, instance and storage configuration, training configuration, data and translator readiness, smoke-test and cleanup procedure, evaluation, risks, files changed, and explicit status.

**Non-claims:** No Runpod account was created. No deposit was made. No GPU was launched. No model or dataset was downloaded. No training, inference, paid API call, commit, or push was performed for this report. No translated Luganda pilot, evaluation item, translator agreement, consent record, native review, benchmark score, or model-quality claim exists. An English source draft for the 100-example pilot and 24-item evaluation now exists in `data/source/pilot-v1/`; it is not Luganda training data and is not approved for training. The prior 99 percent judgment is an informal review of one published translation example, not a benchmark score. Public prices and policies were checked, but live GPU capacity and the tax-inclusive checkout total were not. The existing adapter remains a translation-only baseline and is not the V1 conversational model. The training pipeline and inference helpers have been implemented; local tests cover config, synthetic data, the pinned tokenizer, artifacts, source-draft validation, and inference helpers. No GPU check, 4-bit training test, model load, VRAM measurement, adapter reload, or inference pass has run.

---

## Evidence labels

- **Verified:** read directly from a current public page, a public catalog response, a pinned local file, or an approved project document.
- **Source claim:** published by a provider or model owner. It has not been independently reproduced unless stated.
- **Estimate:** arithmetic or engineering judgment. It is not a measurement.
- **Proposal:** a recommended action that requires owner approval.
- **Blocked / unverified:** cannot be confirmed with the access available, or the prerequisite does not exist.

A verified price is not a quote. A catalog entry is not live capacity. A licence tag is not a legal opinion. A completed smoke test would not be a benchmark score.

---

## A. Runpod RTX 4090 price and availability

### A.1 Current public price

**Verified on 2026-10-21.** The Runpod pricing page is marked updated 2026-10-08 and lists the RTX 4090 with 24 GB of VRAM at:

| Cloud | GPU | VRAM | Listed on-demand price |
|---|---|---:|---:|
| Secure Cloud | NVIDIA GeForce RTX 4090 | 24 GB | $0.89 per hour |
| Community Cloud | NVIDIA GeForce RTX 4090 | 24 GB | $0.34 per hour |

The page's structured data contains the same values: `lowPrice: 0.34`, `highPrice: 0.89`, with separate Community Cloud and Secure Cloud offers [R1]. The owner's stated $0.89 per hour is therefore confirmed for Secure Cloud at the time of this check. Community Cloud is cheaper but has less predictable host quality and capacity, so this plan keeps Secure Cloud, which is the conservative basis used in the feasibility report.

The price is a public list price, not a reservation or a quote. It can change before launch. The launch operator must recheck the console summary and stop if the selected configuration exceeds the approved basis.

### A.2 Live availability

**Blocked / unverified.** Runpod's deployment guide says the console has an **Available** tab that shows only GPUs with capacity at that moment, and an **All** tab that includes out-of-capacity GPUs [R2]. No project Runpod account was created or made available to the agent, so that tab could not be read.

A public GraphQL catalog query on 2026-10-21 returned an `NVIDIA GeForce RTX 4090` entry with `memoryInGb: 24`, `secureCloud: true`, and `communityCloud: true`. This confirms that the GPU type is listed for both tiers. It does not confirm stock. The authenticated catalog API returned HTTP 401 without a token [R3].

**Consequence:** The plan cannot claim that an RTX 4090 is available now. The owner or an authorized operator must check the console at launch. If the GPU is out of capacity, the correct action is to stop and ask for a decision. Do not silently substitute an L4, A100, Community Cloud host, or another GPU. Do not use the "Deploy when available" subscription for this gate because it can start a paid Pod later without an operator present.

### A.3 Region and host

The public price is not a capacity guarantee in a specific region. The report does not select a region. At launch, record the region, data center, host, GPU name, driver, and actual hourly summary. Because this plan does not use a network volume, there is no data-center lock-in.

---

## B. Account, payment, deposit, minimum balance, fees, and taxes

### B.1 Account requirements

| Requirement | Verified position | Implication |
|---|---|---|
| Account | Create an account, verify the email address, and set up two-factor authentication (recommended) [R2]. | The owner must create or prepare a secured account. The agent must not create it, receive credentials, or store them. |
| Payment method | A payment method and credits are requested at deploy time if not already set up [R2]. | Account setup and payment are owner actions. |
| API access | API v2 requires a bearer token. No token exists [R3]. | The agent cannot check live capacity or manage a Pod through the API. |
| SSH | An SSH public key is needed for terminal access [R2]. | Use a dedicated key for this run. Do not reuse a personal key without owner approval. |

### B.2 Credits, deposits, and minimum balance

Runpod uses prepaid credits. Credits are deducted as resources run. The billing page states:

- New users can start with as little as **$10**.
- To deploy a new Pod, the account must have at least **one hour's worth of credits** for the selected configuration.
- Credits are **non-refundable** and cannot be withdrawn.
- If the balance reaches $0, running Pods are stopped or terminated, depending on whether a network volume is attached.
- Billing runs every 5 minutes, and charges are deducted continuously [R4].

For this configuration, one hour's credits are about $0.90. The practical minimum for the gate is therefore the $10 starter amount, unless an existing account already has sufficient credits. The $10 purchase must be treated as a cash purchase, not as a $10 compute budget, because sales tax is added on top.

### B.3 Payment methods and the prepaid-card trap

| Method | Verified position | Fit for this gate |
|---|---|---|
| Standard credit or debit card | Visa, Mastercard, American Express, and other Stripe-supported cards [R4]. | Proposed. Use a card whose issuer does not add an unknown foreign-transaction fee. |
| Prepaid card | Runpod and Stripe recommend a deposit of at least **$100** per transaction for prepaid cards [R4][R5]. | **Do not use.** A $100 minimum would exceed the $20 cap before any compute. |
| Cryptocurrency | Accepted through integrated processors. Complete any required KYC before the first crypto payment [R4]. | Not proposed. It adds identity verification and asset-price complexity. |
| Business invoicing | Available for transactions over $5,000 [R4]. | Not applicable. |

### B.4 Sales tax

Runpod charges digital sales tax on credit purchases in some jurisdictions. The rate depends on the billing address and the payment method. Tax is charged **on top of** the credit purchase and does **not** reduce the credits received. For example, at an 18 percent rate, a $100 credit purchase costs $118 and still provides $100 in credits [R6].

**Consequence:** A $10 credit purchase can cost more than $10. The owner must read the checkout total, not only the credit amount. The total charge including tax and any card fee must be at or below $20. If the checkout total is above $20, do not pay. If the owner has a valid tax ID, it may affect the rate, but this report does not assume an exemption [R7].

The tax rate for the owner's billing address is **not known**. This is a material unknown. The budget plan below is deliberately set so that a $10 credit purchase remains under $20 for any tax rate below 100 percent. Real tax rates are far below that, but the checkout total is the controlling number.

### B.5 Spending limit, auto-pay, and low-balance alerts

Runpod accounts have a default spend limit of **$80 per hour** across all resources. The limit can rise with account history [R4]. This is not a $20 budget control and must not be treated as one.

The account must be configured as follows before launch:

- **Auto-pay off.** Auto-pay can add credits automatically and break the cap.
- **Low-balance alert on.** Set the alert at a level that leaves time to stop the Pod. This plan proposes $4 remaining.
- **No reserved capacity or subscription.** Use on-demand only. Do not buy a savings plan, reserved instance, or add-on.
- **No extra credits.** Buy only the approved $10 amount, and only after the checkout total is at or below $20.
- **No unattended deployment.** A "deploy when available" subscription can start a Pod when capacity appears. Do not use it.
- **Manual stop.** The operator watches the Pod and the balance. The hard stop is 6 hours or $8 of credits consumed, whichever comes first.
- **One retry maximum.** A failed attempt may be retried once only within the same runtime and credit caps.

### B.6 Account status

**No account was created and no deposit was made.** The agent did not enter payment details, accept terms on the owner's behalf, or store credentials. Account creation, identity verification, payment, and tax acceptance are owner actions.

---

## C. Full expected cost and the $20 cap

### C.1 Proposed instance cost

The estimate uses one Secure Cloud RTX 4090, a 30 GB container disk, and a 20 GB volume disk. The volume is deleted when the Pod is terminated.

| Component | Basis | Hourly estimate |
|---|---|---:|
| GPU | $0.89 per hour | $0.890000 |
| Container disk | 30 GB at $0.10 per GB per month, divided by 730 hours | $0.004110 |
| Volume disk, running | 20 GB at $0.10 per GB per month, divided by 730 hours | $0.002740 |
| **Total** | | **$0.896849** |

Rounded planning values:

| Runtime | GPU and storage estimate |
|---:|---:|
| 2 hours | $1.79 |
| 4 hours | $3.59 |
| 6 hours | $5.38 |
| 8 hours | $7.17 |
| 12 hours | $10.76 |

These are estimates from the public list price. They exclude sales tax on the credit purchase, card issuer fees, and any price change. Storage is prorated per second. There is no charge for data transfer according to the billing page [R4].

### C.2 Cash cost with tax

The plan proposes a **$10 credit purchase**, not a $20 purchase. At the tax rates below, the cash charge is:

| Tax rate | Charge for $10 credits | Credits received | Under $20 cap |
|---:|---:|---:|---|
| 0 percent | $10.00 | $10.00 | Yes |
| 10 percent | $11.00 | $10.00 | Yes |
| 18 percent | $11.80 | $10.00 | Yes |
| 20 percent | $12.00 | $10.00 | Yes |
| 30 percent | $13.00 | $10.00 | Yes |
| 50 percent | $15.00 | $10.00 | Yes |

The exact rate is unknown. The owner must stop if the checkout total exceeds $20. A $10 purchase leaves unused credits if the run spends only about $5.38. Credits are non-refundable, but the unused balance remains available for a later approved run. Buying $20 of credits would risk a tax-inclusive charge above $20 and is not proposed.

### C.3 Does the experiment fit within $20?

**Conditional yes, not confirmed.** Under the public price, one 6-hour attempt costs about $5.38 in credits. A $10 credit purchase would reach $20 only at a 100 percent tax rate. At the rates shown above, it costs $11 to $13, leaving several dollars of the cap unused. The run is therefore expected to fit with a wide margin for a single attempt.

The $5.38 figure is for one attempt. A retry is a new attempt in a new run directory and must fit within the same $8 credit stop and $20 cash cap. It does not reset either limit. If a retry would need more credits, stop and obtain a new owner decision instead of enabling auto-pay.

The fit is not confirmed because:

1. Live RTX 4090 capacity is unverified.
2. The tax-inclusive checkout total is unknown.
3. The exact container and volume sizes at checkout may differ.
4. The training code is prepared, but the Linux GPU environment and 4-bit path have not been tested.
5. A failed run could consume time without producing an adapter.

If the console shows a price above $0.89 per hour, recalculate before deploying. At $8 of credits consumed, the maximum runtime at the public price is about 8.9 hours, so the 6-hour cap is still safe. If the price rises above about $1.33 per hour, a 6-hour run would exceed $8 and the runtime cap must be shortened.

### C.4 What the $20 does not cover

The $20 cap covers compute and storage only. It does not cover:

- native-speaker authoring or review;
- translator and reviewer compensation;
- travel, connectivity, or administration;
- a full 1,000 to 1,500 example training run;
- benchmark construction or release work.

No teacher or translator compensation rate or budget is approved. Translation and review preparation can proceed, but the training run cannot begin until the owner records those terms. Native review is likely to cost more than the GPU time.

Google Cloud remains on hold because of the mandatory $30 prepayment. No Google Cloud payment was made. The Runpod gate does not change that decision.

---

## D. Proposed Runpod instance and storage plan

### D.1 Instance

| Setting | Proposed value | Reason |
|---|---|---|
| Provider | Runpod | Owner-selected provider. |
| Cloud | Secure Cloud | More predictable host quality than Community Cloud for a short supervised run. |
| GPU | 1 x NVIDIA GeForce RTX 4090, 24 GB | Fits a 4-bit LoRA run on a 1B model with headroom. |
| CPU and RAM | Record the actual template allocation at launch | The 1B QLoRA run does not need a large CPU tier. Do not guess in the record. |
| Container disk | 30 GB | Holds the operating system, PyTorch image, CUDA libraries, base model, and environment. |
| Volume disk | 20 GB, mounted at `/workspace` | Holds checkpoints, logs, and exports across a restart. Deleted on termination. |
| Network volume | None | Avoids persistent storage charges and data-center lock-in. |
| Image | Official PyTorch CUDA template, exact tag recorded at launch | Provides a CUDA-enabled PyTorch base. Do not use an unverified community image. |
| Python | 3.11, proposed | Broad compatibility with the pinned libraries. |
| Public ports | None beyond the platform's managed access | Reduce exposure. Use SSH keys and the managed Jupyter proxy. |
| Volume encryption | Use if available and if teacher data is sensitive | Container disks and network volumes are not encrypted [R8]. |

The vCPU and RAM values are not asserted because the Runpod template allocation can vary. The launch record must capture them.

### D.2 Why no network volume

A volume disk survives a stop or restart and is deleted when the Pod is terminated. A network volume survives independently and continues to bill at $0.07 per GB per month [R8]. For a short smoke test, a network volume adds a persistent resource that can be forgotten. The plan uses a volume disk, exports artifacts, then terminates the Pod.

### D.3 Stop versus terminate

Stopping a Pod ends GPU billing but keeps the volume disk at $0.20 per GB per month. A 20 GB stopped volume is about $4.00 per month, prorated. That is small but persistent, and it is not a safe cleanup state. The required end state is:

1. Export the adapter, tokenizer, logs, raw outputs, environment freeze, and checksums.
2. Verify the exports can be read locally.
3. **Terminate** the Pod. Do not leave it stopped.
4. Confirm the Pod and volume are gone.
5. Confirm no network volume exists.
6. Recheck the billing page and record the final charge.

If the Pod fails before exports are complete, capture the console log and any accessible files, then terminate. Do not leave a failed Pod running while deciding what to do.

### D.4 Access and secrets

- Use a dedicated SSH key for the run.
- Store the Hugging Face token as an environment variable or Runpod secret. Never write it into the repository, config, shell history, notebook, or logs.
- The base model is gated. The Hugging Face account must have accepted the Gemma terms, and the token must have access. If download fails with an authorization error, stop. Do not use an unofficial mirror.
- Do not expose Jupyter or SSH publicly beyond the managed access path.
- Remove the token from the Pod before termination where practical. Termination removes the container and volume.

---

## E. Reproducible training configuration and dependencies

The machine-readable configuration is `configs/gemma3-1b-lora-smoke.yaml`. It records the intended experiment. It is not evidence that the experiment ran.

### E.1 Base model and tokenizer

| Item | Value |
|---|---|
| Base model | `google/gemma-3-1b-it` |
| Base revision | `dcc83ea841ab6100d6b47a070329e1ba4cf78752` |
| Parameters | 999,885,952 |
| Hidden size | 1,152 |
| Layers | 26 |
| Vocabulary | 262,144 |
| Context limit | 32,768 positions |
| Weight dtype | BF16, about 2.0 GB |
| Tokenizer revision | Same as base |
| Chat template SHA-256 | `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4` |
| EOS tokens | `<eos>` id 1 and `<end_of_turn>` id 106 in the generation config |

These values match the pinned local files and the prior feasibility record [R9]. The tokenizer hash is verified. The chat template is the base template. It is not modified.

### E.2 Fresh LoRA adapter

| Setting | Proposed value |
|---|---|
| Adapter | New LoRA, not a continuation of the existing adapter |
| Task type | `CAUSAL_LM` |
| Rank | 16 |
| Alpha | 32 |
| Dropout | 0.05 |
| Bias | None |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| DoRA / RS-LoRA | Disabled |
| Expected trainable parameters | About 13,045,760, based on the same target set |
| Existing adapter revision | `5d0f24b80a09f582708ff397c989331d7d7b536f` |
| Existing adapter role | Retained only as a translation baseline |

The rank and target set are a proposal for the gate. They match the existing adapter's capacity, which makes the new adapter comparable, but they are not a final architecture decision. D-005 remains open.

The existing adapter is not the V1 candidate. In the prior retest it produced a Luganda translation but answered a Luganda conversation instruction in English. Its public evaluation file has 88 English-to-Luganda and 12 Luganda-to-English examples, with no conversation examples. It remains useful only as a translation baseline and a regression reference.

### E.3 Quantization and precision

| Setting | Proposed value |
|---|---|
| Load in 4-bit | Yes |
| Quantization type | NF4 |
| Double quantization | Yes |
| Compute dtype | BF16 |
| Quant storage | `uint8` |
| FP16 | No |
| TF32 | No, because the training path uses BF16 |

The RTX 4090 is an Ada-generation GPU with BF16 support and 24 GB of VRAM. A 1B model in 4-bit NF4 is roughly 0.6 to 0.8 GB of weights. The adapter, optimizer state, activations at 1,024 tokens, and gradient checkpointing should fit well within 24 GB. This is an estimate, not a measurement. Peak VRAM must be recorded.

### E.4 Loss masking and chat-template compatibility

The base Gemma 3 chat template does **not** contain `{% generation %}` markers. TRL's `assistant_only_loss=True` path expects a chat template that supports assistant-token masks. Setting that flag against the base template would fail or produce the wrong mask [R10].

The proposed path avoids changing the base template:

- Store each pilot example as `messages`.
- For training, expand each assistant turn into a conversational prompt-completion record.
- `prompt` is the list of preceding messages.
- `completion` is the assistant message for that turn.
- Use `completion_only_loss=true` and `assistant_only_loss=false`.
- Do not pack sequences.
- Do not alter the base chat template.

This trains every assistant turn while keeping the rendered format identical to the base template. It also preserves multi-turn context. TRL 0.20.0 is the proposed direct pin and supports this path in its documented API. The pinned combination has not been installed or tested on Linux, so runtime compatibility remains a prerequisite, not a claim.

### E.5 Training hyperparameters

| Parameter | Proposed value | Note |
|---|---|---|
| Max sequence length | 1,024 | Covers the pilot's short conversations. |
| Per-device train batch | 1 | Memory-safe starting point. |
| Gradient accumulation | 8 | Effective batch 8. |
| Epochs | 3 | Smoke-test scale only. |
| Max optimizer steps | 30 | Hard cap; takes precedence over epochs. |
| Learning rate | 2e-4 | Same order as the earlier adapter. |
| Scheduler | Cosine | With 5 percent warmup. |
| Warmup ratio | 0.05 | Proposal. |
| Weight decay | 0.01 | Proposal. |
| Max gradient norm | 0.3 | Matches the earlier adapter record. |
| Optimizer | `paged_adamw_8bit` | Bitsandbytes CUDA optimizer. |
| Gradient checkpointing | Yes, `use_reentrant=false` | Memory reduction with PEFT. |
| Packing | No | Preserve turn boundaries. |
| Eval strategy | Steps, every 10 | Validation loss only. |
| Save strategy | Steps, every 10 | Keep 3 checkpoints. |
| Logging | Every step | Record loss, learning rate, grad norm, throughput. |
| Seed | 42 | Record and do not change without recording. |
| Report to | None | No external experiment tracker. |
| Push to Hub | No | No publication. |

The run is a pipeline and memory test, not a quality run. Thirty optimizer steps on 70 training examples cannot establish useful Luganda ability. The sequence length, batch size, learning rate, and optimizer are proposals for the gate. They are not an approved final training strategy and require owner review before execution.

### E.6 Dependency requirements

The exact direct pins are in `requirements-training.txt`. They are proposed, not a resolved lock file. No package from that file has been installed on Linux or on a GPU host.

| Component | Local state | Proposed Runpod state | Status |
|---|---|---|---|
| Python | 3.13.14 | 3.11 | Runpod image version must be recorded. |
| PyTorch | 2.7.1+cpu | 2.7.1+cu126 | GPU build not tested. |
| Transformers | 4.53.2 | 4.53.2 | Local tokenizer use verified; training path not tested. |
| PEFT | 0.18.1 | 0.18.1 | Local configuration construction tested; training path not tested. |
| Accelerate | 1.8.1 | 1.8.1 | Installed locally; not exercised for training. |
| Bitsandbytes | 0.50.2 | 0.50.2 | Linux CUDA training not tested. |
| Datasets | Not installed | 5.0.1 | Exact release exists on PyPI; runtime compatibility untested. |
| TRL | Not installed | 0.20.0 | Exact release exists on PyPI; runtime compatibility untested. |
| Hugging Face Hub | 0.34.3 | 0.34.3 | Local metadata version matches; runtime integration with Datasets and TRL untested. |
| Tokenizers | 0.21.4 | 0.21.4 | Local version matches the pin; tokenizer checks pass. |
| Safetensors | 0.8.0 | 0.8.0 | Local adapter inspection tested without model weights. |
| SentencePiece | 0.2.2 | 0.2.2 | Local version matches the pin; runtime use untested. |
| CUDA and driver | Not applicable locally | Record actual | Unverified. |

The requirements file pins direct dependencies only. Transitive versions will be selected on the Pod and must be frozen with `pip freeze` and inspected before preflight. Do not let pip choose an unpinned Torch, Transformers, TRL, Datasets, or PEFT version. Do not install a different direct version on the Pod without recording the change and stopping for approval.

### E.7 Environment compatibility checks before training

The following must pass on the Pod before any training step:

1. `nvidia-smi` shows the RTX 4090, 24 GB, and a working driver.
2. `torch.cuda.is_available()` is true.
3. `torch.cuda.is_bf16_supported()` is true.
4. Bitsandbytes can load a 4-bit layer and run a forward pass.
5. The base model loads at the pinned revision with the expected parameter count.
6. The tokenizer chat template hash matches the recorded hash.
7. The tokenizer produces the expected EOS ids 1 and 106.
8. A sample conversation renders identically through the training path and the base template.
9. The prompt-completion conversion preserves every assistant turn and does not leak the held-out split.
10. The dataset schema, token lengths, deduplication, and contamination checks pass.
11. A one-step forward and backward pass completes without OOM.
12. The adapter saves and reloads in a fresh process.

If any check fails, stop. Do not start a full smoke-test run to "see what happens."

The non-GPU parts of this list are implemented and tested locally. Checks 1 through 5, 11, and 12 require the Pod. Check 7 was verified locally against the pinned tokenizer and must be repeated on the Pod. No 4-bit model load or backward pass was performed.

### E.8 Checkpoints and artifacts

The configuration includes a `run_record` block for the runtime, peak VRAM, final credit and cash charges, Pod identity, driver, CUDA, and log paths. Those fields stay null until a run actually happens.

The run must save and export:

- final LoRA adapter weights and `adapter_config.json`;
- tokenizer files, including the chat template;
- the exact resolved training configuration;
- `pip freeze` and the CUDA, driver, and GPU details;
- training log with loss, learning rate, gradient norm, throughput, and peak VRAM;
- validation loss at each evaluation;
- the list of checkpoints and their hashes;
- the dataset version, counts, split hashes, and provenance record;
- raw model outputs from the held-out and evaluation prompts;
- the cost record, including runtime and final charge;
- a run manifest with SHA-256 checksums.

Do not merge the adapter into the base model for this gate. The adapter is small and easier to inspect separately. Merging is a later decision.

### E.9 Reproducibility record

The repository has uncommitted work, and this task does not commit or push. The run record must therefore include:

- a manifest of the training code and config with SHA-256 hashes;
- the exact commands used;
- the resolved package versions;
- the base and tokenizer revisions;
- the dataset version and split hashes;
- the seed and any deviations from this configuration;
- the wall-clock start and end times;
- the GPU, driver, CUDA, and cuDNN versions;
- the actual region and host;
- the final cost.

A later reader must be able to tell what was run without relying on an uncommitted working tree.

### E.10 Training and inference implementation

The guarded implementation is in `src/training/`:

| File | Responsibility |
|---|---|
| `config.py` | Strict YAML loading, unknown and missing field rejection, duplicate-key rejection, secret scan, pins, budgets, authorization. |
| `constants.py` | Pinned base, tokenizer, LoRA, dependency, data, token, and cost values. |
| `pilot.py` | Pilot and evaluation schema, reference rules, review rules, audit coverage, composition. |
| `data.py` | Provenance, split hashes, review links, exact and 8-gram contamination, tokenizer limits, prompt-completion expansion. |
| `environment.py` | Python, package, CUDA, BF16, RTX 4090, and host evidence. |
| `modeling.py` | Pinned tokenizer and base checks, 4-bit NF4 load, LoRA, TRL SFT construction, one-step check, generation. |
| `runner.py` | Authorization-first preflight and training, runtime and credit guard, failure record, final adapter export. |
| `inference.py` | Base, existing-adapter, and new-adapter generation, run binding, raw outputs, blind packet, no scoring. |
| `artifacts.py` | Config snapshot, environment freeze, manifests, checksum inventory, verification, final cost record. |
| `cli.py` and `__main__.py` | `python -m training` commands. There is no authorization bypass flag. |

The implementation enforces:

1. Exact config structure, base and tokenizer pins, LoRA shape, hyperparameters, dataset counts, budget arithmetic, and secret rejection before execution.
2. Execution authorization, approved dataset version, complete data, signed consent, agreed compensation, resolved licences, approved reviews, split integrity, and contamination checks before any model load.
3. Python 3.11, exact direct packages, CUDA 12.6, BF16, and an RTX 4090 24 GB before training.
4. 4-bit NF4 load with BF16 compute, fresh LoRA, conversational prompt-completion records, `completion_only_loss=true`, and `assistant_only_loss=false`.
5. A one-step forward and backward pass with finite-loss and gradient checks before optimizer steps.
6. `max_steps=30`, a 6-hour guard, an $8 credit guard, non-finite-loss stop, and refusal to overwrite a non-empty run directory.
7. A final adapter and tokenizer save, checkpoint and artifact inventories, environment freeze, run manifest, and checksum verification.
8. Post-training inference that is bound to the completed run config, dataset hashes, and saved adapter. It writes raw outputs and a blind review packet. It does not score or create reviews.

Checkpoint resume is disabled for this first gate. The CLI rejects a resume request rather than continuing from an unverified checkpoint. A retry is a new run directory and a recorded attempt.

Local test results are recorded in section M. The GPU-dependent paths remain untested. No local test can substitute for the Pod preflight.

### E.11 Local preparation status

**Verified locally:**

- The current YAML passes structural validation and is correctly not authorized for execution.
- The synthetic 100-example pilot and 24-item evaluation fixture passes schema, provenance, split, audit, exact and 8-gram contamination, and tokenizer checks.
- The pinned tokenizer hash and id checks pass against the existing local tokenizer.
- The CLI, artifact manifests, checksum verification, final cost record, and inference helper checks pass their unit tests. The full run-bound inference path has not been executed.

**Not verified:**

- Linux Python 3.11 runtime compatibility.
- `datasets` 5.0.1, `trl` 0.20.0, `huggingface_hub` 0.34.3, or `sentencepiece` 0.2.2 in the pinned combination.
- The base model load at the pinned revision on a GPU.
- The 4-bit model load, TRL SFT construction, one-step backward pass, VRAM measurement, adapter save, adapter reload, and generation.
- The exact trainable parameter count from an adapter produced by training.
- Peak VRAM, training throughput, loss behavior, and adapter quality.
- Any inference output or native review.

---

## F. Initial 100-example data pilot specification

### F.1 Status

**Blocked for training.** The English source draft now exists in `data/source/pilot-v1/`, with 100 pilot items and 24 separate evaluation items. No Luganda translation, second-speaker native review, formal consent, compensation record, licence, provenance record, or training approval exists. This section defines the training-data specification. The English draft does not satisfy it and must not be copied into the Luganda training paths.

The exact field rules, evaluation schema, provenance shape, review rules, hash recording, and validation commands are in `docs/PILOT-DATA-SPECIFICATION.md`. The source counts, translation workbook, and owner-review status are in `reports/ENGLISH-SOURCE-PILOT-REPORT.md`. That document is the operational companion to this section.

### F.2 Composition

The pilot has 100 examples across six capabilities. The counts are authoring targets, not independent labels. One example may exercise more than one capability, but each example has one primary label.

| Capability | Count | Primary response form |
|---|---:|---|
| Formal comprehension | 17 | Luganda passage plus a question or summary, answered in Luganda. |
| Formal generation | 17 | Formal Luganda paragraph or short essay from an instruction. |
| Rewriting into formal Luganda | 17 | Source text rewritten in formal Luganda with meaning preserved. |
| Question answering | 17 | Luganda question answered in Luganda, including unanswerable cases. |
| Instruction following | 16 | Constrained task with language, length, format, or tone requirements. |
| Short conversation | 16 | Two to four turn dialogue with a context-dependent follow-up. |
| **Total** | **100** | |

At least 30 examples should require a response of more than one sentence. At least 12 should test appropriate uncertainty or an unanswerable question. At least 10 should include a constraint that a model could easily violate, such as "answer in Luganda only" or "use no more than three sentences." At least 8 conversations should include a follow-up that cannot be answered without the earlier turn.

### F.3 Splits

The 100 examples are split by example or conversation, never by random sentence, into:

| Split | Count | Use |
|---|---:|---|
| Train | 70 | Smoke-test training only. |
| Validation | 15 | Checkpoint and loss monitoring only. |
| Held-out | 15 | Memorization and overfitting check only. |
| **Total** | **100** | |

The held-out split is not used for prompt tuning, few-shot examples, checkpoint selection, or training. It is too small for a quality claim. It is a leakage check. The 70 training examples are within the authorized 50 to 100 example smoke-test range.

The separate evaluation set is 24 items, four per capability. It is authored and reviewed separately. It must not overlap the 100 pilot items. The 24-item set is a directional feasibility screen, not a benchmark. The approved benchmark specification is not modified and no benchmark version is created.

### F.4 Capability definitions and expected response characteristics

| Capability | Prompt characteristics | Expected response characteristics | Rejection examples |
|---|---|---|---|
| Formal comprehension | A Luganda passage of 3 to 8 sentences and a question or summary instruction. | Luganda response; correct use of the passage; formal register; no invented facts; concise citation of the relevant idea. | English answer; ignores the passage; invents a detail; wrong register. |
| Formal generation | A formal Luganda instruction such as a short explanation, announcement, or essay. | Formal Luganda; coherent structure; 80 to 200 words unless constrained; appropriate connectives; no unexplained English; culturally appropriate. | Translationese; English paragraph; unsupported factual claims; incoherent structure. |
| Rewriting into formal Luganda | An English or informal Luganda source of 2 to 6 sentences and a rewrite instruction. | Formal Luganda; meaning preserved; no added or removed facts; natural grammar; consistent register. | Changes meaning; leaves English unchanged; adds advice not in the source; overly literal word order. |
| Question answering | A Luganda question, with or without a short context. Includes answerable, ambiguous, and unanswerable items. | Luganda answer; correct if answerable; explicit uncertainty or clarification if not; no fabricated facts; concise. | Confident false answer; English answer; ignores ambiguity; refuses an answerable question. |
| Instruction following | A Luganda instruction with explicit constraints: language, length, format, tone, or content. | All constraints satisfied; response in Luganda; no extra sections that violate format; accurate content. | Wrong language; too long; missing required format; ignores a constraint. |
| Short conversation | Two to four alternating turns. A follow-up depends on an earlier turn. | Luganda response; retains context; natural turn-taking; answers the follow-up; no English unless the user asks for it. | Repeats the first answer; loses context; switches to English; ignores the follow-up. |

The expected-response field is not a model answer. It is a compact rubric that a native reviewer can apply. A full reference answer is required where the task has a determinate answer. Open-ended generation may use a rubric and accepted alternatives instead.

### F.5 Required fields for every pilot example

| Field | Type | Required | Rule |
|---|---|---|---|
| `pilot_id` | string | Yes | Unique, for example `P-001`. |
| `capability` | enum | Yes | One of the six labels in F.2. |
| `messages` | array | Yes | Alternating `user` and `assistant` messages. At least one of each. No system message unless approved. |
| `language` | enum | Yes | `lg` for Luganda, `lg-en` for approved mixed language. The pilot default is `lg`. |
| `register` | enum | Yes | `formal`, `everyday`, or `mixed`. The first pilot targets formal and everyday. |
| `expected_response` | object | Yes | Includes `must_include`, `must_not_include`, `max_words`, `format`, and `uncertainty_behavior`. |
| `reference_answer` | string or null | Conditional | Required for determinate tasks. Null only with a rubric and native approval. |
| `reference_status` | enum | Yes | `authored`, `reviewed`, or `not_required`. |
| `accepted_alternatives` | array | Conditional | Native-approved paraphrases for determinate answers. |
| `author_id` | string | Yes | Pseudonymous teacher ID. No real name in the data file. |
| `reviewers` | array | Yes | Reviewer ID, role, date, decision, and notes. |
| `review_status` | enum | Yes | `draft`, `ambiguity_checked`, `native_reviewed`, `approved`, or `excluded`. |
| `source` | enum | Yes | `teacher_authored`, `adapted`, or `project_original`. No model-generated gold. |
| `source_notes` | string | Yes | What was adapted and from where, or "original". |
| `licence` | string | Yes | Agreement or licence reference. `pending` is not trainable. |
| `consent_ref` | string | Yes | Consent record reference. `pending` is not trainable. |
| `pii_check` | enum | Yes | `none`, `redacted`, or `needs_review`. |
| `contamination_notes` | string | Yes | Exact, 8-gram, and manual checks against evaluation and benchmark items. |
| `validation` | object | Yes | Results of the checks in F.6. |
| `split` | enum | Yes | `train`, `validation`, or `heldout`, matching the file. Excluded records stay out of all three files. |
| `notes` | string | No | Ambiguity, adjudication, or reviewer comment. |

**Schema skeleton (placeholders, not training data):**

```json
{
  "pilot_id": "P-001",
  "capability": "formal_comprehension",
  "messages": [
    {"role": "user", "content": "<Luganda prompt>"},
    {"role": "assistant", "content": "<native-authored Luganda response>"}
  ],
  "language": "lg",
  "register": "formal",
  "expected_response": {
    "must_include": ["<required idea>"],
    "must_not_include": ["<prohibited content>"],
    "max_words": 120,
    "format": "paragraph",
    "uncertainty_behavior": "state_uncertainty_if_unanswerable"
  },
  "reference_answer": "<native-authored reference or null>",
  "reference_status": "reviewed",
  "accepted_alternatives": [],
  "author_id": "T-001",
  "reviewers": [
    {"reviewer_id": "R-001", "role": "independent_review", "date": "YYYY-MM-DD", "decision": "approved", "notes": ""}
  ],
  "review_status": "approved",
  "source": "teacher_authored",
  "source_notes": "Original",
  "licence": "<agreement reference>",
  "consent_ref": "<consent record reference>",
  "pii_check": "none",
  "contamination_notes": "Checked against feasibility and benchmark items on YYYY-MM-DD.",
  "validation": {
    "schema": true,
    "language": true,
    "instruction_response": true,
    "duplicate": true,
    "contamination": true,
    "pii": true,
    "token_length": true,
    "review_complete": true
  },
  "split": "train",
  "notes": ""
}
```

### F.6 Validation checks

| Check | Method | Blocking condition |
|---|---|---|
| Schema | Validate required fields, types, enums, unique IDs, alternating roles. | Any failure. |
| Language | Native review confirms the response is Luganda, with approved loanwords only. | Unexplained English or another language. |
| Instruction-response consistency | Compare the response to the prompt and the expected-response rubric. | Constraint missed or meaning changed. |
| Reference consistency | Compare determinate answers to the reference and accepted alternatives. | Wrong or unsupported answer. |
| Duplicate detection | Exact match and 8-gram overlap within the pilot and against evaluation items. | Duplicate or near-duplicate. |
| Contamination | Exact, 8-gram, and manual review against the 24-item evaluation set and any benchmark item. | Overlap or unverifiable source. |
| PII | Scan for names, phone numbers, addresses, account numbers, and sensitive personal details. | Unredacted personal data. |
| Token length | Tokenize with the pinned tokenizer. Limit to 512 tokens for non-conversation and 1,024 for conversation. | Over limit without approval. |
| Review completeness | Every train, validation, and held-out item has the required review record. | Missing review. |
| Split integrity | No conversation, source passage, or near-duplicate crosses splits. | Leakage. |
| Provenance | Licence, consent, source, and author record are present. | `pending` or missing. |

### F.7 Native-speaker review requirements

The pilot is not a benchmark, but it is training data. The following review standard is proposed:

- **Author:** a native Luganda speaker approved for the project writes the prompt and response, or corrects a draft.
- **Independent reviewer:** a second native speaker reviews every training example for meaning, grammar, naturalness, register, and instruction compliance.
- **Audit:** a third native speaker audits at least 10 percent of the training examples, selected before review, plus every item where the first two reviewers disagree.
- **Evaluation items:** two native reviewers per item, plus a third adjudicator for material disagreements. This is stricter than the training-example rule.
- **Calibration:** reviewers score 6 to 10 calibration items before the main review. Calibration items are not training or evaluation items. The purpose is to align judgments.
- **Blinding:** model outputs are presented without model identity and in randomized order. Authoring is not blinded.
- **Adjudication:** a material disagreement is resolved by a third native reviewer and recorded. Do not average away a disagreement about meaning or grammar.
- **No AI ground truth:** an AI judgment about Luganda quality is not a substitute for native review.
- **No invented approvals:** a review of a model output is not permission to use that output as training data. A pilot review is not approval of the full dataset.

### F.8 Translator participation, consent, compensation, and retention

The Project Director reports that native Luganda speakers are available and have agreed to collaborate. Working arrangements were discussed, and compensation is intended after the project earns its first dollar. No signed agreement, formal consent record, compensation amount or schedule, retention term, or translation licence is present in the repository. The following terms should be recorded before translated data is used for training:

| Topic | Requirement |
|---|---|
| Eligibility | Native speaker of the target Luganda variety, with the agreed orthography and register competence. |
| Consent | Written, informed consent to use the contributed text for training, evaluation, derivatives, and research reporting. Consent must be specific, not implied by participation. |
| Compensation | Owner-approved rate and payment schedule. No rate is approved here. Do not promise payment on the project's behalf. |
| Attribution | The translator and reviewer decide whether to be named in project records or remain pseudonymous. Public release needs separate approval. |
| Withdrawal | A defined process for withdrawing future use, subject to the agreed terms and applicable records. |
| Retention | Pseudonymous IDs, private storage, access control, and a defined retention period. Delete or anonymize at the end of the agreed period. |
| Personal data | Do not collect personal data that is not needed. Redact PII before the data enters the pilot. |
| Licensing | The project receives a written licence sufficient for training, evaluation, and derivatives. The terms must address redistribution and commercial use if those are possible. |
| Review | The contributor may review how their examples were edited. Disagreements go to adjudication, not silent editing. |

The consent record should state, at minimum:

- the purpose and scope of the project;
- the data the translator or reviewer will contribute and how it will be stored;
- that the data may be used for training, evaluation, and research reporting;
- whether derivatives and later model releases are included;
- the attribution choice and the privacy choice;
- the compensation amount, schedule, and payment method;
- the withdrawal process and its limits;
- the retention period and deletion process;
- the contact for questions or complaints;
- the date, signature, and version of the agreement.

The owner must also decide whether translator data may be used in a later public model or release. The pilot consent should not be broader than the owner can honor.

### F.9 Source licensing and provenance

No source is approved for training. The prepared source is original project material in English that the native-speaking team will translate and review. Existing corpora have unresolved constraints:

| Source | Known position | Status for this pilot |
|---|---|---|
| Project-authored English source, translated and reviewed by native speakers | Original project material. No third-party text. Formal translation and review terms are not recorded. | Draft exists in `data/source/pilot-v1/`. Not training-ready. |
| Native-authored original Luganda data | Rights depend on the agreement. | Preferred for future direct authoring, but no agreement exists. |
| SALT | CC BY-SA 4.0 and gated; translation-oriented, not conversational [R11]. | Not approved. Share-alike and attribution need review. |
| Wikipedia Luganda | CC BY-SA; encyclopedic, not conversational. | Not approved. |
| FLORES | Evaluation-oriented; not a conversational training source. | Not proposed for training. |
| MAFAND | CC BY-NC 4.0; non-commercial restriction [R12]. | Not approved. Commercial use is unresolved. |
| Kimera or other Luganda corpora | Upstream provenance and rights unresolved. | Not approved. |
| Existing adapter's SALT-derived data | The adapter card describes SALT-derived translation data. | Not used for conversation training. |

Each source needs a `data/README.md` record before acquisition or use: name, URL or acquisition method, licence, permitted uses, acquisition date, owner, variety, domain, collection method, consent, PII assessment, deduplication, limitations, counts, and checksums. Accessibility is not permission.

### F.10 Contamination and separation from evaluation

- The 100 pilot items and the 24 evaluation items are authored in separate files with separate IDs.
- No evaluation item may be used as a training example, few-shot example, or prompt template.
- Check exact matches, 8-gram overlaps, and source-level reuse. Manual review every flagged pair.
- Do not use the existing adapter's public evaluation examples as training data.
- Do not use the 15 held-out pilot items for checkpoint selection.
- Record what was checked and what remains unknown. A clean check is not proof that no contamination exists.

---

## G. Smoke-test execution and cleanup procedure

### G.1 Gates before launch

| Gate | Requirement | Current status |
|---|---|---|
| G0. Account | Owner-created Runpod account, verified email, 2FA, payment method that is not a prepaid card. | Blocked. No account. |
| G1. Money | Tax-inclusive credit purchase at or below $20; auto-pay off; low-balance alert set. | Blocked. Tax rate and checkout total unknown. |
| G2. Capacity | Console shows RTX 4090 Secure Cloud available at $0.89 per hour, or the owner approves a documented alternative. | Blocked. Live capacity unverified. |
| G3. Data | 100 pilot examples authored, translated, reviewed, schema-valid, contamination-checked, and split 70/15/15. | English source draft exists. Luganda translation and native review are missing. |
| G4. Evaluation | 24 evaluation items authored, translated, and reviewed separately from the pilot. | English source draft exists. Luganda translation and native review are missing. |
| G5. Teachers | Formal consent, licence, compensation, and retention terms. | Owner reports native speakers available. No formal records. |
| G6. Code | Training and inference implementation reviewed and tested with synthetic data and the tokenizer. | Prepared locally. No GPU dry run. |
| G7. Environment | Pinned dependency set and one-step GPU forward/backward test pass on the Pod. | Blocked. No GPU test. |
| G8. Licence | Gemma terms accepted by the Hugging Face account; source licences recorded. | Blocked. Needs review. |

Do not launch a paid Pod to complete a report. Do not launch to test availability. Do not launch until G0 through G8 are satisfied.

### G.2 Launch and setup

1. Before creating the Pod, complete the credit checkout. Read the tax-inclusive total. Do not pay if the total is above $20.00 or if a prepaid card would require the $100 minimum.
2. Sign in to the Runpod console and open the deployment page.
3. Select **Secure Cloud**, one RTX 4090 24 GB, and the region with capacity.
4. Select the official PyTorch CUDA template. Record the exact image tag.
5. Set the Pod name to `luganda-smoke-YYYYMMDD-HHMM`.
6. Set container disk to 30 GB and volume disk to 20 GB. Do not attach a network volume.
7. Enable SSH with a dedicated key. Disable public Jupyter exposure if the managed proxy is sufficient.
8. Review the summary. Confirm the GPU, storage, and hourly total. If the total or price differs materially from this report, stop and ask the owner.
9. Deploy. Record the Pod ID, region, host, GPU, driver, CUDA, and start time.
10. Set a low-balance alert at $4 remaining and confirm auto-pay is off before starting work.
11. Open a terminal and run `nvidia-smi`. Record the output.

### G.3 Environment and data setup

The full operator sequence is in `docs/POD-SETUP.md`. The short version is:

1. Create a Python 3.11 virtual environment on the Pod. Do not modify the local Windows environment. If the image lacks Python 3.11, stop and choose an image that provides it; do not substitute 3.12 or 3.13.
2. Install `requirements-training.txt`. Do not install a different direct version.
3. Record `pip freeze`, the direct package versions, `nvidia-smi`, the image tag, the driver, and the CUDA runtime.
4. Set `HF_TOKEN` through a secret or environment variable. Do not echo it.
5. Download `google/gemma-3-1b-it` at revision `dcc83ea841ab6100d6b47a070329e1ba4cf78752`. Verify the revision and tokenizer hash. This download is not authorized by this preparation.
6. Transfer the approved training code, config, and data with `scp` or `rsync`. Do not clone an uncommitted working tree from a public remote. Do not include secrets.
7. Verify the SHA-256 of every transferred file against the local manifest.
8. Run `validate-config`, `validate-data --require-tokenizer`, and `preflight`.
9. Run the one-step forward/backward check inside the guarded training command. If it fails, stop before the optimizer loop.

### G.4 Training run

1. Start the training process with the approved config and `max_steps=30`.
2. Keep the terminal attached or use a monitored session. Do not run unattended.
3. Check `nvidia-smi` and the log every few minutes. Record peak VRAM, tokens per second, loss, learning rate, and gradient norm.
4. Stop immediately if any of the following occurs:
   - loss becomes NaN or diverges;
   - CUDA out-of-memory occurs and the approved fallback is not enough;
   - the process hangs for more than 10 minutes without progress;
   - runtime reaches 6 hours;
   - credits consumed reach $8;
   - the balance falls below the alert threshold;
   - a data, tokenizer, or revision check fails;
   - the operator must leave and cannot monitor the run.
5. If a transient error occurs, one retry is allowed within the same caps. Record the failure and the retry. Use a new run directory; checkpoint resume is disabled.
6. At the end, confirm the adapter and checkpoints exist. Do not merge the adapter.

### G.4.1 Checkpoint recovery

Checkpoint resume is disabled for this first gate. The runner writes intermediate checkpoints for inspection, but the CLI rejects a resume request before loading a model. This avoids continuing from an unverified optimizer, scheduler, or RNG state on a short, bounded run.

If the process is interrupted, terminate the Pod, preserve the logs and any completed checkpoint, and record the failure. A retry is a new attempt in a new run directory with a new manifest. Do not copy an old checkpoint into a new run and treat it as a continuation. Do not describe a retry as the original run.

A future gate may enable resume only after the checkpoint format, config hash, dataset hash, and RNG behavior are tested and approved.

### G.5 Post-training inference

1. Start a fresh process and reload the base at the pinned revision and the saved adapter.
2. Run the guarded inference command. It checks that the completed run manifest has the same config hash, dataset hashes, and provenance hash, and that the supplied new adapter has the same file tree and hashes as the run's saved adapter. It also checks the adapter weight count against the expected LoRA size and rejects an existing adapter that is identical to the new one.
3. Run the base, existing adapter, and new adapter on the same 15 held-out prompts and the 24 evaluation items.
4. Use greedy decoding, the base chat template, and a 256-token limit unless an item requires more. Record the finish reason.
5. Save every raw output, including empty, English, repeated, or nonsensical output. Do not cherry-pick.
6. Write the blind review packet and a separate key. Randomize the three responses per item and hide the model identity from reviewers.
7. Do not score the output. Native review is separate.

```bash
python -m training infer /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM/config.snapshot.yaml \
  --run-dir /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM \
  --new-adapter /workspace/runs/gemma3-1b-lora-smoke-YYYYMMDD-HHMM/final_adapter \
  --existing-adapter /workspace/adapters/existing-translation-adapter \
  --project-root /workspace/LugandaGPT \
  --model-path /workspace/models/gemma-3-1b-it
```

Use the frozen `config.snapshot.yaml` from the completed run, not the working config. The inference command requires the snapshot hash to match the training manifest. If the working config changes after training, inference refuses it.

The inference manifest records the raw outputs, packet, key, model roles, adapter hashes, prompts, token counts, finish reasons, and runtime. It records no scores and no native-review claims.

### G.6 Export and cleanup

1. Run `python -m training verify-artifacts <run-dir>` before export.
2. Export the adapter, tokenizer, config, logs, raw outputs, environment freeze, dataset manifest, checkpoint inventory, and cost record.
3. Compute SHA-256 checksums for every exported file. The runner writes an artifact inventory and verifies it.
4. Copy the export to the local machine or approved storage. Verify at least one file opens locally, then run `verify-artifacts` again on the copy.
5. Terminate the Pod. Do not stop it and leave it.
6. Confirm the Pod, volume, and any network volume are gone.
7. Check the billing page and record the final credit charge, cash charge, remaining credit, sales tax, and payment fee:

```bash
python -m training record-cost <run-dir> \
  --final-credit-charge <actual credits consumed> \
  --final-cash-charge <actual cash paid> \
  --remaining-credit <actual remaining credit> \
  --sales-tax <actual tax> \
  --payment-fee <actual fee> \
  --notes "Final Runpod billing after termination"
```

8. Confirm the run manifest has `final_billing_recorded=true` and that the cost record is part of the artifact inventory. If `within_caps=true`, the final cash charge is at or below $20.00 and consumed credits are at or below $8.00. If `within_caps=false`, preserve the record and its `breaches` list, report the breach to the owner, and do not delete or edit the evidence.
9. Record the run in `docs/EXPERIMENT_LOG.md` only after it actually happens. Do not add a completed record now.

### G.7 Failure handling

| Failure | Action |
|---|---|
| GPU unavailable | Stop. Do not substitute a GPU without owner approval. |
| Price above the approved basis | Stop and recalculate. Do not deploy. |
| Tax-inclusive charge above $20 | Do not pay. |
| Hugging Face gated access fails | Stop. Do not use an unofficial mirror. |
| Dependency conflict | Stop and record. Do not mix unpinned versions. |
| OOM | Stop. A pre-approved fallback may reduce max length to 768 and re-run the one-step test, but record the change. Do not change the model or LoRA architecture. |
| NaN loss | Stop. Check data, learning rate, and precision. Do not continue. |
| Data schema or contamination failure | Stop. Do not patch data on the Pod. |
| Checkpoint or adapter reload failure | Stop. Preserve logs and terminate. |
| Cost or time cap reached | Stop immediately. Export if possible, then terminate. |
| Operator cannot monitor | Do not start, or terminate. No unattended run. |

---

## H. Evaluation and acceptance criteria

### H.1 Evaluation set

The proposed evaluation is 24 items, four per capability, authored and reviewed separately from the 100-example pilot. It is a directional feasibility screen, not a benchmark and not a statistically powered test. It does not modify `docs/BENCHMARK-SPECIFICATION.md` and does not create a benchmark version.

The set should include at least:

- 12 items that require a Luganda response;
- 4 multi-turn items with a context-dependent follow-up;
- 4 items with appropriate uncertainty or unanswerable questions;
- 4 items with a constrained instruction;
- 2 items that invite English but require Luganda unless the user asks otherwise.

A separate translation probe of 6 to 12 items may be used only if the owner approves the optional translation track. The existing adapter is a translation baseline, not the V1 candidate.

### H.2 Models and generation controls

| Model | Role |
|---|---|
| Base Gemma 3 1B Instruct | Lower bound and language-compliance baseline. |
| Existing Luganda adapter | Translation baseline and regression reference. |
| New LoRA adapter | Candidate from this smoke test, if training succeeds. |

Controls:

- same base revision and tokenizer;
- same chat template and prompt order;
- 4-bit NF4 with BF16 compute for all models;
- greedy decoding, `do_sample=false`;
- maximum 256 new tokens unless an item requires more;
- seed 42 for any sampling fallback;
- record the finish reason, token counts, and raw output;
- randomize model order and hide model identity from reviewers;
- do not use few-shot examples from the evaluation set.

### H.3 Native review

- Two native reviewers score every response.
- A third native reviewer adjudicates material disagreements.
- Reviewers see the prompt, the response, and the scoring rubric. They do not see the model name.
- Use the approved seven dimension names exactly: semantic correctness, grammar and naturalness, instruction compliance, relevance, context retention, factual reliability, and appropriate register. Do not rename them.
- Add pilot-specific checks for response-language compliance, rewriting fidelity, question-answering correctness, short-conversation coherence, and overfitting or memorization. These checks are separate from the seven dimensions.
- Record exact scores, within-one agreement, disagreements, adjudication, and reviewer notes.
- Do not convert the review into a benchmark score. Report per-dimension counts and paired preferences.

### H.4 Acceptance criteria

**Technical acceptance for the smoke test:**

- the run completes within 6 hours and $8 of credits;
- no unhandled OOM, NaN, or data corruption;
- the adapter saves, reloads, and produces output in a fresh process;
- all required artifacts and checksums exist;
- the Pod and storage are terminated;
- the final charge is recorded and within the $20 cash cap.

**Data acceptance:**

- 100 pilot examples and 24 evaluation items are schema-valid;
- every training example has the required native review;
- no unresolved PII or licence issue;
- no exact or 8-gram contamination between training and evaluation;
- the 70/15/15 split is respected;
- no model-generated gold data.

**Quality signal:**

No numeric threshold is set in this report. A threshold invented before native review would be arbitrary. The owner and native reviewers must approve a go/no-go rule before scoring. A proposed directional rule is:

- the new adapter is preferred over the base on response-language compliance and instruction compliance in a majority of paired evaluation items;
- the new adapter shows no severe regression in grammar, naturalness, or semantic correctness;
- the new adapter does not reproduce training examples verbatim on held-out prompts;
- if translation is in scope, the new adapter is not worse than the existing adapter on the translation probe.

This is a proposal. It is not a benchmark score and does not establish general Luganda ability.

### H.5 Overfitting and memorization

- Compare training loss with validation loss. A large divergence is a warning, not proof.
- Check whether the adapter reproduces training prompts or responses verbatim on held-out items.
- Check for repeated phrases, copied instructions, or refusal to answer outside the training patterns.
- Use the 15 held-out items only for this check.
- A 70-example training set and 30 optimizer steps cannot support a broad generalization claim. The expected outcome is a pipeline signal.

### H.6 Translation regression

The existing adapter is the translation baseline. If the owner approves a translation probe:

- use 6 to 12 original or cleared items, not the adapter's public evaluation set;
- compare the existing adapter, the new adapter, and the base;
- have native reviewers judge meaning preservation and naturalness;
- report the result separately from conversation quality;
- do not claim translation improvement from this smoke test.

### H.7 Limitations

- 24 evaluation items are too few for statistical confidence.
- 70 training examples and 30 steps are a pipeline test, not a capability test.
- One base model, one seed, and one hardware configuration limit reproducibility claims.
- Native review is the reference standard, but reviewer variation must be reported.
- The pilot cannot establish cultural depth, broad factuality, or robust multi-turn ability.
- A negative result is useful. A positive result is not a V1 release.

---

## I. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Live RTX 4090 unavailable | Medium | Schedule slip | Check the Available tab at launch. Stop rather than substitute. |
| Price changes before launch | Medium | Cap pressure | Recheck the console summary. Recalculate. Stop if above the approved basis. |
| Tax or card fee pushes cash above $20 | Medium | Cap breach | Buy only $10 credits, read the checkout total, do not use a prepaid card, keep auto-pay off. |
| Credits non-refundable | High | Wasted spend | Buy the minimum, use a hard credit stop, do not overdeposit. |
| Account or payment setup is incomplete | High | No launch | Owner completes it before any Pod is created. |
| No live availability or API access | High | Cannot verify | Treat as a blocker, not an assumption. |
| Data not translated or reviewed | High | No training | Do not launch. Translation and second-speaker review are the critical path. |
| Translator and reviewer terms unresolved | High | Ethical and legal risk | Owner records written consent, licence, pay, and retention before training. |
| Source licence unresolved | High | Cannot use data | Prefer original project-authored source. Record every source. Do not assume public means usable. |
| Training code has no GPU test | High | Failed run | The implementation and synthetic tests exist. Run the guarded Pod preflight and one-step check before any optimizer step. |
| TRL or dependency incompatibility | Medium | Failed run | Pin versions, test on the Pod, keep a one-step check. |
| 4-bit training path fails | Medium | Failed run | Test bitsandbytes training separately. Fall back only with a recorded config change. |
| OOM at 1,024 tokens | Low to medium | Run stops | Batch 1, gradient checkpointing, 24 GB headroom. Reduce max length only with a recorded change. |
| Adapter overfits 70 examples | High | Misleading output | Treat as a smoke test. Use held-out checks and native review. Do not claim quality. |
| Model answers in English | High | Core failure | Measure response-language compliance. Do not hide it. |
| Memorization or verbatim repetition | Medium | False apparent quality | Held-out prompts and manual copy checks. |
| Secret leakage | Low | Security incident | Secret store, no echo, no logs, dedicated key, terminate Pod. |
| Pod left running or stopped | Medium | Unexpected charges | Manual monitoring, terminate after export, verify Pod and volume are gone. |
| Network volume left behind | Low | Persistent charges | Do not create one. Verify none exists. |
| No artifacts exported | Medium | Wasted run | Export and verify before terminate. |
| Results overclaimed | Medium | Reputational and scientific harm | Label as smoke test. No benchmark score. Native review required. |
| Google Cloud prepayment triggered | Low | Unauthorized spend | Keep Google Cloud on hold. Do not pay the $30. |

---

## J. Open decisions and blockers

### J.1 Owner actions required

1. **Create and secure the Runpod account.** Verify email, enable 2FA, and add a standard payment method. Do not use a prepaid card because of the $100 minimum.
2. **Approve the credit purchase.** A $10 credit purchase is proposed. The tax-inclusive charge must be at or below $20. Read the checkout total before paying.
3. **Verify live capacity and price.** At launch, confirm an RTX 4090 Secure Cloud Pod is available at $0.89 per hour. If not, stop and request a decision.
4. **Approve the data and translator terms.** This includes consent, compensation, licensing, attribution, withdrawal, and retention. No rate is approved.
5. **Approve the data sources.** The English source is project-original and ready for owner review. No translated Luganda source is currently approved.
6. **Approve the training and inference implementation and direct dependency pins.** The code is in `src/training/` and passes local tests. The direct pins are in `requirements-training.txt`. The Linux, Python 3.11, CUDA 12.6, and RTX 4090 combination is not tested. Approval of the pins is not a claim that the runtime works.
7. **Decide whether the optional translation probe is in scope.**
8. **Approve the go/no-go rule for native review.** No numeric quality threshold is set.
9. **Confirm the exact run plan, dependency pins, and credit purchase before launch.** The owner has authorized the smoke test in principle, subject to the prerequisites in this report. This preparation report does not itself launch anything.

### J.2 Engineering actions required

1. **Completed locally:** implement the guarded training, data, inference, and artifact pipeline in `src/training/`.
2. **Completed locally:** add schema, split, prompt-completion, tokenizer, config, authorization, artifact, and inference-helper tests.
3. **Completed for direct dependencies:** pin the direct versions in `requirements-training.txt`. A resolved Linux lock file is still missing.
4. **Completed locally:** run the tokenizer-only, synthetic-data, and full repository test suites. Results are in section M.
5. **Completed locally:** implement the blind evaluation packet and separate key. No evaluation items or native-review scoring tool exists yet.
6. **Completed locally:** implement the artifact manifest, checksum verification, and final cost record.
7. **Pending, blocked:** run the Pod preflight, 4-bit load, one-step backward pass, VRAM measurement, and adapter reload.
8. **Pending, blocked:** run training, inference, native review, and record the actual run only after it happens.

### J.3 What is ready

- The Runpod price basis is verified.
- The account and payment requirements are documented.
- The tax, deposit, refund, and spending-limit constraints are documented.
- The $20 budget plan and hard stop are defined.
- The instance and storage plan is defined.
- A machine-readable training configuration is prepared and structurally validated.
- The guarded training and inference implementation is prepared in `src/training/`.
- The pilot schema, evaluation schema, provenance requirements, review rules, consent rules, and validation commands are defined.
- Direct dependency pins and a partial Pod setup procedure exist.
- The artifact manifest, checksum verification, run binding, and final cost record are implemented.
- The smoke-test, failure, cleanup, and evaluation procedures are defined.
- D-008 records the bounded provider and GPU decision.

### J.4 What is not ready

- No Runpod account, payment method, or credits.
- No live availability check.
- No tax-inclusive checkout total.
- English source draft exists, but no Luganda translations, second-speaker reviews, approved data, translator agreement, consent, licence, or compensation record.
- No resolved Linux dependency lock or tested Python 3.11 CUDA runtime.
- No GPU environment test, 4-bit model load, bitsandbytes training test, one-step backward pass, VRAM measurement, or adapter reload.
- No actual adapter, inference output, native review, or evaluation result.
- No confirmation of the exact run plan, dependency pins, and credit purchase at launch.
- The owner reports native speakers available; no formal review schedule or agreement is recorded.

---

## K. Files changed

| Path | Change | Purpose |
|---|---|---|
| `docs/DECISIONS.md` | Added D-008 and D-009 | D-008 records the bounded gate. D-009 records the English source approach, the owner's report that native speakers are available, and the outstanding formal terms. |
| `configs/gemma3-1b-lora-smoke.yaml` | New | Machine-readable proposed training, budget, hardware, data, and artifact configuration. |
| `src/training/*.py` | New | Guarded config, data, environment, model, runner, inference, artifact, storage, and CLI modules. |
| `src/training/source_pilot.py` | New | English source draft validator and translator export writer. |
| `tests/test_training_config.py` | New | Config schema, pins, budgets, duplicate keys, secrets, and authorization tests. |
| `tests/test_training_pilot.py` | New | Pilot and evaluation schema and review tests. |
| `tests/test_training_data.py` | New | Provenance, split, contamination, tokenizer, and prompt-completion tests. |
| `tests/test_training_runner.py` | New | Authorization, runner guard, adapter hash, and inference helper tests. |
| `tests/test_training_artifacts.py` | New | Manifest, checksum, verification, and final cost tests. |
| `tests/test_training_cli.py` | New | CLI command and failure-mode tests. |
| `tests/test_training_tokenizer.py` | New | Pinned tokenizer, chat-template, and rendering tests. |
| `tests/test_training_source_pilot.py` | New | English source counts, splits, statuses, duplicates, exports, and CLI tests. |
| `tests/training_support.py` | New | Synthetic fixture generator. It does not contain real data. |
| `data/source/pilot-v1/source_draft.json` | New | Canonical 100-item pilot and 24-item evaluation English source draft. |
| `data/source/pilot-v1/pilot_en.jsonl` | Generated | 100 pilot source rows. |
| `data/source/pilot-v1/evaluation_en.jsonl` | Generated | 24 evaluation source rows. |
| `data/source/pilot-v1/translator_export.csv` | Generated | 124-row translator and reviewer workbook. |
| `data/source/pilot-v1/source_manifest.json` | Generated | Source counts, composition, owner confirmation, and checksums. |
| `data/source/pilot-v1/README.md` | New | Source status, counts, owner confirmation, and blockers. |
| `data/source/pilot-v1/TRANSLATOR-GUIDE.md` | New | Translation, review, status, and return instructions. |
| `scripts/build_source_pilot.py` and `scripts/source_pilot_*.py` | New | Reproducible source authoring and export builder. |
| `requirements-training.txt` | New | Proposed direct dependency pins. Not a resolved lock file. |
| `docs/PILOT-DATA-SPECIFICATION.md` | Updated | Adds the English source draft, translator workflow, source validation, and revised blockers. |
| `docs/POD-SETUP.md` | Updated | Separates the English source draft from translated training data and updates the blocker list. |
| `data/README.md` | Updated | Adds the English source dataset record and owner confirmation. |
| `README.md` | Updated | Corrects the repository status and structure now that source and training-preparation tooling exist. |
| `docs/PHASE-1-RESEARCH.md` | Updated | Adds a dated note that native speakers are available; the earlier consultation statements are historical. |
| `reports/FINE-TUNING-FEASIBILITY.md` | Updated | Adds a dated note pointing to the English source draft and D-009. |
| `reports/ENGLISH-SOURCE-PILOT-REPORT.md` | New | Owner-facing source report with counts, validation, and outstanding translation work. |
| `reports/RUNPOD-FIRST-GATE-REPORT.md` | New | This report. |

No Luganda training data, model weights, credentials, generated model outputs, or native reviews were added. The English source draft is the only data added. No deployment or publication was performed.

In particular:

- `docs/BENCHMARK-SPECIFICATION.md` was not modified by this training preparation. Existing uncommitted benchmark changes were preserved.
- `docs/EXPERIMENT_LOG.md` was not given a new completed record because no experiment ran. Existing uncommitted changes were preserved.
- The existing adapter and base model were not modified.
- No existing data, model, or checkpoint was deleted.
- No dependency was installed into the local virtual environment for this preparation.
- No Runpod account, Pod, volume, or network volume was created.

The working tree already contained uncommitted changes before this task, including `docs/DECISIONS.md`, `docs/EXPERIMENT_LOG.md`, the benchmark work, and the feasibility report. `git status` also shows those files. They were preserved. This task did not commit or push.

---

## L. Status

**BLOCKED: OWNER DECISION OR PREREQUISITE REQUIRED.**

The no-cost preparation is complete within the approved scope. Execution is not ready. The smoke test is authorized in principle; the remaining barriers are the prerequisites below.

1. No Runpod account, payment method, credits, or live availability check.
2. The tax-inclusive checkout total is unknown and must be at or below $20.
3. English source draft exists, but no translated Luganda pilot or evaluation set.
4. No formal translator agreements, consent, compensation, or retention terms.
5. No approved Luganda data source, provenance record, or licence record.
6. No tested Linux Python 3.11 CUDA 12.6 runtime or resolved dependency lock.
7. No RTX 4090 environment test, 4-bit load, backward pass, VRAM measurement, or adapter reload.
8. No actual adapter, inference output, native review, or evaluation result.
9. No confirmation of the exact run plan, dependency pins, and credit purchase at launch.

The experiment can fit within $20 under the public price and the proposed $10 credit purchase. That is a conditional arithmetic conclusion, not a confirmed booking. No paid infrastructure was launched. No account or deposit was created. No model or dataset was downloaded. No training or inference was performed for this report.

The status remains `BLOCKED: OWNER DECISION OR PREREQUISITE REQUIRED` because the owner approvals, translated data, translator terms, account, and GPU prerequisites are open. The smoke test is authorized in principle; this report is not approval to launch and does not itself launch anything.

---

## M. Local verification and residual GPU checks

All checks in this section were run locally on 2026-10-21. They do not test a GPU, a 4-bit base model, a paid service, or real data.

### M.1 Commands and results

| Check | Command | Result |
|---|---|---|
| Python syntax | `python -m compileall -q src\training tests` | Completed with no syntax error. |
| Training suite | `python -m unittest discover -s tests -p "test_training_*.py" -t .` | 102 tests, unittest reported `OK`. |
| Full repository suite | `python -m unittest discover -s tests -t .` | 401 tests, unittest reported `OK`. |
| Config structure | `python -m training validate-config configs\gemma3-1b-lora-smoke.yaml` | `config_valid`; `execution_authorized=false`; status `authorized_in_principle_subject_to_prerequisites`. |
| Unapproved data | `python -m training validate-data configs\gemma3-1b-lora-smoke.yaml` | Expected failure: `dataset.version` is still marked unapproved or draft. |
| English source draft | `python -m training validate-source` | `source_draft_valid`; 100 pilot and 24 evaluation items; 124 translator rows; `training_authorized=false`. |
| Synthetic project | Training suite fixture | 124 synthetic records checked, including 100 pilot records, 24 evaluation items, and provenance. |
| Tokenizer only | Pinned local tokenizer at `D:\LugandaGPT\models\gemma-3-1b-it` | Chat-template hash, pad id 0, BOS id 2, EOS ids 1 and 106, and prompt-completion prefix checks passed. |
| Environment versions | `training.environment.installed_versions()` | Python 3.13.14, torch 2.7.1+cpu, transformers 4.53.2, peft 0.18.1, accelerate 1.8.1, bitsandbytes 0.50.2, tokenizers 0.21.4, safetensors 0.8.0, sentencepiece 0.2.2, huggingface_hub 0.34.3; datasets and trl absent. |

PowerShell can report exit code 1 for a passing unittest run because test progress is written to stderr. The authoritative result is the unittest summary, which was `OK` for both suites.

### M.2 What the local tests cover

- strict config parsing and rejection of unknown, missing, duplicate, inconsistent, unauthorized, underfunded, and secret-bearing values;
- pinned base, tokenizer, chat template, LoRA shape, and dependency values;
- exact pilot and evaluation composition, IDs, roles, references, reviews, consent links, audit coverage, and PII status;
- provenance counts, split hashes, file hashes, and record-to-consent links;
- exact and 8-word contamination checks across all splits and evaluation items;
- token limits and prompt-completion expansion for every assistant turn;
- environment, authorization, one-step guard, budget, and run-directory behavior where testable without a GPU;
- artifact manifests, checksum inventories, verification, and final billing flags;
- inference prompt construction, adapter tree hashing, blind packet shape, and no-score manifest fields;
- English source counts, splits, capability distribution, pending statuses, provenance, duplicate checks, translator CSV shape, and source manifest checksums;
- CLI commands and expected failure messages.

The synthetic fixture is test-only. It is not a source of Luganda training data and must not be presented as a pilot.

### M.3 GPU-dependent checks still pending

| Check | Status |
|---|---|
| Python 3.11 and exact package resolution on Linux | Pending. |
| PyTorch CUDA 12.6 and BF16 availability | Pending. |
| RTX 4090 24 GB detection | Pending. |
| 4-bit NF4 base model load at the pinned revision | Pending. |
| Bitsandbytes 4-bit forward pass | Pending. |
| TRL 0.20.0 SFT construction with `completion_only_loss=true` | Pending. |
| One-step forward and backward pass | Pending. |
| Peak VRAM and throughput measurement | Pending. |
| Adapter save, fresh-process reload, and parameter count | Pending. |
| Post-training inference and blind packet on 39 items | Pending. |
| Native review and any quality conclusion | Pending, and no review capacity is confirmed. |

No GPU check is marked as passed anywhere in this report. The remaining failures are missing prerequisites and unverified runtime behavior, not local test failures.

---

## References

[R1] Runpod GPU pricing, page updated 2026-10-08, checked 2026-10-21: https://www.runpod.io/pricing

[R2] Runpod, Deploy your first Pod, account, availability tabs, storage, and cleanup: https://docs.runpod.io/get-started

[R3] Runpod public GraphQL catalog, queried at https://api.runpod.io/graphql on 2026-10-21; API v2 catalog endpoint, unauthenticated request returned HTTP 401: https://api.runpod.io/v2/catalog/gpus

[R4] Runpod billing overview, credits, minimum balance, payment methods, spending limit, storage rates: https://docs.runpod.io/accounts-billing/billing

[R5] Runpod payment card declines, prepaid-card minimum: https://docs.runpod.io/accounts-billing/manage-payment-cards

[R6] Runpod sales tax, tax charged on top of credits: https://docs.runpod.io/accounts-billing/sales-tax

[R7] Runpod tax ID: https://docs.runpod.io/accounts-billing/add-tax-id

[R8] Runpod storage options, container, volume, network, and stopped-volume rates: https://docs.runpod.io/pods/storage/types

[R9] Fine-tuning feasibility report and pinned model records: `reports/FINE-TUNING-FEASIBILITY.md`; `docs/EXPERIMENT_LOG.md`; `docs/DECISIONS.md`

[R10] TRL SFT Trainer and dataset formats: https://huggingface.co/docs/trl/main/en/sft_trainer and https://huggingface.co/docs/trl/main/en/dataset_formats

[R11] Sunbird SALT dataset metadata: https://huggingface.co/datasets/Sunbird/salt

[R12] MAFAND dataset metadata: https://huggingface.co/datasets/Masakhane/mafand

[R13] Gemma Terms of Use: https://ai.google.dev/gemma/terms

[R14] Gemma 3 model card: https://ai.google.dev/gemma/docs/core/model_card_3

[R15] Project data governance: `data/README.md`

[R16] Approved benchmark specification and workflow: `docs/BENCHMARK-SPECIFICATION.md`; `docs/BENCHMARK-WORKFLOW.md`

[R17] Project decisions: `docs/DECISIONS.md`

[R18] Guarded training and inference implementation: `src/training/`

[R19] Proposed direct dependency pins: `requirements-training.txt`

[R20] Pilot, evaluation, provenance, consent, and review specification: `docs/PILOT-DATA-SPECIFICATION.md`

[R21] Future Pod setup, hard limits, export, termination, and billing checklist: `docs/POD-SETUP.md`

[R22] Local training tests and synthetic fixture: `tests/test_training_config.py`, `tests/test_training_pilot.py`, `tests/test_training_data.py`, `tests/test_training_runner.py`, `tests/test_training_artifacts.py`, `tests/test_training_cli.py`, `tests/test_training_tokenizer.py`, `tests/training_support.py`

[R23] English source pilot report and translator-facing draft: `reports/ENGLISH-SOURCE-PILOT-REPORT.md`; `data/source/pilot-v1/`; `data/source/pilot-v1/TRANSLATOR-GUIDE.md`

---

## Appendix: Verification log

### Runpod price

- Pricing page `dateModified`: 2026-10-08.
- RTX 4090 product entry: Community Cloud $0.34 per hour, Secure Cloud $0.89 per hour, 24 GB VRAM.
- The public GraphQL catalog returned `NVIDIA GeForce RTX 4090`, `memoryInGb: 24`, `secureCloud: true`, `communityCloud: true`. Query used: `{ gpuTypes { id displayName memoryInGb secureCloud communityCloud } }`.
- The authenticated API v2 catalog request returned HTTP 401 without a token.
- No console availability check was possible because no account exists.

### Runpod account and billing

- Account signup requires email verification and recommends 2FA.
- The console prompts for a payment method and credits at deploy if not already configured.
- Credits are prepaid and non-refundable.
- New users can start with $10.
- A new Pod requires at least one hour of credits for the selected configuration.
- Prepaid cards should deposit at least $100 per transaction.
- Standard cards, crypto, and business invoicing over $5,000 are listed.
- Default spend limit is $80 per hour.
- Sales tax is charged on top of the credit purchase and does not reduce credits.
- The tax rate depends on billing address and payment method.
- Auto-pay can reload credits and must be disabled for this gate.
- Low-balance alerts are available.
- Container and running volume disks are $0.10 per GB per month; stopped volume disks are $0.20 per GB per month; network volumes are $0.07 per GB per month.
- No data-transfer fee is stated on the billing page.

### Model and tokenizer

- Base revision `dcc83ea841ab6100d6b47a070329e1ba4cf78752`.
- Parameter count 999,885,952.
- Hidden size 1,152; 26 layers; vocabulary 262,144; context 32,768.
- Chat template SHA-256 `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4`.
- EOS ids: 1 (`<eos>`) and 106 (`<end_of_turn>`).
- Base chat template has no `{% generation %}` markers, so the assistant-only-loss path is not used.
- The proposed training path uses conversational prompt-completion records and completion-only loss.

### Local environment

- Python 3.13.14.
- PyTorch 2.7.1+cpu.
- Transformers 4.53.2.
- PEFT 0.18.1.
- Accelerate 1.8.1.
- Bitsandbytes 0.50.2.
- Tokenizers 0.21.4, safetensors 0.8.0, sentencepiece 0.2.2, and huggingface_hub 0.34.3.
- `datasets` and `trl` are not installed in the local environment.
- No GPU training, 4-bit model load, or backward pass was performed.

### Local preparation tests

- `python -m compileall -q src\training tests`: completed with no syntax error.
- Training tests: 102 tests, unittest reported `OK`.
- Full repository tests: 401 tests, unittest reported `OK`.
- English source draft: `source_draft_valid`; 100 pilot and 24 evaluation items; 124 translator rows; `training_authorized=false`.
- Current config: structure valid, `execution_authorized=false`, dataset version `pilot-v1-unapproved`.
- Current data validation: expected failure because the dataset version is still marked unapproved or draft.
- Synthetic project: 124 records checked, including 100 pilot records, 24 evaluation items, provenance, split hashes, review links, contamination, tokenizer limits, and prompt-completion rendering.
- Pinned tokenizer check: chat-template SHA-256, pad id 0, BOS id 2, EOS ids 1 and 106, and prompt-completion prefix checks passed.
- No GPU-dependent test was run. The pending list is in section M.3.

### Cost arithmetic

- GPU: $0.89 per hour.
- Container disk: 30 GB x $0.10 / 730 = $0.00410959 per hour.
- Volume disk: 20 GB x $0.10 / 730 = $0.00273973 per hour.
- Total: $0.89684932 per hour.
- Six hours: $5.38109589, rounded to $5.38.
- Eight hours: $7.17479452, rounded to $7.17.
- Twelve hours: $10.7621918, rounded to $10.76.
- A $10 credit purchase at 18 percent tax costs $11.80 and provides $10 in credits.
- The proposed hard stop is 6 hours or $8 of credits consumed, whichever comes first.

### Actions not taken

- No Runpod account.
- No payment method or deposit.
- No GPU Pod.
- No model or dataset download.
- No training or inference.
- No paid API call.
- No data acquisition.
- No formal teacher or translator agreement or payment.
- No benchmark item or score.
- No commit or push.
