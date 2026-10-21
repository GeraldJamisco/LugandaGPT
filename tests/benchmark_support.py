"""Shared synthetic records for benchmark tests.

Nothing here is a real prompt, review, approval, or evaluation result.
"""

import copy

from benchmark.review import (
    AmbiguityCheck,
    CalibrationSession,
    ItemReview,
    ReferenceReview,
    ResponseReview,
)
from benchmark.runs import CostRecord, RawResponse, RunManifest
from benchmark.versioning import ApprovalRecord, NativeReviewSignoff, SourceException


def base_item(**overrides):
    item = {
        "id": "LGP-BENCH-INSTRUCTION-001",
        "benchmark_version": "0.1-draft",
        "track": "conversational",
        "category": "instruction_following",
        "prompt_language": "en",
        "response_language": "en",
        "prompt": "SYNTHETIC TEST DATA. Reply with the word TEST only.",
        "turns": [],
        "expected_behavior": "The response is exactly TEST.",
        "reference_answer": None,
        "reference_status": "not_applicable",
        "accepted_alternatives": [],
        "scoring_dimensions": [
            "semantic_correctness",
            "grammar_naturalness",
            "instruction_compliance",
            "relevance",
        ],
        "ambiguity_notes": "Synthetic fixture; no ambiguity beyond being test data.",
        "contamination_notes": "Synthetic fixture; never used for evaluation.",
        "review_status": "draft",
        "reviewer_notes": [],
        "source": {
            "type": "original",
            "url": None,
            "licence": None,
            "inspiration": "Synthetic validation fixture.",
        },
        "author": {
            "id": "synthetic-author",
            "role": "benchmark_author",
            "created_at": "2026-10-20",
        },
        "created_at": "2026-10-20",
        "updated_at": "2026-10-20",
    }
    item.update(overrides)
    return copy.deepcopy(item)


def ambiguity_check(item, reviewer_id="reviewer-1", outcome="clear"):
    return AmbiguityCheck(
        check_id=f"SYN-AMB-{item['id']}-{reviewer_id}",
        item_id=item["id"],
        reviewer_id=reviewer_id,
        reviewer_role="native_reviewer",
        date="2026-10-20",
        outcome=outcome,
        notes="Synthetic ambiguity check for tests.",
    )


def calibration_session(reviewer_ids=("reviewer-1", "reviewer-2")):
    return CalibrationSession(
        session_id="SYN-CAL-001",
        date="2026-10-20",
        reviewer_ids=tuple(reviewer_ids),
        calibration_item_ids=("LGP-CAL-001",),
        completed=True,
        notes="Synthetic calibration session for tests.",
    )


def item_review(item, reviewer_id, decision="accept", role="native_reviewer", cultural_ok=False):
    return ItemReview(
        review_id=f"SYN-ITEM-{item['id']}-{reviewer_id}",
        item_id=item["id"],
        reviewer_id=reviewer_id,
        role=role,
        date="2026-10-20",
        decision=decision,
        notes="Synthetic item review for tests.",
        calibration_completed=True,
        cultural_note_ok=cultural_ok,
        reference_ok=True,
    )


def reference_review(item, reviewer_id="reviewer-1"):
    from benchmark.storage import sha256_text

    return ReferenceReview(
        review_id=f"SYN-REF-{item['id']}",
        item_id=item["id"],
        reviewer_id=reviewer_id,
        role="native_reviewer",
        date="2026-10-20",
        approved=True,
        note="Synthetic reference review for tests.",
        reference_sha256=sha256_text(item["reference_answer"]),
    )


def approval_for(items, version="1.0"):
    from benchmark.versioning import hash_items

    item_ids = tuple(item["id"] for item in items)
    return ApprovalRecord(
        specification_version="0.1-draft",
        benchmark_version=version,
        approved_by="Synthetic Project Owner",
        role="project_owner",
        date="2026-10-20",
        scope="Synthetic test approval only.",
        conditions="Test data; not a real approval.",
        item_file_sha256=hash_items(items),
        item_ids=item_ids,
        native_review_signoff=NativeReviewSignoff(
            reviewer_panel=("reviewer-1", "reviewer-2"),
            calibration_date="2026-10-20",
            agreement_statistic="quadratic_weighted_kappa=0.85 (synthetic)",
            items_reviewed=item_ids,
            signoff_date="2026-10-20",
        ),
    )


