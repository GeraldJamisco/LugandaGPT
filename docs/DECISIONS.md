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
