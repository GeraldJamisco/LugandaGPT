# LugandaGPT Benchmark Specification

**Document ID:** LGP-BENCH-SPEC

**Version:** 0.1-draft

**Status:** Draft for project-owner review. Not approved.

**Date:** 2026-10-20

**Owner:** Project owner (project director)

**Prepared by:** DeepSeek, engineering agent

**Related documents:** `docs/EVALUATION_PLAN.md`, `docs/PHASE-1-RESEARCH.md`,
`docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/EXPERIMENT_LOG.md`,
`data/README.md`, `AGENTS.md`

---

## 1. Purpose

This document specifies the initial LugandaGPT conversational benchmark. It
is intended to be complete enough for the project owner and native Luganda
reviewers to review before any prompts are written.

The benchmark is designed to measure conversational Luganda ability across
formal, everyday, colloquial, code-switched, instructional, multi-turn,
explanatory, cultural, and factual settings. It is text-only, consistent
with D-002.

This document does not:

- write the approximately 50 prompts;
- claim that any prompt, item, or score exists;
- claim that native-speaker review has occurred;
- approve the benchmark;
- authorize baseline inference;
- authorize dataset acquisition, model downloads, or paid API usage;
- select a model architecture or parameter count;
- change D-005;
- mark Phase 1 complete.

All prompt text in this document is a placeholder or a rule. No benchmark
item exists yet.

---

## 2. Relationship to existing documents

`docs/EVALUATION_PLAN.md` remains the policy source of truth. It defines the
approximately 50-prompt target, the nine categories, the seven scoring
dimensions, the native-review requirement, and the contamination principles.
This specification operationalizes those decisions. It does not rename or
replace the categories or dimensions.

`docs/PHASE-1-RESEARCH.md` records the resource validation, model shortlist,
evidence, and Phase 1 exit-criteria mapping. This document is the operational
benchmark specification that the research document links to.

If this specification is approved, the project owner decides whether to:

- merge its operational details into `docs/EVALUATION_PLAN.md`; or
- keep it as a companion specification referenced by that plan.

No such merge is performed by this draft.

---

## 3. Status and non-claims

| Item | Status |
|---|---|
| Benchmark specification approved | No |
| Benchmark version frozen | No |
| Prompt authoring started | No |
| Prompts written | No |
| Native reviewers recruited | No |
| Native review completed | No |
| Calibration completed | No |
| Agreement statistics available | No |
| Models run on the benchmark | No |
| Baseline results available | No |
| Phase 1 complete | No |
| D-005 changed | No |

This is a proposal. Nothing in it is a measured result, an approval record,
or evidence of Luganda quality.

---

## 4. Definitions

- **Item:** one benchmark task with its prompt, metadata, expected behavior,
  optional reference answer, and scoring instructions.
- **Prompt:** the user text presented to the model. For a multi-turn item,
  the first user turn is the prompt and the remaining scripted turns are in
  `turns`.
- **Turn:** one user or assistant message in a scripted conversation.
- **Response:** one model output for one item, turn, and sample.
- **Run:** one model evaluated on one frozen benchmark version with recorded
  settings.
- **Benchmark version:** the frozen identity of the item file and scoring
  rules, recorded separately from individual item IDs.
- **Native reviewer:** a native Luganda speaker approved to assess language
  quality under D-004.
- **Adjudicator:** a third native reviewer who resolves a material
  disagreement between two reviewers.
- **Calibration set:** a small set of items scored by all reviewers before
  the main review to align use of the rubric. Calibration items are separate
  from the reported benchmark.
- **Composite score:** a single number formed by combining the seven
  dimensions. This specification does not define one.

"Approximately 50" means a target of about 50 conversational items. The
draft allocation below sums to 50. The exact final count and allocation
remain open until owner approval.

---

## 5. Preserved framework

### 5.1 Nine categories

The category names and descriptions are reproduced from
`docs/EVALUATION_PLAN.md`. They must not be silently renamed or replaced.

| Category | Code | Existing description |
|---|---|---|
| Formal Luganda | `formal_luganda` | Educated, formal register. |
| Everyday Luganda | `everyday_luganda` | Ordinary conversational usage. |
| Colloquial language | `colloquial` | Informal speech, slang, regional variation. |
| Luganda-English code-switching | `code_switching` | Mixed-language prompts and responses. |
| Instruction following | `instruction_following` | Clear, constrained tasks. |
| Multi-turn context | `multi_turn` | Prompts that require retaining earlier turns. |
| Explanation and reasoning | `explanation_reasoning` | Concept explanations and multi-step reasoning. |
| Cultural and linguistic interpretation | `cultural_interpretation` | Idiom, proverbs, cultural context. |
| Factuality and appropriate uncertainty | `factuality_uncertainty` | Correct facts and honest "I don't know". |

### 5.2 Seven scoring dimensions

The dimension names are reproduced from `docs/EVALUATION_PLAN.md`. They must
not be silently renamed or replaced.

1. Semantic correctness
2. Grammar and naturalness
3. Instruction compliance
4. Relevance
5. Context retention
6. Factual reliability
7. Appropriate register

Section 10 defines each dimension operationally. A change to a dimension
name or meaning is a major benchmark change under section 15.

### 5.3 Draft category allocation

This allocation is a proposal for review. It is not the approved final
allocation.

| Category | Draft count | Rationale |
|---|---:|---|
| Formal Luganda | 6 | Tests educated register and grammatical control |
| Everyday Luganda | 7 | Core conversational use |
| Colloquial language | 6 | Tests informal speech, slang, and regional variation |
| Luganda-English code-switching | 6 | Core product requirement and distinct capability |
| Instruction following | 5 | Tests constrained compliance, not only fluency |
| Multi-turn context | 5 | Tests context retention beyond single-turn answers |
| Explanation and reasoning | 6 | Tests correctness and coherence, not only style |
| Cultural and linguistic interpretation | 5 | Requires native-authored interpretation and is review-intensive |
| Factuality and appropriate uncertainty | 4 | Tests correct facts and honest uncertainty |
| **Total** | **50** | |

