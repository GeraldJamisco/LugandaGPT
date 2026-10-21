# Decisions (Lightweight ADR Log)

Architecture decision records in a lightweight format. Each entry includes
**Context**, **Decision**, **Rationale**, **Consequences**, and **Status**.

Statuses: *Accepted* | *Open* | *Superseded* | *Rejected*.

---

## D-001 — Luganda-native model, not a translation app or chatbot wrapper

**Context:** Available Luganda tooling tends to be translation-focused or a
wrapper over a general-purpose model. Neither provides deep, native command
of the language.

**Decision:** The project aims to build a **Luganda-native conversational
language model**, not merely a translation application or a wrapper around
another provider's chatbot API.

**Rationale:** The stated goal — natural conversational Luganda, register
control, code-switching, and cultural accuracy — is not achievable by
translation shims alone.

**Consequences:** The project carries the cost and complexity of model
development rather than only prompt engineering. Translation may still be a
useful internal component or benchmark, but it is not the product.

**Status:** Accepted.

---

## D-002 — Initial scope is text-only

**Context:** Speech and multimodal work expand scope and cost substantially.

**Decision:** The initial scope is **text-only**.

**Rationale:** Text provides the fastest path to a usable conversational
model and a testable evaluation benchmark.

**Consequences:** Speech capabilities are explicitly out of scope for now.
Architecture choices should not be forced to accommodate audio yet.

**Status:** Accepted.

---

## D-003 — DeepSeek is the engineering agent, not the model foundation

**Context:** Division of labor among AI systems needs to be explicit.

**Decision:** **DeepSeek** acts as the primary engineering agent
(implementation, debugging, tests, data tooling, training infrastructure).
It is not itself the model that LugandaGPT is built on.

**Rationale:** Separating "who builds the system" from "what the system is"
avoids conflating tooling with architecture.

**Consequences:** No architectural commitment to any DeepSeek model. Model
foundation remains undecided (see D-005).

**Status:** Accepted.

---

## D-004 — Native-speaker evaluation is required

**Context:** Automated metrics and AI judgments do not reliably capture
Luganda grammaticality, naturalness, or cultural accuracy.

**Decision:** **Native Luganda speakers** are required for meaningful
language-quality assessment.

**Rationale:** Human judgment is the reference standard for language
quality; AI-generated judgments are not ground truth.

**Consequences:** Evaluation designs must include a human-review component
and budget/coordinate evaluator time. Automated metrics are supporting
evidence only.

**Status:** Accepted.

---

## D-005 — Model architecture, parameter count, and training strategy remain unselected

**Context:** Choosing a model family, size, tokenizer, or training method
before evidence would be an unjustified assumption and could waste compute.

**Decision:** **Model architecture, parameter count, and training strategy
remain unselected** pending evidence from research, baseline evaluation,
tokenizer experiments, and feasibility studies.

**Rationale:** Decisions should follow documented experiments and
constraints (data volume, licensing, compute, budget), not assumptions.

**Consequences:** No training runs are authorized on the basis of a chosen
architecture yet. When a choice is proposed, it must be documented here with
rationale and approved by the project director before implementation.

**Status:** Open.

---

## D-006 — Separation of responsibilities

**Context:** The project involves a human owner, multiple AI systems, and
human language evaluators. Without an explicit division of labor, roles can
blur — an engineering agent could appear to authorize spending, or an AI
judgment could be mistaken for linguistic ground truth.

**Decision:** Responsibilities are separated as follows:

- **Human project director:** priorities, approvals, and spending.
- **DeepSeek:** primary engineering agent.
- **ChatGPT:** architecture and research review.
- **Native Luganda speakers:** human linguistic evaluation.

**Rationale:** Keeping decision authority, implementation, review, and
language-quality judgment in distinct hands prevents any one party from
simultaneously producing work, reviewing it, and approving it — and keeps
spending control with the human owner.

**Consequences:** Engineering agents implement but do not authorize scope,
budget, or architecture changes. Research and architecture proposals come
from ChatGPT as review input, not as instructions to be executed without
project-director approval. Luganda quality claims require native-speaker
evaluation. These responsibilities are also recorded in `AGENTS.md` §6.

**Status:** Accepted.

---

## D-007 - Benchmark specification approved, benchmark not yet approved

**Context:** The Project Director reviewed and explicitly approved the current
contents of `docs/BENCHMARK-SPECIFICATION.md`, then labelled version
`0.1-draft`. The document still carried draft approval metadata and listed its
own approval as open. No benchmark items, native reviews, or evaluation runs
exist.

