r"""Build, validate, and export the English source pilot draft.

Run from the repository root with:

    $env:PYTHONPATH = "src"
    .\.venv-gemma\Scripts\python.exe scripts\build_source_pilot.py

The generated files are source material only. They do not contain Luganda
translations, native reviews, approvals, or training authorization.
"""

import datetime as _datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import source_pilot_a  # noqa: E402
import source_pilot_b  # noqa: E402
import source_pilot_c  # noqa: E402
import source_pilot_eval  # noqa: E402
from source_pilot_common import OWNER_CONFIRMATION  # noqa: E402
from training.source_pilot import (  # noqa: E402
    SOURCE_PILOT_TOTAL,
    SOURCE_SCHEMA_VERSION,
    SOURCE_STATUS,
    load_source_draft,
    validate_source_dataset,
    validate_source_exports,
    write_source_exports,
)
from training.storage import write_json  # noqa: E402

OUTPUT = ROOT / "data" / "source" / "pilot-v1"
AS_OF = _datetime.date(2026, 10, 21)


def main():
    pilot = source_pilot_a.PILOT + source_pilot_b.PILOT + source_pilot_c.PILOT
    evaluation = source_pilot_eval.EVALUATION
    pilot.sort(key=lambda item: item["item_id"])
    evaluation.sort(key=lambda item: item["item_id"])
    if len(pilot) != SOURCE_PILOT_TOTAL:
        raise SystemExit(
            f"expected {SOURCE_PILOT_TOTAL} pilot examples, found {len(pilot)}"
        )
    if len(evaluation) != 24:
        raise SystemExit(f"expected 24 evaluation items, found {len(evaluation)}")
    data = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "dataset_name": "LugandaGPT English source pilot and feasibility evaluation draft",
        "status": SOURCE_STATUS,
        "created_date": AS_OF.isoformat(),
        "owner_confirmation": OWNER_CONFIRMATION,
        "draft_notes": (
            "Original English source material for team translation and native "
            "review. The 24 evaluation items are separate from the 100 pilot "
            "items and are not an approved benchmark."
        ),
        "pilot": pilot,
        "evaluation": evaluation,
    }
    validate_source_dataset(data, require_complete=True, as_of=AS_OF)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    canonical = OUTPUT / "source_draft.json"
    write_json(canonical, data)
    loaded = load_source_draft(canonical, require_complete=True, as_of=AS_OF)
    manifest = write_source_exports(loaded, OUTPUT)
    exports = validate_source_exports(loaded, OUTPUT)
    print("source_draft=" + str(canonical))
    print("pilot_count=" + str(len(pilot)))
    print("evaluation_count=" + str(len(evaluation)))
    print("capability_counts=" + repr(loaded["summary"]["capability_counts"]))
    print("split_counts=" + repr(loaded["summary"]["pilot_split_counts"]))
    print("multi_sentence=" + str(loaded["summary"]["multi_sentence"]))
    print("uncertainty_cases=" + str(loaded["summary"]["uncertainty_cases"]))
    print("constraint_examples=" + str(loaded["summary"]["constraint_examples"]))
    print(
        "prior_context_conversations="
        + str(loaded["summary"]["prior_context_conversations"])
    )
    print("translator_rows=" + str(exports["translator_rows"]))
    print("manifest=" + str(OUTPUT / "source_manifest.json"))
    return manifest


if __name__ == "__main__":
    main()
