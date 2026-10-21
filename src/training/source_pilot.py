"""Validation and translator export for the English source pilot draft.

This module is deliberately separate from the training-data validator. The
English source draft is not a Luganda training dataset, has no native reviews,
and must not pass the training authorization gate.
"""

import copy
import csv
import datetime as _datetime
import io
import json
import re
from pathlib import Path
from typing import Mapping

from .errors import DataError
from .storage import (
    atomic_write_text,
    read_json,
    read_jsonl,
    sha256_file,
    write_json,
    write_jsonl,
)

SOURCE_SCHEMA_VERSION = "english-source-v1-draft"
SOURCE_STATUS = "draft_pending_translation_and_native_review"
SOURCE_PILOT_TOTAL = 100
SOURCE_EVALUATION_TOTAL = 24
SOURCE_CAPABILITIES = (
    "formal_comprehension",
    "formal_generation",
    "rewriting_formal_luganda",
    "question_answering",
    "instruction_following",
    "short_conversation",
)
SOURCE_CAPABILITY_COUNTS = {
    "formal_comprehension": 17,
    "formal_generation": 17,
    "rewriting_formal_luganda": 17,
    "question_answering": 17,
    "instruction_following": 16,
    "short_conversation": 16,
}
SOURCE_EVALUATION_CAPABILITY_COUNTS = {name: 4 for name in SOURCE_CAPABILITIES}
SOURCE_SPLITS = ("train", "validation", "heldout")
SOURCE_SPLIT_COUNTS = {"train": 70, "validation": 15, "heldout": 15}
SOURCE_REGISTERS = ("formal", "everyday", "mixed")
SOURCE_RESPONSE_LENGTHS = ("single_sentence", "multi_sentence")
SOURCE_REFERENCE_KINDS = ("english_reference", "rubric")
SOURCE_UNCERTAINTY_BEHAVIORS = (
    "not_applicable",
    "state_uncertainty_if_unanswerable",
    "ask_clarifying_question_if_ambiguous",
)
SOURCE_TRANSLATION_STATUSES = (
    "pending",
    "in_progress",
    "submitted",
    "reviewed",
    "approved",
    "excluded",
)
SOURCE_REVIEW_STATUSES = (
    "pending",
    "in_review",
    "reviewed",
    "approved",
    "excluded",
)
SOURCE_COLLECTIONS = ("pilot", "evaluation")
SOURCE_PROVENANCE_FIELDS = (
    "origin",
    "third_party_source",
    "created_date",
    "author_role",
    "rights_note",
    "approval_reference",
)
SOURCE_ITEM_FIELDS = (
    "item_id",
    "collection",
    "primary_capability",
    "secondary_capabilities",
    "source_language",
    "source_prompt",
    "source_context",
    "expected_response_criteria",
    "reference_answer_or_rubric",
    "required_constraints",
    "uncertainty_behavior",
    "conversation_turns",
    "intended_register",
    "proposed_split",
    "translation_status",
    "native_review_status",
    "source_provenance",
    "response_length",
    "requires_prior_context",
    "notes",
)
SOURCE_MANIFEST_FIELDS = (
    "dataset_name",
    "schema_version",
    "status",
    "created_date",
    "owner_confirmation",
    "pilot_count",
    "evaluation_count",
    "capability_counts",
    "evaluation_capability_counts",
    "pilot_split_counts",
    "composition",
    "files",
    "sha256",
    "canonical_sha256",
    "translation_status_counts",
    "native_review_status_counts",
    "training_authorized",
    "training_blocker",
    "near_duplicate_check",
    "notes",
)
PILOT_ITEM_RE = re.compile(r"^P-\d{3}$")
EVALUATION_ITEM_RE = re.compile(r"^E-\d{3}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_RE = re.compile(
    r"(?i)(<[A-Za-z][^>\n]{0,80}>|\bTODO\b|\bTBD\b|\bREPLACE_ME\b|\bPLACEHOLDER\b)"
)
WORD_RE = re.compile(r"[a-z0-9']+")

