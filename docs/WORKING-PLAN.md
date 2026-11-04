# Working plan: Sunflower baseline to a demonstrable Luganda model

**Status:** Proposal and planning record. It does not authorize data
acquisition, paid compute, paid API use, training, deployment, or release.
Those stay behind the approval gates in `AGENTS.md` section 7.

**Date:** 2026-11-02

**Non-claims:** No LugandaGPT model exists. No benchmark item, baseline run,
score, or comparison with Sunbird's models exists. Nothing below is a result.

**Evidence labels:** Verified (read from this repository), Source claim
(published by a third party, not reproduced), Estimate, Proposal.

---

## 1. Direction

The working direction is recorded in `docs/DECISIONS.md` D-017.

- Sunbird's `Sunbird/Sunflower-14B` is the baseline to beat and the preferred
  candidate base for a LoRA or QLoRA adapter. It is a candidate, not a
  selection. D-005 stays open until Gate 5.
- The project does not try to beat Sunflower everywhere. The target is a
  narrow, measured claim: better conversational Luganda in specific
  benchmark categories, shown by native-speaker scores.
- If the baseline shows Sunflower is already strong at conversation, the
  project changes niche (for example domain assistants for mobile money or
  farming) instead of forcing a claim the scores do not support.
- Weights are fine-tuned and served by the project. A hosted Sunbird API is
  at most a measurement tool, never the product (D-001).

## 2. Gate sequence

| Gate | Question | Work | Existing support | Approval needed |
|---|---|---|---|---|
| 0 | Can the data and the people be used? | Signed consent, compensation, licence, withdrawal, retention terms for the native team | D-008, D-009, D-019. Owner confirmed on 2026-11-03 that translators and reviewers consented in writing. Confirmation is the owner's; no copy is stored in the repository. | Owner |
| 1 | Is there reviewed Luganda data? | Translate 124 English source records (100 pilot, 24 evaluation) and second-review each | Translation Studio (`src/translation_studio/`), `data/source/pilot-v1/` | None for local work |
| 2 | Is there a benchmark? | Author about 50 items across the nine categories, native-review, freeze v1 | `docs/BENCHMARK-SPECIFICATION.md` (approved 1.0, D-007), `src/benchmark/` | Owner: allocation (O-02), reviewer panel, freeze |
| 3 | What does Sunflower actually do? | Run Sunflower-14B on the frozen benchmark, blind native scoring, failure analysis | `src/sunbird_api/` (built, see `docs/SUNBIRD-API.md`), run records and blind packets in `src/benchmark/`. The loop that runs benchmark items through the client is not written. | API use approved by D-018 within a request cap. Raise the cap only after checking Sunbird pricing and terms. |
| 4 | Retired | The Gemma 3 1B smoke test was archived on 2026-11-02 (D-018) | `archive/2026-11-02-gemma-runpod-reporter/` | None |
| 5 | Is Sunflower-14B the right base? | Check that the API model matches the Hugging Face weights, test fit on a rented GPU, review licences, then close D-005 | `docs/DECISIONS.md` | Owner. Closes D-005. |
| 6 | Does fine-tuning help? | QLoRA on Sunflower-14B weights using reviewed data, one run | None. A Sunflower training script has not been written. | Owner: GPU budget and configuration |
| 7 | Is it better, where? | Same benchmark, same panel, blind packets, at most two approved retrain cycles | `src/benchmark/review.py` | Owner per cycle |
| 8 | Can we show it? | Chat demo and investor material from measured results only | None | Owner: any deployment or release |

Gates 1 and 2 are the critical path. Both depend on native speakers, not on
compute.

## 3. Where this differs from the earlier workbook

`docs/LugandaAI_Plan.xlsx` was first drafted before this repository was
reviewed and was rebuilt on 2026-11-02 to follow it. Where the workbook and
the repository disagree, the approved repository documents win. The first
draft differed in these ways:

| Workbook draft | Approved position |
|---|---|
| 100 eval prompts in six categories | About 50 items in nine categories, draft allocation 6/7/6/6/5/5/6/5/4 (spec 5.3, O-02 still open) |
| Blind "winner" per prompt and a win rate | Each response scored 1 to 5 per applicable dimension by at least two native reviewers. Spec 11.4 allows no overall score, average, or percentage without owner approval. |
| A100 or H100 rental, about $140 total | D-008 caps the Gemma smoke gate at $20 on one RTX 4090. A 14B run has no approved budget. |
| Baseline through the Sunbird API | API price, terms, data retention, and benchmark-use permission are unverified (`docs/PHASE-1-RESEARCH.md` 6.4). Needs approval. |
| Sunflower training data is public | SALT is tagged CC BY-SA 4.0 and gated. Sunflower's training-data provenance is not documented in the metadata reviewed, so contamination is unknown, not clean (spec 17.3). |

A pairwise comparison between two models is a possible supplementary report
built from the same per-item scores. It is a proposal and needs owner
approval because it changes how results are summarized.

## 4. Sunflower-14B facts and gaps

Verified from `docs/PHASE-1-RESEARCH.md` section 6.4:

- Identifier `Sunbird/Sunflower-14B`, revision
  `83faf5eb318dd1814786944e279204de665646fa`, base `Qwen/Qwen3-14B`.
- 14,768,307,200 parameters, about 29.5 GB in BF16, Apache-2.0 declared,
  gated automatic access.
- No Luganda-only published score. The cited averages cover 31 languages.

Estimates carried from the same section:

- About 7.4 GB of weights at 4-bit. Adapter training on a 24 GB RTX 4090 is
  plausible but unmeasured. It must be tested before any budget is requested.

Source claims seen in public listings on 2026-11-02, from third-party
mirrors and Sunbird documentation pages, not from primary model cards:

- Newer Sunbird releases exist that the Phase 1 research does not cover:
  Sunflower-32B, a GRPO update of the 14B model, a Gemma-4-based preview
  with speech input, and a tutor model under the Gemma licence.
- The 32B card reportedly describes evaluation beyond translation and basic
  question answering as limited.
- Sunbird API documentation lists translation, speech, language
  identification, and summarization endpoints. A general chat endpoint was
  not confirmed.

Refresh the model survey before Gate 3 so the baseline is the strongest
available Sunbird model the budget allows.

## 5. Code and tooling gaps

- The Gemma 1B training code is archived (D-018). A QLoRA training script for
  Sunflower-14B does not exist yet. It needs tests and an approved GPU budget
  before it can run.
- `src/sunbird_api/` sends prompts and records usage. The loop that feeds
  frozen benchmark items through it and writes the run manifest and
  raw-response records `src/benchmark/runs.py` expects is not written. It
  waits for frozen items (Gate 2).
- No inference server or chat page exists. Needed only at Gate 8.

## 6. Investor and public claims

- Quote only measured, per-category, per-dimension results from a frozen
  benchmark, with the number of applicable items.
- State that the model builds on open-weight Sunbird and Qwen releases and
  on data whose licences are recorded in `data/README.md`.
- Do not say a model was trained or evaluated until a run record exists.
- Do not claim superiority over Sunbird in general.

## 7. Next actions

1. Owner: finalize consent and compensation records (Gate 0) and have the
   teachers continue in the Translation Studio (Gate 1). At the 2026-11-02
   snapshot of the local database, 124 items exist and 2 translations have
   been started, 1 of them reviewed.
2. Owner: decide the category allocation (O-02) so prompt authoring can start.
3. Project Director: register with Sunbird, set `SUNBIRD_API_TOKEN` locally,
   run `python -m sunbird_api check`, then a small `translate-source --limit 5`.
4. Engineering, no spend: write the benchmark runner for Gate 3 once items
   exist, and the Sunflower QLoRA script for Gate 6 with tests.

## 8. Preference comparison and early audience (D-025)

Training approach, confirmed by the Project Director on 2026-11-04: Sunflower-14B has already been pretrained, so the project skips pretraining and adapts it with supervised fine-tuning using QLoRA (Gate 6, budget D-021). A later preference step (Roadmap Phase 6b) asks native speakers to choose between two blind answers, to guide improvement and to choose between versions.

Early audience, no chat interface needed:
1. The native group rates two blind answers per prompt (Phase 6b), starting with Sunflower against our first fine-tuned model.
2. A hosted "which answer is better" page for wider Luganda speakers, with a consent notice. Hosting needs owner approval (Gate 8).
3. Share measured findings only (section 6), for example "Sunflower gave the wrong hour in N of M items", with the item counts.
4. Investor material shows evidence: native community size, reviewed data, benchmark results, number of preference ratings, and the run records.