def evidence_for(item, *, approve=False, items=None, decisions=("accept", "accept"), cultural_ok=False):
    items = items or [item]
    evidence = {
        "ambiguity_checks": [ambiguity_check(item)],
        "item_reviews": [
            item_review(item, "reviewer-1", decisions[0], cultural_ok=cultural_ok),
            item_review(item, "reviewer-2", decisions[1], cultural_ok=cultural_ok),
        ],
        "calibration_sessions": [calibration_session()],
        "reference_reviews": [],
    }
    if approve:
        evidence["approval_record"] = approval_for(items, item["benchmark_version"])
    return evidence


def response_review(
    item,
    *,
    reviewer_id="reviewer-1",
    run_id="LGP-RUN-2026-001",
    dimension="semantic_correctness",
    score=3,
    note="",
    role="native_reviewer",
    failure_codes=(),
    **overrides,
):
    values = {
        "review_id": f"SYN-RESP-{item['id']}-{reviewer_id}-{dimension}",
        "item_id": item["id"],
        "run_id": run_id,
        "reviewer_id": reviewer_id,
        "role": role,
        "date": "2026-10-20",
        "calibration_completed": True,
        "dimension": dimension,
        "score": score if role == "native_reviewer" else None,
        "note": note,
        "flag": "none",
        "failure_codes": tuple(failure_codes),
        "adjudication_required": role == "adjudicator",
        "adjudicated_score": None,
        "adjudicator_id": None,
        "adjudication_note": None,
    }
    values.update(overrides)
    return ResponseReview(**values)


def cost_record(**overrides):
    values = {
        "kind": "local_compute",
        "amount": 0.0,
        "currency": "USD",
        "approved_budget": 0.0,
        "approval_reference": "not required",
        "details": {"hardware": "synthetic CPU", "wall_clock_hours": 0.01},
    }
    values.update(overrides)
    return CostRecord(**values)


def run_manifest(**overrides):
    values = {
        "run_id": "LGP-RUN-2026-001",
        "benchmark_version": "0.1-draft",
        "item_file_sha256": "a" * 64,
        "model_id": "synthetic/model",
        "model_revision": "0123456789abcdef",
        "tokenizer_id": "synthetic/tokenizer",
        "tokenizer_revision": "fedcba9876543210",
        "chat_template": "synthetic-chat-template",
        "quantization": "none",
        "dtype": "float32",
        "device": "cpu",
        "framework_versions": {"python": "3.13", "framework": "synthetic-1.0"},
        "decoding": {
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "max_new_tokens": 64,
            "stop_sequences": [],
            "repetition_penalty": 1.0,
        },
        "samples_per_item": 1,
        "batch_size": 1,
        "hardware": "synthetic CPU",
        "operating_system": "synthetic OS",
        "started_at": "2026-10-20T10:00:00+00:00",
        "finished_at": None,
        "wall_clock_seconds": None,
        "cost": cost_record(),
        "approval_reference": "not required",
        "raw_response_path": "raw_responses.jsonl",
        "operator": "synthetic-operator",
        "expected_item_count": 1,
        "completed_item_count": 0,
    }
    values.update(overrides)
    return RunManifest(**values)


def raw_response(**overrides):
    values = {
        "run_id": "LGP-RUN-2026-001",
        "item_id": "LGP-BENCH-INSTRUCTION-001",
        "turn_index": 0,
        "sample_index": 0,
        "model_id": "synthetic/model",
        "model_revision": "0123456789abcdef",
        "timestamp": "2026-10-20T10:01:00+00:00",
        "raw_response": "TEST",
        "finish_reason": "stop",
        "prompt_tokens": 12,
        "completion_tokens": 1,
        "latency_ms": 12.5,
        "error": None,
    }
    values.update(overrides)
    return RawResponse(**values)


def source_exception(item):
    return SourceException(
        item_id=item["id"],
        approved_by="Synthetic Project Owner",
        role="project_owner",
        date="2026-10-20",
        reason="Synthetic source exception for tests.",
    )
