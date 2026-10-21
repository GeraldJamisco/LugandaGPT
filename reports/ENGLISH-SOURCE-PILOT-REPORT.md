# English Source Pilot Report

**Status:** READY FOR OWNER REVIEW for the English source draft.

**Luganda training dataset:** BLOCKED until translation, second-speaker review, provenance, formal terms, and training approval are complete.

**Date:** 2026-10-21

**Prepared by:** DeepSeek, engineering agent

**Owner:** Project Director

## 1. Scope

This report covers the English source material for the 100-example pilot and the separate 24-item feasibility evaluation. The engineering workflow authored the English source. Native Luganda speakers will translate it, and a second native speaker will review the translations.

This report does not claim that any Luganda data exists. It does not claim that the English source has native-reviewed language quality. It does not approve a benchmark, a dataset, a training run, or a paid GPU run.

No model or dataset was downloaded, no GPU was launched, no credits were purchased, and no training or inference was run.

## 2. Deliverables

| Deliverable | Result |
|---|---|
| Pilot source examples | 100 original English source items. |
| Proposed evaluation source | 24 separate English items, four per capability. |
| Translator export | `data/source/pilot-v1/translator_export.csv`, 124 rows. |
| Translation workflow | `data/source/pilot-v1/TRANSLATOR-GUIDE.md` and D-009. |
| Validation | Source schema, counts, splits, duplicates, provenance, status, exports, and checksums. |
| Documentation | D-009, updated pilot specification, updated data governance, this report. |

## 3. Capability counts

| Capability | Pilot | Evaluation |
|---|---:|---:|
| Formal Luganda comprehension | 17 | 4 |
| Formal Luganda generation | 17 | 4 |
| Rewriting into formal Luganda | 17 | 4 |
| Question answering in Luganda | 17 | 4 |
| Instruction following in Luganda | 16 | 4 |
| Short conversations in Luganda | 16 | 4 |
| **Total** | **100** | **24** |

Every source item has one `primary_capability`. Some items list a secondary capability, but the primary counts above are exact.

## 4. Split assignment

| Split | Pilot items |
|---|---:|
| Train | 70 |
| Validation | 15 |
| Held-out | 15 |

The split is assigned to the complete example or conversation. The 24 evaluation items have no training split and are stored separately. No evaluation item is used as a training example or few-shot prompt.

## 5. Composition checks

| Check | Requirement | Actual |
|---|---:|---:|
| Multi-sentence responses | At least 30 | 72 |
| Uncertainty or unanswerable cases | At least 12 | 16 |
| Examples with explicit constraints | At least 10 | 100 |
| Conversations requiring prior context | At least 8 | 16 |

The conversation records keep every prior turn in one item. There are 16 short conversations, and all 16 require context from an earlier turn. The split is applied to the whole conversation record, so no conversation crosses splits.

## 6. Source format

The canonical source is `data/source/pilot-v1/source_draft.json`. Each item has:

- stable `item_id`;
- `collection` (`pilot` or `evaluation`);
- `primary_capability` and `secondary_capabilities`;
- `source_language: en`;
- `source_prompt` and optional `source_context`;
- `expected_response_criteria`;
- `reference_answer_or_rubric` with `kind` and English content;
- `required_constraints`;
- `uncertainty_behavior`;
- `conversation_turns`;
- `intended_register`;
- `proposed_split`;
- `translation_status`;
- `native_review_status`;
- `source_provenance`;
- `response_length`;
- `requires_prior_context`;
- `notes`.

`conversation_turns` contains prior turns before the final user prompt. The final assistant response is the target described by the criteria and the English reference or rubric. The translator export keeps the English fields and the Luganda fields separate.

The English references are not Luganda reference answers. They are meaning guides for the native team.

## 7. Files and checksums

| File | Purpose |
|---|---|
| `data/source/pilot-v1/source_draft.json` | Canonical source draft and owner confirmation. |
| `data/source/pilot-v1/pilot_en.jsonl` | Generated 100 pilot rows. |
| `data/source/pilot-v1/evaluation_en.jsonl` | Generated 24 evaluation rows. |
| `data/source/pilot-v1/translator_export.csv` | Translator and reviewer workbook. |
| `data/source/pilot-v1/source_manifest.json` | Counts, composition, status, and checksums. |
| `data/source/pilot-v1/README.md` | Collection summary and status. |
| `data/source/pilot-v1/TRANSLATOR-GUIDE.md` | Translation and review instructions. |
| `scripts/build_source_pilot.py` | Reproducible builder for the generated files. |
| `src/training/source_pilot.py` | Source validator and export writer. |
| `tests/test_training_source_pilot.py` | Source schema, count, split, status, and export tests. |

Current SHA-256 values from `source_manifest.json`:

| File | SHA-256 |
|---|---|
| `source_draft.json` | `fb17b85c14b56b6b512f4a76d93ff716770705b5580ecfefe92c3b9dfc71d51f` |
| `pilot_en.jsonl` | `82f7d9b3ce82915a3cca828f6f76078fa9b01d130407b57831b3f72a232afb69` |
| `evaluation_en.jsonl` | `d518754aab09f61a4f8da5a88712e86ae3fe95a075ef7d6824c04f546b48e088` |
| `translator_export.csv` | `a6054001ee40b0feacae119016a4911f496ce0f9caba50af96d7c5ff3a49461d` |

