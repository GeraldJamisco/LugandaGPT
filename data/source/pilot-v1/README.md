# English Source Pilot Draft

**Status:** English source draft. Not a Luganda training dataset. Not approved for training.

This directory contains the first project-authored English source material for the 100-example pilot and the separate proposed 24-item feasibility evaluation. Native Luganda speakers will translate the material, and a second native speaker will review it before any record can enter the training gate.

## Counts

| Collection | Count | Capability distribution |
|---|---:|---|
| Pilot | 100 | 17 comprehension, 17 generation, 17 rewriting, 17 question answering, 16 instruction following, 16 conversation |
| Evaluation | 24 | 4 per capability |
| Translator rows | 124 | 100 pilot and 24 evaluation |

Pilot split assignment:

| Split | Count |
|---|---:|
| Train | 70 |
| Validation | 15 |
| Held-out | 15 |

The split is assigned to the complete example or conversation. The evaluation items have no training split.

## Composition checks

| Check | Required | Actual |
|---|---:|---:|
| Multi-sentence responses | At least 30 | 72 |
| Uncertainty or unanswerable cases | At least 12 | 16 |
| Examples with explicit constraints | At least 10 | 100 |
| Conversations requiring prior context | At least 8 | 16 |

## Files

| File | Purpose |
|---|---|
| `source_draft.json` | Canonical machine-readable draft. This is the source of truth. |
| `pilot_en.jsonl` | Generated 100 pilot examples, one object per line. |
| `evaluation_en.jsonl` | Generated 24 evaluation items, one object per line. |
| `translator_export.csv` | Translator-facing spreadsheet export with separate English, Luganda, and review columns. |
| `source_manifest.json` | Counts, composition, status, owner confirmation, and SHA-256 checksums. |
| `TRANSLATOR-GUIDE.md` | Instructions for the native-speaking team. |

The `.jsonl` and `.csv` files are generated from `source_draft.json` by `scripts/build_source_pilot.py`. Do not edit the generated files by hand. A change to the canonical draft must be regenerated and revalidated.

## Status values

- Every pilot and evaluation item has `translation_status` set to `pending`.
- Every item has `native_review_status` set to `pending`.
- No Luganda translation, native review, formal consent record, signed agreement, compensation record, or approval reference exists in this directory.
- The source provenance says `origin: project_original` and `third_party_source: false`. It also records that translation and native-review terms are not yet formal agreements.

## Owner confirmation

The Project Director reports that native Luganda speakers are available and have agreed to collaborate. Working arrangements were discussed. Compensation is intended after the project earns its first dollar.

This is an owner report, not a signed agreement, formal consent record, or documented compensation schedule. The owner and team should formalize the following before translated data is treated as training-ready:

- a written scope for the translators and reviewers;
- consent and data-retention terms;
- a compensation rate, schedule, and payment method;
- a licence or rights statement covering the translated data and derivatives;
- a decision on whether translated data may appear in a later public model or release;
- a process for recording withdrawal and corrections.

These items block the Luganda training dataset. They do not block owner review of the English source draft.

## Validation

From the repository root:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m training validate-source
```

The validator checks exact counts, capability distribution, 70/15/15 splits, evaluation separation, unique IDs, required fields, status truthfulness, provenance, exact duplicates, and 8-word overlap. It also verifies the generated JSONL, CSV, and manifest checksums.

A successful source validation reports `training_authorized: false`. The English draft must not pass the training-data validator. The training configuration remains unapproved and points at different files under `data/pilot/v1` and `data/evaluation`.
