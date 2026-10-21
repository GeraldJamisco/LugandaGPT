# Experiment Log

A standard record format for every experiment. **The records included below
are EXP-2026-001 and EXP-2026-002.** Do not add a record unless the experiment
actually happened; do not represent an unrun experiment as completed.

Use the template below for each experiment. Keep one entry per experiment,
appended in chronological order.

---

## Template

```
### EXP-YYYY-NNN — <short title>

- **Experiment ID:** EXP-YYYY-NNN
- **Date:** <date the experiment was run>
- **Research question:** <what we are trying to learn>
- **Hypothesis:** <expected outcome and reasoning>
- **Dataset and version:** <name and version, or "none">
- **Data permissions / provenance:** <license, source, approval reference>
- **Model and tokenizer configuration:** <config or "undecided">
- **Compute environment:** <hardware, provider, or "local">
- **Random seeds:** <seed values, where applicable>
- **Software versions:** <key libraries and versions>
- **Budget and approval status:** <approved budget, approver, or "not required">
- **Procedure:** <steps performed, enough to reproduce>
- **Metrics:** <metrics and how computed>
- **Results:** <measured results only; label any assumption>
- **Failure analysis:** <what went wrong or was inconclusive, and why>
- **Reproducibility instructions:** <commands/configs to repeat this>
- **Decision and next step:** <what we decided as a result>
```

---

## Field notes

- **Results** must contain measured values only. Any interpretation belongs
  in **Decision and next step**, clearly labelled as interpretation.
- **Data permissions / provenance** must reference the dataset's governance
  record in `data/README.md`. An experiment using unapproved data must not
  proceed.
- **Budget and approval status** must be filled in. Paid compute or paid API
  usage requires explicit project-director approval in advance
  (see `AGENTS.md`).
- **Reproducibility instructions** should be sufficient for another engineer
  to repeat the experiment.

---

### EXP-2026-001 - Luganda-Gemma 1B 4-bit CPU smoke test

- **Experiment ID:** EXP-2026-001
- **Date:** 2026-10-21 (local); 2026-10-20T22:00:31Z (UTC)
- **Research question:** Can the pinned `AmplifiedAccess/Luganda-gemma-1b-it`
  adapter load and generate one short response on the local Windows CPU-only
  machine with 4-bit NF4 quantization?
- **Hypothesis:** The 4-bit CPU path might fit in 7.7 GB of RAM and complete a
  short generation, but latency and output quality were uncertain. The FP32
  fallback was expected to be too tight.
- **Dataset and version:** None for this smoke test.
- **Data permissions / provenance:** No new dataset was acquired. The adapter
  card names `Sunbird/salt`. SALT is gated and tagged CC BY-SA 4.0; the
  adapter's Apache-2.0 declaration does not resolve the share-alike or
  provenance obligations. No SALT data was downloaded or used here.
- **Model and tokenizer configuration:** Base `google/gemma-3-1b-it` at
  `dcc83ea841ab6100d6b47a070329e1ba4cf78752`; adapter
  `AmplifiedAccess/Luganda-gemma-1b-it` at
  `5d0f24b80a09f582708ff397c989331d7d7b536f`; base tokenizer at the base
  revision; adapter `chat_template.jinja` with SHA-256
  `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4`;
  PEFT LoRA r=16, alpha=32, target modules q, k, v, o, gate, up, down.
- **Compute environment:** Local Windows 11 Enterprise 10.0.26200, Intel
  Core i5-13420H, 8 physical cores and 12 logical processors, 7.7 GB visible
  RAM, no NVIDIA GPU.
- **Random seeds:** None. Greedy decoding with `do_sample=False`.
- **Software versions:** Python 3.13.14, torch 2.7.1+cpu, transformers
  4.53.2, peft 0.18.1, accelerate 1.8.1, bitsandbytes 0.50.2,
  huggingface_hub 0.34.3, safetensors 0.8.0, sentencepiece 0.2.2.
- **Budget and approval status:** Local CPU inference only. No paid API or
  paid compute. Owner approved Gemma terms acceptance, the pinned download,
  and one 4-bit CPU smoke test on 2026-10-21.