TRANSLATOR_COLUMNS = (
    "item_id",
    "collection",
    "primary_capability",
    "secondary_capabilities",
    "proposed_split",
    "intended_register",
    "source_language",
    "source_context_en",
    "source_context_lg",
    "prior_turns_en",
    "source_prompt_en",
    "expected_response_criteria_en",
    "reference_answer_or_rubric_en",
    "reference_kind",
    "required_constraints_en",
    "uncertainty_behavior",
    "response_length",
    "requires_prior_context",
    "notes",
    "source_provenance",
    "translation_status",
    "prior_turns_lg",
    "source_prompt_lg",
    "final_assistant_response_lg",
    "translator_id",
    "translation_date",
    "translation_notes",
    "native_review_status",
    "reviewer_id",
    "review_date",
    "review_decision",
    "review_notes",
)
TRANSLATOR_LG_FIELDS = (
    "source_context_lg",
    "prior_turns_lg",
    "source_prompt_lg",
    "final_assistant_response_lg",
)


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


def _source_provenance(value, record_id, as_of):
    value = _mapping(value, "source_provenance", record_id)
    _keys(
        value,
        "source_provenance",
        required=SOURCE_PROVENANCE_FIELDS,
        record_id=record_id,
    )
    origin = _enum(
        value["origin"], "source_provenance.origin", ("project_original",), record_id
    )
    third_party = _bool(
        value["third_party_source"],
        "source_provenance.third_party_source",
        record_id,
    )
    if third_party is not False:
        raise DataError(
            "the English source draft must be project-authored, not third-party material",
            "source_provenance.third_party_source",
            record_id,
        )
    _date(
        value["created_date"],
        "source_provenance.created_date",
        record_id,
        as_of=as_of,
    )
    _content(value["author_role"], "source_provenance.author_role", record_id)
    _content(value["rights_note"], "source_provenance.rights_note", record_id)
    if value["approval_reference"] is not None:
        raise DataError(
            "no approval reference is recorded for the English source draft",
            "source_provenance.approval_reference",
            record_id,
        )
    return value


def _conversation_turns(value, record_id, capability):
    if not isinstance(value, list):
        raise DataError("must be a list", "conversation_turns", record_id)
    if capability != "short_conversation":
        if value:
            raise DataError(
                "must be empty outside short conversations",
                "conversation_turns",
                record_id,
            )
        return value
    if len(value) < 2:
        raise DataError(
            "short conversations need prior user and assistant turns",
            "conversation_turns",
            record_id,
        )
    if len(value) % 2 != 0:
        raise DataError(
            "prior turns must end with an assistant turn",
            "conversation_turns",
            record_id,
        )
    for index, turn in enumerate(value):
        field = f"conversation_turns[{index}]"
        turn = _mapping(turn, field, record_id)
        _keys(turn, field, required=("role", "content"), record_id=record_id)
        expected = "user" if index % 2 == 0 else "assistant"
        if turn["role"] != expected:
            raise DataError(
                f"must have role {expected!r} at this position",
                f"{field}.role",
                record_id,
            )
        _content(turn["content"], f"{field}.content", record_id)
    return value


def _reference(value, record_id, capability):
    value = _mapping(value, "reference_answer_or_rubric", record_id)
    _keys(
        value,
        "reference_answer_or_rubric",
        required=("kind", "content"),
        record_id=record_id,
    )
    kind = _enum(
        value["kind"],
        "reference_answer_or_rubric.kind",
        SOURCE_REFERENCE_KINDS,
        record_id,
    )
    _content(value["content"], "reference_answer_or_rubric.content", record_id)
    if capability in (
        "formal_comprehension",
        "rewriting_formal_luganda",
        "question_answering",
        "instruction_following",
    ) and kind != "english_reference":
        raise DataError(
            "determinate source tasks need an English reference answer",
            "reference_answer_or_rubric.kind",
            record_id,
        )
    return value


