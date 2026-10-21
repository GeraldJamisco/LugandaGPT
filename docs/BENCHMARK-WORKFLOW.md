# Benchmark Workflow

Operational guide for the benchmark preparation code in `src/benchmark/`.
It implements the record types and checks described in
`docs/BENCHMARK-SPECIFICATION.md`. It does not contain benchmark prompts,
native-review results, model runs, or an approval record.

## Status note

The specification is approved at specification version `1.0`; the approval is
recorded in `docs/DECISIONS.md`, D-007. The item schema, language rules,
reference and ambiguity policy, scoring scale, and applicability rules were
approved as specification content through O-01 and O-03 through O-07.

The benchmark itself remains unfrozen and unapproved. No prompt set, native
review, benchmark `ApprovalRecord`, or evaluation run exists. The code does
not treat the specification approval or file existence as benchmark approval.
A benchmark requires a separate `ApprovalRecord`, native-review sign-off, and
matching manifest hash. No such record exists in this repository.

This guide is therefore operational documentation for a workflow, not a claim
that the benchmark itself is approved or released.

## Requirement map

| Requirement | Implementation | Validation | Status |
|---|---|---|---|
| Item schema and controlled values | `src/benchmark/constants.py`, `src/benchmark/item.py` | `tests/test_benchmark_item.py` | Implemented |
| Stable item IDs and version matching | `validate_item_id`, `validate_version`, `validate_item_set` | ID, version, and duplicate-ID tests | Implemented |
| Required fields, unknown-field rejection, reference status, ambiguity notes | `validate_item` | Schema tests | Implemented |
| Source and licence metadata, owner source exceptions | `_validate_source`, `SourceException` | Source tests | Implemented |
| Seven dimensions and applicability | `_validate_dimensions` | Dimension tests | Implemented |
| Review status transitions | `can_transition`, `transition_item` | Transition tests | Implemented |
| Ambiguity check, reference review, native item review, calibration | `src/benchmark/review.py` | Review-evidence tests | Implemented; human records pending |
| Independent scoring and disagreement handling | `validate_independent_reviews`, `material_disagreements`, `build_adjudication` | Review tests | Implemented |
| Score range, notes, and applicable dimensions | `ResponseReview`, `validate_response_review` | Response-review tests | Implemented |
| Blind reviewer packets | `build_review_packet`, `assert_blind_packet` | Packet test | Implemented |
| Missing review or approval evidence | `_validate_review_status`, `validate_item_review_evidence` | Evidence tests | Implemented |
| Agreement reporting | `agreement_report`, `quadratic_weighted_kappa` | Agreement tests | Implemented |
| Per-dimension summary without a composite | `summarize_scores` | Summary tests | Implemented |
| Exclusion records with reasons | `ExclusionRecord`, `_validate_review_status` | Exclusion tests | Implemented |
| Version manifests and change classes | `src/benchmark/versioning.py` | Version tests | Implemented |
| Owner approval, hash matching, native sign-off | `ApprovalRecord`, `NativeReviewSignoff`, `build_manifest`, `load_approved_benchmark` | Approval tests | Implemented; no real approval exists |
| Run manifest, pinned revisions, decoding, cost, timestamps | `src/benchmark/runs.py` | Run tests | Implemented |
| Verbatim raw responses | `RawResponse`, `RunStore.append_raw_response` | Raw-response preservation test | Implemented |
| Failed, incomplete, and completed runs | `RunManifest`, `RunStore.finalize`, `mark_failed`, `mark_incomplete` | Run-status tests | Implemented |
| Reproducibility metadata and item hash | `RunStore.verify_reproducibility`, `manifest_sha256` | Reproducibility test | Implemented |
| Conversational and translation separation | `summarize_scores`, `track` checks | Track-separation test | Implemented |
| Local validation command | `src/benchmark/cli.py` | CLI tests | Implemented |
| Synthetic validation fixture | `tests/fixtures/benchmark/` | CLI fixture test | Implemented; test data only |

## Validate records

From the repository root:

```powershell
$env:PYTHONPATH="src"
python -m benchmark validate tests/fixtures/benchmark/synthetic_items.jsonl --version 0.1-draft
```

The command exits 0 only when every record passes. It exits 2 and prints a
field-level error when a record is malformed. It never repairs a record.

