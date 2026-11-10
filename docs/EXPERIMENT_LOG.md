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

---

### EXP-2026-003 — First Sunflower-14B QLoRA fine-tune (train-v0.2)

- **Experiment ID:** EXP-2026-003
- **Date:** 2026-11-09
- **Research question:** Does a QLoRA fine-tune of Sunflower-14B on the native-written Luganda data improve the weak areas (clock time, part-of-day, hour conversion, not inventing dates) over the base model?
- **Hypothesis:** A small LoRA adapter trained on the time/day rule data plus native situations will correct the hour-conversion and part-of-day errors the base model makes, and generalise to held-out hours.
- **Dataset and version:** train-v0.2.jsonl, sha256 37c37b4e2cfb1aa351928756e816e020b8189a92b8dfe96296e22da1cbcea4d4. 4,762 chat examples: 4,000 SALT pairs (capped), 594 native situations (99 unique x6), 168 time/day (56 unique x3). Held-out hours {8,9,10,13,14} and held-out day facts kept out (D-020).
- **Data permissions / provenance:** Native data owned by the project (D-019). SALT CC BY-SA 4.0 (D-023, D-024). Base weights Sunbird/Sunflower-14B, Apache-2.0, gated access granted to owner.
- **Model and tokenizer configuration:** Base Sunbird/Sunflower-14B (Qwen3-14B, ~14.83B params). 4-bit NF4, double quant, bf16 compute. LoRA r=16, alpha=32, dropout=0.05, targets q/k/v/o/gate/up/down_proj. Trainable params 64,225,280 (0.433%). max_seq_len 1024, 1 epoch, batch 1 x grad_accum 16, lr 2e-4 cosine, seed 7, paged_adamw_8bit. (warmup_ratio unsupported by installed transformers and skipped.)
- **Compute environment:** RunPod, 1x RTX 4090 (24 GB). PyTorch 2.8.0+cu128.
- **Random seeds:** 7
- **Software versions:** transformers 5.22.2, peft 0.21.2, bitsandbytes 0.50.2, torch 2.8.0+cu128.
- **Budget and approval status:** D-021 ($20 cap). Actual training ~40.6 min; total pod use well under the cap.
- **Procedure:** Uploaded code+data bundle to pod; `python -m training.train_sunflower --train data/training/train-v0.2.jsonl --output runs/sunflower-v0.2 --confirm-approval D-021`. Adapter saved to runs/sunflower-v0.2. Then greedy generation (max_new_tokens 100, do_sample False) on 5 prompts, base vs base+adapter.
- **Metrics:** Training loss (start ~1.554, final train_loss 0.7517). Qualitative side-by-side on 5 prompts (2 held-out hours). No benchmark score computed; no blind native scoring yet.
- **Results (measured, verbatim outputs):**
  - Q1 "Ssaawa 9:00am ... ssaawa mmeka?" (held-out) — BASE: "...ssaawa ssatu ez'oku makya." ADAPTER: "Ssaawa ssatu ez'okumakya."
  - Q2 "Ssaawa 1:00pm ... ssaawa mmeka?" (held-out) — BASE: "...ssaawa 7:00 ez'olweggulo." ADAPTER: "Ssaawa musanvu ez'emisana."
  - Q3 "...meet at the market on Wednesday at 11 in the morning." — BASE: "...ku Lwokusatu ku ssaawa 11 ez'oku makya." ADAPTER: "Tujja kusisinkana ku Lwokusatu ssaawa ttaano ez'okumakya mu katale."
  - Q4 "...does not know the date..." — BASE: restated the task; no date invented. ADAPTER: "Sekakasa lunaku lutuufu lwa nsisinkano, sonyiwa obutakutegeeza kubanga simanyi"; no date invented.
  - Q5 "Good morning, how did you sleep?" — BASE: doubled/awkward. ADAPTER: "Wasuze otya?"