def validate_source_record(record, collection, as_of=None):
    """Validate one English source draft record without modifying it."""
    record = _mapping(record, "record")
    item_id = record.get("item_id", "<missing item_id>")
    _keys(
        record,
        "record",
        required=SOURCE_ITEM_FIELDS,
        record_id=item_id,
    )
    _string(record["item_id"], "item_id", item_id)
    expected_collection = _enum(
        record["collection"], "collection", SOURCE_COLLECTIONS, item_id
    )
    if expected_collection != collection:
        raise DataError(
            f"record is in the {collection!r} collection but declares {expected_collection!r}",
            "collection",
            item_id,
        )
    pattern = PILOT_ITEM_RE if collection == "pilot" else EVALUATION_ITEM_RE
    label = "P-NNN" if collection == "pilot" else "E-NNN"
    if not pattern.match(record["item_id"]):
        raise DataError(f"must match {label}", "item_id", item_id)
    capability = _enum(
        record["primary_capability"],
        "primary_capability",
        SOURCE_CAPABILITIES,
        item_id,
    )
    secondary = _text_list(
        record["secondary_capabilities"], "secondary_capabilities", item_id
    )
    for index, name in enumerate(secondary):
        _enum(name, f"secondary_capabilities[{index}]", SOURCE_CAPABILITIES, item_id)
    if capability in secondary:
        raise DataError(
            "must not repeat the primary capability",
            "secondary_capabilities",
            item_id,
        )
    if record["source_language"] != "en":
        raise DataError("must be 'en'", "source_language", item_id)
    _content(record["source_prompt"], "source_prompt", item_id)
    context = record["source_context"]
    if context is not None:
        _content(context, "source_context", item_id)
    if capability in ("formal_comprehension", "rewriting_formal_luganda") and context is None:
        raise DataError(
            "needs source_context for this capability",
            "source_context",
            item_id,
        )
    criteria = _text_list(
        record["expected_response_criteria"],
        "expected_response_criteria",
        item_id,
        allow_empty=False,
    )
    _reference(record["reference_answer_or_rubric"], item_id, capability)
    _text_list(record["required_constraints"], "required_constraints", item_id)
    _enum(
        record["uncertainty_behavior"],
        "uncertainty_behavior",
        SOURCE_UNCERTAINTY_BEHAVIORS,
        item_id,
    )
    _conversation_turns(record["conversation_turns"], item_id, capability)
    _enum(record["intended_register"], "intended_register", SOURCE_REGISTERS, item_id)
    split = record["proposed_split"]
    if collection == "pilot":
        _enum(split, "proposed_split", SOURCE_SPLITS, item_id)
    elif split is not None:
        raise DataError(
            "evaluation items must not have a training split",
            "proposed_split",
            item_id,
        )
    _enum(
        record["translation_status"],
        "translation_status",
        SOURCE_TRANSLATION_STATUSES,
        item_id,
    )
    _enum(
        record["native_review_status"],
        "native_review_status",
        SOURCE_REVIEW_STATUSES,
        item_id,
    )
    _source_provenance(record["source_provenance"], item_id, as_of)
    _enum(
        record["response_length"],
        "response_length",
        SOURCE_RESPONSE_LENGTHS,
        item_id,
    )
    _bool(record["requires_prior_context"], "requires_prior_context", item_id)
    if capability == "short_conversation":
        if record["requires_prior_context"] is not True:
            raise DataError(
                "short conversations must require prior context",
                "requires_prior_context",
                item_id,
            )
    elif record["requires_prior_context"] is not False:
        raise DataError(
            "only short conversations may require prior context",
            "requires_prior_context",
            item_id,
        )
    _content(record["notes"], "notes", item_id)
    if record["translation_status"] != "pending":
        raise DataError(
            "the source draft has no completed translation; status must be pending",
            "translation_status",
            item_id,
        )
    if record["native_review_status"] != "pending":
        raise DataError(
            "the source draft has no native review; status must be pending",
            "native_review_status",
            item_id,
        )
    return copy.deepcopy(record)


def _normalized_text(text):
    return " ".join(WORD_RE.findall(text.casefold()))


