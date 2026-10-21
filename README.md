# LugandaGPT

An early-stage research project to build a **Luganda-native conversational
language model**.

> **Status: early-stage research. No trained LugandaGPT model currently
> exists.** This repository contains project documentation and, as the
> project develops, tooling for data handling, tokenizer evaluation, and
> evaluation. Nothing here should be read as a claim that a model has been
> built, trained, or evaluated.

## Mission

Build an AI system that understands and generates natural Luganda and can
hold useful, context-aware conversations in the language, in formal and
educated Luganda, everyday and colloquial Luganda, and Luganda-English
code-switching. LugandaGPT is not a translation application, a language
education website, or a wrapper around another provider's chatbot API.

The initial scope is **text-only**. Implementation strategy, base model,
architecture, tokenizer, parameter count, training method, and compute
provider are **undecided** pending research and benchmarking.

## Current development status

- Phase 0 (project foundation, documentation, Git hygiene) and early preparation are underway.
- No approved Luganda training dataset and no trained model exist. A project-authored English source draft exists for the 100-example pilot; native translation and review are pending.
- Guarded training, inference, source-validation, and benchmark tooling is present, but no GPU training run has occurred.
- No model has been trained or evaluated.
- Local tooling now includes the project reporter: read-only activity
  collection, local report generation, and optional Telegram delivery to
  the private group. Scheduled delivery stays disabled until the project
  director enables it (see the [reporter guide](docs/PROJECT_REPORTER_README.md)).

See the [roadmap](docs/ROADMAP.md) for the staged plan.

## Repository structure

```
LugandaGPT/
├── AGENTS.md            Engineering rules and working arrangement
├── README.md            This file
├── configs/             Proposed experiment and model configurations
├── checkpoints/         Model checkpoints (ignored by Git; empty)
├── data/                Data governance, English source draft, and no approved training data
├── docs/                Project documentation
├── reports/             Gate, source, and research reports
├── src/                 Benchmark, training-preparation, and reporter code
├── tests/               Python test suite
└── tokenizer/           Tokenizer tooling and pinned checks
```

## Documentation

- [Vision](docs/VISION.md): mission, goals, scope, non-goals
- [Architecture](docs/ARCHITECTURE.md): proposed system boundaries
- [Roadmap](docs/ROADMAP.md): phased plan
- [Decisions](docs/DECISIONS.md): architecture decision records
- [Experiment log](docs/EXPERIMENT_LOG.md): experiment record template
- [Evaluation plan](docs/EVALUATION_PLAN.md): benchmark and rubric design
- [Benchmark specification](docs/BENCHMARK-SPECIFICATION.md): approved benchmark specification
- [Pilot data specification](docs/PILOT-DATA-SPECIFICATION.md): Luganda training schema and English source draft
- [English source pilot report](reports/ENGLISH-SOURCE-PILOT-REPORT.md): counts, validation, and outstanding translation work
- [Reporter spec](docs/PROJECT_REPORTER_SPEC.md): requirements for automatic reporting and Telegram delivery
- [Reporter guide](docs/PROJECT_REPORTER_README.md): running the reporter, checking delivery, retrying failures, enabling scheduling
- [Data governance](data/README.md): dataset requirements and rules
- [Agents](AGENTS.md): engineering instructions and working arrangement

## Development principles

- Inspect before editing; explain purpose before implementing.
- Prefer small, testable changes.
- Never invent results, scores, or provenance; never claim a model was
  trained or evaluated unless it actually was.
- Separate measured results, assumptions, and proposals.
- Native Luganda speakers are required for language-quality evaluation.
- Python for ML and data tooling, with minimal dependencies.

## Data and model-training restrictions

- Publicly accessible text is **not** automatically licensed for training or
  redistribution. Datasets are governed by [data/README.md](data/README.md).
- No dataset acquisition, scraping, or paid compute without project-director
  approval.
- No large model or dataset downloads without approval.
- No credentials in code, logs, or commits; no private data or model weights
  pushed to GitHub.

The local development machine has roughly 8 GB RAM and limited free disk
space, so local work focuses on code, small samples, tests, and evaluation
tooling.

See [AGENTS.md](AGENTS.md) for the full set of rules and approval gates.
