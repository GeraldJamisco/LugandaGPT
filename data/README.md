# Data Governance

Rules and record-keeping requirements for any dataset used by LugandaGPT.

> **No datasets are currently present in this repository.** This document
> defines requirements; it does not record an acquisition.

**Publicly accessible text is not automatically permitted for unrestricted
training or redistribution.** Accessibility is not the same as a license
granting those rights. Every dataset must be reviewed and approved before
use.

---

## Required record for every dataset

Each dataset used or considered must have an entry containing:

- **Dataset name and source.**
- **Source URL or documented acquisition method.**
- **License and permitted uses.** Including whether redistribution,
  derivatives, and commercial use are allowed or prohibited.
- **Acquisition date.**
- **Data owner or origin**, where known.
- **Language variety and domain.** (e.g., formal Luganda, colloquial
  Luganda, Luganda-English code-switching; domain such as news, literature,
  conversation.)
- **Collection methodology.** How the data was produced or gathered.
- **Consent requirements**, where applicable (e.g., speaker recordings).
- **Personal-information / privacy assessment.** Whether the data contains
  personal data, and how it is handled.
- **Deduplication methodology.**
- **Quality checks** performed.
- **Dataset version and integrity checks** (e.g., checksums, counts).
- **Known limitations and potential biases.**

---

## Rules

- **No acquisition or scraping** without explicit project-director approval.
- Verify license terms **before** use, not after.
- Datasets with unclear licensing must not be used for training or
  redistribution until clarified.
- Data containing personal information must be assessed for privacy risk;
  prefer de-identified sources or documented consent.
- Keep benchmark/evaluation data **separate** from training data to limit
  contamination.
- Record every dataset's provenance in this file (or a linked record) so
  that experiments in `docs/EXPERIMENT_LOG.md` can reference it.

---

## Committing metadata vs. raw data

- **Raw data files are ignored by default** via `.gitignore` (common data
  formats such as `*.csv`, `*.jsonl`, `*.parquet`, and archives).
- **Dataset metadata** — this README, provenance notes, license text,
  checksums, counts, and small approved samples — **may be committed**.
- **Preferred approach:** use formats that are not ignored at all —
  `.md`, `.json`, `.yaml`, `.yml` — for provenance, license, and index
  records. These commit with no `.gitignore` change.
- **If an approved metadata or benchmark file matches an ignore rule**
  (e.g. a benchmark stored as `.jsonl`), add a narrow, path-specific,
  commented negation to `.gitignore` scoped to that exact approved
  directory, with the approval date. Never add broad negations (such as
  `!data/**`) that could re-include raw datasets.
- Benchmark/evaluation files belong in a **separate, dedicated path**
  (not alongside training data) so contamination checks stay simple.
- Never commit private datasets, model weights, or credentials.