Reviewed or approved records need external evidence. The evidence file is a
JSON object keyed by item ID. Each value can contain these arrays:

- `ambiguity_checks`
- `item_reviews`
- `reference_reviews`
- `calibration_sessions`
- `approval_record` for an approved item
- `exclusion_record` for an excluded item

Example command shape:

```powershell
python -m benchmark validate path\to\items.jsonl `
  --version 1.0 `
  --evidence path\to\evidence.json `
  --manifest path\to\manifest.json
```

When the manifest is approved, the validator checks the item-file hash,
approval hash, approval item list, and native-review sign-off through
`load_approved_benchmark`. A draft manifest is checked for version and hash
only. If a non-original item has an explicit owner source exception, pass a
JSON mapping with `--source-exceptions`.

## Draft items

Put each item on one JSON line. Use the exact fields in section 6.1 of the
specification. Additional fields are rejected. The stable ID format is:

```text
LGP-BENCH-<CATEGORY>-<NNN>
```

`<CATEGORY>` is the uppercase category prefix, for example `FORMAL`,
`CODESWITCH`, `INSTRUCTION`, or `FACTUALITY`. IDs are permanent. Do not put
the benchmark version in the ID. `benchmark_version` records the version.

The synthetic fixture is test data only. Its prompt starts with
`SYNTHETIC TEST FIXTURE` and must not be copied into the benchmark.

## Review status

The supported transitions are:

```text
draft -> ambiguity_checked -> native_reviewed -> approved
any status -> excluded
```

Use `transition_item(item, target, date=..., evidence=...)` to change status.
The function returns a copy and validates the evidence. It does not create
review records.

Evidence types:

- `AmbiguityCheck`: a second reviewer records `clear`, `revised`,
  `intrinsic_ambiguity`, or `unresolved`. `unresolved` cannot support a
  promotion.
- `ReferenceReview`: a native reviewer approves the exact reference text.
  The record stores the SHA-256 of `reference_answer`, so a later text change
  invalidates the review.
- `ItemReview`: an item-level native review decision: `accept`, `revise`, or
  `exclude`. At least two distinct native reviewers with completed calibration
  are required for `native_reviewed`.
- `CalibrationSession`: records the reviewer panel and calibration items and
  must be completed before native item review counts. Calibration item IDs
  must be separate from the benchmark item IDs.
- `ResponseReview`: response scoring for one applicable dimension in one run.
  A panel produces one record per reviewer per dimension. Each record carries
  the score, note, flag, failure codes, and adjudication fields. Agreement
  reporting skips missing scores and reports insufficient data as null rather
  than inventing a value.
- `build_review_packet`: creates a blinded packet with item content, expected
  behavior, scoring dimensions, and the exact response text. It omits model,
  provider, tokenizer, run, timestamp, and cost metadata.
  `assert_blind_packet` rejects a packet that exposes those fields.

An item cannot claim `native_reviewed` or `approved` from item notes alone.
The external records must exist. No reviewer is recruited by this code.

Material disagreement includes a score difference of at least two points,
an acceptability disagreement, or a failure-code disagreement.
`build_adjudication` refuses to create an adjudicator record when no recorded
disagreement exists, and it requires an adjudicator who did not score the same
item and dimension. The original review records are left unchanged.

## Approval and versions

`ApprovalRecord` contains the specification version, benchmark version,
approver, role, date, scope, conditions, item-file hash, approved item IDs,
and `NativeReviewSignoff`. The sign-off names at least two reviewers, the
calibration date, the agreement statistic, the reviewed items, and the
sign-off date.

`build_manifest` enforces:

- every item uses the manifest version;
- every item has `review_status: approved`;
- an approved item cannot use a draft version;
- one item file cannot mix the conversational and translation tracks;
- the approval names every item and no others;
- the approval hash matches the item file;
- the native sign-off covers every item;
- a draft manifest has no approval record.

`load_approved_benchmark` rechecks the file hash and all approval links. This
is why copying a JSONL file into an approved folder is not enough.

Version rules:

- drafts use `0.x-draft`;
- an approved manifest cannot use a draft version;
- the first frozen version is `1.0`;
- later versions use `MAJOR.MINOR`;
- `compare_versions` reports added, removed, changed, and unchanged IDs;
- `classify_change` returns `editorial`, `minor`, or `major`;
- `next_version` and `assert_version_change_allowed` enforce the direction;
- a version check compares the old item set with the prior manifest hash;
- each manifest records the item hash, changelog, changed items, and parent
  version.

`ExclusionRecord` requires an item ID, version, date, actor, and reason. An
item with `review_status: excluded` does not validate without a complete
record.

## Translation track

The optional translation track uses `track: translation_probe`, a separate
item file, and a separate report. It is not part of the 50 conversational
items and is never combined with the seven-dimension conversational summary.
`summarize_scores` rejects a mixed track set. Work on this track requires
separate project-owner approval, including data licensing and contamination
review.

## Evaluation runs

`RunStore` writes under a caller-supplied root. The proposed production root
from the specification is:

```text
reports/benchmark/runs/<run_id>/
  run_manifest.json
  raw_responses.jsonl
  costs.jsonl
  scores/review_records.jsonl