The allocation is conversation-weighted. It gives more items to Everyday,
Formal, Colloquial, and Code-switching because those are the product's core
use cases. It gives fewer items to Factuality because factual verification
requires external checks as well as language review.

The owner may change the allocation before prompt authoring. The exact
distribution remains open until approved.

---

## 6. Item schema

### 6.1 Schema example

```json
{
  "id": "LGP-BENCH-FORMAL-001",
  "benchmark_version": "0.1-draft",
  "track": "conversational",
  "category": "formal_luganda",
  "prompt_language": "lg",
  "response_language": "lg",
  "prompt": "<prompt text>",
  "turns": [],
  "expected_behavior": "<what a correct response must do>",
  "reference_answer": null,
  "reference_status": "pending",
  "accepted_alternatives": [],
  "scoring_dimensions": [
    "semantic_correctness",
    "grammar_naturalness",
    "appropriate_register"
  ],
  "ambiguity_notes": "",
  "cultural_note": "",
  "contamination_notes": "",
  "review_status": "draft",
  "reviewer_notes": [],
  "source": {
    "type": "original",
    "url": null,
    "licence": null,
    "inspiration": null
  },
  "author": {
    "id": "author-001",
    "role": "benchmark_author",
    "created_at": "2026-10-20"
  },
  "created_at": "2026-10-20",
  "updated_at": "2026-10-20"
}
```

The angle-bracket values are placeholders. They are not prompts.

This schema refines the earlier research-draft schema in
`docs/PHASE-1-RESEARCH.md`. It uses `scoring_dimensions` for the applicable
dimensions, groups source metadata under `source`, groups author metadata
under `author`, and stores reviewer comments in `reviewer_notes`. The
underlying requirements are unchanged. The research document remains a
draft; this specification is the operational schema for review.

### 6.2 Field rules

| Field | Required | Type | Rules |
|---|---|---|---|
| `id` | Yes | String | Stable item ID. Format `LGP-BENCH-<CATEGORY>-<NNN>`. Retired IDs are never reused. The ID does not contain the benchmark version, so an item can be carried across versions |
| `benchmark_version` | Yes | String | Version of the item file, for example `0.1-draft` or `1.0`. Must match the file-level version |
| `track` | Yes | String | `conversational` or `translation_probe`. The 50 conversational items use `conversational` |
| `category` | Yes | String | One of the nine category codes in section 6.3 |
| `prompt_language` | Yes | String | `lg`, `lg-en`, or `en` |
| `response_language` | Yes | String | `lg`, `lg-en`, `en`, or `model_choice`. The expected language is stated, not inferred |
| `prompt` | Yes | String | First user turn. No personal data, credentials, or unlicensed copyrighted text |
| `turns` | Yes | Array | Empty for single-turn items. For multi-turn items, scripted user and assistant turns. Must contain at least one follow-up that depends on an earlier turn |
| `expected_behavior` | Yes | String | What a correct response must do, including response language, constraints, and whether uncertainty is acceptable. This is not a reference answer |
| `reference_answer` | Conditional | String or null | Required only when `reference_status` is `authored`. Must be authored or approved by a native speaker. Never model-generated |
| `reference_status` | Yes | String | `authored`, `pending`, or `not_applicable` |
| `accepted_alternatives` | No | Array of strings | Native-approved alternatives that should not be marked wrong. Each alternative must be attributed to a reviewer |
| `scoring_dimensions` | Yes | Array of strings | Subset of the seven canonical dimension names. No duplicates. Only dimensions the item actually tests |
| `ambiguity_notes` | Yes | String | Record the ambiguity check. "None found" is acceptable only after a documented check |
| `cultural_note` | Conditional | String | Required for Cultural and linguistic interpretation items. Native-authored note on accepted interpretation or range |
| `contamination_notes` | Yes | String | What overlap was checked, what is known, and what remains unknown. "Not checked" is not acceptable for an approved item |
| `review_status` | Yes | String | `draft`, `ambiguity_checked`, `native_reviewed`, `approved`, or `excluded` |
| `reviewer_notes` | Yes | Array | Empty before review. After review, objects with reviewer ID, role, date, dimension, score, note, and flag |
| `source` | Yes | Object | `type`, `url`, `licence`, and `inspiration`. If `type` is not `original`, `url` and `licence` are required unless the owner records an explicit exception |
| `author` | Yes | Object | Pseudonymous `id`, `role`, and `created_at`. Do not store unnecessary personal data |
| `created_at` | Yes | String | ISO date |
| `updated_at` | Yes | String | ISO date. Changes after a frozen version require a version bump |

### 6.3 Controlled values

Category codes:

- `formal_luganda`
- `everyday_luganda`
- `colloquial`
- `code_switching`
- `instruction_following`
- `multi_turn`
- `explanation_reasoning`
- `cultural_interpretation`
- `factuality_uncertainty`

Canonical dimension names:

- `semantic_correctness`
- `grammar_naturalness`
- `instruction_compliance`
- `relevance`
- `context_retention`
- `factual_reliability`
- `appropriate_register`

Reference status:

- `authored`: a native-authored reference exists.
- `pending`: a reference is expected but has not been authored.
- `not_applicable`: the item is open-ended or intrinsically ambiguous, and
  scoring uses `expected_behavior` plus the rubric.

Review status:

- `draft`: author is still working.
- `ambiguity_checked`: a second reviewer has checked the item for ambiguity.
- `native_reviewed`: at least two native reviewers have reviewed the item and
  any material disagreement has been adjudicated.
- `approved`: the project owner has approved the item for the frozen
  benchmark after native review.
- `excluded`: the item is withdrawn. The reason is recorded.

Source type:

- `original`
- `salt`
- `flores`
- `mafand`
- `wikipedia`
- `other`

Author role:

- `benchmark_author`
- `native_reviewer`
- `adjudicator`
- `project_owner`

Reviewer-note flags:

- `none`
- `ambiguity`
- `contamination`
- `safety`
- `other`

### 6.4 Item ID rules

