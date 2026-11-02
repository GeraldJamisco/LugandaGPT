# Archive: Gemma 1B training setup, Runpod gate, project reporter

Moved here on 2026-11-02 when the project direction changed to Sunflower (D-017,
D-018). Nothing was deleted. To restore a file, move it back to the same path
relative to the repository root.

| Archived | Original location |
|---|---|
| Project reporter code | `src/reporter/` |
| Gemma 1B training, inference, config, data, environment, artifact modules and the full training CLI | `src/training/` (only the listed files) |
| Tests for the above, plus `training_support.py` (full copy) | `tests/` |
| Gemma 1B LoRA smoke-test config | `configs/gemma3-1b-lora-smoke.yaml` |
| Runpod pod checklist and first-gate report, fine-tuning feasibility report | `docs/POD-SETUP.md`, `reports/` |
| Reporter spec, guide, and generated reports | `docs/`, `reports/reporter/` |
| Training requirements | `requirements-training.txt` |

## What stayed and why

The Translation Studio imports `training.constants`, `training.errors`,
`training.storage`, `training.pilot`, and `training.source_pilot`, so those stay
in `src/training/`. A slim `src/training/cli.py` keeps only `validate-source`,
`export-source`, and `hash`; the full CLI is archived here.

Decision records D-008 to D-016 are not archived. History stays in
`docs/DECISIONS.md`. The experiment records in `reports/experiments/` also stay.
