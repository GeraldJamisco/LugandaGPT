# Evaluation Plan

How LugandaGPT will be evaluated. This document defines the plan; **the
benchmark items and any scores or results do not exist yet.** The actual
prompts will be developed in a later task. Do not fabricate items or
results.

---

## Benchmark design

An initial benchmark of **approximately 50 prompts**, with coverage across
the categories below. The exact distribution will be set when the prompts
are written.

| Category | Description |
|---|---|
| Formal Luganda | Educated, formal register. |
| Everyday Luganda | Ordinary conversational usage. |
| Colloquial language | Informal speech, slang, regional variation. |
| Luganda-English code-switching | Mixed-language prompts and responses. |
| Instruction following | Clear, constrained tasks. |
| Multi-turn context | Prompts that require retaining earlier turns. |
| Explanation and reasoning | Concept explanations and multi-step reasoning. |
| Cultural and linguistic interpretation | Idiom, proverbs, cultural context. |
| Factuality and appropriate uncertainty | Correct facts and honest "I don't know". |

---

## Scoring rubric

Each response is scored against the following dimensions. The concrete scale
(e.g., 1–5) and per-dimension weights will be fixed when the benchmark is
built; they are noted here as required dimensions, not final values.

- **Semantic correctness**: does the response mean what it should?
- **Grammar and naturalness**: is the Luganda grammatical and fluent?
- **Instruction compliance**: was the instruction actually followed?
- **Relevance**: does it answer the question asked?
- **Context retention**: was conversation context maintained?
- **Factual reliability**: are factual claims correct?
- **Appropriate register**: does the register match the request?

---

## Human evaluation

- **Native Luganda speakers** perform the language-quality assessment.
  This is required, not optional (see `docs/DECISIONS.md`, D-004).
- AI-generated judgments are **not** the sole ground truth for Luganda
  quality; they may support, but do not replace, human review.
- Evaluators should be given a consistent rubric and, where possible,
  overlapping items to allow agreement checking.

---

## Contamination control

- Benchmark data must be **kept separate from training data**.
- Training data should be checked for overlap with benchmark items before
  any evaluation run is reported.
- Benchmark items should not be used for tuning or few-shot examples in
  reported evaluations unless that is explicitly documented.

---

## Reporting

- Report **measured results** separately from interpretation.
- Include the model/tokenizer configuration, data version, and seeds used.
- Record runs using `docs/EXPERIMENT_LOG.md`.
- Never report scores for a model that was not actually run.
- When comparing a candidate with a baseline such as Sunflower-14B, use the
  same frozen benchmark version, the same blinded packets, and the same
  reviewers, and report per-dimension distributions side by side. Report no
  overall score or win rate unless the owner approves a decision rule
  (`docs/BENCHMARK-SPECIFICATION.md` section 11.4).