- Use `LGP-BENCH-<CATEGORY>-<NNN>`.
- Category is the uppercase form of the code, for example `FORMAL`,
  `EVERYDAY`, `COLLOQUIAL`, `CODESWITCH`, `INSTRUCTION`, `MULTITURN`,
  `EXPLANATION`, `CULTURAL`, or `FACTUALITY`.
- `NNN` starts at `001` and increments within the category.
- IDs are permanent. If an item is excluded, keep the ID and set
  `review_status` to `excluded`.
- Do not reuse an ID for a different prompt, even in a later version.
- The research draft used a version-prefixed example ID. This specification
  uses a version-independent ID so that an item can be carried across
  versions; `benchmark_version` records the version. This is a proposed
  refinement, not a change to the item's identity.

### 6.5 Minimum viable item

An item may move from `draft` to `ambiguity_checked` only when:

- all required fields are present;
- the category and prompt language are consistent with section 7;
- `scoring_dimensions` contains only canonical names and no duplicates;
- `reference_answer` is present only when `reference_status` is `authored`;
- `reference_status` is `not_applicable` only when `ambiguity_notes`
  explains why;
- `ambiguity_notes` and `contamination_notes` record an actual check;
- the source and author metadata are complete;
- the item contains no personal data, credentials, or unlicensed text;
- the item does not require harmful or illegal content.

An item may move to `native_reviewed` only after the process in section 12.
An item may move to `approved` only after owner approval and a frozen
benchmark version.

### 6.6 Privacy and safety

- Do not include personal data, private information, passwords, tokens, or
  credentials.
- Do not include copyrighted text without a recorded licence or permission.
- Do not require harmful, illegal, or private information.
- If a safety refusal is the expected behavior, state that in
  `expected_behavior` and score it under Instruction compliance and
  Relevance, not as a language failure.
- Use pseudonymous reviewer IDs. Do not store reviewer contact details in the
  item file.

---

## 7. Prompt and response language

### 7.1 Language rules by category

| Category | Prompt language | Response language | Notes |
|---|---|---|---|
| Formal Luganda | Luganda (`lg`) | Luganda (`lg`) | Educated register |
| Everyday Luganda | Luganda (`lg`) | Luganda (`lg`) | Ordinary conversational usage |
| Colloquial language | Luganda (`lg`) | Luganda (`lg`) | Record the regional variety or slang set |
| Luganda-English code-switching | Mixed (`lg-en`) | Match the prompt's mix (`lg-en`) | State the expected mix in `expected_behavior` |
| Instruction following | English (`en`) or Luganda (`lg`) | Stated per item | Record both languages |
| Multi-turn context | Luganda (`lg`) | Luganda (`lg`) | Scripted turns in `turns` |
| Explanation and reasoning | Luganda (`lg`) or  Mixed (`lg-en`)  | Luganda (`lg`) or  Mixed (`lg-en`) | Technical terms may be handled as section 7.3 allows, many people in uganda or luganda speakers speak luganda mixed with english so always you have to get to know that users will respond in both languages  Mixed (`lg-en`) |
| Cultural and linguistic interpretation | Luganda (`lg`) | Luganda (`lg`) | Native-authored cultural note required, some cultural stuff are in english and some have not beeen found a wording yet for in luganda, so expect some words to be in still in english but simplified to a speaking tone in both languanges  Mixed (`lg-en`) |
| Factuality and appropriate uncertainty | Luganda (`lg`) | Luganda (`lg`) | Proper names may remain in their usual form |

### 7.2 Orthography and script

- Script is Latin.
- Orthography follows the standard agreed by the native reviewers. This
  specification does not invent or impose a standard.
- The agreed standard is recorded in the benchmark documentation before item
  approval.
- Spelling variants that the reviewers accept are recorded in
  `accepted_alternatives` or in the review notes.
- A Luganda-only prompt contains no English gloss. If a term has no settled
  Luganda equivalent, the item states how the term is handled.

### 7.3 Technical terms and names

- Proper names may remain in their usual form.
- Established loanwords may be used if the native reviewers accept them.
- If a technical term has no settled Luganda equivalent, the item may allow a
  Luganda description, an established loanword, or a gloss in the expected
  behavior. The choice is recorded and reviewed.
- A model that substitutes an English word for an available Luganda term may
  lose register or grammar points, depending on the item's expected behavior.

### 7.4 Code-switching

- Code-switching items intentionally mix Luganda and English.
- The item states whether the expected response should be mostly Luganda,
  mostly English, or balanced.
- The item states whether switching is required, optional, or prohibited
  within the response.
- A response that avoids the requested mix is an Instruction compliance or
  Appropriate register failure, not automatically a grammar failure.

### 7.5 Response language is part of the task

The expected response language is part of `expected_behavior`. A model that
answers a Luganda prompt in English fails the language requirement even if
the content is correct. Record this as a `wrong_language` failure under
section 14.

---

## 8. Expected behavior and reference answers

### 8.1 Expected behavior

Every item has an `expected_behavior` statement. It describes:

- what the response must accomplish;
- the required response language;
- any format, length, or content constraints;
- whether uncertainty or a refusal is acceptable;
- any cultural interpretation the response must respect;
- any required code-switching behavior.

`expected_behavior` is not a single gold answer. It is the basis for scoring
open-ended items.

### 8.2 Reference-answer policy

- Closed factual items may have one native-authored reference answer.
- Translation-probe items may have one reference translation.
- Open conversational items use `expected_behavior` plus the rubric, not a
  single reference string.
- Cultural items may record more than one accepted interpretation, with a
  native-authored note explaining the range.
- A `reference_answer` is set only when a native speaker authored or
  approved it. A model must never fill in a Luganda reference answer.
- `accepted_alternatives` records defensible variants that should not be
  marked wrong.

### 8.3 Reference status

- `authored`: a native-authored reference exists. The reviewer ID and date are
  recorded.
- `pending`: a reference is expected but has not been authored. The item
  cannot be approved until it is resolved.
- `not_applicable`: the item is open-ended or intrinsically ambiguous. The
  reason is recorded in `ambiguity_notes`.

