"""Benchmark item schema and validation.

The validator is deliberately strict. It rejects malformed records instead of
guessing a missing value or repairing a controlled field.
"""

import copy
import re
from datetime import date
from typing import Any, Mapping

from .constants import (
    AUTHOR_ROLES,
    CATEGORY_CODES,
    CATEGORY_TO_PREFIX,
    DIMENSION_NAMES,
    ID_PREFIXES,
    ITEM_ALLOWED_FIELDS,
    ITEM_REQUIRED_FIELDS,
    PROMPT_LANGUAGES,
    REFERENCE_STATUSES,
    RESPONSE_LANGUAGES,
    REVIEW_STATUSES,
    REVIEW_TRANSITIONS,
    REVIEWER_NOTE_FIELDS,
    REVIEWER_NOTE_FLAGS,
    SOURCE_TYPES,
    TRACKS,
)
from .errors import ValidationError, WorkflowError

VERSION_RE = re.compile(r"^(?:0\.\d+-draft|[1-9]\d*\.\d+)$")
ITEM_ID_RE = re.compile(
    r"^LGP-BENCH-(?P<prefix>" + "|".join(ID_PREFIXES) + r")-(?P<number>\d{3})$"
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|password|passwd|secret|bearer|access[_-]?token)\b\s*[:=]\s*\S+"
)


def validate_version(value: Any, field="benchmark_version"):
    if not isinstance(value, str) or not VERSION_RE.match(value):
        raise ValidationError(
            "must be a draft version such as 0.1-draft or an approved version such as 1.0 or later",
            field,
        )
    return value


def validate_iso_date(value: Any, field):
    if not isinstance(value, str) or not ISO_DATE_RE.match(value):
        raise ValidationError("must be an ISO date such as 2026-10-20", field)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValidationError(f"is not a valid date: {error}", field) from error
    return value


def validate_item_id(item_id: Any, category: Any):
    if not isinstance(item_id, str):
        raise ValidationError("must be a string", "id")
    match = ITEM_ID_RE.match(item_id)
    if not match:
        raise ValidationError(
            "must match LGP-BENCH-<CATEGORY>-<NNN> with an uppercase category prefix",
            "id",
        )
    if int(match.group("number")) < 1:
        raise ValidationError("category number must start at 001", "id")
    if category not in CATEGORY_TO_PREFIX:
        raise ValidationError(f"unknown category: {category!r}", "category")
    if match.group("prefix") != CATEGORY_TO_PREFIX[category]:
        raise ValidationError(
            f"prefix {match.group('prefix')} does not match category {category}",
            "id",
        )
    return item_id


def _require_string(value, field, allow_empty=False):
    if not isinstance(value, str):
        raise ValidationError("must be a string", field)
    if not allow_empty and not value.strip():
        raise ValidationError("must not be empty", field)
    return value


def _require_bool(value, field):
    if not isinstance(value, bool):
        raise ValidationError("must be a boolean", field)
    return value


def _require_int(value, field, minimum=None, maximum=None, nullable=False):
    if value is None and nullable:
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("must be an integer", field)
    if minimum is not None and value < minimum:
        raise ValidationError(f"must be at least {minimum}", field)
    if maximum is not None and value > maximum:
        raise ValidationError(f"must be at most {maximum}", field)
    return value


def _require_list(value, field):
    if not isinstance(value, list):
        raise ValidationError("must be a list", field)
    return value


def _require_object(value, field):
    if not isinstance(value, Mapping):
        raise ValidationError("must be an object", field)
    return value


def _validate_turns(item):
    turns = _require_list(item["turns"], "turns")
    for index, turn in enumerate(turns):
        field = f"turns[{index}]"
        _require_object(turn, field)
        if set(turn) != {"role", "content"}:
            raise ValidationError("must contain exactly role and content", field)
        if turn["role"] not in ("user", "assistant"):
            raise ValidationError("role must be user or assistant", f"{field}.role")
        _require_string(turn["content"], f"{field}.content")

    if item["category"] == "multi_turn":
        if not turns:
            raise ValidationError("multi_turn items require at least one scripted turn", "turns")
        if not any(turn["role"] == "user" for turn in turns):
            raise ValidationError(
                "multi_turn items require at least one follow-up user turn", "turns"
            )
    elif turns:
        raise ValidationError("single-turn items must have an empty turns list", "turns")


