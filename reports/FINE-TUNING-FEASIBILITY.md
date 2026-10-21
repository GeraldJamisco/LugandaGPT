# Fine-Tuning Feasibility Report: Gemma 3 1B for LugandaGPT V1

**Status:** Investigation only. This report is not an approval record and does not authorize training, inference, data acquisition, spending, or release.

**Date:** 2026-10-21

**Prepared by:** DeepSeek, engineering agent

**Owner:** Project Director

**Scope:** Determine whether the pinned Gemma 3 1B Instruct base and the existing Luganda adapter can support a useful Luganda-native conversational assistant through supervised fine-tuning, compare two training paths, propose a data and evaluation plan, assess local and hosted compute, and state the next owner decision.

**Non-claims:** No LugandaGPT model has been trained. No benchmark item, reference answer, score, or teacher approval is created here. The 99 percent judgment recorded in EXP-2026-002 is an informal native review of one published translation example, not a benchmark result. No model inference, training, fine-tuning, dataset download, paid API call, GPU rental, commit, or push was performed for this report.

**Update 2026-10-21:** An English source draft now exists in `data/source/pilot-v1/` for the 100-example pilot and 24-item evaluation. It is not a translated Luganda dataset and is not approved for training. The Project Director reports that native Luganda speakers are available and have agreed to collaborate; formal terms remain outstanding. See D-009 and `reports/ENGLISH-SOURCE-PILOT-REPORT.md`. Statements below about the earlier absence of a dataset describe the feasibility baseline.

---

## Evidence labels

The report uses four labels:

- **Verified:** read directly from the pinned local files, the public repository metadata, the approved project documents, or the measured EXP-2026-002 record.
- **Source claim:** published by the adapter author, Google, Hugging Face, or a hosting provider. It has not been independently reproduced unless stated.
- **Estimate:** arithmetic or engineering judgment. It is not a measurement.
- **Proposal:** a recommended action that requires owner approval.

A verified licence tag is not a legal opinion. A published benchmark number is not an independent score. A successful inference run is not evidence that training is feasible.

---

## 1. Executive recommendation

1. **Do not treat the existing adapter as the V1 path.** The evidence supports it as a translation-only candidate on one published example. It failed the teacher-supplied Luganda conversation instruction, and its published evaluation is translation-only. It is not a demonstrated conversational or instruction-following model.

2. **If V1 requires conversation and instruction following, recommend Approach B:** start a new LoRA adapter from the pinned Gemma 3 1B Instruct base and train it on a small, native-authored supervised dataset. The recommendation is about a cleaner experiment, not a promise that the base model will become a useful conversational assistant.

3. **Do not continue the existing adapter as the main V1 strategy.** Approach A, continuing the existing adapter, is technically possible in principle, but it inherits a translation-oriented objective, an incomplete training record, SALT-derived data, unresolved share-alike and gating questions, and a risk of preserving translation behaviour while still failing conversation.

4. **Do not train on the local Windows machine.** The machine has 8 GB RAM and no NVIDIA GPU. Full fine-tuning does not fit. A LoRA or QLoRA run might fit memory only under restrictive settings, but CPU throughput and the unverified 4-bit training path make it unsuitable for iterative work in the remaining schedule. A hosted 24 GB GPU is the realistic option if training is approved.

5. **Start small.** A first feasibility experiment should use roughly 1,000 to 1,500 native-authored examples, not a large corpus. Data authoring and native review are the critical path. A V1 target of 3,000 to 5,000 examples would be built over more than one cycle. These numbers are estimates, not proven requirements.

6. **The realistic outcome is a narrow signal, not a finished V1 assistant.** Fine-tuning can plausibly improve response-language compliance, format following, register, and short conversational patterns. It is unlikely to deliver broad conversational Luganda, factual reliability, cultural depth, or robust multi-turn behaviour within 27 days. A negative result would still be useful evidence.

7. **The next decision is a bounded gate, not a full training authorization.** Approve or reject Approach B for a first gate covering licence and data review, teacher agreements, a 100-example authoring pilot, and a capped hosted-GPU environment check. A separate approval should be required before the full supervised fine-tuning run.

---

## 2. Existing adapter assessment

### 2.1 Verified technical facts

The adapter is public, not gated, and pinned at revision `5d0f24b80a09f582708ff397c989331d7d7b536f` [R1]. The base model is pinned at `dcc83ea841ab6100d6b47a070329e1ba4cf78752` [R2].

