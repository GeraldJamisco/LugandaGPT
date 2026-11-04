# Roadmap

A staged plan. **No dates or costs are asserted here**, and no phase is
more advanced than its "Status" line indicates.

See [WORKING-PLAN.md](WORKING-PLAN.md) for the gate sequence that applies
these phases to the Sunflower baseline direction (D-017).

Each phase lists Objectives, Deliverables, Exit criteria, and
Dependencies / Risks.

---

## Phase 0 — Project foundation

**Status:** In progress.

**Objectives**
- Establish documentation, governance, and repository hygiene.
- Verify the development environment and reproducibility.

**Deliverables**
- `AGENTS.md`, `README.md`, `docs/` set, `data/README.md`, `.gitignore`.
- Environment and dependency conventions documented.

**Exit criteria**
- Documentation inventory complete and internally consistent.
- Git hygiene in place (ignore rules validated; no secrets committed).
- Environment requirements recorded.

**Dependencies / Risks**
- Small local machine (~8 GB RAM, limited free disk). Risky: assuming
  local capacity for anything beyond tooling and tiny samples.

---

## Phase 1 — Research and baseline

**Status:** In progress. `docs/PHASE-1-RESEARCH.md` and the approved benchmark specification (D-007) exist. No benchmark items, native review, or baseline benchmark runs exist yet.

**Objectives**
- Survey existing Luganda resources, models, and prior work.
- Evaluate existing models as baselines.
- Design an evaluation benchmark.

**Deliverables**
- Research notes and a baseline evaluation report.
- `docs/EVALUATION_PLAN.md` benchmark specification.
- Data-source investigation notes.

**Exit criteria**
- Baseline behavior of existing models documented.
- Benchmark specification reviewed and approved.
- Candidate data sources identified with licensing noted.

**Dependencies / Risks**
- Requires Phase 0 documentation. Risks: over-trusting automated
  judgments; benchmarking shortcuts that do not reflect Luganda quality.

---

## Phase 2 — Data acquisition and preparation

**Status:** Partly started. The English source pilot and the Translation Studio exist, and native translation has begun. No external dataset has been acquired, and acquisition stays blocked on owner approval.

**Objectives**
- Acquire datasets under approved licensing and privacy rules.
- Clean, deduplicate, and quality-check data.

**Deliverables**
- Documented datasets with provenance records per `data/README.md`.
- Cleaning and deduplication tooling, with tests.

**Exit criteria**
- Licensing and privacy reviewed and approved per dataset.
- Quality checks pass; datasets versioned with integrity checks.

**Dependencies / Risks**
- Requires explicit project-director approval to acquire data.
- Risks: unclear licensing, private/PII content, contamination of
  evaluation data.

---

## Phase 3 — Tokenizer and feasibility

**Status:** Blocked on Phase 2.

**Objectives**
- Evaluate tokenizer options for Luganda.
- Run small feasibility experiments.

**Deliverables**
- Tokenizer evaluation report (fertility, vocabulary coverage, etc.).
- Documented feasibility findings on tiny samples.

**Exit criteria**
- Tokenizer choice documented with evidence (or explicitly left open).
- Feasibility constraints understood and recorded.

**Dependencies / Risks**
- Requires prepared data. Risks: local compute insufficient; drawing
  conclusions from samples that do not represent the target domain.

---

## Phase 4 — Approved initial training or adaptation

**Status:** Blocked on Phase 3 and explicit approval.

**Objectives**
- Run the first approved training or adaptation experiment.

**Deliverables**
- Reproducible experiment record(s) per `docs/EXPERIMENT_LOG.md`.
- Checkpoint(s) and evaluation results.

**Exit criteria**
- Experiment completed within approved budget.
- Results documented with failure analysis.

**Dependencies / Risks**
- Requires approved budget, compute, and configuration.
- Risks: cost overrun, non-reproducible runs, overfitting to a small
  corpus.

---

## Phase 5 — Evaluation and iteration

**Status:** Blocked on Phase 4.

**Objectives**
- Evaluate against the benchmark.
- Conduct error analysis and native-speaker human assessment.
- Iterate.

**Deliverables**
- Evaluation report with measured results.
- Human assessment summaries.
- Documented iteration decisions.

**Exit criteria**
- Results compared against baselines with documented methodology.
- Clear go / no-go decision for instruction tuning.

**Dependencies / Risks**
- Requires trained artifacts and native speakers.
- Risks: small evaluator pools; evaluation contamination.

---

## Phase 6 — Instruction tuning and conversational evaluation

**Status:** Conditional — only if supported by earlier results.

**Objectives**
- Instruction-tune and evaluate conversational ability.

**Deliverables**
- Instruction-tuning experiment records.
- Multi-turn and instruction-following evaluation results.

**Exit criteria**
- Demonstrated improvement over the Phase 5 baseline on the approved
  rubric.

**Dependencies / Risks**
- Depends on favorable Phase 5 results. Risks: instruction data quality,
  register drift, evaluation cost.

---

## Phase 7 — Inference, deployment, monitoring

**Status:** Long-term.

**Objectives**
- Serve the model, monitor quality, and continue development.

**Deliverables**
- Inference tooling and deployment plan.
- Monitoring and evaluation process.

**Exit criteria**
- Defined and approved by the project director.

**Dependencies / Risks**
- Requires a validated model. Risks: hosting cost, privacy, misuse,
  maintenance burden.

---

## Phase 6b — Preference comparison (A/B) feedback

**Status:** Planned (D-025). Not started. Added at the Project Director's request on 2026-11-04, following the early practice of showing people two answers and asking which they prefer.

**Objectives**
- Collect which of two answers native speakers prefer, to improve the model and to choose between model versions.
- Build an audience of Luganda speakers who take part before a chat interface exists.

**How it works**
- Two answers to the same prompt are shown side by side in random order, with no labels. The rater picks "A is better", "B is better", "Both fine" or "Both bad", and may say why.
- The pair can be our model against Sunflower, or two versions of our model, or two samples from the same model.
- Each record keeps the prompt, both answers, which model and version produced each, the choice, and a pseudonymous rater code. No names or contact details.

**Deliverables**
- A comparison page (the local `tools/luganda-compare/` is the starting point).
- A preference record format and storage under `data/`.
- A report of preference counts per category, with the number of pairs.

**Exit criteria**
- Native-group pairs collected and read, with failure patterns written up.
- A decision on whether enough clean pairs exist to try preference tuning (a later step, separate approval).

**Rules**
- Blind, random position, model identity hidden until the choice is saved.
- The native group is the first rater pool. A public audience needs a consent notice on the page, no personal data collected, and owner approval to host it (Gate 8).
- Prompts typed by the public are not used as training data without notice and approval.
- Preference counts are a supplementary signal. Benchmark claims stay governed by spec 11.4 (no overall score, average or percentage without owner approval).

**Dependencies / Risks**
- Needs a first fine-tuned model to compare, and hosting approval for any public use. Risks: small or unrepresentative rater pools, raters preferring longer or more polite answers over correct ones, public data privacy.
