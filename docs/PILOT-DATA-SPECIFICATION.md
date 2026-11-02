# Pilot Data Specification: 100 Training Examples and 24 Evaluation Items

**Status:** English source draft exists. No Luganda translation, native review, provenance record, formal consent record, translator agreement, compensation record, or benchmark item exists. The English draft is not training-ready.

**Scope:** This document defines the files that `src/training/data.py` and `src/training/pilot.py` will accept for the bounded smoke test. It also records the separate English source draft that the native-speaking team will translate. It does not approve a source, create a Luganda dataset, or authorize acquisition. It is separate from `docs/BENCHMARK-SPECIFICATION.md`, which remains unchanged.

## 1. Two separate collections

| Collection | Count | Purpose | File |
|---|---:|---|---|
| Pilot train | 70 | Smoke-test training only | `data/pilot/v1/train.jsonl` |
| Pilot validation | 15 | Validation loss and checkpoint monitoring only | `data/pilot/v1/validation.jsonl` |
| Pilot held-out | 15 | Overfitting and memorization check only | `data/pilot/v1/heldout.jsonl` |
| Evaluation | 24 | Directional feasibility screen, four per capability | `data/evaluation/feasibility-v1.jsonl` |
| Provenance | 1 record | Rights, consent, counts, and file hashes | `data/provenance/pilot-v1.json` |

### 1.1 English source draft

The project has an English source draft before translation:

| File | Count | Status |
|---|---:|---|
| `data/source/pilot-v1/source_draft.json` | 124 objects | Canonical draft, 100 pilot and 24 evaluation. |
| `data/source/pilot-v1/pilot_en.jsonl` | 100 | Generated from the canonical draft. |
| `data/source/pilot-v1/evaluation_en.jsonl` | 24 | Generated from the canonical draft. |
| `data/source/pilot-v1/translator_export.csv` | 124 | Translator and review workbook. |
| `data/source/pilot-v1/source_manifest.json` | 1 | Counts, composition, status, and checksums. |

Each source record has a stable `item_id`, `collection`, `primary_capability`, `secondary_capabilities`, `source_language`, `source_prompt`, `source_context`, `expected_response_criteria`, `reference_answer_or_rubric`, `required_constraints`, `uncertainty_behavior`, `conversation_turns`, `intended_register`, `proposed_split`, `translation_status`, `native_review_status`, `source_provenance`, `response_length`, `requires_prior_context`, and `notes`.

`conversation_turns` holds the prior turns before the final user prompt. It is empty for single-turn items. For a short conversation, it contains complete user and assistant pairs and the final user prompt is `source_prompt`. The final assistant response is the target response described by the criteria and the English reference or rubric.

The source validator requires:

- 100 pilot items with 17/17/17/17/16/16 capability counts;
- 24 evaluation items with four per capability;
- 70 train, 15 validation, and 15 held-out pilot items;
- no evaluation item in a training split;
- `source_language: en` for every item;
- `translation_status: pending` and `native_review_status: pending` for every item;
- project-original provenance with no approval reference;
- no exact duplicate text and no 8-word overlap between records;
- at least 30 multi-sentence responses, 12 uncertainty cases, 10 constraint examples, and 8 context-dependent conversations.

The source draft is not accepted by `validate-data`. The training validator requires Luganda messages, native-reviewed references, approved reviews, resolved licences and consent, and passing validation flags. The English draft must not be copied into `data/pilot/v1` to bypass those checks.

The native-speaking team translates the source and a second native speaker reviews it. The workflow and column definitions are in `data/source/pilot-v1/TRANSLATOR-GUIDE.md`. The current owner confirmation is recorded in `docs/DECISIONS.md` D-009 and in the source manifest. It is an owner report, not a signed agreement or formal consent record.

The translator CSV is an intermediate work product. It is not a training file and is not read by `validate-data`. After review, the coordinator converts approved rows into the training JSONL schema and records provenance. A completed CSV does not itself authorize training.