| Item | Verified value | Basis |
|---|---|---|
| Base model | `google/gemma-3-1b-it` | Adapter config and public metadata |
| Base revision | `dcc83ea841ab6100d6b47a070329e1ba4cf78752` | Public metadata and local files |
| Base parameter count | 999,885,952 | Safetensors metadata, local file |
| Base weight storage | About 2.0 GB in BF16 | Local `model.safetensors` size and dtype |
| Base context limit | 32,768 positions for the 1B model | Base `config.json` and Gemma 3 model card [R8] |
| Base vocabulary | 262,144 tokens | Base `config.json` |
| Adapter type | PEFT LoRA, causal language model | `adapter_config.json` |
| Adapter file size | 52,231,312 bytes | Local file and public metadata |
| Adapter tensors | 364 | Safetensors metadata |
| LoRA parameters | 13,045,760 | Safetensors metadata |
| Rank and alpha | r=16, alpha=32 | `adapter_config.json` |
| LoRA dropout | 0.05 | `adapter_config.json` |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` | `adapter_config.json` |
| PEFT version recorded by adapter | 0.18.1 | `adapter_config.json` |
| Adapter saved state | `inference_mode: true` | `adapter_config.json` |
| Chat template | Identical to the pinned base template, SHA-256 `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4` | Local files, hash comparison |
| Local retest runtime | Python 3.13.14, torch 2.7.1+cpu, transformers 4.53.2, peft 0.18.1, bitsandbytes 0.50.2 | EXP-2026-002 [R15] |

The adapter repository contains `README.md`, `adapter_config.json`, `adapter_model.safetensors`, `chat_template.jinja`, `eval_results.json`, `tokenizer.json`, `tokenizer_config.json`, and `training_args.bin` [R1]. It does not contain a training script, a dataset card, a data manifest, a split file, per-example provenance, or a `LICENSE` file. The licence is declared only in the model card metadata and README.

### 2.2 What the public card says

The following are source claims from the adapter card [R3], not independently verified results:

- The adapter was trained with QLoRA using 4-bit NF4 and LoRA.
- The training set had 94,542 examples derived from about 24,000 clean English-Luganda parallel sentence pairs.
- The primary source was `Sunbird/salt`, described as a professionally translated multi-way parallel corpus covering agriculture, health, society, and related topics.
- The card lists three task types: English-to-Luganda translation, Luganda-to-English translation, and Luganda conversation.
- The split is described as 90 percent train, 5 percent validation, and 5 percent test.
- Training used one epoch, effective batch size 16, learning rate 2e-4 with a cosine schedule, maximum sequence length 256, BF16, and paged AdamW 8-bit.
- Training took about 8 hours on a Tesla T4.
- Final training loss was 1.55 and final validation loss was 1.26.
- The card reports BLEU 13.85 and chrF++ 46.59 on 100 examples, against BLEU 0.06 for the base model.

The public `eval_results.json` does contain 100 examples [R6]. Counting the prompt directions in that file gives 88 English-to-Luganda examples and 12 Luganda-to-English examples. The file reports the same BLEU and chrF++ values as the card. It contains no conversation examples.

The public `training_args.bin` is a serialized TRL `SFTConfig` [R5]. It records:

- maximum length 256;
- per-device training batch size 8;
- gradient accumulation 2;
- learning rate 2e-4;
- one epoch;
- cosine schedule with 5 percent warmup;
- BF16 enabled;
- `paged_adamw_8bit`;
- gradient checkpointing enabled;
- `dataset_text_field` set to `text`;
- `completion_only_loss` not set;
- `assistant_only_loss` false.

The saved object is marked `do_train=false` and `do_eval=true`, and its output directory is `/kaggle/working/luganda_checkpoints`. It appears to be an evaluation-time snapshot, not a complete training invocation. It does not establish how the conversation examples were built, how loss was masked, or whether the 100 evaluation examples were excluded from training.

### 2.3 Is the original objective known?

Only at a high level. The card says the adapter was trained for translation and Luganda conversation. The training data source, SALT, is sentence-level parallel text, not a conversational corpus. The card does not publish the prompt templates, the conversation construction method, the split assignment, the deduplication method, or the mapping from about 24,000 pairs to 94,542 examples. The expansion is consistent with template or task augmentation, but that is an inference, not a verified fact.

This matters for interpretation. An adapter can be trained on many translation-derived prompt variants and still fail a free-form conversational instruction. The retest is consistent with that possibility. No root cause is claimed.

### 2.4 Measured retest evidence

EXP-2026-002 measured one controlled CPU retest with 4-bit NF4, BF16 compute, the adapter active, and no runtime errors [R15]. The adapter loaded as `PeftModelForCausalLM` with active adapter `default`, 13,045,760 LoRA parameters in 364 tensors, and all seven target modules. There was no FP32 fallback.

- Translation prompt: the adapter card's published English example.
- Translation output: `Abalimi beetaaga ensigo ennungi okwongera ku bikungulwa byabwe.`
- Teacher-supplied comparison sentence, not used for scoring: `Abalimi betaaga ensigo enunji okwongera okulogoosa mu makungula gaabwe`.
- Teacher review: the translation was judged excellent on this single example, with an informal 99 percent judgment.
- Conversation prompt: a teacher-supplied Luganda sentence with an instruction to respond in Luganda.
- Conversation output: `Farmers need to plant more maize seeds to increase their production.`
- Teacher review: the instruction was not followed because the response was English; the teacher also noted added content involving `maize` (`kasooli`) and `production`, with overlap between `production` and `harvest` around `amakungula`.

The translation result is one positive native review of one example. It does not establish general translation quality. The conversation result is a direct failure of the observable language instruction. The adapter card's translation-only evaluation is consistent with the failure, but it is not proof of the cause.

### 2.5 Is continued fine-tuning technically supported?

**In principle, yes, with conditions.** PEFT documents `PeftModel.from_pretrained(..., is_trainable=True)` for loading an adapter as trainable [R9]. The same base family, tokenizer, target modules, and quantization path are available locally. A continuation run would need:

- the exact base revision `dcc83ea841ab6100d6b47a070329e1ba4cf78752`;
- the exact adapter revision `5d0f24b80a09f582708ff397c989331d7d7b536f`;
- the pinned tokenizer and chat template;
- a PEFT version compatible with the adapter, with 0.18.1 as the recorded baseline;
- 4-bit NF4 storage and BF16 compute, because the adapter card says the LoRA weights were trained against 4-bit base weights;
- a training smoke test that confirms the adapter is actually trainable, because the saved config has `inference_mode: true`;
- a check that the new maximum sequence length and data format are compatible with the adapter's 256-token training limit.

This report did not run that smoke test. Continued training is technically possible in principle, not demonstrated on this machine.

Do not merge the adapter into the base and then assume a second adapter can be trained safely. Merging changes the base weights and removes the condition under which the original adapter was trained. PEFT can hold multiple adapters and can merge weights for inference, but merging is not a substitute for a validated continuation experiment [R10].

### 2.6 Licensing and provenance

| Component | Verified status | Unresolved issue |
|---|---|---|
| Base model | Gemma licence, gated manual on Hugging Face [R2] | Gemma terms impose use restrictions and distribution obligations; legal review is still required for the planned release |
| Adapter | Card declares Apache-2.0 [R1][R3] | No `LICENSE` file is present in the repository; the declaration does not resolve the base terms or the training-data terms |
| Training data | SALT is tagged CC BY-SA 4.0 and is gated automatic [R14] | Gated terms, speaker consent, translator agreements, source-text rights, and the effect of share-alike on adapter weights are unresolved |
| Evaluation data | The 100 evaluation examples are published inside the adapter repository [R6] | Their relationship to the 90/5/5 split and their source sentences are not documented |

The Gemma Terms of Use permit use, reproduction, modification, and distribution only in accordance with the terms [R7]. Distribution of Gemma or a Model Derivative requires including the terms and the Section 3.2 use restrictions, notifying recipients that the model is subject to those restrictions, and marking modified files. Google claims no rights in outputs, but outputs remain the user's responsibility. Under the terms' definition, a fine-tuned checkpoint is a Model Derivative and remains subject to the terms. Legal review is still required.

Apache-2.0 permits commercial use, modification, and distribution, and requires the licence, notices, and patent terms to be preserved. It cannot grant rights the uploader does not hold. The adapter's Apache-2.0 tag therefore does not answer whether SALT's share-alike obligations reach the adapter weights or whether the gated terms were satisfied.

SALT is a sentence-level multi-way parallel corpus, not a conversation corpus [R18]. Its licence tag is CC BY-SA 4.0, and access is gated [R14]. The project's data governance rules require a recorded source, licence, acquisition date, provenance, consent assessment, quality checks, and version before any training use [R17]. No such record exists for the adapter's training data.

The combined licence status is unresolved. A legal review is required before distribution, before a public release, and before relying on the adapter as a component of a released model. This report does not provide legal advice.

### 2.7 Is the adapter a reasonable starting point?

- **For a translation-only baseline:** yes, as a candidate. One native-reviewed example is positive, and the adapter is small and runs locally. It still needs a separate translation evaluation with approved data and native review.
- **For a V1 conversational or instruction-following model:** no. The measured conversation failure, the translation-only evaluation, the missing conversational data provenance, the 256-token training limit, and the unresolved licence combination are too many gaps to treat it as the main foundation.
- **For a low-cost continuation experiment:** conditionally. It could test whether a small amount of conversational data can redirect the adapter while preserving translation. That is a narrower question than V1 and would still need compatibility, licence, and data approvals.

---

## 3. Comparison of the two training approaches

### 3.1 Approach A: continue fine-tuning the existing adapter

**Technical feasibility.** PEFT supports loading the adapter as trainable. The base revision is pinned, the adapter is intact, and the local environment already loads it. However, the saved `inference_mode: true` must be overridden or reset, the 4-bit training path must be verified on the chosen GPU, and the 256-token limit must be handled for conversational examples.

**Likely benefits.**

- Preserves whatever translation behaviour the adapter already learned.
- Requires fewer trainable parameters and possibly fewer examples than a fresh adapter.
- Can use a translation replay mixture to reduce forgetting.
- Is the fastest way to test whether a small conversational correction can shift behaviour.

**Risks and limitations.**

- Inherits a translation-oriented objective and a data mixture built from sentence pairs.
- Inherits SALT provenance, gated terms, and share-alike questions.
- The adapter's original conversation construction is undocumented, so its existing behaviour is hard to diagnose.
- Catastrophic forgetting of translation is possible if the new data is small and conversational.
- The 256-token training limit may truncate multi-turn examples.
- The adapter card warns that loading in 8-bit or full precision may degrade translations; the training stack must preserve the 4-bit condition.
- A positive result would still not establish a clean V1 foundation, because the combined licence and data provenance remain unresolved.

**Training-data requirements.** Roughly 800 to 1,500 conversational and instruction examples, plus 150 to 300 translation replay examples, with a held-out split. These are estimates.

**Compatibility requirements.** Exact base revision, exact adapter revision, pinned tokenizer and chat template, PEFT 0.18.1 compatibility, 4-bit NF4 with BF16 compute, the same seven target modules, and a training smoke test that confirms the adapter parameters are trainable. Do not merge adapters to simulate continuation.

**Licensing implications.** Gemma terms plus Apache-2.0 plus SALT CC BY-SA 4.0 and gated terms. The combined status is unresolved. Any distribution would require a legal review.

**Compute and memory.** A 1B QLoRA run on a 24 GB GPU is expected to fit. A first run is estimated at 3 to 8 GPU-hours including setup and evaluation. Local CPU training is not recommended. These are estimates, not measurements.

**Suitability for the remaining schedule.** Technically possible if data and approvals are ready, but the data is not ready and the licence questions are unresolved. It is not a clean V1 path.

### 3.2 Approach B: train a new adapter from the pinned base

**Technical feasibility.** Standard LoRA or QLoRA supervised fine-tuning on the pinned base. Google publishes a QLoRA guide that runs Gemma 1B on a 16 GB T4 with maximum length 512 and batch size 1 [R11], which supports the claim that the model size is within reach of a 24 GB hosted GPU. The exact training configuration still needs a smoke test.

**Likely benefits.**

- Cleaner provenance: the new adapter is trained on data the project chooses and documents.
- No inherited translation bias from the existing adapter.
- Control over the data mixture, prompt format, loss masking, sequence length, and evaluation splits.
- Avoids inheriting the existing adapter's unresolved SALT obligations, although new data licences still apply.
- Easier to explain and reproduce as a project artifact.

**Risks and limitations.**

- Requires more native-authored data and more review time than a small continuation run.
- The fresh adapter may lose the existing translation quality unless translation examples are included.
- The base model may lack enough latent Luganda for fluent generation; SFT cannot create knowledge or fluency that is not present.
- A 1B model may be too small for robust reasoning, factual reliability, and long multi-turn context.
- Training from scratch on a small dataset can overfit to templates or surface patterns.
- Gemma terms still apply, and every new data source needs its own licence and provenance review.

**Training-data requirements.** A first experiment of roughly 1,000 to 1,500 examples. A broader V1 target of 3,000 to 5,000 examples would be built in later cycles. Include translation replay only if translation is an explicit requirement and the data is cleared.

**Compatibility requirements.** Exact base revision, pinned base tokenizer and chat template, a new LoRA configuration, 4-bit NF4 storage with BF16 compute if using QLoRA, a maximum length of 512 or 1024 for conversation, gradient checkpointing, and assistant-only loss masking. These are proposals, not approved settings.

**Licensing implications.** Gemma terms plus the licences of the new training data. Teacher-authored data requires documented ownership or permission, consent, and retention terms. Starting from the base avoids the existing adapter's SALT-derived weights, but it does not make the dataset automatically clean.

**Compute and memory.** Similar to A: 24 GB GPU, an estimated 3 to 8 GPU-hours for a first run, and 20 to 30 GB of hosted storage. Local CPU training is not recommended. These are estimates.

**Suitability for the remaining schedule.** Feasible only as a small pilot. The critical path is data authoring and native review, not GPU time. A 1,000 to 1,500 example pilot can fit in 27 days if work starts immediately and review capacity is available. A 3,000 to 5,000 example V1 dataset is unlikely to be completed and reviewed within the same window.

### 3.3 Side-by-side comparison

| Dimension | A: continue existing adapter | B: fresh adapter from base |
|---|---|---|
| Technical feasibility | Possible in principle; needs trainable-load smoke test | Standard LoRA/QLoRA; needs smoke test |
| Translation preservation | Likely easier; replay can help | Needs explicit translation examples |
| Conversational target | Inherits translation bias and undocumented conversation data | Directly targets the chosen data mixture |
| Data documentation | Incomplete; SALT provenance and split unknown | Can be documented from the start |
| Licence position | Gemma + Apache-2.0 + SALT share-alike and gating; unresolved | Gemma + new data licences; cleaner but not automatically clean |
| Data volume for first run | 800 to 1,500 examples plus replay | 1,000 to 1,500 examples |
| Compatibility risk | Higher: exact adapter, PEFT, 4-bit, 256-token limit | Lower: new adapter on pinned base |
| Catastrophic forgetting | Translation may be forgotten | No existing adapter to forget, but base behaviour may shift |
| Compute | 24 GB GPU, 3 to 8 GPU-hours, estimate | 24 GB GPU, 3 to 8 GPU-hours, estimate |
| Schedule | Faster if data exists; data does not exist | Data-limited; pilot is possible |
| V1 suitability | Narrow continuation experiment only | Recommended path for a clean V1 feasibility test |

### 3.4 Recommendation

**Recommend Approach B for the V1 feasibility track.** The recommendation is based on provenance, control, and the target capability, not on an assumption that B will produce better Luganda. A is technically possible and may be useful for a narrow translation-preserving experiment, but it is not the right foundation for a V1 conversational claim.

The evidence is not sufficient to promise that either approach will work. It is sufficient to say which experiment is cleaner and which risks are better understood.

D-005 remains open. This report does not select the final architecture, parameter count, or training strategy. It recommends a bounded experiment that can inform that decision [R19].

---

## 4. Training dataset plan

### 4.1 The four data types are not interchangeable

| Data type | What it contains | What it can support | What it cannot support |
|---|---|---|---|
| Raw Luganda text | Monolingual sentences, paragraphs, articles, or transcripts | Language-model support data, tokenizer analysis, spelling and vocabulary checks, passage sources | Direct instruction following or conversation; raw text has no response target |
| Parallel translation data | Aligned source and target sentences | Translation training, translation evaluation, seed material for rewriting | Conversation; a translation pair is not a dialogue turn |
| Instruction-response examples | One user instruction and one assistant response | Formal generation, comprehension, QA, rewriting, constrained instruction following, uncertainty behaviour | Multi-turn context retention unless the example contains turns |
| Multi-turn conversation examples | A sequence of user and assistant turns with follow-ups | Conversational flow, context retention, short dialogue behaviour | Broad knowledge or reasoning by itself; dialogue data can be shallow or repetitive |

A translation pair can inspire a rewriting example, but the instruction and the formal Luganda response still need native authoring or native approval. A raw Wikipedia paragraph can be a comprehension passage, but the question and answer still need native authoring. A model-generated response is not gold data until a native teacher has reviewed it.

### 4.2 Existing project sources and their limits

No dataset is currently present in the repository, and no dataset is approved for training [R17]. The Phase 1 research record classifies the main candidates as follows [R18]:

| Source | Type | Licence status | Possible contribution | Main limitation |
|---|---|---|---|---|
| Sunbird SALT | Sentence-level multi-way parallel text and speech | CC BY-SA 4.0; gated automatic [R14] | Translation and rewriting seed material after approval; reference-text inspiration | Not conversational; share-alike; speaker and translator provenance unresolved; existing adapter trained on SALT |
| Luganda Wikipedia | Monolingual encyclopedic text | Live wiki CC BY-SA 4.0; mirror is stale and tagged differently | Comprehension passages, vocabulary and style reference | Not conversational; quality varies; article-level provenance and contamination risk |
| FLORES-200 `lug_Latn` | Professionally translated parallel evaluation set | CC BY-SA 4.0 per README and HF tag; gated | Translation evaluation only | Evaluation only; do not train; hidden test split; contamination risk |
| MAFAND-MT `en-lug` | News-domain parallel corpus | CC BY-NC 4.0 data; Apache-2.0 code | Translation or comprehension evaluation if non-commercial terms are accepted | Non-commercial restriction; news provenance unresolved; not conversational |
| Kimera English-Luganda corpus | Parallel text, including Bible material | CC0 repository claim over third-party sources; unresolved | Possible translation or linguistic reference after rights review | Upstream rights and alignment quality unresolved; religious register |
| MasakhaNER 2.0 and MasakhaPOS | Token-level linguistic annotations | AFL-3.0 | Linguistic probes and error analysis | Not conversational; not a source of gold responses |
| Tatoeba Luganda export | Small sentence collection | Licence not re-verified | Possible prompt inspiration | Small; sentence-level; licence unresolved |

The safe planning assumption is that **no existing source is approved for training**. SALT and Wikipedia are the most plausible sources for seed material, but both carry share-alike obligations and neither is a conversational corpus. FLORES is evaluation-only. MAFAND is non-commercial. Kimera's upstream rights are unresolved.

### 4.3 First experiment size and composition

The following is an illustrative first-run allocation. It is a proposal and an estimate, not a proven requirement.

**Target:** 1,000 to 1,500 total examples, with 15 to 20 percent held out for development and testing.

| Capability | Example form | Illustrative share | Illustrative count in a 1,200-example set |
|---|---|---:|---:|
| Formal Luganda generation | Instruction plus a formal Luganda response | 15 percent | 180 |
| Luganda comprehension | Luganda passage plus a question or summary task | 12 percent | 144 |
| Question answering | Answerable and unanswerable questions, including clarification | 13 percent | 156 |
| Rewriting into formal Luganda | Source text plus a native-approved formal rewrite | 15 percent | 180 |
| Instruction following | Constrained tasks: language, length, format, tone, or content | 15 percent | 180 |
| Short conversation | Two to four turn dialogues with follow-ups | 15 percent | 180 dialogues |
| Appropriate uncertainty | Questions with missing or ambiguous information | 10 percent | 120 |
| Translation replay, optional | English-Luganda pairs for preservation | 5 percent | 60 |
| **Total** | | **100 percent** | **1,200** |

The categories overlap. A formal QA item can also test instruction following. The counts are authoring targets, not independent labels. The conversation count refers to dialogues, not turns; a two-to-four turn dialogue contributes multiple turns to the token budget.

A 1,200-example set could be split by source or conversation, not by random sentence, into roughly 840 training examples, 180 development examples, and 180 held-out examples. The exact split must be approved before training. The held-out set must not be used for prompt tuning, few-shot examples, or checkpoint selection.

**Why this size.** A 1B model can show a directional change from roughly 1,000 to 2,000 high-quality examples, but that is not a guarantee. The number is chosen for review capacity and schedule, not because it is known to be sufficient. A 3,000 to 5,000 example V1 target is a later-stage estimate. More data of poor quality is worse than less data with native review.

**Why not 94,000 examples.** The existing adapter used about 94,000 translation-derived examples. That volume is not a template for conversational SFT. It is dominated by translation templates, it is expensive to review at native-speaker quality, and it does not answer the conversational question.

### 4.4 How native teachers should create, correct, approve, and review examples

1. **Owner gate.** The Project Director approves the data sources, licence review, teacher compensation, consent terms, and retention policy before authoring begins. No teacher approval is implied by this report.

2. **Style and register guide.** Native teachers define the target variety or varieties, orthography, formality levels, code-switching policy, and acceptable loanwords. The guide is a project artifact, not a model output.

3. **Authoring.** A native teacher writes the prompt and the response, or corrects a draft. Every example records an author pseudonymous ID, date, source, licence, register, and capability label.

4. **Independent review.** A second native teacher checks every gold example for meaning, grammar, naturalness, register, and instruction compliance. A third teacher adjudicates material disagreements. For a lower-cost pilot, one independent review per training example plus a 10 to 20 percent audit is a possible proposal, but the owner must approve it. Evaluation items should follow the stricter two-reviewer rule in the benchmark specification [R16].

5. **Calibration.** A small calibration set of about 20 to 30 examples is scored by all reviewers before the main review. Calibration items are separate from training and evaluation data. The purpose is to align judgments, not to produce scores.

6. **Rejection rules.** Reject machine-translated text that has not been native-reviewed, model-generated text presented as gold, examples with unresolved source rights, examples with personal data, and examples that duplicate a benchmark or feasibility item.

7. **Freeze and hash.** The approved dataset is versioned, counted, deduplicated, and hashed. The training, development, and held-out files are stored separately. The dataset record follows `data/README.md`.

8. **Contamination check.** Compare the training data against the feasibility items and any future benchmark items with exact matching, an 8-gram overlap check, and manual review of flagged pairs. Record what was checked and what remains unknown.

9. **No invented approvals.** A teacher's review of a model output is not approval to use that output as training data. A teacher's participation in a pilot is not approval of the full dataset.

### 4.5 Data licensing and provenance gates

Before any training use, each source needs a record with:

- source name and URL or acquisition method;
- licence and permitted uses, including redistribution, derivatives, and commercial use;
- acquisition date and dataset version;
- data owner and origin;
- language variety and domain;
- collection method and consent status;
- personal-information assessment;
- deduplication and quality checks;
- known limitations and biases;
- checksums and counts.

For teacher-authored data, the record must also state who owns the work, what licence the project receives, how attribution works, whether the teacher consents to reuse in model training, and how long the data is retained. These are unresolved and require owner decisions.

---

## 5. Hardware and cost assessment

### 5.1 Local Windows machine

Verified environment [R15]:

- Windows 11 Enterprise, build 10.0.26200.
- Intel Core i5-13420H, 8 physical cores and 12 logical processors.
- 7.7 GB visible RAM.
- No NVIDIA GPU.
- Local inference with 4-bit NF4, BF16 compute, and the adapter active completed without runtime errors.
- Process RSS reached 1,275.1 MB after both retest generations.
- System available memory was about 1.4 to 1.7 GB during the retest.

These are inference measurements. They do not establish training feasibility.

**Full fine-tuning.** A 1B model has about 1.0 billion parameters. BF16 weights are about 2.0 GB. Full fine-tuning adds gradients at about 2.0 GB and AdamW first and second moments at about 8.0 GB in FP32, before activations and temporary buffers. That is already over 12 GB, above the machine's 8 GB. Full fine-tuning is not feasible locally.

**LoRA without quantization.** Frozen BF16 weights are about 2.0 GB. The adapter's 13 million trainable parameters add small gradients and optimizer state, roughly 0.1 to 0.2 GB. Activations at sequence length 512, batch size 1, and gradient checkpointing might add 1 to 3 GB. The total might be roughly 3 to 5 GB, which could fit in 8 GB only with a clean system and careful settings. The measured 1.4 to 1.7 GB of available memory during inference shows how little headroom exists. This is an estimate, not a measured training run.

**QLoRA.** A 4-bit base is roughly 0.5 GB, plus adapter state and activations. Memory might be lower than unquantized LoRA, but the 4-bit training path on Windows CPU was not tested. The successful 4-bit inference run does not prove that 4-bit training works. The published QLoRA tooling is GPU-oriented [R20].

**CPU throughput.** The adapter card reports 94,542 examples at maximum length 256, one epoch, about 8 hours on a T4. That is roughly 24.2 million example-tokens in 8 hours, or about 841 example-tokens per second on a T4. A 1,500-example, maximum-length-512, three-epoch run is about 2.30 million example-tokens, or about 0.76 hours at the same throughput. A 50 to 100 times CPU slowdown implies roughly 38 to 76 hours of pure compute, before data loading, failures, and evaluation. These are arithmetic estimates from a source claim, not measurements. They support the conclusion that local training is not suitable for iteration in the remaining schedule.

**Merging.** Google's Gemma QLoRA guide states that merging a 1B adapter requires more than 30 GB of CPU memory [R11]. The local machine cannot plan to merge the adapter into the base model. Keep the adapter separate or merge on a hosted machine.

**Storage.** The adapter is 52 MB. A checkpoint with adapter weights and optimizer state is likely a few hundred megabytes. Three checkpoints are under 1 GB. A merged BF16 model is about 2 GB. The training data is likely under 100 MB. The D: drive has ample free space; C: is tighter. Storage is not the main blocker.

### 5.2 Hosted GPU options

A 24 GB GPU is sufficient for a 1B QLoRA run with a maximum length of 512 to 1024, batch size 1 to 4, and gradient checkpointing. A 16 GB T4 is the minimum used by Google's Gemma 1B QLoRA guide [R11]. A 24 GB card provides headroom for evaluation and larger batches. A 40 GB or 80 GB card is not required for this model size, though it may finish faster.

Current public on-demand prices checked on 2026-10-21:

| Provider and GPU | Memory | Listed price | Source |
|---|---:|---:|---|
| RunPod RTX 4090, Secure Cloud | 24 GB | $0.89 per hour | [R12] |
| RunPod L4, Secure Cloud | 24 GB | $0.59 per hour | [R12] |
| RunPod A100 80 GB, Secure Cloud | 80 GB | $1.79 per hour | [R12] |
| Lambda A10 | 24 GB | $1.29 per hour | [R13] |
| Lambda A100 40 GB | 40 GB | $1.99 per hour | [R13] |
| Lambda A6000 | 48 GB | $1.09 per hour | [R13] |

RunPod's page is marked as updated 2026-10-08 and states per-second billing. Community Cloud may be cheaper, but availability and host quality vary; the Secure Cloud rates above are used as a conservative planning basis. Lambda prices exclude applicable tax. Prices can change, and no account or GPU instance was created for this report.

### 5.3 Estimated runtime and total cost

Assumptions for a first experiment:

- 1,000 to 1,500 training examples.
- Maximum sequence length 512.
- One to three epochs.
- Effective batch size 16.
- 4-bit NF4 base with BF16 compute.
- 24 GB GPU.
- Setup, data loading, checkpointing, and a small evaluation included.

Estimated GPU time: 3 to 8 GPU-hours. This is deliberately conservative. The token-volume arithmetic above suggests under 2 hours of pure training on a T4-class GPU for a 1,200-example, three-epoch run; setup and failures can dominate a first run.

| Option | Estimated GPU hours | Estimated compute cost | Notes |
|---|---:|---:|---|
| RunPod RTX 4090 24 GB | 3 to 8 | $2.67 to $7.12 | Good default if available |
| RunPod L4 24 GB | 3 to 8 | $1.77 to $4.72 | Lower cost, slower than 4090 |
| RunPod A100 80 GB | 3 to 8 | $5.37 to $14.32 | More capacity than needed |
| Lambda A10 24 GB | 3 to 8 | $3.87 to $10.32 | Comparable capacity |
| Lambda A100 40 GB | 3 to 8 | $5.97 to $15.92 | Faster, more expensive |

Storage: a 20 to 30 GB volume is enough for the base model, adapter, environment, data, and checkpoints. RunPod lists container and running volume disk at $0.10 per GB per month [R12]. A 30 GB volume is about $3 per month, prorated for a short run. For a one-day run, storage is well under $1, but the exact container disk policy should be confirmed at checkout.

**Planning cap:** $10 to $20 for compute and storage, including a contingency for setup, a failed run, and a second short run. This is a proposal, not an approved budget. Native review and data authoring are excluded and are likely to dominate the total cost.

### 5.4 Non-compute costs

The GPU is not the main cost. Native authoring and review are.

For a 1,200-example first set:

- At 10 to 20 minutes of authoring per example, authoring is roughly 200 to 400 teacher-hours.
- At one independent review per example and 3 to 5 minutes per review, review is roughly 60 to 100 reviewer-hours.
- A 24-item feasibility evaluation with three models and two reviewers per response is 144 response reviews. At 5 to 10 minutes each, that is 12 to 24 reviewer-hours, plus calibration and adjudication.

These are workload estimates, not costs. The dollar cost cannot be stated without an owner-approved reviewer rate, compensation model, and consent terms. The schedule implication is clear: a 1,000 to 1,500 example pilot is ambitious for 27 days unless multiple teachers can contribute consistently.

---

## 6. Evaluation plan

### 6.1 Constraints from the approved benchmark specification

The benchmark specification is approved at version 1.0, but no benchmark item set, native review, benchmark version, or evaluation run is approved [R16]. The specification's item schema, nine categories, seven scoring dimensions, language rules, reference policy, native-review rules, run records, and contamination rules are constraints.

This report does not modify the specification. It proposes a separate feasibility evaluation, not a new benchmark version. The optional translation track remains optional and is not in scope until the owner approves it.

### 6.2 A separate feasibility set

Proposed feasibility set: 24 items, four per capability, using the existing item schema and review tooling. The six capabilities are formal comprehension, formal generation, rewriting into formal Luganda, question answering, instruction following, and short conversation. The brief lists six capabilities and later calls them five; this report covers all six.

- 24 items total, with four per capability.
- At least half of the items require a Luganda response.
- At least four items are multi-turn, with a follow-up that depends on an earlier turn.
- At least four items test appropriate uncertainty, including unanswerable or ambiguous questions.
- At least four items test a constrained instruction such as language, length, format, or register.
- A separate translation probe of 6 to 12 items may be added only if the owner approves the optional translation track.

The items must be original or rewritten so they are not near-duplicates of SALT, FLORES, MAFAND, Wikipedia, or a model's training data. If an item is inspired by a source, the source is recorded and the wording is changed. SALT sentences must not be used as conversational items because the existing adapter was trained on SALT [R16].

The 24-item set is a directional signal, not a statistically powered benchmark. A result on 24 items cannot establish general Luganda competence.

### 6.3 Models compared

1. **Base Gemma 3 1B Instruct**, pinned at `dcc83ea841ab6100d6b47a070329e1ba4cf78752`.
2. **Existing adapter**, pinned at `5d0f24b80a09f582708ff397c989331d7d7b536f`, with the pinned base.
3. **New adapter**, if training is later approved, trained from the same base revision.

Fairness rules:

- Use the same prompts for every model.
- Use the same chat template. The existing adapter's template is byte-identical to the base template, so there is no template difference to explain.
- Use greedy decoding with `do_sample=False`, the same maximum new tokens, and the same stop conditions.
- Record quantization, dtype, device, framework versions, latency, memory, and finish reason for every run.
- Do not tune prompts per model.
- Store raw responses verbatim, including English responses, empty responses, and errors.
- Do not use the feasibility items as few-shot examples, training data, or prompt-tuning material.

The base model may answer in English or refuse. That is a valid baseline result, not a reason to change its prompt.

### 6.4 Avoiding contamination

- Keep training data, development data, feasibility items, and future benchmark items in separate paths.
- Freeze and hash the feasibility item file before any model run.
- Split training and held-out data by source document or conversation, not by random sentence. Otherwise near-duplicate sentences can cross the split.
- Run exact matching and an 8-gram overlap check between training data and every evaluation item. Manually review flagged pairs.
- Record what was checked and what remains unknown. A negative check on available data does not prove the base model never saw the item.
- Treat SALT-based translation probes as in-domain for the existing adapter and report that status. Do not present them as clean out-of-domain evidence.
- Do not use FLORES for training. It is an evaluation resource.
- If items are published, consider a private holdout for future contamination checks.

### 6.5 Native review

- At least two native Luganda speakers review each item and each response.
- A third native reviewer adjudicates material disagreements.
- Reviewers are blind to model identity and see responses in randomized order where feasible.
- Reviewers score only the applicable dimensions: semantic correctness, grammar and naturalness, instruction compliance, relevance, context retention, factual reliability, and appropriate register.
- Use the five-point scale and anchors in the approved specification.
- Run a calibration set of about five items before the main review.
- Report exact agreement and agreement within one point per dimension, plus a chance-corrected statistic. The owner must approve the statistic and threshold before scoring.
- Do not use AI judgments, automated metrics, or model self-reports as a substitute for native review.
- Do not present a small feasibility result as proof of general Luganda competence.

### 6.6 Reporting

Report per-dimension results and failure counts, not a single composite score. The approved specification does not define a composite. Include:

- model and revision;
- base and adapter revisions;
- item file hash and version;
- chat template hash;
- quantization and dtype;
- decoding settings;
- raw response counts, including failures and exclusions;
- native-review records and agreement;
- cost and wall-clock time;
- explicit limitations.

A go/no-go rule should be approved before scoring. A reasonable proposal is: proceed to a larger data and training stage only if native reviewers find a material improvement over the base in instruction compliance and grammar or naturalness, with no severe semantic regressions. The exact threshold is not set here and must be approved by the owner.

---

## 7. Realistic outcome

### 7.1 What fine-tuning can plausibly improve

- Response-language compliance: answering in Luganda when instructed.
- Format and constraint following: length, structure, tone, and simple task instructions.
- Register control: formal versus everyday phrasing, if the training data distinguishes them.
- Short conversational patterns: greetings, clarification questions, short follow-ups.
- Rewriting and summarization style on topics represented in the data.
- Appropriate uncertainty phrasing when the model lacks information.

These are plausible because they are behavioural patterns that supervised examples can teach. They are not guaranteed, especially with 1,000 to 2,000 examples.

### 7.2 What requires better data

- Natural, grammatically correct Luganda across registers and regions.
- Orthography and spelling consistency.
- Cultural interpretation, idiom, and proverb use.
- Code-switching behaviour.
- Multi-turn context retention.
- Factual question answering and domain knowledge.

These depend on native-authored, reviewed examples. A model cannot learn a standard that the dataset does not encode.

### 7.3 What may be limited by the base model

- The 1B parameter budget may be too small for robust reasoning and factual reliability.
- The base model is instruction-tuned but its Luganda capability is not separately documented. The Gemma 3 model card reports training data in over 140 languages but does not report a Luganda evaluation [R8].
- The tokenizer may fragment Luganda words more than English words. Token length must be measured on the pilot; the adapter's 256-token limit may truncate conversation.
- The base model's knowledge cutoff and English-centric instruction tuning may limit culturally specific answers.
- Long multi-turn context may exceed the useful capacity of a 1B model even if the context window is larger.

### 7.4 What cannot be known without an experiment

- Whether the base model has enough latent Luganda to support fluent generation after SFT.
- Whether 1,000 to 1,500 examples produce a general behavioural change or only template memorization.
- Whether native reviewers see a material improvement over the base.
- Whether translation ability can be preserved while adding conversation.
- Whether the training run is stable on the available GPU and within the budget.
- Whether the data authoring and review process can produce enough quality in 27 days.

### 7.5 Overall judgment

There is a credible chance of a narrow, measurable improvement in instruction compliance and register. There is no credible basis to promise a useful general Luganda conversational assistant from this 1B model, this data volume, and this schedule. A well-run pilot can produce a useful go/no-go signal. A negative result would be informative and should not be hidden.

---

## 8. Main risks and unresolved questions

### 8.1 Main risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Data authoring slips | The schedule is data-limited, not GPU-limited | Start with a 100-example pilot; reduce scope rather than skip review |
| Licence and provenance unresolved | SALT share-alike, gated terms, Gemma terms, and teacher rights affect release | Legal review before training or distribution; use documented teacher-authored data where possible |
| Local training is impractical | 8 GB RAM and no NVIDIA GPU; CPU throughput is poor | Use a hosted 24 GB GPU if approved; keep local work to tooling and tiny smoke tests |
| 4-bit training path unverified | Inference success does not prove training support | Run a 50 to 100 example smoke test on the chosen GPU and record memory and time |
| Catastrophic forgetting | A conversational adapter may lose translation or base behaviour | Include a small translation replay set if translation matters; evaluate both before and after |
| Overfitting | 1B model with a small dataset can memorize templates | Use 1 to 3 epochs, held-out data, early stopping, and qualitative error analysis |
| Contamination | SALT and public text may overlap evaluation items | Separate paths, hashes, 8-gram checks, whole-document splits, and in-domain labels |
| Reviewer disagreement | Small panels and register variation can produce unstable scores | Calibration, two reviewers, adjudication, and agreement reporting |
| Base model limits | 1B may not have enough Luganda or reasoning ability | Scope claims; compare against base; treat a negative result as valid |
| Cost overrun | GPU and reviewer costs can grow | Set a compute cap and a reviewer budget before work; stop at the cap |
| Benchmark confusion | A 24-item feasibility set is not the approved benchmark | Keep it separate, label it a feasibility screen, and do not modify the specification |

### 8.2 Unresolved questions

- Is LugandaGPT V1 intended to be commercial? This affects MAFAND's CC BY-NC 4.0 restriction and the overall licence analysis.
- Can SALT be used for training under its gated terms? What do the gated terms require for share-alike, attribution, and redistribution?
- Does the adapter's Apache-2.0 declaration cover weights trained on SALT? This requires legal review, not an engineering assumption.
- What rights will the project receive from native teachers, and what consent and retention terms apply?
- Which Luganda variety or varieties are in scope, and which orthography standard will reviewers use?
- What is the target register mix for V1: formal, everyday, colloquial, or code-switched?
- What is the minimum quality bar for a go decision, and who approves the threshold?
- Is 1B the intended parameter count, or is this only a feasibility probe? D-005 remains open.
- Is a hosted GPU budget available, and what is the cap?
- Is the existing adapter retained only as a translation baseline, or is a separate translation-only screen wanted?
- Can the project recruit at least two native reviewers with the required time and consent?
- Does the base model's Gemma licence allow the intended distribution and hosted-service use after legal review?

---

## 9. Staged implementation plan and exact next decision

### 9.1 Staged plan

| Stage | Work | Output | Gate |
|---|---|---|---|
| 0. Decision | Choose A, B, or pause; approve the first-gate scope | Written owner decision | No work starts without it |
| 1. Licence and data design | Review Gemma, SALT, teacher-data, and any new source terms; define style guide and data record | Licence record, data specification, reviewer agreements | Owner approves data sources and budget |
| 2. Pilot | Author 100 examples across the six capabilities; calibrate reviewers; measure token lengths and review time | Pilot set, calibration notes, time estimate | Owner reviews pilot quality before scaling |
| 3. Dataset build | Author and review 1,000 to 1,500 examples; deduplicate; freeze splits | Versioned dataset, hash, counts, provenance | Owner approves dataset and split |
| 4. Training smoke test | On a hosted 24 GB GPU, train on 50 to 100 examples; record memory, time, loss, and failures | Smoke-test record | Owner approves full run and cap |
| 5. Full feasibility run | Train the chosen approach for 1 to 3 epochs within the cap; save adapter checkpoints | Adapter, training log, cost record | Stop at the cap |
| 6. Evaluation | Run base, existing adapter, and new adapter on the 24-item feasibility set; native review and adjudication | Raw responses, review records, agreement report | No score without native review |
| 7. Decision | Analyze per-dimension results, cost, and limitations; recommend next step | Feasibility report | Owner decides whether to continue, change data, or change candidate |

The plan fits 27 days only if Stages 1 and 2 start immediately and review capacity is real. If authoring slips, reduce the dataset size or stop. Do not compress native review to protect the date.

### 9.2 Exact decision requiring owner approval next

**Decision requested:** Approve or reject **Approach B, a fresh LoRA adapter from the pinned Gemma 3 1B Instruct base**, for a first gate limited to:

1. licence and provenance review for the proposed data sources;
2. native-teacher agreements, compensation, consent, and retention terms;
3. a 100-example authoring and review pilot across the six capabilities;
4. a hosted 24 GB GPU environment check and a 50 to 100 example training smoke test, with a total compute and storage cap of **$20**.

This approval would **not** authorize the full 1,000 to 1,500 example training run, a public benchmark, deployment, or release. A second owner approval would be required after the pilot and smoke test, once the dataset, training configuration, actual cost, and evaluation plan are known.

If the owner rejects Approach B, the alternatives are:

- authorize only a separate translation-only screen of the existing adapter, with no conversational claim; or
- pause the 1B path and evaluate another candidate for conversational and instruction-following ability.

No further inference, training, data acquisition, paid service, commit, or push should occur until the owner records that decision.

---

## References

[R1] Adapter repository, pinned revision: https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it/tree/5d0f24b80a09f582708ff397c989331d7d7b536f

[R2] Base model repository, pinned revision: https://huggingface.co/google/gemma-3-1b-it/tree/dcc83ea841ab6100d6b47a070329e1ba4cf78752

[R3] Adapter model card: https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it

[R4] Adapter configuration, local: `D:\LugandaGPT\models\luganda-gemma-adapter\adapter_config.json`; public: https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it/blob/main/adapter_config.json

[R5] Adapter training arguments, public: https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it/blob/main/training_args.bin

[R6] Adapter evaluation results, public: https://huggingface.co/AmplifiedAccess/Luganda-gemma-1b-it/blob/main/eval_results.json

[R7] Gemma Terms of Use: https://ai.google.dev/gemma/terms

[R8] Gemma 3 model card: https://ai.google.dev/gemma/docs/core/model_card_3

[R9] PEFT `PeftModel.from_pretrained` reference: https://huggingface.co/docs/peft/main/en/package_reference/peft_model

[R10] PEFT LoRA guide: https://huggingface.co/docs/peft/main/en/developer_guides/lora

[R11] Google Gemma QLoRA guide: https://ai.google.dev/gemma/docs/core/huggingface_text_finetune_qlora

[R12] RunPod GPU pricing, updated 2026-10-08: https://www.runpod.io/pricing

[R13] Lambda GPU pricing, checked 2026-10-21: https://lambda.ai/pricing

[R14] Sunbird SALT dataset metadata: https://huggingface.co/datasets/Sunbird/salt

[R15] EXP-2026-002, local: `docs/EXPERIMENT_LOG.md`; raw retest record: `reports/experiments/gemma-retest-20261020-232851.json`; native review: `reports/experiments/gemma-retest-20261020-232851-native-review.json`

[R16] Approved benchmark specification, local: `docs/BENCHMARK-SPECIFICATION.md`; workflow: `docs/BENCHMARK-WORKFLOW.md`

[R17] Data governance, local: `data/README.md`

[R18] Phase 1 research record, local: `docs/PHASE-1-RESEARCH.md`

[R19] Project decisions, local: `docs/DECISIONS.md`

[R20] Hugging Face 4-bit quantization and QLoRA article: https://huggingface.co/blog/4bit-transformers-bitsandbytes

---

## Appendix A: Verification notes

- The base has 999,885,952 parameters in 340 BF16 tensors, read from the local safetensors header. No model weights were loaded for inference in this investigation.
- The adapter has 13,045,760 parameters in 364 F32 tensors, read from the local safetensors header.
- The adapter chat template and the base chat template have the same SHA-256 hash, `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4`.
- The public evaluation file has 100 examples: 88 English-to-Luganda and 12 Luganda-to-English, counted from the prompt strings. The metrics in that file are source claims and were not reproduced.
- The public `training_args.bin` was inspected as a serialized configuration, not executed. It is an evaluation-time snapshot with `do_train=false` and retains training hyperparameters.
- No model weights or datasets were downloaded for this report. Public metadata and documentation were read. The adapter and base were already present locally.
- No GPU instance, account, paid API, or paid service was used.
- No repository files other than this report were created or modified by this investigation.

## Appendix B: Questions for the Project Director

1. Is the V1 target a conversational assistant, a translation assistant, or both?
2. Is the intended use commercial, non-commercial, or undecided?
3. Is there an approved budget for native authoring, native review, and hosted compute?
4. Which native teachers are available, for how many hours, and under what consent and compensation terms?
5. Should the existing adapter be kept only as a translation baseline, or should it receive a separate translation screen?
6. Which Luganda variety or varieties should the first dataset represent?
7. Is a 24-item feasibility screen acceptable as a directional test, separate from the approved benchmark?
8. Does the owner approve Approach B for the first gate described in section 9.2?
