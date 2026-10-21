# Translator and Native Review Guide

**Collection:** LugandaGPT English source pilot and proposed feasibility evaluation

**Current state:** 100 English pilot items and 24 separate English evaluation items. No Luganda translation and no native review exist yet.

This guide is for the native Luganda-speaking team that will translate and review the source material. The English source is a meaning reference, not a Luganda answer key. The team produces the Luganda text.

## 1. What is being translated

The team translates the English source into natural Luganda that a Luganda speaker would use with another speaker. The result is not a word-for-word gloss. Preserve the meaning, the requested action, the register, and every explicit constraint.

The 24 evaluation items are separate from the 100 pilot items. Do not move an evaluation item into the pilot, and do not use an evaluation item as a training example, few-shot example, or prompt template. The evaluation set is not an approved benchmark.

## 2. Files and identifiers

| File | Use |
|---|---|
| `translator_export.csv` | Spreadsheet export for translation and review. |
| `source_draft.json` | Canonical source record. Do not edit it during translation. |
| `pilot_en.jsonl` | Generated pilot source for reference only. |
| `evaluation_en.jsonl` | Generated evaluation source for reference only. |

Every row keeps the original `item_id`. Pilot IDs start with `P-`; evaluation IDs start with `E-`. Do not renumber, merge, split, or reuse IDs. If a record needs a substantive change, record the reason in `translation_notes` or `review_notes` and ask the coordinator before changing the source.

## 3. Column guide

The English columns describe the task. The Luganda columns are for the team. The review columns are completed only after a review has actually happened.

### English source columns

| Column | Meaning |
|---|---|
| `source_context_en` | Background passage or source text. Translate it when the user would see it. |
| `prior_turns_en` | Earlier conversation turns as a JSON array of objects with `role` and `content`. Translate each turn. |
| `source_prompt_en` | The user request or the final user turn. Translate it into Luganda. |
| `expected_response_criteria_en` | What the response must contain, avoid, or do. This is a review rubric, not a sentence to translate. |
| `reference_answer_or_rubric_en` | An English reference answer or an English rubric. It is not a Luganda reference answer. |
| `reference_kind` | `english_reference` or `rubric`. |
| `required_constraints_en` | Explicit rules the final response must satisfy. |
| `uncertainty_behavior` | What to do when information is missing or the question is ambiguous. |
| `response_length` | Whether the response is expected to be one sentence or more than one. |
| `requires_prior_context` | Whether the final response depends on an earlier turn. |
| `notes` | Item-specific authoring note. Do not edit it during translation; use the translation and review note columns instead. |
| `source_provenance` | JSON record showing project-original source, no third-party material, and no approval reference. Keep it unchanged. |

### Luganda columns to complete

| Column | What to enter |
|---|---|
| `source_context_lg` | The Luganda translation of the source context or passage. Leave empty when there is no source context. |
| `prior_turns_lg` | A JSON array of translated prior turns, using the same `role` values. Leave empty for single-turn items. |
| `source_prompt_lg` | The Luganda translation of the user request or final user turn. |
| `final_assistant_response_lg` | The Luganda response that the model should learn. This is not a translation of the English reference unless that is truly the natural answer. |
| `translator_id` | A pseudonymous translator ID assigned by the coordinator. Do not enter a real name or personal contact detail. |
| `translation_date` | Date in `YYYY-MM-DD` format. |
| `translation_notes` | Notes about choices, uncertainty, or a needed clarification. Leave empty if there is nothing to record. |

The English columns must remain unchanged. Do not place a Luganda answer in an English column. Do not place an English answer in `final_assistant_response_lg`.

### Review columns to complete

| Column | What to enter |
|---|---|
| `native_review_status` | Keep `pending` until a review is complete. Use `reviewed` only after a second native speaker has reviewed the row. |
| `reviewer_id` | A pseudonymous reviewer ID assigned by the coordinator. |
| `review_date` | Date in `YYYY-MM-DD` format. |
| `review_decision` | `approved`, `revise`, or `exclude`. |
| `review_notes` | The reason for the decision, with specific corrections when needed. |

A translator must not review their own translation as the second reviewer. A disagreement should be documented and resolved by a third native speaker. Do not mark a row `approved` until that review has happened.

## 4. Translation rules

1. Use natural, appropriate Luganda. Do not force English word order.
2. Preserve the requested register. Formal items should remain formal; everyday conversation should sound like ordinary speech.
3. Preserve names, dates, times, amounts, places, and conditions exactly as supplied. Do not add facts.
4. Translate all prior conversation turns when `prior_turns_en` is not empty. Keep the same turn order and roles.
5. The final response must satisfy `expected_response_criteria_en` and `required_constraints_en`. If the criteria conflict, stop and report the conflict.
6. When `uncertainty_behavior` says the information is missing, the response should say what is missing instead of inventing an answer. When it asks for clarification, ask a clear question.
7. Do not use model-generated Luganda as approved ground truth. A model suggestion may be used only as a draft that a native speaker reviews and rewrites.
8. Do not silently edit a translator's Luganda. Record corrections in `review_notes` and preserve the original translation for comparison if the coordinator requests it.
9. Do not translate the English rubric into a Luganda answer and mark it complete. The rubric guides the response; it is not the response.
10. Do not add personal information, real contact details, or sensitive details to any row.

## 5. Workflow

1. The engineering workflow drafts the English source examples.
2. The Project Director reviews relevance and coverage of the English draft.
3. The native-speaking team translates the source material into Luganda.
4. A second native speaker reviews each translated item.
5. Disagreements are documented and resolved.
6. The team records translation status and review decisions.
7. The dataset validator checks the completed records.
8. Approved records are assigned to their final splits.
9. Provenance, consent references, and checksums are recorded.

The current files stop at step 1 or step 2. Steps 3 through 9 are outstanding.

## 6. Status handling

- Start with `translation_status: pending` and `native_review_status: pending`.
- A translator may change `translation_status` to `submitted` when the row is ready for review, if the coordinator's tracking sheet supports that value.
- A reviewer may change `native_review_status` to `reviewed` only after the review.
- `approved` means the required review is complete. It does not mean the owner has approved the dataset or authorized training.
- If a row is excluded, record why and do not put it in a training split.
- Missing Luganda text remains pending. Never fill a missing translation with English or a model output and mark it complete.

## 7. What the owner and team still need to formalize

The Project Director reports that native speakers are available and have agreed to collaborate, and that compensation is intended after the project earns its first dollar. The repository does not contain signed agreements, formal consent records, a compensation amount or schedule, retention terms, or a licence for translated data.

Before translated material is used for training, the owner and team should record:

- translator and reviewer scope, including permitted uses;
- consent and withdrawal terms;
- compensation rate, schedule, and payment method;
- data retention and deletion terms;
- a licence or rights statement for the translations and derivatives;
- attribution and privacy choices;
- a decision on later public release.

These are blockers for the Luganda training dataset, not for translation work or review of the English source.

## 8. Returning work

Keep the original `item_id` values and the CSV column order. Return the completed CSV with a short note listing:

- the number of rows submitted;
- the number of rows approved, revised, or excluded;
- any source item that needs clarification;
- the date and pseudonymous translator and reviewer IDs.

The coordinator will regenerate the checksums and run:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m training validate-source
```

The source validator is for the English draft. The completed Luganda dataset must pass the separate training-data validator before any training run is authorized.