The pilot and the evaluation set are not the benchmark. The 24 evaluation items are not benchmark items and must not be added to `docs/BENCHMARK-SPECIFICATION.md`. The held-out split is not used for training, prompt tuning, few-shot examples, or checkpoint selection.

## 2. Pilot composition

The validator requires these exact counts, but they are authoring targets, not independently verified quality labels.

| Capability | Count | Response form |
|---|---:|---|
| `formal_comprehension` | 17 | Luganda passage plus a question or summary instruction, answered in Luganda. |
| `formal_generation` | 17 | Formal Luganda paragraph or short essay from an instruction. |
| `rewriting_formal_luganda` | 17 | Source text rewritten in formal Luganda with meaning preserved. |
| `question_answering` | 17 | Luganda question answered in Luganda, including uncertainty cases. |
| `instruction_following` | 16 | Constrained task with language, length, format, or tone requirements. |
| `short_conversation` | 16 | At least two user turns, with a context-dependent follow-up. |
| **Total** | **100** | |

The evaluation set contains exactly four items for each of the six capabilities.

## 3. Pilot record schema

Each pilot JSONL line is one object. Unknown fields are rejected. IDs must match `P-NNN`.

| Field | Type | Rule |
|---|---|---|
| `pilot_id` | string | Unique `P-NNN` identifier. |
| `capability` | enum | One of the six labels in section 2. |
| `messages` | array | Alternating `user` and `assistant` messages. At least one complete turn. No system message. |
| `language` | enum | `lg` or `lg-en`. |
| `register` | enum | `formal`, `everyday`, or `mixed`. |
| `expected_response` | object | See section 4. |
| `reference_answer` | string or null | Required and non-empty for a reviewed reference. Null when `reference_status` is `not_required`. |
| `reference_status` | enum | `authored`, `reviewed`, or `not_required`. Training requires `reviewed` for determinate tasks and rejects `authored` everywhere. |
| `accepted_alternatives` | array | Native-approved alternatives. Must be empty when there is no reference answer. |
| `author_id` | string | Pseudonymous teacher ID matching `T-NNN`. No real name in the data file. |
| `reviewers` | array | Review records. See section 5. |
| `review_status` | enum | `draft`, `ambiguity_checked`, `native_reviewed`, `approved`, or `excluded`. Training requires `approved`; `excluded` records must not be in a split file. |
| `source` | enum | `teacher_authored`, `adapted`, or `project_original`. |
| `source_notes` | string | What was adapted and from where, or a specific original-source statement. `"original"` is rejected for an `adapted` record. |
| `licence` | string | Recorded agreement or licence reference. Unresolved values block training. |
| `consent_ref` | string | Consent record reference that matches the provenance file. Unresolved values block training. |
| `pii_check` | enum | `none`, `redacted`, or `needs_review`. Training requires `none` or `redacted`. |
| `contamination_notes` | string | Exact, 8-gram, and manual checks against the evaluation set and benchmark items. Unresolved text blocks training. |
| `validation` | object | All eight boolean checks in section 6 must be true. |
| `split` | enum | `train`, `validation`, or `heldout`, matching the file. |
| `notes` | string | Optional reviewer or ambiguity note. |

### 3.1 Deterministic reference rules

A natively reviewed `reference_answer` is required for:

- `formal_comprehension`;
- `rewriting_formal_luganda`;
- `question_answering`;
- `instruction_following`.

`formal_generation` and `short_conversation` may use `not_required` when the rubric is sufficient. If a reference is supplied for either, it must still be `reviewed`; `authored` is not training-ready.

## 4. Expected-response rubric

`expected_response` is not a model answer. It is a compact review rubric.