### 8.4 Source-derived references

If a reference is borrowed from SALT, FLORES, MAFAND, Wikipedia, or another
source:

- record the source URL and licence in `source`;
- confirm that the licence permits this use;
- check for contamination under section 17;
- do not copy a source sentence verbatim into a conversational item merely
  to save authoring effort;
- do not use the hidden FLORES test split.

---

## 9. Ambiguity review

Every item gets an ambiguity check before native review.

### 9.1 Procedure

1. The author records the intended reading and any plausible alternatives in
   `ambiguity_notes`.
2. A second reviewer, fluent in Luganda and not the author, reads the item
   without the intended answer and states what they think it asks.
3. If the two readings differ materially, the item is rewritten.
4. If the ambiguity is intrinsic, for example a proverb with several accepted
   interpretations, the item sets `reference_status` to `not_applicable`,
   records the alternatives, and is scored on the rubric rather than against
   one answer.
5. The second reviewer records the outcome and moves the item to
   `ambiguity_checked` if it is ready for native review.

### 9.2 Rules

- An ambiguous item is never scored as a model failure merely because the
  model chose a defensible alternative.
- If the ambiguity cannot be resolved, exclude the item or mark it
  `not_applicable` with a clear note.
- The ambiguity reviewer may be a native speaker or a fluent second reviewer.
  Native review under section 12 is still required for language quality.
- Ambiguity notes are part of the item file, not an informal comment.

---

## 10. Scoring dimensions

The seven dimensions are defined below. The names are unchanged from
`docs/EVALUATION_PLAN.md`.

### 10.1 Semantic correctness

Does the response mean what it should, given the prompt and expected
behavior? This includes meaning preservation, correct entailment, no
distortion, and no omission of critical content. It does not measure grammar,
style, or factual truth independently.

### 10.2 Grammar and naturalness

Is the Luganda grammatical, idiomatic, and fluent for the requested register?
This includes morphology, agreement, word order, orthography, collocation,
and naturalness. It does not measure factual correctness or whether the
instruction was followed.

### 10.3 Instruction compliance

Was the instruction actually followed? This includes format, length,
response language, required elements, and explicit constraints. It does not
measure whether the content is true, except where the instruction is about
truth or uncertainty.

### 10.4 Relevance

Does the response answer the question asked, with appropriate scope? This
includes no drift, no unnecessary content, and coverage of sub-questions. It
does not measure factual truth.

### 10.5 Context retention

Was conversation context maintained across turns? This includes resolving
references, respecting earlier constraints, and avoiding contradictions.
This dimension applies only to multi-turn items.

### 10.6 Factual reliability

Are factual claims correct, appropriately qualified, and free of
fabrication? This includes admitting uncertainty when the model does not
know. It applies to Factuality and appropriate uncertainty, Explanation and
reasoning, and factual claims inside Cultural and linguistic interpretation
items.

### 10.7 Appropriate register

Does the register match the request? This includes formality, honorifics,
slang, code-switch balance, and cultural appropriateness. It does not measure
grammar alone.

### 10.8 Applicability matrix

| Dimension | Applies to | Notes |
|---|---|---|
| Semantic correctness | All items | Always applicable |
| Grammar and naturalness | All items | Always applicable |
| Instruction compliance | Instruction following, Multi-turn, Code-switching, and any item with hard constraints | Conditional items declare it in `scoring_dimensions` |
| Relevance | All items | Always applicable |
| Context retention | Multi-turn only | Not applicable to single-turn items |
| Factual reliability | Factuality, Explanation and reasoning, and factual claims in Cultural items | Conditional for Cultural items |
| Appropriate register | Formal, Everyday, Colloquial, Code-switching, and Cultural items | Conditional for other items when the item specifies a register |

"Conditional" means the item's `scoring_dimensions` array must include the
dimension and `expected_behavior` must state the relevant constraint.

This matrix refines the research-draft matrix in
`docs/PHASE-1-RESEARCH.md` by applying Appropriate register to Everyday items,
because ordinary conversational usage also has a register, and by making
Instruction compliance and Appropriate register conditional whenever an item
states a relevant constraint. These refinements are proposals for owner
approval. They do not rename or replace any dimension.

### 10.9 Non-applicable dimensions

- A dimension that does not apply is recorded as `null`, not `0`.
- `null` is allowed only when the dimension is absent from the item's
  `scoring_dimensions`.
- Nulls are not averaged, imputed, or treated as zero.
- The report states how many items each dimension applied to.
- Do not use `null` to hide a failure. If a dimension applies but the
  response is empty, truncated, or otherwise unjudgeable, record a failure
  code under section 14 and follow the exclusion rules.

---

## 11. Scoring scale and anchors

### 11.1 Five-point scale

| Score | Label | General meaning |
|---:|---|---|
| 1 | Unacceptable | Fails the requirement in a way that makes the response unusable or misleading |
| 2 | Weak | Partly meets the requirement, with major problems |
| 3 | Adequate | Meets the core requirement, with noticeable but non-blocking problems |
| 4 | Good | Meets the requirement with minor problems |
| 5 | Excellent | Fully meets the requirement with no material problems |

Scores are integers. Do not use half points.

### 11.2 Dimension anchors

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Semantic correctness | Meaning is wrong or contradicts the prompt | Main meaning is preserved; minor omission or imprecision | Meaning is fully preserved, including nuance and implied content |
| Grammar and naturalness | Not understandable as Luganda, or systematic grammar failure | Understandable; noticeable errors or unidiomatic phrasing that do not block meaning | Grammatical, idiomatic, native-sounding Luganda for the requested register |
| Instruction compliance | Ignores the instruction or violates a hard constraint | Follows the main instruction; misses a secondary constraint | Follows all stated constraints, format, length, and response language |
| Relevance | Off-topic or does not answer | Partly relevant; some drift or a missing sub-question | Directly answers the question with appropriate scope |
| Context retention | Forgets or contradicts earlier turns | Retains the main context; loses a minor detail | Consistently uses earlier turns, resolves references, and avoids contradictions |
| Factual reliability | Confident false claim or fabricated source | Mostly correct; a minor error or unsupported detail | Correct, appropriately qualified, no fabrication; says "I do not know" when needed |
| Appropriate register | Register is wrong for the request | Broadly appropriate; some mixing or inconsistency | Consistently matches the requested register and audience |