- **Procedure:** Created `.venv-gemma`; installed the pinned stack; logged in
  interactively to Hugging Face and accepted the Gemma terms; downloaded only
  the pinned inference files; verified the base and adapter weight SHA-256
  values against the Hugging Face LFS metadata; loaded the base with
  bitsandbytes 4-bit NF4, double quantization, and FP32 compute dtype on CPU;
  attached the adapter with PEFT; applied the adapter chat template; generated
  with greedy decoding and `max_new_tokens=64`; recorded latency, token counts,
  process memory, and system available memory.
- **Metrics:** Load time 13.025 s. Generation time 16.332 s. Total 29.388 s.
  Prompt tokens 29. Output tokens 17. Finish reason `eos_or_stop`. Process RSS
  326.9 MB before load, 605.6 MB after load, and 1309.9 MB after generation.
  System available memory 2172.4 MB before load, 2170.6 MB after load, and
  1758.5 MB after generation. Base weight SHA-256
  `3d4ef8d71c14db7e448a09ebe891cfb6bf32c57a9b44499ae0d1c098e48516b6`.
  Adapter weight SHA-256
  `05fdfa2f733b81eb24c6d6604086760b020c64a0e9ae4d59255dd00ac6f82c6a`.
- **Results:** Status `completed`; no exceptions. Output verbatim:
  `Nnamukuba omuntu omulala nga nnamukolera.` The warning
  `top_p` and `top_k` flags were reported as invalid and ignored because
  sampling was disabled.
- **Failure analysis:** No runtime failure. The output has not been reviewed
  by a native Luganda speaker, so this record does not establish correctness,
  naturalness, register, or suitability for Version 1.
- **Reproducibility instructions:** Raw record:
  `reports/experiments/gemma-smoke-20261020-220000.json`. Reuse the pinned
  revisions, software versions, 4-bit NF4 configuration, adapter chat
  template, prompt, and greedy decoding settings above. Do not record or
  commit access tokens.
- **Decision and next step:** The 4-bit CPU path is technically usable for a
  short smoke generation on this machine. This is not evidence that the model
  meets the Version 1 capabilities. The next step is owner review of the
  output and a separate decision on native review and the 10-item feasibility
  screen. No training or fine-tuning is approved.

---

### EXP-2026-002 - Luganda-Gemma 1B 4-bit BF16 diagnostic retest

- **Experiment ID:** EXP-2026-002
- **Date:** 2026-10-21 (local); 2026-10-20T23:29:36Z (UTC)
- **Research question:** With the adapter active and BF16 compute, does the
  pinned Luganda-Gemma 1B adapter produce a usable Luganda translation for
  the adapter card's published example and a Luganda response to a
  teacher-supplied conversational prompt?
- **Hypothesis:** Using the adapter's documented prompt formats and BF16
  compute might remove the configuration deviations in EXP-2026-001. Quality
  and instruction following were still uncertain because the adapter card
  reports translation metrics only.
- **Dataset and version:** None. The translation prompt is the adapter card's
  published example. The conversational content is a teacher-supplied Luganda
  sentence. No benchmark item or reference answer was generated.
- **Data permissions / provenance:** No new dataset was acquired or used.
  SALT remains gated and CC BY-SA 4.0; the adapter's Apache-2.0 declaration
  does not resolve share-alike or provenance. The teacher-supplied sentence
  is recorded for review only and was not used for scoring.
- **Model and tokenizer configuration:** Base `google/gemma-3-1b-it` at
  `dcc83ea841ab6100d6b47a070329e1ba4cf78752`; adapter
  `AmplifiedAccess/Luganda-gemma-1b-it` at
  `5d0f24b80a09f582708ff397c989331d7d7b536f`; tokenizer at the base
  revision; adapter `chat_template.jinja` with SHA-256
  `7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4`;
  4-bit NF4 with double quantization and BF16 compute; PEFT LoRA r=16,
  alpha=32, target modules q, k, v, o, gate, up, down.
- **Compute environment:** Local Windows 11 Enterprise 10.0.26200, Intel
  Core i5-13420H, 8 physical cores and 12 logical processors, 7.7 GB visible
  RAM, no NVIDIA GPU, CPU inference.