| Field | Rule |
|---|---|
| `must_include` | Array of required ideas or strings. At least one of `must_include` or `must_not_include` must be non-empty. |
| `must_not_include` | Array of prohibited content or failure modes. |
| `max_words` | Integer from 1 to 1000. |
| `format` | Non-empty format label or description, with no placeholder markers. |
| `uncertainty_behavior` | `not_applicable`, `state_uncertainty_if_unanswerable`, or `ask_clarifying_question_if_ambiguous`. |

## 5. Review records

Each reviewer object has exactly these fields:

```json
{
  "reviewer_id": "R-001",
  "role": "independent_review",
  "date": "2026-10-20",
  "decision": "approved",
  "notes": ""
}
```

Rules enforced by the validator:

- `reviewer_id` matches `R-NNN` and is unique within the record.
- The author cannot be the independent reviewer.
- `role` is `independent_review`, `audit`, or `adjudicator`.
- `date` is not in the future.
- `decision` is `approved`, `revise`, or `exclude`.
- Training requires at least one approved independent review and rejects any non-approved independent or audit review.
- Every pilot record needs an approved independent review.
- An audit is required for at least 7 of the 70 training records, which is 10 percent rounded up. An approved audit review covers one record.
- Every evaluation item needs at least two approved independent reviews. A material disagreement should be adjudicated by a third native reviewer and recorded, but the validator cannot infer a disagreement from scores and does not enforce an adjudicator field.

Native review is the reference standard. An AI judgment about Luganda quality is not a substitute. A review of a model output is not permission to use that output as training data.

## 6. Validation object

All eight fields must be present and boolean. Training requires every field to be `true`.

| Field | Meaning |
|---|---|
| `schema` | Types, enums, IDs, and required fields pass. |
| `language` | A native reviewer has checked the language and approved any loanwords. |
| `instruction_response` | The response answers the instruction and preserves meaning. |
| `duplicate` | Exact and near-duplicate checks pass. |
| `contamination` | The record is checked against evaluation and benchmark items. |
| `pii` | No unredacted personal data remains. |
| `token_length` | The pinned tokenizer check passes. |
| `review_complete` | Required review and adjudication are complete. |

The code checks that the declared flags are true. It does not independently prove that the human review happened. The review record and provenance are the evidence.

## 7. Evaluation record schema

Evaluation items use `E-NNN` IDs and JSONL objects with these fields:

`eval_id`, `capability`, `messages`, `language`, `register`, `expected_response`, `reference_answer`, `reference_status`, `accepted_alternatives`, `author_id`, `reviewers`, `review_status`, `source`, `source_notes`, `licence`, `consent_ref`, `pii_check`, and optional `notes`.

Differences from pilot records:

- no `split` field;
- no `validation` object;
- no `contamination_notes` field;
- at least two approved independent reviewers in strict mode;
- capability counts must be exactly four each, for 24 items total.

The evaluation items are authored and reviewed separately from the pilot. They must not be used as training examples or few-shot prompts.

## 8. Provenance record

The file `data/provenance/pilot-v1.json` is one JSON object. These fields are required:

| Field | Rule |
|---|---|
| `dataset_name` | Non-empty name. |
| `dataset_version` | Must exactly match `dataset.version` in the YAML. |
| `source` | Non-empty description. |
| `acquisition_method` | Non-empty description. |
| `licence_references` | Non-empty unique list. Every record `licence` must appear here. |
| `permitted_uses` | Must include `training`, `evaluation`, `derivatives`, and `research_reporting` in strict mode. |
| `acquisition_date` | `YYYY-MM-DD`, not in the future. |
| `data_owner` | Non-empty responsible party. |
| `language_varieties` | Non-empty unique list. |
| `domains` | Non-empty unique list. |
| `collection_method` | Non-empty description. |
| `consent` | Non-empty list of consent objects. |
| `compensation` | Object with `status` and `details`. |
| `pii_assessment` | Non-empty description. |
| `deduplication` | Non-empty description of exact and 8-gram checks. |
| `limitations` | Non-empty statement. |
| `counts` | Exact object with `train` 70, `validation` 15, `heldout` 15, `evaluation` 24. |
| `split_sha256` | Exact SHA-256 for each of the four data files. |
| `approval_reference` | Resolved owner or project approval reference. |