Scores of 2 and 4 are used when the response falls between the adjacent
anchors. Reviewers record a short note explaining why a score is 2 or 4,
because the anchors are written for 1, 3, and 5.

### 11.3 Scoring rules

- Score only the dimensions in the item's `scoring_dimensions`.
- Use the anchors for 1, 3, and 5, and interpolate for 2 and 4.
- Record a note for every dimension scored below 3 or above 4.
- Record a failure code separately from the dimension scores when a failure
  category in section 14 applies.
- Do not adjust a score because of another dimension. For example, do not
  raise Grammar because the content is factually correct.
- Do not score a response against a reference answer when
  `reference_status` is `not_applicable`.
- Do not score a model on an item it did not receive in the identified run.

### 11.4 No unweighted composite

This specification does not define an overall score, an average of the seven
dimensions, or a leaderboard rank.

- Report per-dimension distributions.
- Report the number of applicable items per dimension.
- Do not average across dimensions with different applicability.
- Do not convert scores to percentages unless the owner approves a
  documented transformation.
- If a single decision score is required later, the owner must approve
  weights or a decision rule in advance, and the change requires a new
  benchmark version.

---

## 12. Native-speaker review

D-004 makes native-speaker review mandatory for language-quality
assessment. This section defines the proposed process. No reviewer has been
recruited, and no review has occurred.

### 12.1 Panel

- At least two native Luganda speakers review each item and each response.
- A third native reviewer adjudicates material disagreements.
- Reviewers must be literate in Luganda and able to apply the rubric.
- The panel should cover the registers in the benchmark, including formal,
  everyday, colloquial, and code-switched usage.
- Regional and dialect coverage should be recorded. A single variety must not
  be treated as the only correct Luganda.
- Reviewers must not be authors of the model output being scored.
- An item author may review the item, but that involvement is recorded.
- Reviewer IDs are pseudonymous in the item file.

Reviewer qualifications, panel size, compensation, consent, and data
retention require owner approval.

### 12.2 Calibration

1. Use a calibration set of about five items, separate from the 50 reported
   items.
2. All reviewers score the calibration set independently.
3. Reviewers compare scores and discuss differences against the anchors.
4. The calibration is used to align interpretation, not to produce results.
5. Calibration scores are recorded and are not included in the reported
   benchmark results.
6. If calibration reveals that an anchor is unclear, revise the anchor before
   the main review. A change to an anchor is a benchmark version change.

### 12.3 Independent scoring

- Reviewers score independently and do not see each other's scores before
  submitting.
- Reviewers do not see model identity. Responses are presented in a
  randomised order where feasible.
- Reviewers see the item, `expected_behavior`, reference answer if any,
  accepted alternatives, ambiguity notes, and the rubric.
- Reviewers record a score for each applicable dimension and a note for
  material problems.
- Reviewers may flag ambiguity, contamination, safety, or other issues.

### 12.4 Disagreement and adjudication

A material disagreement is:

- a difference of two or more points on any dimension; or
- a disagreement about whether a response is acceptable at all; or
- a disagreement about the failure code.

For a material disagreement:

1. The original scores and notes are preserved.
2. A third native reviewer reviews the item, response, both score sets, and
   notes.
3. The adjudicator assigns a final score per dimension and a final failure
   code, with a written rationale.
4. The adjudicated score is the primary score for reporting.
5. The original scores remain available for agreement analysis.

### 12.5 Agreement

- Report exact agreement and agreement within one point for each dimension.
- Report a chance-corrected statistic, such as quadratic-weighted Cohen's
  kappa or an intraclass correlation coefficient. Record which statistic was
  used.
- A proposed minimum is 0.60 for quadratic-weighted kappa or 0.75 for the
  intraclass correlation coefficient. The owner must approve the threshold
  before scoring.
- If agreement is below the approved threshold, recalibrate or revise the
  anchors, then rescore the affected items. Do not publish the scores as
  final while agreement is below threshold.
- Report agreement per dimension, not only overall.

### 12.6 Review records

Each review record contains:

- `review_id`;
- `item_id`;
- `run_id`;
- `reviewer_id`;
- `role` (`native_reviewer` or `adjudicator`);
- `date`;
- `calibration_completed`;
- `dimension`;
- `score`;
- `note`;
- `flag`;
- `adjudication_required`;
- `adjudicated_score`;
- `adjudicator_id`;
- `adjudication_note`.

### 12.7 Review status transitions

- `draft` to `ambiguity_checked`: second reviewer completes the ambiguity
  check.
- `ambiguity_checked` to `native_reviewed`: at least two native reviewers
  complete scoring and any material disagreement is adjudicated.
- `native_reviewed` to `approved`: project owner approves the item for a
  frozen benchmark version.
- Any status to `excluded`: owner or designate records the reason.

No item is currently beyond `draft`, because no item exists.

### 12.8 What native review must not be replaced by

AI judgments, automated metrics, or model self-reports must not be presented
as native-speaker review. They may support logistics, such as flagging
possible errors, but they do not satisfy D-004.

---

## 13. Model-run protocol and metadata

No run is authorized by this specification. A run requires owner approval of
the benchmark version, model list, access path, budget, and native-review
plan.

### 13.1 Pre-run requirements

Before a reported run:

- the benchmark version is frozen and hashed;
- the item file has passed the ambiguity and native-review requirements;
- the model and revision are approved;
- gated access and licence terms are approved;
- the budget is approved;
- the run manifest template is ready;
- the raw-response storage path is ready;
- the native-review plan is ready;
- a pilot run on 3 to 5 items has validated the pipeline.

### 13.2 Run manifest fields