def _validate_reference_fields(item):
    status = item["reference_status"]
    if status not in REFERENCE_STATUSES:
        raise ValidationError(f"must be one of {REFERENCE_STATUSES}", "reference_status")

    reference = item.get("reference_answer")
    if status == "authored":
        if not isinstance(reference, str) or not reference.strip():
            raise ValidationError(
                "a non-empty reference_answer is required when reference_status is authored",
                "reference_answer",
            )
        if not any(
            note.get("dimension") == "reference_answer"
            and note.get("role") == "native_reviewer"
            and note.get("score") is None
            and note.get("note")
            for note in item["reviewer_notes"]
        ):
            raise ValidationError(
                "an authored reference requires a native reviewer reference_answer note",
                "reference_answer",
            )
    elif status in ("pending", "not_applicable"):
        if reference not in (None, ""):
            raise ValidationError(
                "reference_answer must be null unless reference_status is authored",
                "reference_answer",
            )
        if status == "not_applicable" and not item["ambiguity_notes"].strip():
            raise ValidationError(
                "reference_status not_applicable requires ambiguity_notes explaining why",
                "ambiguity_notes",
            )


def _validate_language_rules(item):
    if item["track"] == "translation_probe":
        return
    rules = {
        "formal_luganda": ({"lg"}, {"lg"}),
        "everyday_luganda": ({"lg"}, {"lg"}),
        "colloquial": ({"lg"}, {"lg"}),
        "code_switching": ({"lg-en"}, {"lg-en"}),
        "instruction_following": (
            {"en", "lg"},
            {"lg", "lg-en", "en", "model_choice"},
        ),
        "multi_turn": ({"lg"}, {"lg"}),
        "explanation_reasoning": ({"lg", "lg-en"}, {"lg", "lg-en"}),
        "cultural_interpretation": ({"lg", "lg-en"}, {"lg", "lg-en"}),
        "factuality_uncertainty": ({"lg"}, {"lg"}),
    }
    prompt_allowed, response_allowed = rules[item["category"]]
    if item["prompt_language"] not in prompt_allowed:
        raise ValidationError(
            f"prompt_language for {item['category']} must be one of {sorted(prompt_allowed)}",
            "prompt_language",
        )
    if item["response_language"] not in response_allowed:
        raise ValidationError(
            f"response_language for {item['category']} must be one of {sorted(response_allowed)}",
            "response_language",
        )


def _validate_reviewer_notes(item):
    notes = _require_list(item["reviewer_notes"], "reviewer_notes")
    for index, note in enumerate(notes):
        field = f"reviewer_notes[{index}]"
        _require_object(note, field)
        if set(note) != REVIEWER_NOTE_FIELDS:
            raise ValidationError(
                "must contain exactly reviewer_id, role, date, dimension, score, note, and flag",
                field,
            )
        _require_string(note["reviewer_id"], f"{field}.reviewer_id")
        if note["role"] not in AUTHOR_ROLES:
            raise ValidationError(f"must be one of {AUTHOR_ROLES}", f"{field}.role")
        validate_iso_date(note["date"], f"{field}.date")
        if note["dimension"] not in DIMENSION_NAMES + ("ambiguity", "reference_answer"):
            raise ValidationError(
                "must be a canonical dimension, ambiguity, or reference_answer",
                f"{field}.dimension",
            )
        if note["dimension"] in ("ambiguity", "reference_answer"):
            if note["score"] is not None:
                raise ValidationError(
                    "score must be null for ambiguity and reference_answer notes",
                    f"{field}.score",
                )
        else:
            if note["dimension"] not in item["scoring_dimensions"]:
                raise ValidationError(
                    "dimension is not applicable to this item", f"{field}.dimension"
                )
            _require_int(note["score"], f"{field}.score", 1, 5)
        _require_string(note["note"], f"{field}.note")
        if note["flag"] not in REVIEWER_NOTE_FLAGS:
            raise ValidationError(f"must be one of {REVIEWER_NOTE_FLAGS}", f"{field}.flag")

    for alternative in item.get("accepted_alternatives", []):
        if not any(alternative in note["note"] for note in notes):
            raise ValidationError(
                f"accepted alternative {alternative!r} is not attributed in a reviewer note",
                "accepted_alternatives",
            )


