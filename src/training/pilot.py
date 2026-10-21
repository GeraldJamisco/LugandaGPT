"""Schema and review checks for the proposed 100-example pilot.

Every example is training data, not benchmark data. The validator rejects a
record rather than repairing it. No model-generated text may be presented as
teacher-authored gold data.
"""

import copy
import datetime as _datetime
import math
import re
from typing import Mapping

from .constants import (
    AUDIT_FRACTION,
    CAPABILITIES,
    CAPABILITY_COUNTS,
    CAPABILITIES_REQUIRING_REFERENCE,
    EVALUATION_CAPABILITY_COUNTS,
    EVALUATION_TOTAL,
    LANGUAGES,
    PII_STATUSES,
    PILOT_TOTAL,
    REFERENCE_STATUSES,
    REGISTERS,
    REVIEW_DECISIONS,
    REVIEW_STATUSES,
    REVIEWER_ROLES,
    SOURCE_TYPES,
    SPLITS,
    SPLIT_COUNTS,
    UNCERTAINTY_BEHAVIORS,
    VALIDATION_CHECKS,
)
from .errors import DataError

PILOT_ID_RE = re.compile(r"^P-\d{3}$")
EVALUATION_ID_RE = re.compile(r"^E-\d{3}$")
TEACHER_ID_RE = re.compile(r"^T-\d{3}$")
REVIEWER_ID_RE = re.compile(r"^R-\d{3}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_RE = re.compile(
    r"(?i)(<[A-Za-z][^>\n]{0,80}>|\bTODO\b|\bTBD\b|\bREPLACE_ME\b|\bPLACEHOLDER\b)"
)
UNRESOLVED_MARKERS = ("pending", "tbd", "todo", "unresolved", "needs review")


def _mapping(value, field, record_id=None):
    if not isinstance(value, Mapping):
        raise DataError("must be an object", field, record_id)
    return value