| Field | Required | Notes |
|---|---|---|
| `run_id` | Yes | Unique, for example `LGP-RUN-2026-001` |
| `benchmark_version` | Yes | Frozen version |
| `item_file_sha256` | Yes | Hash of the exact item file |
| `model_id` | Yes | Exact repository or provider identifier |
| `model_revision` | Yes | Commit hash or provider version. Do not use a moving `main` |
| `base_model_id` | Conditional | For adapters |
| `base_model_revision` | Conditional | For adapters |
| `adapter_id` | Conditional | For adapters |
| `adapter_revision` | Conditional | For adapters |
| `tokenizer_id` | Yes | Exact tokenizer |
| `tokenizer_revision` | Yes | Exact revision |
| `chat_template` | Yes | Template or a hash of it |
| `system_prompt` | Conditional | Null if none |
| `quantization` | Yes | For example `none`, `8-bit`, `4-bit` |
| `dtype` | Yes | For example `float32`, `bfloat16` |
| `device` | Yes | CPU, GPU, or hosted |
| `framework_versions` | Yes | Python, PyTorch, Transformers, PEFT, runtime |
| `decoding` | Yes | Temperature, top_p, top_k, max new tokens, stop sequences, repetition penalty |
| `seed` | Conditional | Null if the interface does not expose one |
| `samples_per_item` | Yes | 1 for the primary greedy run |
| `batch_size` | Yes | Recorded even if 1 |
| `hardware` | Yes | CPU, GPU, memory, provider |
| `operating_system` | Yes | Exact version |
| `started_at` | Yes | Timestamp |
| `finished_at` | Yes | Timestamp |
| `wall_clock_seconds` | Yes | Measured |
| `peak_memory` | Conditional | Record if measured |
| `cost` | Yes | Local, paid, or none, with fields in section 13.6 |
| `approval_reference` | Yes | Owner approval identifier or "not required" |
| `raw_response_path` | Yes | Path to the raw response file |
| `operator` | Yes | Pseudonymous operator ID |

For a hosted API, also record the provider, model version or date, request
ID, region if exposed, and data-retention terms.

### 13.3 Raw response record

Each raw response record contains:

```json
{
  "run_id": "LGP-RUN-2026-001",
  "item_id": "LGP-BENCH-FORMAL-001",
  "turn_index": 0,
  "sample_index": 0,
  "model_id": "<model identifier>",
  "model_revision": "<revision>",
  "timestamp": "<ISO timestamp>",
  "raw_response": "<verbatim model output>",
  "finish_reason": "<reason or null>",
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "latency_ms": 0,
  "error": null
}
```

Rules:

- `raw_response` is stored verbatim.
- Do not edit, normalise, translate, or truncate the stored response.
- If a normalised version is needed for analysis, store it separately under
  `derived/` and keep the raw version as canonical.
- Record errors and empty responses. Do not silently drop them.
- Keep the model-identity mapping separate from reviewer packets so that
  reviewers can score blind.

### 13.4 Proposed storage layout

The following paths are proposals. They are not created by this document.

```
reports/benchmark/runs/<run_id>/run_manifest.json
reports/benchmark/runs/<run_id>/raw_responses.jsonl
reports/benchmark/runs/<run_id>/derived/
reports/benchmark/runs/<run_id>/scores/
reports/benchmark/runs/<run_id>/review_packets/
```

`reports/` is ignored by Git, so raw responses and reviewer packets are not
committed. The benchmark item file itself is proposed for a dedicated path
such as `data/benchmark/items/<version>.jsonl`, but that path is not created
here. If a `.jsonl` item file is later committed, it requires a narrow,
path-specific `.gitignore` negation approved by the owner, as required by
`data/README.md`.

### 13.5 Reproducibility

1. Freeze the item file and record its SHA-256.
2. Pin the model, tokenizer, and adapter revisions.
3. Record every decoding setting.
4. Use greedy decoding, temperature 0, as the primary setting.
5. Optionally run three samples at a documented higher temperature to show
   variance. Report those separately from the greedy results.
6. Use the same prompt template for every model. If a model requires a
   different chat template, record it and do not tune the prompt per model.
7. Record the Python version, operating system, and key library versions.
8. Store raw responses verbatim.
9. A change to the prompts, model revision, or settings creates a new run ID
   or benchmark version. Do not compare results across versions without
   documenting the difference.
10. Record the access path for gated resources so a rerun can establish
    whether the same snapshot was used.
11. Record the date and version of a hosted API. A provider update after the
    run is a new run.

### 13.6 Cost recording

| Cost type | Fields | Rule |
|---|---|---|
| Local compute | Hardware, wall-clock hours, estimated marginal cost or "no marginal cost" | Record actual use |
| Paid API | Provider, model, input tokens, output tokens, unit price, total, currency, approval reference, cap | No call without prior owner approval |
| Native review | Reviewer hours, rate, total, approval reference | Budget must be approved before recruitment |
| Storage and other | Storage, tooling, or service cost | Record actual cost |

Record approved budget and actual cost separately. Stop a run if the
approved cap is reached. Do not hide cost in an aggregate.

### 13.7 Local environment

The primary development machine is Windows with approximately 8 GB RAM.
Quantised local inference, especially 4-bit inference, must be tested before
local feasibility is claimed. If a runtime is not supported on Windows,
record that and do not present the model as locally runnable.

---

## 14. Exclusions and failure handling

### 14.1 Item exclusions

Exclude an item, and record the reason, when:

- the licence is unresolved;
- the ambiguity is unresolved;
- contamination is known or suspected;
- the item duplicates another item;
- required metadata is missing;
- the item has not received the required native review;
- the source text is unlicensed or cannot be used.

### 14.2 Run exclusions

Exclude a run, and record the reason, when:

- the model revision or benchmark hash is missing;
- the prompt set or benchmark version does not match the reported version;
- decoding settings or the chat template are missing;
- the required native review is absent for a reported language score;
- the approved cost cap was exceeded without approval;
- a hosted model changed version during the run;
- the run used benchmark items as few-shot examples or tuning data.

### 14.3 Output exclusions

Exclude an output, and report the count, when:

- it is truncated by a token limit, unless truncation is the behavior being
  measured;