**Decision:** The benchmark specification is approved at specification
version `1.0`, without substantive changes to the reviewed contents. The
approval covers the specification's categories, dimensions, item schema,
language rules, reference and ambiguity policy, scoring rules, review rules,
versioning, and run-record requirements. It resolves O-01 and O-03 through
O-07 in section 19 of the specification.

This decision does not approve an item file, benchmark version, native-review
process, model access, budget, evaluation run, or release. It is not a native
speaker sign-off and does not replace the `ApprovalRecord` required for a
frozen benchmark version. The actual benchmark remains unfrozen and
unapproved.

**Rationale:** Owner approval of a specification is separate from native
language review and from release approval. Recording the distinction prevents
the approved document from being mistaken for an approved benchmark.

**Consequences:** The specification approval is recorded in D-007. Prompt
authoring, native review, benchmark freezing, and evaluation remain blocked on
the owner actions listed in section 19 and the native-review dependencies in
section 20. O-02, O-08 through O-15, and O-17 remain open. O-16 is partly
resolved because this decision record was added; the owner has not decided
whether to update roadmap or README status.

**Status:** Accepted.

---

## D-008 - Bounded Runpod RTX 4090 gate for Approach B

**Context:** The Project Director reviewed `reports/FINE-TUNING-FEASIBILITY.md`
and approved Approach B for a first bounded gate. The owner selected Runpod
and an NVIDIA RTX 4090 with 24 GB of VRAM, capped total compute and storage
spending at $20, authorized a 100-example data pilot and a 50 to 100 example
training smoke test, and required a separate approval before full fine-tuning.
D-005 remains open. This decision does not select the final architecture,
parameter count, or training strategy.

**Decision:** The first gate uses one Runpod Secure Cloud RTX 4090 at the
publicly listed $0.89 per hour, checked on 2026-10-21. The candidate is a fresh
LoRA adapter from the pinned base, not a continuation of the existing adapter.
The gate covers licence and provenance review, native-teacher agreements and
consent, a 100-example native-authored pilot, a separate evaluation set, and a
50 to 100 example smoke test. The total cash cap is $20 including taxes and
fees. The existing adapter remains a translation baseline and is not continued
as the main conversational model. No full 1,000 to 1,500 example run,
deployment, publication, or release is approved.

**Rationale:** A 24 GB RTX 4090 is sufficient for a 4-bit LoRA smoke test on a
1B model and avoids the memory limits of the local machine. Runpod's prepaid
credits and short-running Pods allow a hard spending stop. Secure Cloud is
selected over the cheaper Community Cloud tier for predictable host quality
during a short, supervised run.

**Consequences:** Execution is blocked until the owner completes account and
payment setup, live RTX 4090 availability and the tax-inclusive charge are
verified, data and teacher approvals exist, and a training script and GPU
environment have been tested. Runpod credits are non-refundable and sales tax
is charged on top of credit purchases, so the purchase must keep the total
charge at or below $20. No paid infrastructure was launched for this decision.
See `reports/RUNPOD-FIRST-GATE-REPORT.md` and
`configs/gemma3-1b-lora-smoke.yaml`.

**Status:** Accepted for the bounded gate only. D-005 remains open.

---

## D-009 - English source draft first, then native translation and review

**Context:** The Project Director reports that native Luganda speakers are
available and have agreed to collaborate. The owner and team discussed working
arrangements, and compensation is intended after the project earns its first
dollar. The repository does not contain signed agreements, formal consent
records, a compensation amount or schedule, retention terms, or a licence for
translated data. No Luganda pilot dataset exists yet.

**Decision:** The engineering workflow prepares 100 original English source
examples for the pilot and a separate 24-item English evaluation draft. The
native-speaking team translates the source into Luganda, and a second native
speaker reviews each translated item. The English source keeps stable IDs and
a draft schema that reports every translation and review as pending. The
training-data schema and its authorization checks are not weakened.

This refines the data-authoring method in D-008. The D-008 provider, GPU,
budget, and bounded-gate decision remain in force. The pilot source is
authored in English and translated and reviewed by native speakers rather
than fully authored in Luganda by the engineering workflow.

**Rationale:** English source authoring can proceed without inventing
translations, reviewers, consent, or approvals. Separating the source draft
from the training dataset prevents the English material from being mistaken
for Luganda training data. Native speakers remain the reference standard for
translation and review.

**Consequences:** The English source pilot is available for owner review in
`data/source/pilot-v1/` and `reports/ENGLISH-SOURCE-PILOT-REPORT.md`. The
Luganda training dataset remains blocked until translations, second-speaker
reviews, formal consent and compensation records, licence terms, provenance,
and training approvals exist. This decision does not create a formal
agreement or authorize a paid run. The approved benchmark specification is
unchanged. The 24-item feasibility set is not a benchmark.

**Status:** Accepted for source preparation only. Training remains blocked.