- **Random seeds:** None. Greedy decoding with `do_sample=False`.
- **Software versions:** Python 3.13.14, torch 2.7.1+cpu, transformers
  4.53.2, peft 0.18.1, bitsandbytes 0.50.2.
- **Budget and approval status:** Local CPU inference only. No paid API or
  paid compute. Owner approved one controlled diagnostic retest on
  2026-10-21. Teacher Schmarc was identified by the owner as the source of
  the conversational content; the post-run native review was received on
  2026-10-21 and is recorded in
  `reports/experiments/gemma-retest-20261020-232851-native-review.json`.
- **Procedure:** Loaded the pinned base with 4-bit NF4, double quantization,
  and BF16 compute on CPU; attached the pinned adapter with PEFT; verified
  `PeftModelForCausalLM`, active adapter `default`, 13,045,760 LoRA
  parameters in 364 tensors, and 7 target modules; applied the adapter chat
  template; generated from the published translation prompt and the
  teacher-supplied conversational prompt with greedy decoding and
  `max_new_tokens=128`; recorded rendered prompts, prompt and output token
  IDs, outputs, finish reasons, latency, process and system memory, and
  console warnings.
- **Metrics:** Total wall time 43.072 s. Process RSS 327.3 MB before load,
  559.3 MB after load, and 1,275.1 MB after both generations. System available
  memory 1,443.1 MB before load and 1,734.5 MB after both generations.
  Translation: 25 prompt tokens, 24 output tokens (23 visible), 18.799 s,
  finish reason `eos`. Conversation: 37 prompt tokens, 13 output tokens
  (12 visible), 10.394 s, finish reason `eos`.
- **Results:** Adapter active. No runtime exceptions. Translation output
  verbatim:
  `Abalimi beetaaga ensigo ennungi okwongera ku bikungulwa byabwe.`
  Teacher-supplied comparison sentence, not used for scoring:
  `Abalimi betaaga ensigo enunji okwongera okulogoosa mu makungula gaabwe`.
  Conversational output verbatim:
  `Farmers need to plant more maize seeds to increase their production.`
  Two `top_p` and `top_k` invalid-flag warnings appeared on the console;
  sampling was disabled, so they did not affect decoding. Per-prompt warning
  capture was empty.
- **Native review:** Teacher Schmarc, 2026-10-21. Translation: "the published
  translation is excellent on this if i am to award marks, i would give it
  99%". Conversation: "the prompt says to respond in luganda but instead
  english is the one that was produced, which means that instructions were
  not followed"; the teacher also noted the introduced words `maize`
  (`kasooli`) and `production`, with `production` and `harvest` overlapping
  slightly with `amakungula`. The 99% is an informal judgment on one example,
  not a benchmark score.
- **Failure analysis:** Teacher Schmarc judged the translation example
  excellent and gave it an informal 99%. That result applies to this single
  published example only; it does not establish general translation quality.
  The conversational example failed the observable language instruction: the
  prompt said `Respond in Luganda`, but the output is English. Teacher
  Schmarc confirmed that instructions were not followed and noted that the
  output introduced `maize` (`kasooli`) and `production`, with `production`
  and `harvest` overlapping slightly with `amakungula`. The adapter card
  reports translation-only evaluation examples, so the conversational
  failure is consistent with the documented training objective, but no root
  cause is claimed. The run used CPU rather than a GPU, and BF16 compute
  rather than the original FP32 smoke configuration.
- **Reproducibility instructions:** Raw record:
  `reports/experiments/gemma-retest-20261020-232851.json`. Reuse the pinned
  revisions, 4-bit NF4 configuration, BF16 compute, adapter chat template,
  prompts, and greedy settings above. Do not record or commit access tokens.
- **Decision and next step:** Measured result: the adapter runs with BF16
  compute and the active PEFT adapter; it produced a Luganda translation that
  Teacher Schmarc judged excellent on the single published example, and an
  English response that failed the Luganda instruction. Interpretation: the
  adapter is a translation-only candidate supported by one positive native
  review. It is not a demonstrated conversational or instruction-following
  candidate. The proposed next step is an owner decision on a small
  translation-only feasibility screen. If Version 1 requires conversation or
  instruction following, this adapter alone is insufficient and another
  candidate or additional data and training would need separate approval. No
  further experiment, training, or fine-tuning is approved.