def _record_texts(record):
    texts = [("source_prompt", record["source_prompt"])]
    if record["source_context"]:
        texts.append(("source_context", record["source_context"]))
    for index, turn in enumerate(record["conversation_turns"]):
        texts.append((f"conversation_turns[{index}]", turn["content"]))
    texts.append(
        ("reference_answer_or_rubric", record["reference_answer_or_rubric"]["content"])
    )
    return texts


def _check_duplicates(records):
    exact = {}
    ngrams = {}
    for record in records:
        item_id = record["item_id"]
        for field, text in _record_texts(record):
            normalized = _normalized_text(text)
            if not normalized:
                continue
            if normalized in exact and exact[normalized][0] != item_id:
                previous = exact[normalized]
                raise DataError(
                    f"exact duplicate text with {previous[0]} ({previous[1]})",
                    field,
                    item_id,
                )
            exact[normalized] = (item_id, field)
            words = normalized.split()
            for index in range(len(words) - 7):
                ngram = " ".join(words[index : index + 8])
                previous = ngrams.get(ngram)
                if previous and previous[0] != item_id:
                    raise DataError(
                        f"8-word overlap with {previous[0]} ({previous[1]})",
                        field,
                        item_id,
                    )
                ngrams[ngram] = (item_id, field)


def _check_composition(records, summary):
    multi_sentence = sum(
        1 for record in records if record["response_length"] == "multi_sentence"
    )
    uncertainty = sum(
        1
        for record in records
        if record["uncertainty_behavior"] != "not_applicable"
    )
    constraints = sum(1 for record in records if record["required_constraints"])
    prior_context = sum(
        1 for record in records if record["requires_prior_context"] is True
    )
    conversations = [
        record
        for record in records
        if record["primary_capability"] == "short_conversation"
    ]
    if multi_sentence < 30:
        raise DataError(
            f"at least 30 examples must require a multi-sentence response; found {multi_sentence}",
            "composition.multi_sentence",
        )
    if uncertainty < 12:
        raise DataError(
            f"at least 12 examples must test uncertainty; found {uncertainty}",
            "composition.uncertainty",
        )
    if constraints < 10:
        raise DataError(
            f"at least 10 examples must contain explicit constraints; found {constraints}",
            "composition.required_constraints",
        )
    if prior_context < 8:
        raise DataError(
            f"at least 8 conversations must require prior context; found {prior_context}",
            "composition.prior_context",
        )
    if conversations and prior_context != len(conversations):
        raise DataError(
            "every short conversation must require prior context",
            "composition.prior_context",
        )
    summary.update(
        {
            "multi_sentence": multi_sentence,
            "uncertainty_cases": uncertainty,
            "constraint_examples": constraints,
            "prior_context_conversations": prior_context,
        }
    )


def validate_source_collection(
    records,
    collection,
    require_complete=True,
    as_of=None,
):
    """Validate one collection and its exact composition."""
    if not isinstance(records, list):
        raise DataError("must be a list", collection)
    validated = []
    ids = set()
    capability_counts = {name: 0 for name in SOURCE_CAPABILITIES}
    split_counts = {name: 0 for name in SOURCE_SPLITS}
    for index, record in enumerate(records):
        item = validate_source_record(record, collection, as_of=as_of)
        item_id = item["item_id"]
        if item_id in ids:
            raise DataError(f"duplicate item_id {item_id}", "item_id", item_id)
        ids.add(item_id)
        capability_counts[item["primary_capability"]] += 1
        if collection == "pilot":
            split_counts[item["proposed_split"]] += 1
        validated.append(item)
    if require_complete:
        expected_total = (
            SOURCE_PILOT_TOTAL
            if collection == "pilot"
            else SOURCE_EVALUATION_TOTAL
        )
        if len(validated) != expected_total:
            raise DataError(
                f"expected {expected_total} records, found {len(validated)}",
                f"{collection}_count",
            )
        expected_capabilities = (
            SOURCE_CAPABILITY_COUNTS
            if collection == "pilot"
            else SOURCE_EVALUATION_CAPABILITY_COUNTS
        )
        if capability_counts != expected_capabilities:
            raise DataError(
                "capability counts do not match the draft composition: "
                f"expected {expected_capabilities}, found {capability_counts}",
                "primary_capability",
            )
        if collection == "pilot" and split_counts != SOURCE_SPLIT_COUNTS:
            raise DataError(
                "split counts do not match 70/15/15: "
                f"expected {SOURCE_SPLIT_COUNTS}, found {split_counts}",
                "proposed_split",
            )
    return validated, capability_counts, split_counts, ids


