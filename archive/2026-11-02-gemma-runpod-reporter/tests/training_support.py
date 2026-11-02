"""Synthetic fixtures for training-pipeline tests.

Nothing in this file is Luganda data, a teacher contribution, a consent record,
a native review, or an experiment result. Every string is generated for schema
and plumbing tests in a temporary directory.
"""

import copy
import datetime as _datetime
from pathlib import Path

import yaml

from training.config import load_config
from training.constants import (
    CAPABILITIES,
    CAPABILITY_COUNTS,
    CAPABILITIES_REQUIRING_REFERENCE,
    VALIDATION_CHECKS,
)
from training.storage import sha256_file, write_json, write_jsonl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = PROJECT_ROOT / "configs" / "gemma3-1b-lora-smoke.yaml"
REVIEW_DATE = "2026-10-20"
AS_OF = _datetime.date(2026, 10, 21)


def _review(reviewer_id, role="independent_review", decision="approved"):
    return {
        "reviewer_id": reviewer_id,
        "role": role,
        "date": REVIEW_DATE,
        "decision": decision,
        "notes": "Synthetic review record for tests only.",
    }


def _messages(record_id, capability, prefix="p"):
    unique = record_id.replace("-", "").lower()
    if capability == "short_conversation":
        return [
            {
                "role": "user",
                "content": f"synthetic user one {prefix}{unique}a",
            },
            {
                "role": "assistant",
                "content": f"synthetic assistant one {prefix}{unique}b",
            },
            {
                "role": "user",
                "content": f"synthetic user two {prefix}{unique}c",
            },
            {
                "role": "assistant",
                "content": f"synthetic assistant two {prefix}{unique}d",
            },
        ]
    return [
        {"role": "user", "content": f"synthetic user marker {prefix}{unique}a"},
        {
            "role": "assistant",
            "content": f"synthetic assistant marker {prefix}{unique}b",
        },
    ]


def _expected_response(record_id, capability, prefix="p"):
    unique = record_id.replace("-", "").lower()
    uncertainty = (
        "state_uncertainty_if_unanswerable"
        if capability == "question_answering"
        else "not_applicable"
    )
    return {
        "must_include": [f"{prefix}{unique}b"],
        "must_not_include": ["model refusal"],
        "max_words": 20,
        "format": "short_answer",
        "uncertainty_behavior": uncertainty,
    }


def valid_pilot_record(record_id="P-001", capability="formal_comprehension", split="train"):
    reference_required = capability in CAPABILITIES_REQUIRING_REFERENCE
    record = {
        "pilot_id": record_id,
        "capability": capability,
        "messages": _messages(record_id, capability),
        "language": "lg",
        "register": "formal",
        "expected_response": _expected_response(record_id, capability),
        "reference_answer": (
            f"Synthetic reference answer r{record_id.replace('-', '').lower()}."
            if reference_required
            else None
        ),
        "reference_status": "reviewed" if reference_required else "not_required",
        "accepted_alternatives": [],
        "author_id": "T-001",
        "reviewers": [_review("R-001")],
        "review_status": "approved",
        "source": "teacher_authored",
        "source_notes": "Synthetic test fixture; not real Luganda data.",
        "licence": "LIC-001",
        "consent_ref": "CONSENT-001",
        "pii_check": "none",
        "contamination_notes": (
            "Exact and 8-gram checks run by the synthetic validator on 2026-10-20."
        ),
        "validation": {name: True for name in VALIDATION_CHECKS},
        "split": split,
        "notes": "Synthetic fixture, not language data.",
    }
    if split == "train" and record_id in {f"P-{index:03d}" for index in range(1, 8)}:
        record["reviewers"].append(_review("R-002", role="audit"))
    return record


def valid_evaluation_record(record_id="E-001", capability="formal_comprehension"):
    reference_required = capability in CAPABILITIES_REQUIRING_REFERENCE
    return {
        "eval_id": record_id,
        "capability": capability,
        "messages": _messages(record_id, capability, prefix="e"),
        "language": "lg",
        "register": "formal",
        "expected_response": _expected_response(record_id, capability, prefix="e"),
        "reference_answer": (
            f"Synthetic reference answer r{record_id.replace('-', '').lower()}."
            if reference_required
            else None
        ),
        "reference_status": "reviewed" if reference_required else "not_required",
        "accepted_alternatives": [],
        "author_id": "T-001",
        "reviewers": [_review("R-101"), _review("R-102")],
        "review_status": "approved",
        "source": "teacher_authored",
        "source_notes": "Synthetic test fixture; not real Luganda data.",
        "licence": "LIC-001",
        "consent_ref": "CONSENT-001",
        "pii_check": "none",
        "notes": "Synthetic fixture, not language data.",
    }


def _capability_sequence():
    pools = dict(CAPABILITY_COUNTS)
    sequence = []
    while any(pools.values()):
        for capability in CAPABILITIES:
            if pools[capability] > 0:
                sequence.append(capability)
                pools[capability] -= 1
    return sequence