Optional fields are `source_url`, `collection_dates`, `review_process`, `retention`, `contact`, and `notes`.

Each consent object has `reference`, `teacher_id`, `status`, `withdrawal_terms`, `retention`, and optional `notes`. `status` is `signed`, `pending`, or `withdrawn`. Strict validation requires `signed`. The `teacher_id` must match the `author_id` of every record using that consent reference. A record cannot point to a consent record for a different teacher.

`compensation.status` is `agreed`, `paid`, or `pending`. Strict validation requires `agreed` or `paid`. The details must state the rate, schedule, and payment method.

Unresolved markers such as `pending`, `tbd`, `todo`, `unresolved`, or `needs review` are rejected in strict fields. A public web page is not a licence. Accessibility is not permission to train or redistribute.

### 8.1 Shape example

This example shows field shape only. It is not a real provenance record and must not be used as data.

```json
{
  "dataset_name": "EXAMPLE NAME",
  "dataset_version": "pilot-v1",
  "source": "EXAMPLE SOURCE",
  "acquisition_method": "EXAMPLE METHOD",
  "licence_references": ["LIC-001"],
  "permitted_uses": ["training", "evaluation", "derivatives", "research_reporting"],
  "acquisition_date": "2026-10-20",
  "data_owner": "EXAMPLE OWNER",
  "language_varieties": ["Luganda"],
  "domains": ["conversation"],
  "collection_method": "EXAMPLE COLLECTION METHOD",
  "consent": [
    {
      "reference": "CONSENT-001",
      "teacher_id": "T-001",
      "status": "signed",
      "withdrawal_terms": "EXAMPLE WITHDRAWAL TERMS",
      "retention": "EXAMPLE RETENTION TERMS"
    }
  ],
  "compensation": {
    "status": "agreed",
    "details": "EXAMPLE RATE AND SCHEDULE"
  },
  "pii_assessment": "EXAMPLE PII ASSESSMENT",
  "deduplication": "Exact and 8-gram checks against all splits and evaluation items.",
  "limitations": "EXAMPLE LIMITATIONS",
  "counts": {
    "train": 70,
    "validation": 15,
    "heldout": 15,
    "evaluation": 24
  },
  "split_sha256": {
    "train": "0000000000000000000000000000000000000000000000000000000000000000",
    "validation": "0000000000000000000000000000000000000000000000000000000000000000",
    "heldout": "0000000000000000000000000000000000000000000000000000000000000000",
    "evaluation": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "approval_reference": "EXAMPLE-APPROVAL"
}
```

The zero hashes in that example are invalid as real evidence. Real hashes are the raw file SHA-256 values.

## 9. Translator consent, compensation, and retention

The Project Director reports that native Luganda speakers are available and have agreed to collaborate. Working arrangements were discussed, and compensation is intended after the project earns its first dollar. This is an owner report. The repository does not contain signed agreements, formal consent records, a compensation amount or schedule, retention terms, or a licence for translated data.

The owner and team should settle the following before translated material is treated as training-ready:

- written, informed consent to use the contributed text for training, evaluation, derivatives, and research reporting;
- a written licence sufficient for those uses, including redistribution and commercial use if the owner may need them;
- an owner-approved compensation rate, schedule, and payment method;
- an attribution choice, including whether the translator or reviewer remains pseudonymous;
- a withdrawal process and its limits;
- a retention period, storage location, access controls, and deletion process;
- a PII minimization and redaction process;
- a review and adjudication process for edits and disagreements.

Do not promise payment on the project's behalf. Do not use translated data for training until consent and licence references are recorded in the provenance file and matched to the records. The English source draft can be reviewed before those formal records exist.

## 10. Contamination and split integrity

