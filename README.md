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

The initial scope is **text-only**. The working direction (D-017) is to
measure Sunbird's Sunflower-14B on the project benchmark and, if the
evidence supports it, train a LoRA or QLoRA adapter on an open-weight base.
The base model, architecture, tokenizer, parameter count, training method,
and compute provider remain **undecided** until the base-selection gate in
[docs/WORKING-PLAN.md](docs/WORKING-PLAN.md).

## Current development status

- Phase 0 (project foundation, documentation, Git hygiene) and early preparation are underway.
- Phase 1 research (`docs/PHASE-1-RESEARCH.md`) and the benchmark specification (approved 1.0, D-007) exist. No benchmark items and no baseline benchmark runs exist.
- No approved Luganda training dataset and no trained model exist. A project-authored English source draft exists for the 100-example pilot; native translation and review are at an early stage (dated snapshot in `docs/WORKING-PLAN.md` section 7).
- Source-validation, benchmark, and Sunbird API tooling is present. No GPU training run has occurred. The Gemma 1B training setup was archived on 2026-11-02 (D-018).
- The Sunbird API connection (`src/sunbird_api/`, [guide](docs/SUNBIRD-API.md)) is built and unit-tested. A 14-request live test on 2026-11-02 succeeded. Sunbird publishes no API price, so spending beyond that test is not approved until the price is known.
- The Python Translation Studio in `src/translation_studio/` is the sole supported implementation for native-speaker translation and review.
- No model has been trained or evaluated.
- The project reporter was archived on 2026-11-02 and is not running.

See the [roadmap](docs/ROADMAP.md) for the staged plan.

## Repository structure

```
LugandaGPT/
├── AGENTS.md            Engineering rules and working arrangement
├── README.md            This file
├── archive/             Archived Gemma 1B, Runpod, and reporter material (restorable)
├── configs/             Experiment and model configurations (none active)
├── checkpoints/         Model checkpoints (ignored by Git; empty)
├── data/                Data governance, English source draft, and no approved training data
├── docs/                Project documentation
├── reports/             Gate, source, and research reports
├── src/                 Benchmark, source-draft, Translation Studio, and Sunbird API code
├── tests/               Python test suite
└── tokenizer/           Tokenizer tooling and pinned checks
```

## Documentation

- [Vision](docs/VISION.md): mission, goals, scope, non-goals
- [Architecture](docs/ARCHITECTURE.md): proposed system boundaries
- [Roadmap](docs/ROADMAP.md): phased plan
- [Working plan](docs/WORKING-PLAN.md): gate sequence from the Sunflower baseline to a demonstration
- [Decisions](docs/DECISIONS.md): architecture decision records
- [Experiment log](docs/EXPERIMENT_LOG.md): experiment record template
- [Evaluation plan](docs/EVALUATION_PLAN.md): benchmark and rubric design
- [Benchmark specification](docs/BENCHMARK-SPECIFICATION.md): approved benchmark specification
- [Pilot data specification](docs/PILOT-DATA-SPECIFICATION.md): Luganda training schema and English source draft
- [English source pilot report](reports/ENGLISH-SOURCE-PILOT-REPORT.md): counts, validation, and outstanding translation work
- [Translation Studio](docs/TRANSLATION-STUDIO.md): local translation and review web application setup
- [Translation Studio report](reports/TRANSLATION-STUDIO-REPORT.md): implementation, test, and limitation report
- [PythonAnywhere deployment guide](deployment/translation-studio/README.md): package contents and manual deployment instructions
- [Sunbird API guide](docs/SUNBIRD-API.md): running Sunflower through Sunbird's API and collecting translation suggestions
- [Archive](archive/2026-11-02-gemma-runpod-reporter/README.md): what was archived on 2026-11-02 and how to restore it
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