def make_pilot_splits():
    sequence = _capability_sequence()
    splits = {"train": [], "validation": [], "heldout": []}
    for index, capability in enumerate(sequence, 1):
        if index <= 70:
            split = "train"
        elif index <= 85:
            split = "validation"
        else:
            split = "heldout"
        splits[split].append(
            valid_pilot_record(
                record_id=f"P-{index:03d}",
                capability=capability,
                split=split,
            )
        )
    return splits


def make_evaluation_records():
    records = []
    for index in range(24):
        capability = CAPABILITIES[index % len(CAPABILITIES)]
        records.append(
            valid_evaluation_record(
                record_id=f"E-{index + 1:03d}",
                capability=capability,
            )
        )
    return records


def _provenance(version, hashes, overrides=None):
    value = {
        "dataset_name": "SYNTHETIC TEST FIXTURE, NOT REAL LUGANDA DATA",
        "dataset_version": version,
        "source": "Generated by tests for schema validation",
        "acquisition_method": "Programmatic temporary fixture generation",
        "licence_references": ["LIC-001"],
        "permitted_uses": [
            "training",
            "evaluation",
            "derivatives",
            "research_reporting",
        ],
        "acquisition_date": REVIEW_DATE,
        "data_owner": "Synthetic test fixture",
        "language_varieties": ["Test strings, not Luganda"],
        "domains": ["schema_test"],
        "collection_method": "Generated; no human or web collection",
        "consent": [
            {
                "reference": "CONSENT-001",
                "teacher_id": "T-001",
                "status": "signed",
                "withdrawal_terms": "Synthetic term; not a real agreement.",
                "retention": "Temporary test directory only.",
                "notes": "Synthetic consent record for tests.",
            }
        ],
        "compensation": {
            "status": "agreed",
            "details": "Synthetic status; no compensation exists.",
        },
        "pii_assessment": "No personal data; generated test strings only.",
        "deduplication": "Exact and 8-gram checks in the validator.",
        "limitations": "Schema testing only; not language data.",
        "counts": {
            "train": 70,
            "validation": 15,
            "heldout": 15,
            "evaluation": 24,
        },
        "split_sha256": dict(hashes),
        "approval_reference": "SYNTHETIC-TEST-ONLY",
        "review_process": "Synthetic reviews; not real native review.",
        "retention": "Delete with the temporary test directory.",
        "notes": "Synthetic fixture only.",
    }
    if overrides:
        value.update(copy.deepcopy(overrides))
    return value


def write_synthetic_project(
    root,
    *,
    pilot_splits=None,
    evaluation_records=None,
    version="pilot-v1-synthetic",
    provenance_overrides=None,
    config_mutator=None,
):
    """Write a complete synthetic data and config tree under ``root``."""
    root = Path(root).resolve()
    pilot_splits = copy.deepcopy(pilot_splits) if pilot_splits is not None else make_pilot_splits()
    evaluation_records = (
        copy.deepcopy(evaluation_records)
        if evaluation_records is not None
        else make_evaluation_records()
    )
    paths = {
        "train": root / "data" / "pilot" / "v1" / "train.jsonl",
        "validation": root / "data" / "pilot" / "v1" / "validation.jsonl",
        "heldout": root / "data" / "pilot" / "v1" / "heldout.jsonl",
        "evaluation": root / "data" / "evaluation" / "feasibility-v1.jsonl",
    }
    for split in ("train", "validation", "heldout"):
        write_jsonl(paths[split], pilot_splits[split])
    write_jsonl(paths["evaluation"], evaluation_records)
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    provenance = _provenance(version, hashes, overrides=provenance_overrides)
    provenance_path = root / "data" / "provenance" / "pilot-v1.json"
    write_json(provenance_path, provenance)

    base = load_config(BASE_CONFIG, project_root=PROJECT_ROOT)
    config = copy.deepcopy(base.data)
    config["experiment"]["status"] = "approved"
    config["experiment"]["authorization_status"] = "approved"
    config["experiment"]["execution_authorized"] = True
    config["experiment"]["full_run_authorized"] = False
    config["dataset"]["version"] = version
    config["dataset"]["split_hashes"] = hashes
    config["training"]["output_dir"] = str(root / "runs" / "smoke").replace("\\", "/")
    config["hardware"]["image"] = "synthetic-test-image-digest"
    config["hardware"]["region"] = "synthetic-test-region"
    if config_mutator:
        config_mutator(config)
    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    loaded = load_config(config_path, project_root=root)
    return {
        "root": root,
        "config": loaded,
        "config_path": config_path,
        "paths": paths,
        "provenance_path": provenance_path,
        "hashes": hashes,
        "pilot_splits": pilot_splits,
        "evaluation": evaluation_records,
    }