def _validate_source(item, source_exception):
    source = _require_object(item["source"], "source")
    if set(source) != {"type", "url", "licence", "inspiration"}:
        raise ValidationError(
            "must contain exactly type, url, licence, and inspiration", "source"
        )
    if source["type"] not in SOURCE_TYPES:
        raise ValidationError(f"must be one of {SOURCE_TYPES}", "source.type")
    if source["url"] is not None and not isinstance(source["url"], str):
        raise ValidationError("must be a string or null", "source.url")
    if source["licence"] is not None and not isinstance(source["licence"], str):
        raise ValidationError("must be a string or null", "source.licence")
    if source["inspiration"] is not None and not isinstance(source["inspiration"], str):
        raise ValidationError("must be a string or null", "source.inspiration")

    if source["type"] == "original":
        if source["url"] or source["licence"]:
            raise ValidationError(
                "original items must not claim a source URL or licence",
                "source",
            )
        return

    has_url = isinstance(source["url"], str) and source["url"].strip()
    has_licence = isinstance(source["licence"], str) and source["licence"].strip()
    if has_url and has_licence:
        return
    if not _valid_source_exception(item["id"], source_exception):
        raise ValidationError(
            "non-original items require source.url and source.licence, or an owner source exception",
            "source",
        )


def _valid_source_exception(item_id, exception):
    if exception is None:
        return False
    get = exception.get if isinstance(exception, Mapping) else lambda key, default=None: getattr(
        exception, key, default
    )
    return (
        get("item_id") == item_id
        and get("role") == "project_owner"
        and bool(str(get("approved_by") or "").strip())
        and bool(str(get("reason") or "").strip())
    )


def _validate_author(item):
    author = _require_object(item["author"], "author")
    if set(author) != {"id", "role", "created_at"}:
        raise ValidationError("must contain exactly id, role, and created_at", "author")
    _require_string(author["id"], "author.id")
    if author["role"] not in AUTHOR_ROLES:
        raise ValidationError(f"must be one of {AUTHOR_ROLES}", "author.role")
    validate_iso_date(author["created_at"], "author.created_at")


def _validate_dimensions(item):
    dimensions = _require_list(item["scoring_dimensions"], "scoring_dimensions")
    if len(set(dimensions)) != len(dimensions):
        raise ValidationError("must not contain duplicates", "scoring_dimensions")
    for dimension in dimensions:
        if dimension not in DIMENSION_NAMES:
            raise ValidationError(
                f"unknown dimension {dimension!r}; use one of {DIMENSION_NAMES}",
                "scoring_dimensions",
            )

    if item["track"] == "translation_probe":
        return

    category = item["category"]
    required = {"semantic_correctness", "grammar_naturalness", "relevance"}
    if category == "multi_turn":
        required.add("context_retention")
        required.add("instruction_compliance")
    if category in ("instruction_following", "code_switching"):
        required.add("instruction_compliance")
    if category in ("factuality_uncertainty", "explanation_reasoning"):
        required.add("factual_reliability")
    if category in (
        "formal_luganda",
        "everyday_luganda",
        "colloquial",
        "code_switching",
        "cultural_interpretation",
    ):
        required.add("appropriate_register")

    missing = sorted(required - set(dimensions))
    if missing:
        raise ValidationError(
            f"missing required dimensions for {category}: {missing}",
            "scoring_dimensions",
        )
    if "context_retention" in dimensions and category != "multi_turn":
        raise ValidationError(
            "context_retention applies only to multi_turn items",
            "scoring_dimensions",
        )
    if item["track"] == "conversational" and category not in (
        "factuality_uncertainty",
        "explanation_reasoning",
        "cultural_interpretation",
    ):
        if "factual_reliability" in dimensions:
            raise ValidationError(
                "factual_reliability is not applicable to this category",
                "scoring_dimensions",
            )