- it is empty because of a runtime error;
- it contains a system error rather than a model response.

Wrong-language output is a failure, not an exclusion. A model that cannot
produce Luganda at all is reported as failing the relevant items.

### 14.4 Failure codes

Record these separately from dimension scores:

- `wrong_language`
- `refusal`
- `hallucination`
- `truncation`
- `unsafe`
- `off_topic`
- `format_violation`
- `empty`

### 14.5 Reporting exclusions and failures

- Report the number of excluded items, runs, and outputs.
- Report the reason for each exclusion category.
- Do not silently drop failures.
- Do not report a score for a model that was not run.
- Do not compare a run that used a different benchmark version without
  documenting the difference.

---

## 15. Benchmark versioning and change control

### 15.1 Version format

- Draft versions use `0.x-draft`, for example `0.1-draft`.
- The first approved frozen version is `1.0`.
- Later versions use `MAJOR.MINOR`.
- A version is frozen only when the item file and scoring rules are fixed
  and the owner has approved them.

### 15.2 Change classes

| Change | Version effect | Approval |
|---|---|---|
| Typo or formatting only, no prompt or score change | Patch or editorial note | Owner or designate |
| Add or remove items without changing categories, dimensions, scale, or allocation | Minor | Owner |
| Change category definitions, dimension definitions, scale anchors, applicability, or allocation | Major | Owner |
| Change scoring rules or add a composite score | Major | Owner |
| Freeze an approved benchmark | `1.0` | Owner |

### 15.3 Change records

Every version has:

- a version identifier;
- a date;
- a changelog entry;
- the item-file SHA-256;
- the approval record, when approved;
- a list of changed items, if any.

### 15.4 Freeze rules

- Freeze the item file before a reported run.
- Do not edit the frozen file during a run.
- Any edit after the freeze creates a new version and a new hash.
- A run cites the exact version and hash.
- Do not compare results across versions without documenting the difference.

### 15.5 No silent edits

No category, dimension, prompt, anchor, allocation, or scoring rule may be
changed silently. Each change is recorded in the changelog and, where
required, approved by the owner.

---

## 16. Optional translation track

Translation evaluation is separate from the conversational benchmark. It is
an optional track, not part of the 50 conversational prompts.

### 16.1 Purpose

The translation track would compare translation-only models on Luganda to
English and English to Luganda. It exists because translation-only models
cannot be scored fairly on the nine conversational categories.

### 16.2 Scope

- Separate item file and separate report.
- Not included in the 50 conversational items.
- Not combined with the seven-dimension conversational score.
- Uses `track: translation_probe`.
- Requires owner approval before any work.

### 16.3 Data candidates

Possible evaluation data, subject to licence and contamination review:

- FLORES-200 `lug_Latn` devtest;
- SALT dev or test text, if the licence and gating terms permit it.

Do not use the hidden FLORES test split. Do not train on the evaluation data.
Do not use SALT sentences as conversational items.

### 16.4 Metrics

Possible metrics, subject to approval:

- chrF++;
- spBLEU;
- COMET, if an approved implementation and model are available.

Report each translation direction separately. Report the data snapshot,
licence, model revision, and decoding settings.

### 16.5 Native review for translation

If translation quality is reported as a language-quality claim, native
reviewers must assess adequacy and fluency. Use a separate translation
protocol approved by the owner. Do not reuse the conversational rubric as if
it measured translation.

### 16.6 Models

The translation track may use translation-only models such as NLLB, Sunbird's
translation model, or OPUS-MT. Model selection, access, and budget require a
separate owner decision.

### 16.7 Status

The translation track is proposed only. It is not in scope until the owner
approves it.

---

## 17. Contamination control

### 17.1 Principles

- Benchmark items are original. They are not copied from SALT, FLORES,
  MAFAND, Wikipedia, or a model's training set.
- If an item is inspired by a source, the source is recorded and the item is
  rewritten so it is not a near-duplicate.
- Benchmark data is kept separate from training data.
- Benchmark items are not used for tuning, few-shot examples, or
  demonstration examples in a reported evaluation.

### 17.2 Checks

- Check exact and near-duplicate overlap between benchmark items and any
  training data whose contents are known.
- Use an 8-gram overlap check plus manual review of flagged pairs as a
  starting point.
- Record what was checked and what remains unknown.
- A negative check on available data does not prove the model never saw the
  item.

### 17.3 Model-specific risks

- `AmplifiedAccess/Luganda-gemma-1b-it` states that it was trained on SALT.
  SALT sentences must not be used as conversational benchmark items.
- Sunflower's training data is not public in the metadata reviewed. Its
  contamination status is unknown, not clean.
- If the translation track uses FLORES or SALT, check overlap with each
  model's training data where possible.

### 17.4 Private holdout

If benchmark items are published, consider keeping a private holdout subset
to detect future contamination. The owner decides whether the benchmark is
public, private, or partly private.

### 17.5 Record limits

Contamination control is limited by the absence of a complete training-data
inventory. Unknown training data is recorded as unknown, not as clean.

---

## 18. Limitations

- Approximately 50 items give limited statistical power. Small differences
  should not be over-interpreted.
- The model set is a convenience sample, not a leaderboard.
- The native reviewer pool may be small and may not represent all Luganda
  varieties or registers.
- No trained LugandaGPT exists. This is a baseline benchmark specification,
  not a product evaluation.
- Translation-only models cannot be scored on the nine conversational
  categories. They belong in the optional translation track.
- Self-reported numbers on model cards are not independently verified.
- Contamination cannot be fully ruled out without a training-data inventory.
- The orthography and register standards depend on native-speaker agreement
  that has not yet happened.
- Automated metrics and AI judgments are supporting evidence, not ground
  truth.
- Local memory estimates are arithmetic, not measured peak memory.
- This specification is a draft and has not been approved.

---

## 19. Decisions requiring project-owner approval

All decisions below are open. No decision is approved by this document.