The validator checks every user text, every assistant text with at least four words, and every full transcript. It normalizes whitespace and casefold, then compares:

- exact normalized text across different records;
- every overlapping 8-word sequence across different records;
- evaluation text against all pilot splits;
- pilot splits against each other.

Any hit blocks loading. The check is a screen, not proof that no semantic or source-level contamination exists. Manual review is still required for flagged pairs and for shared source passages.

The English source draft has a separate exact and 8-word check in `validate-source`. That source check does not replace the training-data contamination check after translation.

The 70/15/15 split is by example or conversation, never by random sentence. No conversation, source passage, or near-duplicate may cross splits. The evaluation IDs must not overlap pilot IDs.

## 11. Token limits

With the pinned tokenizer:

| Record type | Limit |
|---|---:|
| Non-conversation full rendering | 512 tokens |
| Short conversation full rendering | 1024 tokens |
| Each expanded prompt plus completion for training | 1024 tokens |

Every assistant turn becomes one prompt-completion expansion. The prompt is the preceding conversation; the completion is exactly one assistant message. The tokenizer must show that the prompt is a token prefix of the full rendering and that the completion begins with the base model turn marker. If the tokenizer is not supplied, structural validation still runs but token checks remain pending.

## 12. Hash recording

> **Archive note (2026-11-02, D-018):** the Gemma 1B config and the `validate-config`, `validate-data`, `preflight`, `train`, and `infer` commands named in sections 12 and 13 were archived under `archive/2026-11-02-gemma-runpod-reporter/`. The `validate-source`, `export-source`, and `hash` commands still run from `src/training/`. The schema rules in this specification still apply to any Luganda training data.

File hashes are SHA-256 over the raw JSONL bytes. They must match in both places:

- `dataset.split_hashes` in `configs/gemma3-1b-lora-smoke.yaml`;
- `split_sha256` in the provenance file.

The dataset version must also match. The current configuration uses `pilot-v1-unapproved` and is not executable. An approved run needs a version such as `pilot-v1` in both files.

Compute a hash with:

```bash
python -m training hash data/pilot/v1/train.jsonl
```

Record the exact result. Do not hand-build a digest or copy one from another file.

## 13. Validation commands

Structural validation, without a tokenizer:

```bash
python -m training validate-config configs/gemma3-1b-lora-smoke.yaml
python -m training validate-data configs/gemma3-1b-lora-smoke.yaml --project-root .
```

Token and prompt-completion validation with the pinned local tokenizer:

```bash
python -m training validate-data configs/gemma3-1b-lora-smoke.yaml \
  --project-root . \
  --tokenizer-path /path/to/gemma-3-1b-it \
  --require-tokenizer
```

Draft review only, which does not authorize training:

```bash
python -m training validate-data configs/gemma3-1b-lora-smoke.yaml \
  --project-root . \
  --allow-draft \
  --allow-incomplete
```

The current config is expected to fail with an unapproved dataset version. That is the correct result until the owner approves the data and updates the status.

Validate the English source draft and its generated exports:

```bash
python -m training validate-source
```

Regenerate the JSONL, translator CSV, and source manifest after changing the canonical draft:

```bash
python -m training export-source
```

The source command reports `training_authorized: false`. A successful source validation does not authorize training and does not satisfy the training-data checks.

Do not run `train` on the local laptop. It requires the exact Python 3.11, CUDA, bitsandbytes, and RTX 4090 preflight. See `docs/POD-SETUP.md`.

## 14. Open blockers

- The English source draft exists, but no Luganda translations exist.
- No second-speaker native review, adjudication, or review retention record exists.
- No formal consent, compensation, licence, or retention agreement is recorded.
- No Luganda provenance record with real counts and hashes exists.
- No approved Luganda data version exists.
- The 24-item feasibility set is not an approved benchmark.
- No benchmark change. `docs/BENCHMARK-SPECIFICATION.md` must remain unchanged.
