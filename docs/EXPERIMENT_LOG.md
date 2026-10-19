# Experiment Log

A standard record format for every experiment. **No experiment records are
included yet** — none have been run. Do not add a record unless the
experiment actually happened; do not represent an unrun experiment as
completed.

Use the template below for each experiment. Keep one entry per experiment,
appended in chronological order.

---

## Template

```
### EXP-YYYY-NNN — <short title>

- **Experiment ID:** EXP-YYYY-NNN
- **Date:** <date the experiment was run>
- **Research question:** <what we are trying to learn>
- **Hypothesis:** <expected outcome and reasoning>
- **Dataset and version:** <name and version, or "none">
- **Data permissions / provenance:** <license, source, approval reference>
- **Model and tokenizer configuration:** <config or "undecided">
- **Compute environment:** <hardware, provider, or "local">
- **Random seeds:** <seed values, where applicable>
- **Software versions:** <key libraries and versions>
- **Budget and approval status:** <approved budget, approver, or "not required">
- **Procedure:** <steps performed, enough to reproduce>
- **Metrics:** <metrics and how computed>
- **Results:** <measured results only; label any assumption>
- **Failure analysis:** <what went wrong or was inconclusive, and why>
- **Reproducibility instructions:** <commands/configs to repeat this>
- **Decision and next step:** <what we decided as a result>
```

---

## Field notes

- **Results** must contain measured values only. Any interpretation belongs
  in **Decision and next step**, clearly labelled as interpretation.
- **Data permissions / provenance** must reference the dataset's governance
  record in `data/README.md`. An experiment using unapproved data must not
  proceed.
- **Budget and approval status** must be filled in. Paid compute or paid API
  usage requires explicit project-director approval in advance
  (see `AGENTS.md`).
- **Reproducibility instructions** should be sufficient for another engineer
  to repeat the experiment.