The manifest is the authority for checksums. Regenerate the exports after any canonical source change.

## 8. Validation results

Command:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m training validate-source
```

Result:

- `status: source_draft_valid`
- `pilot_count: 100`
- `evaluation_count: 24`
- `pilot_split_counts: train 70, validation 15, heldout 15`
- `capability_counts: 17, 17, 17, 17, 16, 16`
- `multi_sentence: 72`
- `uncertainty_cases: 16`
- `constraint_examples: 100`
- `prior_context_conversations: 16`
- `translator_rows: 124`
- `translation_status: pending for 124`
- `native_review_status: pending for 124`
- `training_authorized: false`
- `source_exports_valid`

The validator rejects:

- wrong total or capability counts;
- wrong split counts;
- an evaluation item with a training split;
- duplicate IDs or unknown fields;
- exact duplicate source text or 8-word overlap;
- a non-pending translation or review status;
- missing or non-project provenance;
- a translator CSV with non-empty Luganda fields or tampered checksums.

Repository tests: 102 training tests and 401 full-suite tests reported `OK`. Python compilation reported no syntax error.

The training configuration still reports `config_valid` with `execution_authorized=false`, dataset version `pilot-v1-unapproved`. The training data validator fails as expected because the Luganda dataset is not present or approved. This is the correct gate result.

## 9. Owner confirmation and formal terms

The Project Director reports that native Luganda speakers are available and have agreed to collaborate. Working arrangements were discussed. Compensation is intended after the project earns its first dollar.

This is recorded as an owner report, not as a signed agreement or formal consent record. The repository still lacks:

- a written translator and reviewer scope;
- formal consent and withdrawal terms;
- a compensation amount, schedule, and payment method;
- a data-retention and deletion policy;
- a translation licence or rights statement, including derivatives and later release;
- an attribution and privacy decision;
- a documented reviewer panel and adjudication process.

These items block the Luganda training dataset. They do not block owner review of the English source or translation work.

## 10. Translation and review state

| State | Count |
|---|---:|
| Translated rows | 0 |
| Submitted translations | 0 |
| Second-speaker reviews | 0 |
| Approved translations | 0 |
| Pending translation rows | 124 |
| Pending native-review rows | 124 |

No translator or reviewer identity is invented. The CSV has empty translator and reviewer fields. The review status remains `pending` until a real second native speaker reviews the row.

The team should follow `data/source/pilot-v1/TRANSLATOR-GUIDE.md`. The workflow is:

1. Owner reviews the English source for relevance and coverage.
2. Native translators translate the source, including prior conversation turns.
3. A second native speaker reviews each item.
4. Disagreements are documented and resolved.
5. Translation and review status are recorded.
6. The completed Luganda records are validated against the training schema.
7. Approved records are assigned to their final splits.
8. Provenance, consent references, and checksums are recorded.

The translator CSV is an intermediate work product. It is not read by the training-data validator. A coordinator must convert approved rows into the training JSONL schema before the training checks can run. Completing the CSV does not authorize training.

## 11. What is ready

- 100 English source items with exact primary capability counts.
- 24 separate English evaluation items.
- A 70/15/15 pilot split with complete conversations kept together.
- A translator-facing CSV with distinct English, Luganda, and review fields.
- A source validator, exporter, manifest, and tests.
- Documentation of the owner's confirmation and the outstanding formal terms.
- An unchanged training authorization gate.

## 12. What is not ready

- No Luganda translations.
- No second-speaker native reviews or adjudications.
- No Luganda training dataset or token-length validation.
- No formal consent, compensation, retention, attribution, or licence record.
- No Luganda provenance record or approved dataset version.
- No benchmark item or benchmark score.
- No native-speaker quality judgment about the English source.
- No training, inference, GPU run, or spending.

## 13. Limitations and review points for the owner

The English source is a drafting artifact. It is not evidence that the Luganda responses will be natural or correct. The native team may find that a source prompt is culturally awkward, ambiguous, too long, or unsuitable for a natural Luganda response. Those cases should be corrected or excluded before training.

The 100 examples are project-authored, but they have not been independently reviewed for coverage or educational value. The owner should review the capability balance, the everyday situations, and the amount of formal versus conversational material.

The evaluation set is a proposed feasibility screen, not a benchmark. It must remain separate from training and must not be described as an approved benchmark. The automated check covers exact and 8-word overlap, but it does not prove semantic independence. The owner and native reviewers should still check for conceptual overlap and shared source ideas.

The English reference answers are meaning guides. They do not replace native Luganda references. The model must not be trained on the English references as if they were Luganda ground truth.

## 14. Decision requested

The owner is asked to review the English source draft in `data/source/pilot-v1/` and the translator workbook. The owner may approve it for translation, request changes, or reject specific items.

Approval for translation is not approval for training. The Luganda dataset remains blocked until the translated records, second-speaker reviews, formal terms, provenance, and training approval exist.

## 15. Final status

**English source pilot:** READY FOR OWNER REVIEW.

**Luganda training dataset:** BLOCKED: TRANSLATION, NATIVE REVIEW, PROVENANCE, AND FORMAL TERMS REQUIRED.

No paid infrastructure, model download, dataset download, training run, inference run, commit, or push was performed for this report.