def _validate_owner_confirmation(value, as_of):
    value = _mapping(value, "owner_confirmation")
    _keys(
        value,
        "owner_confirmation",
        required=("reported_by", "report_date", "statement", "formal_agreements"),
    )
    _content(value["reported_by"], "owner_confirmation.reported_by")
    _date(
        value["report_date"],
        "owner_confirmation.report_date",
        as_of=as_of,
    )
    _content(value["statement"], "owner_confirmation.statement")
    _content(
        value["formal_agreements"],
        "owner_confirmation.formal_agreements",
    )
    lowered = value["formal_agreements"].casefold()
    if "signed" in lowered and "not" not in lowered:
        raise DataError(
            "do not claim signed agreements that are not documented",
            "owner_confirmation.formal_agreements",
        )
    return value


def validate_source_dataset(data, require_complete=True, as_of=None):
    """Validate the canonical English source draft object."""
    data = _mapping(data, "source_draft")
    _keys(
        data,
        "source_draft",
        required=(
            "schema_version",
            "dataset_name",
            "status",
            "created_date",
            "owner_confirmation",
            "pilot",
            "evaluation",
        ),
        optional=("draft_notes",),
    )
    if data["schema_version"] != SOURCE_SCHEMA_VERSION:
        raise DataError(
            f"must be {SOURCE_SCHEMA_VERSION!r}",
            "schema_version",
        )
    _content(data["dataset_name"], "dataset_name")
    if data["status"] != SOURCE_STATUS:
        raise DataError(
            f"must be {SOURCE_STATUS!r}",
            "status",
        )
    _date(data["created_date"], "created_date", as_of=as_of)
    _validate_owner_confirmation(data["owner_confirmation"], as_of)
    if "draft_notes" in data:
        _content(data["draft_notes"], "draft_notes")
    pilot, pilot_counts, split_counts, pilot_ids = validate_source_collection(
        data["pilot"],
        "pilot",
        require_complete=require_complete,
        as_of=as_of,
    )
    evaluation, evaluation_counts, _, evaluation_ids = validate_source_collection(
        data["evaluation"],
        "evaluation",
        require_complete=require_complete,
        as_of=as_of,
    )
    overlap = pilot_ids & evaluation_ids
    if overlap:
        raise DataError(
            f"pilot and evaluation IDs overlap: {sorted(overlap)}",
            "item_id",
        )
    _check_duplicates(pilot + evaluation)
    summary = {
        "dataset_name": data["dataset_name"],
        "schema_version": data["schema_version"],
        "status": data["status"],
        "pilot_count": len(pilot),
        "evaluation_count": len(evaluation),
        "capability_counts": pilot_counts,
        "pilot_split_counts": split_counts,
        "evaluation_capability_counts": evaluation_counts,
        "translation_status_counts": {"pending": len(pilot) + len(evaluation)},
        "native_review_status_counts": {"pending": len(pilot) + len(evaluation)},
        "training_authorized": False,
        "training_blocker": (
            "No Luganda translations, native reviews, formal provenance, or "
            "training authorization exist."
        ),
        "near_duplicate_check": "exact normalized text and 8-word overlap",
    }
    _check_composition(pilot, summary)
    return {
        "data": copy.deepcopy(data),
        "pilot": pilot,
        "evaluation": evaluation,
        "summary": summary,
    }