def _validate_review_status(item, evidence):
    status = item["review_status"]
    if status not in REVIEW_STATUSES:
        raise ValidationError(f"must be one of {REVIEW_STATUSES}", "review_status")
    if status == "draft":
        return
    if status == "approved" and item["benchmark_version"].endswith("-draft"):
        raise ValidationError(
            "approved items require a non-draft benchmark version",
            "benchmark_version",
        )
    if status == "excluded":
        record = evidence.get("exclusion_record") if evidence else None
        if record is None:
            raise ValidationError(
                "excluded items require an exclusion record with a reason",
                "review_status",
            )
        get = record.get if isinstance(record, Mapping) else lambda key, default=None: getattr(
            record, key, default
        )
        if get("item_id") != item["id"]:
            raise ValidationError(
                "exclusion record must identify this item",
                "review_status",
            )
        if get("version") != item["benchmark_version"]:
            raise ValidationError(
                "exclusion record version must match the item version",
                "review_status",
            )
        if not str(get("reason") or "").strip():
            raise ValidationError(
                "exclusion record must include a reason",
                "review_status",
            )
        for field in ("exclusion_id", "actor"):
            if not str(get(field) or "").strip():
                raise ValidationError(
                    f"exclusion record must include {field}",
                    "review_status",
                )
        validate_iso_date(get("date"), "exclusion_record.date")
        return
    if not item["ambiguity_notes"].strip():
        raise ValidationError(
            "items beyond draft must record an ambiguity check", "ambiguity_notes"
        )
    if not item["contamination_notes"].strip():
        raise ValidationError(
            "items beyond draft must record a contamination check",
            "contamination_notes",
        )
    if status == "approved" and item["contamination_notes"].strip().lower() in {
        "not checked",
        "none",
        "unknown",
    }:
        raise ValidationError(
            "approved items cannot use an unchecked contamination note",
            "contamination_notes",
        )
    if status == "approved" and item["reference_status"] == "pending":
        raise ValidationError(
            "an item with a pending reference cannot be approved",
            "reference_status",
        )
    if not evidence:
        raise ValidationError(
            f"review_status {status} requires review evidence", "review_status"
        )
    # Imported here to keep the item schema independent from review storage.
    from .review import validate_item_review_evidence

    validate_item_review_evidence(item, evidence)


def validate_item(
    item: Mapping[str, Any],
    *,
    expected_version: str | None = None,
    existing_ids: set[str] | None = None,
    source_exception: Any = None,
    evidence: Mapping[str, Any] | None = None,
):
    """Validate one item and return an unmodified deep copy.

    ``evidence`` is required for any status above draft. It contains the
    external records that support the claim, for example
    ``{"ambiguity_checks": [...], "item_reviews": [...],
    "reference_reviews": [...], "calibration_sessions": [...],
    "approval_record": ...}``.
    """
    if not isinstance(item, Mapping):
        raise ValidationError("item must be an object")
    item = copy.deepcopy(dict(item))
    unknown = sorted(set(item) - ITEM_ALLOWED_FIELDS)
    if unknown:
        raise ValidationError(f"unknown fields: {unknown}")
    missing = sorted(ITEM_REQUIRED_FIELDS - set(item))
    if missing:
        raise ValidationError(f"missing required fields: {missing}")

    validate_version(item["benchmark_version"])
    if expected_version is not None and item["benchmark_version"] != expected_version:
        raise ValidationError(
            f"item version {item['benchmark_version']} does not match file version {expected_version}",
            "benchmark_version",
        )
    if item["track"] not in TRACKS:
        raise ValidationError(f"must be one of {TRACKS}", "track")
    if item["category"] not in CATEGORY_CODES:
        raise ValidationError(f"must be one of {CATEGORY_CODES}", "category")
    validate_item_id(item["id"], item["category"])
    if existing_ids and item["id"] in existing_ids:
        raise ValidationError("duplicate stable item ID", "id")
    if item["prompt_language"] not in PROMPT_LANGUAGES:
        raise ValidationError(f"must be one of {PROMPT_LANGUAGES}", "prompt_language")
    if item["response_language"] not in RESPONSE_LANGUAGES:
        raise ValidationError(f"must be one of {RESPONSE_LANGUAGES}", "response_language")
    _validate_language_rules(item)
    _require_string(item["prompt"], "prompt")
    if item["prompt"].strip() in {"<prompt text>", "TODO"}:
        raise ValidationError("placeholder prompt text is not a benchmark item", "prompt")
    if SECRET_RE.search(item["prompt"]):
        raise ValidationError("prompt looks like it contains a credential", "prompt")
    _require_string(item["expected_behavior"], "expected_behavior")
    _validate_turns(item)
    _validate_dimensions(item)
    _validate_reviewer_notes(item)
    _validate_reference_fields(item)
    _validate_source(item, source_exception)
    _validate_author(item)
    validate_iso_date(item["created_at"], "created_at")
    validate_iso_date(item["updated_at"], "updated_at")
    if item["updated_at"] < item["created_at"]:
        raise ValidationError("updated_at must not be earlier than created_at", "updated_at")
    _require_string(item["ambiguity_notes"], "ambiguity_notes", allow_empty=True)
    _require_string(item["contamination_notes"], "contamination_notes", allow_empty=True)

    if item["category"] == "cultural_interpretation":
        if not isinstance(item.get("cultural_note"), str) or not item["cultural_note"].strip():
            raise ValidationError(
                "cultural_interpretation items require a non-empty cultural_note",
                "cultural_note",
            )
    elif "cultural_note" in item and not isinstance(item["cultural_note"], str):
        raise ValidationError("must be a string", "cultural_note")

    alternatives = item.get("accepted_alternatives", [])
    _require_list(alternatives, "accepted_alternatives")
    for index, alternative in enumerate(alternatives):
        _require_string(alternative, f"accepted_alternatives[{index}]")

    _validate_review_status(item, evidence)
    return item