def _keys(value, field, required, optional=(), record_id=None):
    allowed = set(required) | set(optional)
    missing = sorted(set(required) - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise DataError(f"missing required fields: {missing}", field, record_id)
    if unknown:
        raise DataError(f"unknown fields: {unknown}", field, record_id)
    return value


def _string(value, field, record_id=None, allow_empty=False):
    if not isinstance(value, str):
        raise DataError("must be a string", field, record_id)
    if not allow_empty and not value.strip():
        raise DataError("must not be empty", field, record_id)
    return value


def _content(value, field, record_id=None):
    _string(value, field, record_id)
    if PLACEHOLDER_RE.search(value):
        raise DataError("contains a placeholder or template marker", field, record_id)
    return value


def _text_list(value, field, record_id=None, allow_empty=True):
    if not isinstance(value, list):
        raise DataError("must be a list", field, record_id)
    if not allow_empty and not value:
        raise DataError("must not be empty", field, record_id)
    for index, item in enumerate(value):
        _content(item, f"{field}[{index}]", record_id)
    if len(value) != len(set(value)):
        raise DataError("must not contain duplicate values", field, record_id)
    return value


def _bool(value, field, record_id=None):
    if not isinstance(value, bool):
        raise DataError("must be true or false", field, record_id)
    return value


def _integer(value, field, record_id=None, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError("must be an integer", field, record_id)
    if minimum is not None and value < minimum:
        raise DataError(f"must be at least {minimum}", field, record_id)
    if maximum is not None and value > maximum:
        raise DataError(f"must be at most {maximum}", field, record_id)
    return value


def _enum(value, field, choices, record_id=None):
    _string(value, field, record_id)
    if value not in choices:
        raise DataError(f"must be one of {tuple(choices)}", field, record_id)
    return value


def _date(value, field, record_id=None, as_of=None):
    _string(value, field, record_id)
    if not ISO_DATE_RE.match(value):
        raise DataError("must use YYYY-MM-DD", field, record_id)
    try:
        parsed = _datetime.date.fromisoformat(value)
    except ValueError as error:
        raise DataError(f"is not a valid date: {error}", field, record_id) from error
    reference = as_of or _datetime.date.today()
    if parsed > reference:
        raise DataError(f"must not be after {reference.isoformat()}", field, record_id)
    return parsed


def _id(value, field, pattern, label, record_id=None):
    _string(value, field, record_id)
    if not pattern.match(value):
        raise DataError(f"must match {label}", field, record_id)
    return value


def _is_unresolved(value):
    if not isinstance(value, str):
        return True
    lowered = value.strip().casefold()
    return not lowered or any(marker in lowered for marker in UNRESOLVED_MARKERS)


def _reviewer_list(value, record_id, author_id, strict, as_of, evaluation=False):
    if not isinstance(value, list):
        raise DataError("must be a list", "reviewers", record_id)
    if evaluation and len(value) < 2:
        raise DataError("evaluation items need at least two reviewers", "reviewers", record_id)
    if not value:
        raise DataError("must not be empty", "reviewers", record_id)
    independent = []
    audit = []
    seen_ids = set()
    for index, item in enumerate(value):
        field = f"reviewers[{index}]"
        item = _mapping(item, field, record_id)
        _keys(
            item,
            field,
            required=("reviewer_id", "role", "date", "decision", "notes"),
            record_id=record_id,
        )
        reviewer_id = _id(
            item["reviewer_id"], f"{field}.reviewer_id", REVIEWER_ID_RE, "R-NNN", record_id
        )
        if reviewer_id in seen_ids:
            raise DataError("reviewer IDs must be unique", field, record_id)
        seen_ids.add(reviewer_id)
        if reviewer_id == author_id:
            raise DataError("author cannot be the independent reviewer", field, record_id)
        role = _enum(item["role"], f"{field}.role", REVIEWER_ROLES, record_id)
        _date(item["date"], f"{field}.date", record_id, as_of)
        decision = _enum(
            item["decision"], f"{field}.decision", REVIEW_DECISIONS, record_id
        )
        _string(item["notes"], f"{field}.notes", record_id, allow_empty=True)
        if role == "independent_review":
            independent.append(decision)
        elif role == "audit":
            audit.append(decision)
    if strict:
        if "approved" not in independent:
            raise DataError(
                "requires at least one approved independent_review",
                "reviewers",
                record_id,
            )
        if any(decision != "approved" for decision in independent):
            raise DataError(
                "all independent reviews must be approved before training",
                "reviewers",
                record_id,
            )
        if any(decision != "approved" for decision in audit):
            raise DataError("audit reviews must be approved", "reviewers", record_id)
        if evaluation:
            approved = sum(1 for decision in independent if decision == "approved")
            if approved < 2:
                raise DataError(
                    "evaluation items need two approved independent reviews",
                    "reviewers",
                    record_id,
                )
    return value


def _messages(value, record_id, capability):
    if not isinstance(value, list):
        raise DataError("must be a list", "messages", record_id)
    if len(value) < 2 or len(value) % 2 != 0:
        raise DataError(
            "must contain complete user/assistant turns", "messages", record_id
        )
    for index, message in enumerate(value):
        field = f"messages[{index}]"
        message = _mapping(message, field, record_id)
        _keys(message, field, required=("role", "content"), record_id=record_id)
        expected_role = "user" if index % 2 == 0 else "assistant"
        if message["role"] != expected_role:
            raise DataError(
                f"must have role {expected_role!r} at this position",
                f"{field}.role",
                record_id,
            )
        _content(message["content"], f"{field}.content", record_id)
    user_turns = sum(1 for message in value if message["role"] == "user")
    if capability == "short_conversation" and user_turns < 2:
        raise DataError(
            "short conversations need at least two user turns with a follow-up",
            "messages",
            record_id,
        )
    return value


def _expected_response(value, record_id):
    value = _mapping(value, "expected_response", record_id)
    _keys(
        value,
        "expected_response",
        required=(
            "must_include",
            "must_not_include",
            "max_words",
            "format",
            "uncertainty_behavior",
        ),
        record_id=record_id,
    )
    include = _text_list(
        value["must_include"], "expected_response.must_include", record_id
    )
    exclude = _text_list(
        value["must_not_include"], "expected_response.must_not_include", record_id
    )
    if not include and not exclude:
        raise DataError(
            "needs at least one must_include or must_not_include rule",
            "expected_response",
            record_id,
        )
    _integer(value["max_words"], "expected_response.max_words", record_id, 1, 1000)
    _content(value["format"], "expected_response.format", record_id)
    _enum(
        value["uncertainty_behavior"],
        "expected_response.uncertainty_behavior",
        UNCERTAINTY_BEHAVIORS,
        record_id,
    )
    return value


def _validation(value, record_id, strict):
    value = _mapping(value, "validation", record_id)
    _keys(value, "validation", required=VALIDATION_CHECKS, record_id=record_id)
    for field in VALIDATION_CHECKS:
        _bool(value[field], f"validation.{field}", record_id)
    if strict and not all(value[field] is True for field in VALIDATION_CHECKS):
        failed = [field for field in VALIDATION_CHECKS if value[field] is not True]
        raise DataError(
            f"training-ready examples must pass all validation checks; failed: {failed}",
            "validation",
            record_id,
        )
    return value


def _reference(record, record_id, capability, strict):
    status = _enum(
        record["reference_status"], "reference_status", REFERENCE_STATUSES, record_id
    )
    answer = record["reference_answer"]
    alternatives = record["accepted_alternatives"]
    _text_list(alternatives, "accepted_alternatives", record_id)
    if status in ("authored", "reviewed"):
        _content(answer, "reference_answer", record_id)
    elif answer is not None:
        raise DataError(
            "must be null when reference_status is not_required",
            "reference_answer",
            record_id,
        )
    if status == "not_required" and alternatives:
        raise DataError(
            "must be empty when there is no reference answer",
            "accepted_alternatives",
            record_id,
        )
    if strict and capability in CAPABILITIES_REQUIRING_REFERENCE:
        if status != "reviewed":
            raise DataError(
                "determinate tasks need a natively reviewed reference answer",
                "reference_status",
                record_id,
            )
    if strict and status == "authored":
        raise DataError(
            "an authored but unreviewed reference is not training-ready",
            "reference_status",
            record_id,
        )


def _provenance_fields(record, record_id, strict):
    source = _enum(record["source"], "source", SOURCE_TYPES, record_id)
    _content(record["source_notes"], "source_notes", record_id)
    if source == "adapted" and record["source_notes"].strip().casefold() == "original":
        raise DataError(
            "adapted records must describe what was adapted and from where",
            "source_notes",
            record_id,
        )
    _string(record["licence"], "licence", record_id)
    _string(record["consent_ref"], "consent_ref", record_id)
    pii = _enum(record["pii_check"], "pii_check", PII_STATUSES, record_id)
    if strict:
        if _is_unresolved(record["licence"]):
            raise DataError("licence reference is unresolved", "licence", record_id)
        if _is_unresolved(record["consent_ref"]):
            raise DataError("consent reference is unresolved", "consent_ref", record_id)
        if pii != "none" and pii != "redacted":
            raise DataError("PII check must be complete", "pii_check", record_id)


def validate_pilot_record(
    record,
    expected_split=None,
    require_trainable=True,
    as_of=None,
):
    """Validate one pilot record without modifying it.

    ``require_trainable=False`` is for draft review. It still enforces types,
    controlled values, and declared results, but does not require approvals,
    resolved licences, or passing validation flags.
    """
    record = _mapping(record, "record")
    record_id = record.get("pilot_id", "<missing pilot_id>")
    _keys(
        record,
        "record",
        required=(
            "pilot_id",
            "capability",
            "messages",
            "language",
            "register",
            "expected_response",
            "reference_answer",
            "reference_status",
            "accepted_alternatives",
            "author_id",
            "reviewers",
            "review_status",
            "source",
            "source_notes",
            "licence",
            "consent_ref",
            "pii_check",
            "contamination_notes",
            "validation",
            "split",
        ),
        optional=("notes",),
        record_id=record_id,
    )
    _id(record["pilot_id"], "pilot_id", PILOT_ID_RE, "P-NNN", record_id)
    capability = _enum(record["capability"], "capability", CAPABILITIES, record_id)
    _messages(record["messages"], record_id, capability)
    _enum(record["language"], "language", LANGUAGES, record_id)
    _enum(record["register"], "register", REGISTERS, record_id)
    _expected_response(record["expected_response"], record_id)
    author_id = _id(record["author_id"], "author_id", TEACHER_ID_RE, "T-NNN", record_id)
    _reviewer_list(
        record["reviewers"],
        record_id,
        author_id,
        strict=require_trainable,
        as_of=as_of,
    )
    review_status = _enum(
        record["review_status"], "review_status", REVIEW_STATUSES, record_id
    )
    _reference(record, record_id, capability, require_trainable)
    _provenance_fields(record, record_id, require_trainable)
    _string(record["contamination_notes"], "contamination_notes", record_id)
    _validation(record["validation"], record_id, require_trainable)
    split = _enum(record["split"], "split", SPLITS, record_id)
    if expected_split is not None and split != expected_split:
        raise DataError(
            f"record declares split {split!r} but is in the {expected_split!r} file",
            "split",
            record_id,
        )
    if review_status == "excluded":
        raise DataError(
            "excluded records must not appear in a split file", "review_status", record_id
        )
    if "notes" in record:
        _string(record["notes"], "notes", record_id, allow_empty=True)
    if require_trainable:
        if review_status != "approved":
            raise DataError(
                "review_status must be approved before training",
                "review_status",
                record_id,
            )
        if _is_unresolved(record["contamination_notes"]):
            raise DataError(
                "contamination check is unresolved", "contamination_notes", record_id
            )
    return copy.deepcopy(record)


def validate_evaluation_record(record, require_approved=True, as_of=None):
    """Validate one of the 24 proposed evaluation items.

    These are not benchmark items and carry no benchmark version or score.
    """
    record = _mapping(record, "record")
    record_id = record.get("eval_id", "<missing eval_id>")
    _keys(
        record,
        "record",
        required=(
            "eval_id",
            "capability",
            "messages",
            "language",
            "register",
            "expected_response",
            "reference_answer",
            "reference_status",
            "accepted_alternatives",
            "author_id",
            "reviewers",
            "review_status",
            "source",
            "source_notes",
            "licence",
            "consent_ref",
            "pii_check",
        ),
        optional=("notes",),
        record_id=record_id,
    )
    _id(record["eval_id"], "eval_id", EVALUATION_ID_RE, "E-NNN", record_id)
    capability = _enum(record["capability"], "capability", CAPABILITIES, record_id)
    _messages(record["messages"], record_id, capability)
    _enum(record["language"], "language", LANGUAGES, record_id)
    _enum(record["register"], "register", REGISTERS, record_id)
    _expected_response(record["expected_response"], record_id)
    author_id = _id(record["author_id"], "author_id", TEACHER_ID_RE, "T-NNN", record_id)
    _reviewer_list(
        record["reviewers"],
        record_id,
        author_id,
        strict=require_approved,
        as_of=as_of,
        evaluation=True,
    )
    review_status = _enum(
        record["review_status"], "review_status", REVIEW_STATUSES, record_id
    )
    _reference(record, record_id, capability, require_approved)
    _provenance_fields(record, record_id, require_approved)
    if require_approved and review_status != "approved":
        raise DataError(
            "review_status must be approved before use",
            "review_status",
            record_id,
        )
    if "notes" in record:
        _string(record["notes"], "notes", record_id, allow_empty=True)
    return copy.deepcopy(record)


def validate_collection(
    records,
    expected_split=None,
    require_complete=True,
    require_approved=True,
    as_of=None,
):
    """Validate pilot records and their combined composition."""
    validated = []
    ids = set()
    capability_counts = {name: 0 for name in CAPABILITIES}
    for index, record in enumerate(records):
        item = validate_pilot_record(
            record,
            expected_split=expected_split,
            require_trainable=require_approved,
            as_of=as_of,
        )
        pilot_id = item["pilot_id"]
        if pilot_id in ids:
            raise DataError(f"duplicate pilot_id {pilot_id}", "pilot_id", pilot_id)
        ids.add(pilot_id)
        capability_counts[item["capability"]] += 1
        validated.append(item)
    if expected_split is not None and require_complete:
        expected = SPLIT_COUNTS[expected_split]
        if len(validated) != expected:
            raise DataError(
                f"expected {expected} records, found {len(validated)}",
                "split_count",
                expected_split,
            )
    if expected_split is None:
        if require_complete and len(validated) != PILOT_TOTAL:
            raise DataError(
                f"expected {PILOT_TOTAL} records, found {len(validated)}", "pilot_count"
            )
        if require_complete and capability_counts != CAPABILITY_COUNTS:
            raise DataError(
                "capability counts do not match the pilot composition: "
                f"expected {CAPABILITY_COUNTS}, found {capability_counts}",
                "capability",
            )
    return validated, capability_counts, ids


def validate_evaluation_collection(
    records,
    require_complete=True,
    require_approved=True,
    as_of=None,
):
    validated = []
    ids = set()
    capability_counts = {name: 0 for name in CAPABILITIES}
    for record in records:
        item = validate_evaluation_record(
            record, require_approved=require_approved, as_of=as_of
        )
        eval_id = item["eval_id"]
        if eval_id in ids:
            raise DataError(f"duplicate eval_id {eval_id}", "eval_id", eval_id)
        ids.add(eval_id)
        capability_counts[item["capability"]] += 1
        validated.append(item)
    if require_complete:
        if len(validated) != EVALUATION_TOTAL:
            raise DataError(
                f"expected {EVALUATION_TOTAL} evaluation items, found {len(validated)}",
                "evaluation_count",
            )
        if capability_counts != EVALUATION_CAPABILITY_COUNTS:
            raise DataError(
                "evaluation capability counts do not match four per capability: "
                f"expected {EVALUATION_CAPABILITY_COUNTS}, found {capability_counts}",
                "capability",
            )
    return validated, capability_counts, ids


def audit_coverage(records):
    """Count training records with an approved audit record."""
    covered = 0
    for record in records:
        if any(
            review["role"] == "audit" and review["decision"] == "approved"
            for review in record["reviewers"]
        ):
            covered += 1
    return covered


def validate_audit_coverage(train_records, require_complete=True):
    if not train_records:
        raise DataError("training split is empty", "train")
    required = int(math.ceil(len(train_records) * AUDIT_FRACTION))
    covered = audit_coverage(train_records)
    if require_complete and covered < required:
        raise DataError(
            f"only {covered} training records have an approved audit; need at least {required}",
            "reviewers",
        )
    return {"required": required, "covered": covered}


def composition_summary(records):
    capabilities = {name: 0 for name in CAPABILITIES}
    multi_sentence = 0
    uncertainty = 0
    constrained = 0
    multi_turn = 0
    for record in records:
        capabilities[record["capability"]] += 1
        final = record["messages"][-1]["content"]
        if len(re.findall(r"[.!?](?:\s|$)", final)) >= 2:
            multi_sentence += 1
        if record["expected_response"]["uncertainty_behavior"] != "not_applicable":
            uncertainty += 1
        if record["capability"] == "instruction_following":
            constrained += 1
        if record["capability"] == "short_conversation":
            multi_turn += 1
    return {
        "total": len(records),
        "capabilities": capabilities,
        "multi_sentence_responses": multi_sentence,
        "uncertainty_items": uncertainty,
        "instruction_constraint_items": constrained,
        "short_conversations": multi_turn,
    }
