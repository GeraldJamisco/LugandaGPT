# Architecture

This document describes **proposed system boundaries** only. It does not
commit the project to any model family, architecture, parameter count,
tokenizer, corpus size, or compute provider.

> **Status:** Proposal. Nothing described below is implemented.
> No trained LugandaGPT model currently exists.

**UNDECIDED (pending documented experiments):**
- Model family and architecture
- Parameter count
- Tokenizer choice
- Training corpus size
- Training method (pre-training, continued pre-training, adaptation)
- Compute provider

These will be selected through documented experiments and constraints —
not by assumption. See `docs/DECISIONS.md` (D-005).

---

## System boundaries

The system is conceived as a pipeline with clear boundaries between stages.
Each stage should be independently testable and documented.

### 1. Data ingestion and provenance
- Accepts data from approved sources only.
- Records provenance, license, acquisition date, and origin per dataset.
- Governed by `data/README.md`.
- Nothing is acquired without project-director approval.

### 2. Data cleaning and quality validation
- Normalization, filtering, deduplication, and quality checks.
- Tooling written in Python, with tests.
- Produces versioned, integrity-checked datasets.

### 3. Tokenizer evaluation
- Compares candidate tokenizers on Luganda-specific measures (e.g.,
  token fertility, vocabulary coverage of Luganda morphology).
- Produces a documented recommendation, or explicitly leaves the choice
  open.

### 4. Model training or adaptation
- **Undecided and not implemented.** Runs only after explicit approval, an
  approved experiment design, and an approved budget.
- On this machine (~8 GB RAM, limited free disk), only code, tests, and
  tiny-sample smoke checks are realistic.

### 5. Instruction tuning
- **Conditional**, performed only if justified by earlier results.

### 6. Evaluation and human review
- Automated evaluation plus mandatory native-speaker assessment.
- Benchmark kept separate from training data to limit contamination.
- See `docs/EVALUATION_PLAN.md`.

### 7. Inference and future deployment
- Long-term. Requires an approved, validated model and director sign-off.

---

## Environment constraints

The primary development machine has approximately **8 GB RAM and limited
free disk space**. Therefore:

- Local development focuses on **code, small samples, tests, and evaluation
  tooling**.
- Large-scale data processing and training will not run on this machine.

## Dependency policy

**No specific ML dependency stack is selected yet.** Framework choice
follows from the architecture decision, not the reverse. New dependencies
should be justified and minimal.