def validate_item_set(
    items,
    *,
    expected_version: str | None = None,
    evidence_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    source_exceptions: Mapping[str, Any] | None = None,
):
    """Validate a collection and reject duplicate stable IDs."""
    if not isinstance(items, list):
        raise ValidationError("item file must contain a list of objects")
    if expected_version is not None:
        validate_version(expected_version, "expected_version")
    seen = set()
    validated = []
    for index, item in enumerate(items):
        try:
            record = validate_item(
                item,
                expected_version=expected_version,
                existing_ids=seen,
                source_exception=(source_exceptions or {}).get(item.get("id"))
                if isinstance(item, Mapping)
                else None,
                evidence=(evidence_by_id or {}).get(item.get("id"))
                if isinstance(item, Mapping)
                else None,
            )
        except ValidationError as error:
            raise ValidationError(f"item {index + 1}: {error}") from error
        seen.add(record["id"])
        validated.append(record)
    versions = {item["benchmark_version"] for item in validated}
    if len(versions) > 1:
        raise ValidationError(f"items contain multiple benchmark versions: {sorted(versions)}")
    tracks = {item["track"] for item in validated}
    if len(tracks) > 1:
        raise ValidationError(
            "conversational and translation items must use separate item files"
        )
    return validated


def can_transition(current, target):
    if current not in REVIEW_STATUSES:
        raise ValidationError(f"unknown review status: {current!r}", "review_status")
    return target in REVIEW_TRANSITIONS[current]


def transition_item(item, target, *, date, evidence=None):
    """Return a copy with a supported review status and its evidence.

    The function does not invent review records. A transition above draft
    fails when the required evidence is absent.
    """
    if not isinstance(item, Mapping):
        raise ValidationError("item must be an object")
    current = item.get("review_status")
    if not can_transition(current, target):
        raise WorkflowError(
            f"review status transition {current!r} to {target!r} is not supported"
        )
    updated = copy.deepcopy(dict(item))
    updated["review_status"] = target
    updated["updated_at"] = validate_iso_date(date, "updated_at")
    return validate_item(updated, evidence=evidence)


def category_counts(items):
    counts = {category: 0 for category in CATEGORY_CODES}
    for item in items:
        counts[item["category"]] += 1
    return counts


def validate_category_allocation(items, allocation: Mapping[str, int]):
    """Check a caller-supplied allocation. The approved draft is not final."""
    counts = category_counts(items)
    if dict(counts) != dict(allocation):
        raise ValidationError(
            f"category allocation mismatch: actual {counts}, expected {dict(allocation)}",
            "category",
        )
    return True