| ID | Decision | Proposal in this document | Status |
|---|---|---|---|
| O-01 | Approve this specification as the benchmark specification for review | Version `0.1-draft` | Open |
| O-02 | Approve the draft category allocation | 6/7/6/6/5/5/6/5/4, total 50 | Open |
| O-03 | Approve the item schema and stable ID scheme | Section 6 | Open |
| O-04 | Approve prompt and response language rules | Section 7 | Open |
| O-05 | Approve reference-answer and ambiguity policy | Sections 8 and 9 | Open |
| O-06 | Approve the five-point scale and anchors | Section 11 | Open |
| O-07 | Approve the applicability matrix and the no-composite rule | Sections 10 and 11 | Open |
| O-08 | Approve the native reviewer panel, qualifications, compensation, consent, and data retention | Section 12 | Open |
| O-09 | Approve calibration, disagreement, adjudication, and agreement thresholds | Section 12 | Open |
| O-10 | Approve the optional translation track | Section 16 | Open |
| O-11 | Approve benchmark storage, version-control, and public/private status | Sections 13 and 15 | Open |
| O-12 | Approve the model shortlist, access path, and run plan | Separate from this specification | Open |
| O-13 | Approve the budget for native review and any hosted inference | Section 13 | Open |
| O-14 | Approve legal and licence review for any source-derived item | Sections 6, 8, and 17 | Open |
| O-15 | Approve prompt authoring and the start of native review | This is the next phase after approval | Open |
| O-16 | Decide whether to add a decision record for the approved benchmark specification and whether to update roadmap or README status | Not done here | Open |
| O-17 | Approve reporting, exclusion, and release rules | Sections 14 and 15 | Open |

D-005 is not among these decisions. It remains open and unchanged.

---

## 20. Requirements awaiting native-speaker review

The following requirements cannot be completed until native Luganda
reviewers are recruited, approved, and available. No reviewer has been
recruited.

| Requirement | Why native review is required | Status |
|---|---|---|
| Orthography standard | Native speakers must agree on acceptable spelling and conventions | Blocked |
| Formal register definition | Formal Luganda cannot be defined by an AI judgment alone | Blocked |
| Everyday and colloquial register definitions | Naturalness and slang vary by community and region | Blocked |
| Cultural interpretations and proverb meanings | Accepted meanings and cultural context require native knowledge | Blocked |
| Reference answers for closed items | A Luganda reference must be native-authored or native-approved | Blocked |
| Accepted alternatives for open items | Several answers may be correct; native reviewers must decide | Blocked |
| Ambiguity adjudication | Native reading is needed to judge whether an item is ambiguous | Blocked |
| Calibration and anchor validation | Reviewers must align on the five-point anchors | Blocked |
| Independent scoring of responses | D-004 requires native language-quality assessment | Blocked |
| Disagreement adjudication | A third native reviewer must resolve material disagreements | Blocked |
| Agreement statistics | Agreement must be computed from real reviewer scores | Blocked |
| Dialect and regional variation decisions | No single variety should be treated as the only correct Luganda | Blocked |
| Code-switching norms | Acceptable mixing patterns require native judgment | Blocked |
| Technical terminology choices | Loanwords, descriptions, and glosses need native review | Blocked |
| Final language-quality sign-off | The benchmark cannot be approved without native review | Blocked |
| Translation adequacy and fluency, if the optional track is approved | Translation quality claims require separate native assessment | Blocked |

These are dependencies, not completed work.

---

## 21. Review checklist

### 21.1 Project-owner checklist

- [ ] The nine categories are preserved.
- [ ] The seven dimensions are preserved.
- [ ] The approximately 50-prompt target is preserved.
- [ ] The category allocation is treated as a draft, not a final allocation.
- [ ] The item schema includes all required fields.
- [ ] The five-point scale and anchors are acceptable.
- [ ] Non-applicable dimensions are handled without an unweighted composite.
- [ ] The native-review process is feasible and funded.
- [ ] Translation evaluation is separate from the conversational benchmark.
- [ ] All owner decisions in section 19 are reviewed.
- [ ] Native-review dependencies in section 20 are accepted.
- [ ] No prompts, native-review claims, approvals, or results are implied.

### 21.2 Native-review checklist

- [ ] Orthography standard agreed.
- [ ] Register definitions agreed.
- [ ] Calibration completed.
- [ ] Anchors understood consistently.
- [ ] Cultural notes and accepted interpretations authored.
- [ ] Reference answers and alternatives authored where needed.
- [ ] Independent scoring completed.
- [ ] Disagreements adjudicated.
- [ ] Agreement statistics computed.
- [ ] Final language-quality sign-off recorded.

### 21.3 Engineering checklist

- [ ] Item file schema validated.
- [ ] Stable IDs checked for duplicates.
- [ ] Benchmark version and hash recorded.
- [ ] Run manifest template ready.
- [ ] Raw-response storage ready.
- [ ] Reviewer packets blind to model identity.
- [ ] Exclusion reporting ready.
- [ ] No secrets, personal data, or unlicensed text in the item file.

---

## 22. Approval record template

This section is a template. It is blank because the specification is not
approved.

```
Specification version:
Benchmark version:
Approved by:
Role:
Date:
Scope:
Conditions:
```

Native-review sign-off:

```
Reviewer panel:
Calibration date:
Agreement statistic:
Items reviewed:
Sign-off date:
```

No approval is recorded in this draft.

---

## 23. Change log

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1-draft | 2026-10-20 | Initial benchmark specification for owner review | Draft |

---

## 24. References

- `docs/EVALUATION_PLAN.md`: existing benchmark policy, nine categories,
  seven dimensions, approximately 50-prompt target, contamination principles.
- `docs/PHASE-1-RESEARCH.md`: resource validation, model shortlist, evidence,
  and Phase 1 exit-criteria mapping.
- `docs/DECISIONS.md`: D-001 to D-006.
- `docs/ROADMAP.md`: Phase 1 objectives and exit criteria.
- `docs/EXPERIMENT_LOG.md`: experiment record template.
- `data/README.md`: dataset governance and provenance requirements.
- `AGENTS.md`: working, honesty, cost, secrets, and approval-gate rules.