- **Failure analysis:** Two library issues fixed before the run completed: transformers 5.x rejected warmup_ratio (now only supported TrainingArguments are passed) and returned tokenised input as a dict (generation now unpacks it). No training failure.
- **Interpretation (not measured):** On these 5 prompts the adapter corrected the base model's wrong part-of-day (Q2) and its failure to convert the clock hour (Q3, ssaawa 11 -> ssaawa ttaano), including on held-out hours, and produced cleaner spellings and a natural reply for Q4. This is an encouraging first signal only; 5 author-graded prompts are not proof.
- **Reproducibility instructions:** `docs/TRAINING-SUNFLOWER.md`. Rebuild train-v0.2 with `python -m training_data.build --output data/training/train-v0.2.jsonl --repeat-native 6 --repeat-rule 3 --max-salt 4000`. Do not commit or print HF tokens.
- **Decision and next step:** Adapter runs/sunflower-v0.2 is the first LugandaGPT candidate. Next: freeze the benchmark and have the native group score the adapter vs base Sunflower **blind** (Gate 7) before any claim. No deployment or public launch approved by this run (D-026 prerequisites still open).

---

### EXP-2026-004 — Blind group comparison on pilot benchmark P1 (base vs v0.2 adapter)

- **Experiment ID:** EXP-2026-004
- **Date:** 2026-11-10
- **Research question:** On the frozen pilot set P1, which answer does the native group prefer when it does not know which model wrote it?
- **Hypothesis:** The v0.2 adapter is preferred on time, day and formal items and is no worse elsewhere.
- **Dataset and version:** Pilot benchmark P1, 29 items, `data/benchmark/frozen/pilot-p1-0.7-draft.jsonl`, SHA-256 3a7b909ac817fad6814bcce2be0dd656146a99b8b2ae757a5f1c02cd302fa8ad (D-027).
- **Data permissions / provenance:** Project-authored items confirmed by GROUP-1.
- **Model and tokenizer configuration:** Sunbird/Sunflower-14B, 4-bit NF4, bf16 compute, with and without adapter runs/sunflower-v0.2 (EXP-2026-003). Greedy, max_new_tokens 400, thinking disabled.
- **Compute environment:** RunPod, 1x RTX 4090.
- **Random seeds:** Pairing seed 11 (A/B side).
- **Software versions:** As installed on the pod by `pip install -U` on 2026-11-10 (not recorded per package).
- **Budget and approval status:** D-021.
- **Procedure:** `python -m benchmark.run_model` for each model; `python -m benchmark.blind make`; GROUP-1 scored the blind page together; `python -m benchmark.blind tally`. Raw files: `data/benchmark/answers-base.jsonl`, `answers-v0.2.jsonl`, `data/benchmark/blind/blind-p1-v0.2-Group-1-2026-11-10.csv`, key in `data/benchmark/keys/`.
- **Metrics:** Preference counts per category. No overall score (spec 11.4).
- **Results (measured):** Preferred v0.2 / preferred base / both good / both bad. Everyday 3/2/2/0. Formal 3/1/2/0. Instruction 1/1/2/0. Code-switching 1/1/1/2. Explanation 1/0/3/0. Factuality 1/1/0/1. All 29 items: 10/6/10/3. Seen-hour items: FORMAL-001 both good, CODESWITCH-002 both bad.
- **Failure analysis:** v0.2 faults seen in the answers: wrong English hour for held-out Luganda hours in EVERYDAY-004 (answered "ssaawa kkumi") and EVERYDAY-002 (answered "ssaawa emu ey'okumakya"); clock times added that the prompt did not give (CODESWITCH-003, FORMAL-006, FORMAL-002); an English reply to a Luganda request (CODESWITCH-005); a confident weather forecast where it should decline (FACTUALITY-002). Base faults: wrong day (EVERYDAY-007), repeated the question (EVERYDAY-005), invented organisation, date and place names in notices (FORMAL-004, FORMAL-006), English answer (EXPLANATION-001). Both invented a description of a book that may not exist (FACTUALITY-003).
- **Limits:** One group scoring together, 29 items, differing writing styles may reveal the model, wording of four time questions ("zibeera mmeka") differs from the training wording ("ziba mmeka").
- **Reproducibility instructions:** Commands above with the frozen file and the adapter.
- **Decision and next step:** Pilot evidence only. v0.2 is not ready for release. Next: build v0.3 data to address the listed v0.2 faults, retrain, and repeat this comparison on P1.