```

`reports/` is ignored by Git. The proposed item-file path
`data/benchmark/items/<version>.jsonl` is not created here and would need the
owner-approved ignore exception described in the specification.

`RunManifest` records the frozen benchmark version and hash, exact model and
tokenizer revisions, chat template, quantization, dtype, device, framework
versions, decoding, sample count, batch size, hardware, operating system,
timestamps, wall-clock time, peak memory if measured, cost, approval
reference, raw-response path, and operator. Moving revisions such as `main`
and `latest` are rejected. Create a new run with `RunStore.create_manifest`;
it refuses to reuse an existing run ID.

`RawResponse` stores the response string exactly as received. Do not edit,
normalise, translate, or truncate it. Store derived text separately if needed.

Run status values are `planned`, `running`, `completed`, `failed`,
`incomplete`, and `excluded`. A `completed` run must have finish metadata, no
errors, and the expected number of items. A `failed` run must record at least
one non-empty error. A raw response with an error is not counted as completed
and marks finalization as failed. Failed and incomplete runs record finish
metadata and the completed item count. Terminal runs cannot accept new raw
responses or be finalized again. An incomplete or failed run is never treated
as a completed evaluation. The CLI returns 2 for both.

Costs use `CostRecord`. Paid API records require provider, model, token
counts, unit price, total, cap, currency, approved budget, and an approval
reference. Native-review records require currency, an approved budget,
reviewer hours, rate, and an approval reference. If a value was not measured,
leave it null; do not invent it. The manifest holds the primary inference cost.
`RunStore.append_cost` and `read_costs` keep a `costs.jsonl` ledger for
additional cost types, including native review.

## Reproduce a run

1. Check `RunStore.verify_reproducibility(manifest, item_file_path)`.
2. Use the manifest's exact benchmark version and item-file hash.
3. Use the pinned model, tokenizer, and adapter revisions. The check also
   compares the recorded model revision with the raw-response records.
4. Use the same chat template and decoding settings.
5. Compare the new run manifest hash with the recorded one.
6. Keep the raw responses and review records with the run directory.
7. Report per-dimension results only. Do not add a cross-dimension composite
   or leaderboard rank.

## Human and owner steps still required

- Recruit and qualify native Luganda reviewers.
- Approve reviewer compensation, consent, data retention, and pseudonymous
  IDs.
- Approve the panel composition, dialect coverage, and adjudication process.
- Run calibration and approve the agreement threshold.
- Author the actual benchmark items and native reference answers.
- Complete ambiguity, reference, cultural, and native item review.
- Approve the frozen benchmark version and sign the approval record.
- Approve models, access paths, budgets, and gated-licence terms before any
  baseline run.
- Decide whether the benchmark item file is committed and, if so, approve a
  narrow `.gitignore` exception.
- Resolve the remaining owner decisions in section 19 of the specification:
  final allocation, reviewer terms, agreement threshold, translation scope,
  storage status, model plan, budget, legal review, prompt authoring, and
  release rules.

## Commands

```powershell
# Validate the synthetic fixture
$env:PYTHONPATH="src"
python -m benchmark validate tests/fixtures/benchmark/synthetic_items.jsonl --version 0.1-draft

# Validate a run manifest
python -m benchmark validate-run path\to\run_manifest.json

# Print an item-file hash
python -m benchmark hash path\to\items.jsonl

# Run the full suite
python -m unittest discover -s tests -t . -v
```

No command in this workflow downloads a model or dataset, calls a paid API,
runs inference, sends Telegram messages, or changes reporter state.