def load_source_draft(path, require_complete=True, as_of=None):
    """Read and validate the canonical English source draft JSON file."""
    path = Path(path)
    data = read_json(path)
    result = validate_source_dataset(
        data,
        require_complete=require_complete,
        as_of=as_of,
    )
    result["path"] = path.resolve()
    result["sha256"] = sha256_file(path)
    return result


def translator_rows(pilot, evaluation):
    rows = []
    for record in sorted(pilot + evaluation, key=lambda item: item["item_id"]):
        reference = record["reference_answer_or_rubric"]
        split = record["proposed_split"] or "evaluation_only"
        rows.append(
            {
                "item_id": record["item_id"],
                "collection": record["collection"],
                "primary_capability": record["primary_capability"],
                "secondary_capabilities": "; ".join(
                    record["secondary_capabilities"]
                ),
                "proposed_split": split,
                "intended_register": record["intended_register"],
                "source_language": record["source_language"],
                "source_context_en": record["source_context"] or "",
                "source_context_lg": "",
                "prior_turns_en": json.dumps(
                    record["conversation_turns"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
                if record["conversation_turns"]
                else "",
                "source_prompt_en": record["source_prompt"],
                "expected_response_criteria_en": json.dumps(
                    record["expected_response_criteria"],
                    ensure_ascii=False,
                ),
                "reference_answer_or_rubric_en": reference["content"],
                "reference_kind": reference["kind"],
                "required_constraints_en": json.dumps(
                    record["required_constraints"],
                    ensure_ascii=False,
                )
                if record["required_constraints"]
                else "",
                "uncertainty_behavior": record["uncertainty_behavior"],
                "response_length": record["response_length"],
                "requires_prior_context": "true"
                if record["requires_prior_context"]
                else "false",
                "notes": record["notes"],
                "source_provenance": json.dumps(
                    record["source_provenance"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "translation_status": record["translation_status"],
                "prior_turns_lg": "",
                "source_prompt_lg": "",
                "final_assistant_response_lg": "",
                "translator_id": "",
                "translation_date": "",
                "translation_notes": "",
                "native_review_status": record["native_review_status"],
                "reviewer_id": "",
                "review_date": "",
                "review_decision": "",
                "review_notes": "",
            }
        )
    return rows


def write_source_exports(loaded, output_dir):
    """Write JSONL, translator CSV, and a checksum manifest from a loaded draft."""
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    pilot_path = output / "pilot_en.jsonl"
    evaluation_path = output / "evaluation_en.jsonl"
    csv_path = output / "translator_export.csv"
    write_jsonl(pilot_path, sorted(loaded["pilot"], key=lambda item: item["item_id"]))
    write_jsonl(
        evaluation_path,
        sorted(loaded["evaluation"], key=lambda item: item["item_id"]),
    )
    rows = translator_rows(loaded["pilot"], loaded["evaluation"])
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=TRANSLATOR_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(csv_path, buffer.getvalue())
    manifest = {
        "dataset_name": loaded["summary"]["dataset_name"],
        "schema_version": loaded["summary"]["schema_version"],
        "status": loaded["summary"]["status"],
        "created_date": loaded["data"]["created_date"],
        "owner_confirmation": loaded["data"]["owner_confirmation"],
        "pilot_count": loaded["summary"]["pilot_count"],
        "evaluation_count": loaded["summary"]["evaluation_count"],
        "capability_counts": loaded["summary"]["capability_counts"],
        "evaluation_capability_counts": loaded["summary"][
            "evaluation_capability_counts"
        ],
        "pilot_split_counts": loaded["summary"]["pilot_split_counts"],
        "composition": {
            key: loaded["summary"][key]
            for key in (
                "multi_sentence",
                "uncertainty_cases",
                "constraint_examples",
                "prior_context_conversations",
            )
        },
        "files": {
            "pilot": "pilot_en.jsonl",
            "evaluation": "evaluation_en.jsonl",
            "translator_export": "translator_export.csv",
        },
        "sha256": {
            "pilot": sha256_file(pilot_path),
            "evaluation": sha256_file(evaluation_path),
            "translator_export": sha256_file(csv_path),
        },
        "canonical_sha256": loaded["sha256"],
        "translation_status_counts": loaded["summary"][
            "translation_status_counts"
        ],
        "native_review_status_counts": loaded["summary"][
            "native_review_status_counts"
        ],
        "training_authorized": False,
        "training_blocker": loaded["summary"]["training_blocker"],
        "near_duplicate_check": loaded["summary"]["near_duplicate_check"],
        "notes": (
            "Derived from the canonical source_draft.json. The English source "
            "is not a Luganda training dataset. All translation and native "
            "review fields remain pending."
        ),
    }
    write_json(output / "source_manifest.json", manifest)
    return manifest


def validate_source_exports(loaded, output_dir):
    """Check that generated JSONL, CSV, and manifest match the canonical draft."""
    output = Path(output_dir).resolve()
    pilot = read_jsonl(output / "pilot_en.jsonl")
    evaluation = read_jsonl(output / "evaluation_en.jsonl")
    if len(pilot) != SOURCE_PILOT_TOTAL:
        raise DataError(f"expected 100 exported pilot rows, found {len(pilot)}")
    if len(evaluation) != SOURCE_EVALUATION_TOTAL:
        raise DataError(
            f"expected 24 exported evaluation rows, found {len(evaluation)}"
        )
    if [item["item_id"] for item in pilot] != [
        item["item_id"] for item in sorted(loaded["pilot"], key=lambda x: x["item_id"])
    ]:
        raise DataError("pilot JSONL IDs do not match the canonical draft")
    if [item["item_id"] for item in evaluation] != [
        item["item_id"]
        for item in sorted(loaded["evaluation"], key=lambda x: x["item_id"])
    ]:
        raise DataError("evaluation JSONL IDs do not match the canonical draft")
    with (output / "translator_export.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != TRANSLATOR_COLUMNS:
            raise DataError("translator CSV header does not match the template")
        rows = list(reader)
    if len(rows) != SOURCE_PILOT_TOTAL + SOURCE_EVALUATION_TOTAL:
        raise DataError(
            f"expected 124 translator rows, found {len(rows)}"
        )
    expected_ids = sorted(
        [item["item_id"] for item in loaded["pilot"]]
        + [item["item_id"] for item in loaded["evaluation"]]
    )
    if [row["item_id"] for row in rows] != expected_ids:
        raise DataError("translator CSV IDs do not match the canonical draft")
    for row in rows:
        for field in TRANSLATOR_LG_FIELDS:
            if row[field].strip():
                raise DataError(
                    f"{row['item_id']}: {field} must remain empty in the source draft",
                    field,
                    row["item_id"],
                )
        if row["translation_status"] != "pending":
            raise DataError(
                f"{row['item_id']}: translation_status must be pending",
                "translation_status",
                row["item_id"],
            )
        if row["native_review_status"] != "pending":
            raise DataError(
                f"{row['item_id']}: native_review_status must be pending",
                "native_review_status",
                row["item_id"],
            )
    manifest = read_json(output / "source_manifest.json")
    for key in SOURCE_MANIFEST_FIELDS:
        if key not in manifest:
            raise DataError(f"source manifest missing {key}", key)
    if manifest["training_authorized"] is not False:
        raise DataError("the English source draft must not authorize training")
    if manifest["pilot_count"] != SOURCE_PILOT_TOTAL:
        raise DataError("source manifest pilot count is wrong")
    if manifest["evaluation_count"] != SOURCE_EVALUATION_TOTAL:
        raise DataError("source manifest evaluation count is wrong")
    for key, relative in manifest["files"].items():
        actual = sha256_file(output / relative)
        if actual != manifest["sha256"][key]:
            raise DataError(f"{relative} does not match the manifest checksum", key)
    return {
        "status": "source_exports_valid",
        "pilot_count": len(pilot),
        "evaluation_count": len(evaluation),
        "translator_rows": len(rows),
        "manifest": str(output / "source_manifest.json"),
        "training_authorized": False,
    }
