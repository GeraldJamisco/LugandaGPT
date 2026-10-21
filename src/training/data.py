"""Pilot loading, split integrity, contamination checks, and conversion.

This module never downloads data and never imports Datasets or TRL. It reads
local JSONL files, applies the schema in ``pilot.py``, and produces the
conversational prompt-completion records that TRL will receive.
"""

import copy
import datetime as _datetime
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .constants import (
    CAPABILITIES,
    CAPABILITY_COUNTS,
    CONVERSATION_MAX_TOKENS,
    EVALUATION_TOTAL,
    NGRAM_SIZE,
    NON_CONVERSATION_MAX_TOKENS,
    PILOT_TOTAL,
    SPLITS,
    SPLIT_COUNTS,
    TRAINING_MAX_LENGTH,
)
from .errors import DataError, ProvenanceError
from .pilot import (
    TEACHER_ID_RE,
    _is_unresolved,
    composition_summary,
    validate_audit_coverage,
    validate_collection,
    validate_evaluation_collection,
)
from .storage import read_json, read_jsonl, sha256_file

PROVENANCE_FIELDS = (
    "dataset_name",
    "dataset_version",
    "source",
    "acquisition_method",
    "licence_references",
    "permitted_uses",
    "acquisition_date",
    "data_owner",
    "language_varieties",
    "domains",
    "collection_method",
    "consent",
    "compensation",
    "pii_assessment",
    "deduplication",
    "limitations",
    "counts",
    "split_sha256",
    "approval_reference",
)
PROVENANCE_OPTIONAL = (
    "source_url",
    "collection_dates",
    "review_process",
    "retention",
    "contact",
    "notes",
)
REQUIRED_PERMITTED_USES = {
    "training",
    "evaluation",
    "derivatives",
    "research_reporting",
}
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class PilotDataset:
    train: tuple
    validation: tuple
    heldout: tuple
    evaluation: tuple
    provenance: Mapping
    provenance_sha256: str
    hashes: Mapping
    summary: Mapping
    paths: Mapping


def _mapping(value, field):
    if not isinstance(value, Mapping):
        raise ProvenanceError("must be an object", field)
    return value


def _keys(value, field, required, optional=()):
    allowed = set(required) | set(optional)
    missing = sorted(set(required) - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ProvenanceError(f"missing required fields: {missing}", field)
    if unknown:
        raise ProvenanceError(f"unknown fields: {unknown}", field)
    return value


def _string(value, field, allow_empty=False):
    if not isinstance(value, str):
        raise ProvenanceError("must be a string", field)
    if not allow_empty and not value.strip():
        raise ProvenanceError("must not be empty", field)
    return value


def _string_list(value, field, allow_empty=False):
    if not isinstance(value, list):
        raise ProvenanceError("must be a list", field)
    if not allow_empty and not value:
        raise ProvenanceError("must not be empty", field)
    for index, item in enumerate(value):
        _string(item, f"{field}[{index}]")
    if len(value) != len(set(value)):
        raise ProvenanceError("must not contain duplicates", field)
    return value


def _date(value, field, as_of=None):
    _string(value, field)
    try:
        parsed = _datetime.date.fromisoformat(value)
    except ValueError as error:
        raise ProvenanceError(f"must use YYYY-MM-DD: {error}", field) from error
    reference = as_of or _datetime.date.today()
    if parsed > reference:
        raise ProvenanceError(f"must not be after {reference.isoformat()}", field)
    return parsed


def _resolve(root, relative, field):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise DataError(f"path escapes project root: {relative}", field) from error
    return path


def validate_provenance(record, strict=True, as_of=None):
    record = _mapping(record, "provenance")
    _keys(
        record,
        "provenance",
        required=PROVENANCE_FIELDS,
        optional=PROVENANCE_OPTIONAL,
    )
    _string(record["dataset_name"], "provenance.dataset_name")
    _string(record["dataset_version"], "provenance.dataset_version")
    _string(record["source"], "provenance.source")
    _string(record["acquisition_method"], "provenance.acquisition_method")
    if "source_url" in record:
        _string(record["source_url"], "provenance.source_url")
    licences = _string_list(
        record["licence_references"], "provenance.licence_references", allow_empty=False
    )
    uses = set(_string_list(record["permitted_uses"], "provenance.permitted_uses", allow_empty=False))
    missing_uses = sorted(REQUIRED_PERMITTED_USES - uses)
    if strict and missing_uses:
        raise ProvenanceError(
            f"does not cover required uses: {missing_uses}", "provenance.permitted_uses"
        )
    _date(record["acquisition_date"], "provenance.acquisition_date", as_of)
    _string(record["data_owner"], "provenance.data_owner")
    _string_list(record["language_varieties"], "provenance.language_varieties", allow_empty=False)
    _string_list(record["domains"], "provenance.domains", allow_empty=False)
    _string(record["collection_method"], "provenance.collection_method")

    consent = record["consent"]
    if not isinstance(consent, list) or not consent:
        raise ProvenanceError("must be a non-empty list", "provenance.consent")
    consent_refs = set()
    signed_teacher_consents = {}
    for index, item in enumerate(consent):
        field = f"provenance.consent[{index}]"
        item = _mapping(item, field)
        _keys(
            item,
            field,
            required=(
                "reference",
                "teacher_id",
                "status",
                "withdrawal_terms",
                "retention",
            ),
            optional=("notes",),
        )
        reference = _string(item["reference"], f"{field}.reference")
        if reference in consent_refs:
            raise ProvenanceError("duplicate consent reference", f"{field}.reference")
        consent_refs.add(reference)
        teacher_id = _string(item["teacher_id"], f"{field}.teacher_id")
        if not TEACHER_ID_RE.match(teacher_id):
            raise ProvenanceError("must match T-NNN", f"{field}.teacher_id")
        status = _string(item["status"], f"{field}.status")
        if status not in ("signed", "pending", "withdrawn"):
            raise ProvenanceError(
                "must be signed, pending, or withdrawn", f"{field}.status"
            )
        _string(item["withdrawal_terms"], f"{field}.withdrawal_terms")
        _string(item["retention"], f"{field}.retention")
        if "notes" in item:
            _string(item["notes"], f"{field}.notes", allow_empty=True)
        if status == "signed":
            signed_teacher_consents[teacher_id] = reference
        if strict and status != "signed":
            raise ProvenanceError(
                "teacher consent must be signed before training", f"{field}.status"
            )

    compensation = _mapping(record["compensation"], "provenance.compensation")
    _keys(compensation, "provenance.compensation", required=("status", "details"))
    status = _string(compensation["status"], "provenance.compensation.status")
    if status not in ("agreed", "paid", "pending"):
        raise ProvenanceError(
            "must be agreed, paid, or pending", "provenance.compensation.status"
        )
    _string(compensation["details"], "provenance.compensation.details")
    if strict and status not in ("agreed", "paid"):
        raise ProvenanceError(
            "teacher compensation must be agreed before training",
            "provenance.compensation.status",
        )

    _string(record["pii_assessment"], "provenance.pii_assessment")
    _string(record["deduplication"], "provenance.deduplication")
    _string(record["limitations"], "provenance.limitations")
    for key in ("retention", "review_process", "contact", "notes"):
        if key in record:
            _string(record[key], f"provenance.{key}", allow_empty=(key == "notes"))
    if "collection_dates" in record:
        _string_list(record["collection_dates"], "provenance.collection_dates", allow_empty=False)

    counts = _mapping(record["counts"], "provenance.counts")
    _keys(
        counts,
        "provenance.counts",
        required=("train", "validation", "heldout", "evaluation"),
    )
    for key, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProvenanceError(
                "must be a non-negative integer", f"provenance.counts.{key}"
            )
    expected_counts = dict(SPLIT_COUNTS)
    expected_counts["evaluation"] = EVALUATION_TOTAL
    if strict and counts != expected_counts:
        raise ProvenanceError(
            f"must be {expected_counts}, found {counts}", "provenance.counts"
        )

    split_hashes = _mapping(record["split_sha256"], "provenance.split_sha256")
    _keys(
        split_hashes,
        "provenance.split_sha256",
        required=("train", "validation", "heldout", "evaluation"),
    )
    for key, value in split_hashes.items():
        if value == "pending":
            if strict:
                raise ProvenanceError(
                    "must record the actual SHA-256 before training",
                    f"provenance.split_sha256.{key}",
                )
            continue
        _string(value, f"provenance.split_sha256.{key}")
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ProvenanceError(
                "must be a lowercase SHA-256 digest",
                f"provenance.split_sha256.{key}",
            )
    _string(record["approval_reference"], "provenance.approval_reference")
    if strict and _is_unresolved(record["approval_reference"]):
        raise ProvenanceError(
            "dataset approval reference is unresolved", "provenance.approval_reference"
        )
    if strict:
        for field in (
            "source",
            "acquisition_method",
            "data_owner",
            "collection_method",
            "pii_assessment",
            "deduplication",
            "limitations",
            "approval_reference",
        ):
            if _is_unresolved(record[field]):
                raise ProvenanceError("is unresolved", f"provenance.{field}")
    return record


def _check_provenance_links(provenance, records, strict=True):
    licences = set(provenance["licence_references"])
    consents = {item["reference"]: item for item in provenance["consent"]}
    for record in records:
        record_id = record.get("pilot_id") or record.get("eval_id")
        licence = record["licence"]
        if licence not in licences:
            raise ProvenanceError(
                f"record licence {licence!r} is not in provenance.licence_references",
                "licence",
                record_id,
            )
        consent_ref = record["consent_ref"]
        if consent_ref not in consents:
            raise ProvenanceError(
                f"record consent {consent_ref!r} is not in provenance.consent",
                "consent_ref",
                record_id,
            )
        consent = consents[consent_ref]
        if consent["teacher_id"] != record["author_id"]:
            raise ProvenanceError(
                "consent teacher_id does not match the record author_id",
                "consent_ref",
                record_id,
            )
        if strict and consent["status"] != "signed":
            raise ProvenanceError(
                "record author consent is not signed", "consent_ref", record_id
            )
    return True


def _normalized_text(text):
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _ngrams(text, size=NGRAM_SIZE):
    words = [word for word in WORD_RE.findall(text.casefold())]
    if len(words) < size:
        return set()
    return {" ".join(words[index : index + size]) for index in range(len(words) - size + 1)}


def _record_text_units(record):
    units = []
    messages = record["messages"]
    for index, message in enumerate(messages):
        role = message["role"]
        content = message["content"]
        if role == "user":
            units.append((f"{record.get('pilot_id') or record.get('eval_id')}:user:{index}", content))
        else:
            words = WORD_RE.findall(content)
            if len(words) >= 4:
                units.append(
                    (f"{record.get('pilot_id') or record.get('eval_id')}:assistant:{index}", content)
                )
    transcript = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
    units.append((f"{record.get('pilot_id') or record.get('eval_id')}:transcript", transcript))
    return units


def _text_owner(record):
    return record.get("pilot_id") or record.get("eval_id")


def check_contamination(named_sets, exact=True, ngram_size=NGRAM_SIZE):
    """Find exact and n-gram overlaps inside and between named record sets.

    ``named_sets`` is a mapping of label to records. Records are compared
    across all labels, including within one label. Every overlap is blocking.
    """
    units = []
    for label, records in named_sets.items():
        for record in records:
            for unit_name, text in _record_text_units(record):
                units.append(
                    {
                        "label": label,
                        "record_id": _text_owner(record),
                        "unit": unit_name,
                        "text": text,
                        "exact": _normalized_text(text),
                        "ngrams": _ngrams(text, ngram_size),
                    }
                )
    pairs_checked = 0
    exact_seen = {}
    ngram_seen = {}
    for unit in units:
        if exact:
            previous = exact_seen.get(unit["exact"])
            if previous is not None and previous["record_id"] != unit["record_id"]:
                raise DataError(
                    f"exact duplicate text between {previous['record_id']} and "
                    f"{unit['record_id']}: {unit['text'][:120]!r}",
                    "contamination",
                    unit["record_id"],
                )
            exact_seen.setdefault(unit["exact"], unit)
        for gram in unit["ngrams"]:
            previous = ngram_seen.get(gram)
            if previous is not None and previous["record_id"] != unit["record_id"]:
                raise DataError(
                    f"{ngram_size}-gram overlap between {previous['record_id']} "
                    f"and {unit['record_id']}: {gram!r}",
                    "contamination",
                    unit["record_id"],
                )
            ngram_seen.setdefault(gram, unit)
        pairs_checked += 1
    return {
        "exact_units_checked": len(units) if exact else 0,
        "ngram_size": ngram_size,
        "ngram_units_checked": len(units),
        "text_units_compared": pairs_checked,
        "status": "no_exact_or_ngram_overlap_detected",
    }


def _render_ids(tokenizer, messages):
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        return_attention_mask=False,
    )
    return encoded["input_ids"], text


def check_token_limits(record, tokenizer, max_length=TRAINING_MAX_LENGTH):
    record_id = record.get("pilot_id") or record.get("eval_id")
    if record["capability"] == "short_conversation":
        limit = min(CONVERSATION_MAX_TOKENS, max_length)
    else:
        limit = min(NON_CONVERSATION_MAX_TOKENS, max_length)
    full_ids, _ = _render_ids(tokenizer, record["messages"])
    if not full_ids:
        raise DataError("produces no tokens", "messages", record_id)
    if len(full_ids) > limit:
        raise DataError(
            f"renders to {len(full_ids)} tokens, over the {limit}-token limit",
            "messages",
            record_id,
        )
    expanded = expand_prompt_completion(record)
    max_completion = 0
    for item in expanded:
        prompt_ids, _ = _render_ids(tokenizer, item["prompt"])
        completion_ids, _ = _render_ids(tokenizer, item["prompt"] + item["completion"])
        if completion_ids[: len(prompt_ids)] != prompt_ids:
            raise DataError(
                "tokenized prompt is not a prefix of prompt plus completion",
                "messages",
                record_id,
            )
        remainder = completion_ids[len(prompt_ids) :]
        if not remainder:
            raise DataError(
                "assistant completion produced no tokens", "messages", record_id
            )
        decoded = tokenizer.decode(remainder, skip_special_tokens=False)
        if not decoded.lstrip().startswith("<start_of_turn>model"):
            raise DataError(
                "completion does not begin with the base model turn marker",
                "messages",
                record_id,
            )
        if len(completion_ids) > max_length:
            raise DataError(
                f"expanded training record is {len(completion_ids)} tokens, "
                f"over max_length {max_length}",
                "messages",
                record_id,
            )
        max_completion = max(max_completion, len(completion_ids))
    return {
        "record_id": record_id,
        "full_tokens": len(full_ids),
        "limit": limit,
        "max_prompt_completion_tokens": max_completion,
        "assistant_turns": len(expanded),
    }


def expand_prompt_completion(record):
    """Turn every assistant message into one conversational SFT record.

    The prompt is the preceding conversation and the completion is exactly
    one assistant message. This keeps the base chat template unchanged and
    lets TRL mask prompt tokens with ``completion_only_loss``.
    """
    record_id = record.get("pilot_id") or record.get("eval_id")
    messages = record["messages"]
    expanded = []
    for index, message in enumerate(messages):
        if message["role"] != "assistant":
            continue
        prompt = copy.deepcopy(messages[:index])
        completion = copy.deepcopy([message])
        if not prompt or prompt[-1]["role"] != "user":
            raise DataError(
                "assistant turn is not preceded by a user turn",
                "messages",
                record_id,
            )
        expanded.append(
            {
                "record_id": record_id,
                "capability": record["capability"],
                "split": record.get("split", "evaluation"),
                "turn_index": index,
                "prompt": prompt,
                "completion": completion,
            }
        )
    expected = sum(1 for message in messages if message["role"] == "assistant")
    if len(expanded) != expected:
        raise DataError(
            "not every assistant turn produced one training record",
            "messages",
            record_id,
        )
    indices = [item["turn_index"] for item in expanded]
    if len(indices) != len(set(indices)):
        raise DataError("assistant turn appears more than once", "messages", record_id)
    return expanded


def expand_split(records):
    expanded = []
    for record in records:
        expanded.extend(expand_prompt_completion(record))
    return expanded


def _load_jsonl(path, label):
    if not path.is_file():
        raise DataError(f"{label} file is not prepared: {path}")
    try:
        records = read_jsonl(path)
    except DataError as error:
        raise DataError(f"{label}: {error}") from error
    if not records:
        raise DataError(f"{label} file is empty: {path}")
    return records


def _load_provenance(path, strict, as_of):
    if not path.is_file():
        raise ProvenanceError(f"provenance record is not prepared: {path}")
    try:
        value = read_json(path)
    except DataError as error:
        raise ProvenanceError(f"provenance: {error}") from error
    return validate_provenance(value, strict=strict, as_of=as_of)


def _check_config_split_hashes(config, actual, strict):
    configured = config["dataset"]["split_hashes"]
    if configured == "pending":
        if strict:
            raise ProvenanceError(
                "dataset.split_hashes is pending; record the actual file hashes "
                "in the config before training",
                "dataset.split_hashes",
            )
        return
    for key, digest in actual.items():
        if configured.get(key) in (None, "pending"):
            if strict:
                raise ProvenanceError(
                    f"dataset.split_hashes.{key} is pending",
                    f"dataset.split_hashes.{key}",
                )
            continue
        if configured[key] != digest:
            raise ProvenanceError(
                f"config hash does not match {key} file: "
                f"configured {configured[key]}, actual {digest}",
                f"dataset.split_hashes.{key}",
            )


def _check_provenance_hashes(provenance, actual, strict):
    for key, digest in actual.items():
        recorded = provenance["split_sha256"][key]
        if recorded == "pending":
            if strict:
                raise ProvenanceError(
                    f"provenance hash is pending for {key}",
                    f"provenance.split_sha256.{key}",
                )
            continue
        if recorded != digest:
            raise ProvenanceError(
                f"provenance hash does not match {key} file: "
                f"recorded {recorded}, actual {digest}",
                f"provenance.split_sha256.{key}",
            )


def _check_provenance_counts(provenance, actual, strict=True):
    if not strict:
        return
    for key, count in actual.items():
        recorded = provenance["counts"][key]
        if recorded != count:
            raise ProvenanceError(
                f"provenance count does not match {key} file: "
                f"recorded {recorded}, actual {count}",
                f"provenance.counts.{key}",
            )


def load_pilot_dataset(
    config,
    project_root=None,
    *,
    require_complete=True,
    require_approved=True,
    tokenizer=None,
    require_token_checks=False,
    as_of=None,
):
    """Load and validate the proposed pilot, evaluation set, and provenance.

    ``require_approved=False`` supports draft review. It still checks schema,
    counts when requested, and contamination, but allows unresolved review,
    licence, consent, and validation fields.
    """
    root = Path(project_root or Path.cwd()).resolve()
    dataset = config["dataset"]
    if require_approved:
        version = dataset["version"].casefold()
        if any(marker in version for marker in ("unapproved", "pending", "draft")):
            raise ProvenanceError(
                "dataset.version is still marked unapproved or draft",
                "dataset.version",
            )
    paths = {
        "train": _resolve(root, dataset["train_path"], "dataset.train_path"),
        "validation": _resolve(
            root, dataset["validation_path"], "dataset.validation_path"
        ),
        "heldout": _resolve(root, dataset["heldout_path"], "dataset.heldout_path"),
        "evaluation": _resolve(
            root, dataset["evaluation_path"], "dataset.evaluation_path"
        ),
    }
    provenance_path = _resolve(
        root, dataset["provenance_path"], "dataset.provenance_path"
    )
    all_paths = list(paths.values()) + [provenance_path]
    if len(set(all_paths)) != len(all_paths):
        raise ProvenanceError("dataset files and provenance record must be distinct")
    for name, path in paths.items():
        if not path.is_file():
            raise DataError(f"{name} file is not prepared: {path}")
    if not provenance_path.is_file():
        raise ProvenanceError(f"provenance record is not prepared: {provenance_path}")
    actual_hashes = {
        key: sha256_file(path) for key, path in paths.items()
    }
    if require_approved:
        _check_config_split_hashes(config, actual_hashes, strict=True)
    provenance = _load_provenance(provenance_path, strict=require_approved, as_of=as_of)
    if provenance["dataset_version"] != dataset["version"]:
        raise ProvenanceError(
            f"provenance dataset_version {provenance['dataset_version']!r} "
            f"does not match config {dataset['version']!r}",
            "provenance.dataset_version",
        )

    raw = {
        "train": _load_jsonl(paths["train"], "training split"),
        "validation": _load_jsonl(paths["validation"], "validation split"),
        "heldout": _load_jsonl(paths["heldout"], "held-out split"),
        "evaluation": _load_jsonl(paths["evaluation"], "evaluation set"),
    }
    loaded = {}
    id_sets = {}
    capability_counts = {}
    for split in SPLITS:
        records, counts, ids = validate_collection(
            raw[split],
            expected_split=split,
            require_complete=require_complete,
            require_approved=require_approved,
            as_of=as_of,
        )
        loaded[split] = tuple(records)
        id_sets[split] = ids
        capability_counts[split] = counts
    evaluation, evaluation_counts, evaluation_ids = validate_evaluation_collection(
        raw["evaluation"],
        require_complete=require_complete,
        require_approved=require_approved,
        as_of=as_of,
    )
    loaded["evaluation"] = tuple(evaluation)

    all_pilot_ids = set().union(*(id_sets[split] for split in SPLITS))
    if len(all_pilot_ids) != sum(len(id_sets[split]) for split in SPLITS):
        raise DataError("pilot IDs are not unique across splits", "pilot_id")
    if all_pilot_ids & evaluation_ids:
        raise DataError("pilot and evaluation IDs overlap", "pilot_id")
    if require_complete and len(all_pilot_ids) != PILOT_TOTAL:
        raise DataError(
            f"expected {PILOT_TOTAL} unique pilot IDs, found {len(all_pilot_ids)}",
            "pilot_count",
        )
    combined = tuple(
        record for split in SPLITS for record in loaded[split]
    )
    total_capabilities = {name: 0 for name in CAPABILITIES}
    for split in SPLITS:
        for name, count in capability_counts[split].items():
            total_capabilities[name] += count
    if require_complete and total_capabilities != CAPABILITY_COUNTS:
        raise DataError(
            f"combined capability counts are inconsistent: {total_capabilities}",
            "capability",
        )

    _check_provenance_counts(
        provenance,
        {
            "train": len(loaded["train"]),
            "validation": len(loaded["validation"]),
            "heldout": len(loaded["heldout"]),
            "evaluation": len(loaded["evaluation"]),
        },
        strict=require_complete,
    )
    _check_provenance_hashes(provenance, actual_hashes, strict=require_approved)
    _check_provenance_links(
        provenance,
        list(combined) + list(evaluation),
        strict=require_approved,
    )
    audit = validate_audit_coverage(loaded["train"], require_complete=require_complete)
    contamination = check_contamination(
        {
            "train": loaded["train"],
            "validation": loaded["validation"],
            "heldout": loaded["heldout"],
            "evaluation": loaded["evaluation"],
        }
    )

    token_summary = None
    if tokenizer is not None:
        checked = [
            check_token_limits(record, tokenizer)
            for split in SPLITS
            for record in loaded[split]
        ] + [
            check_token_limits(record, tokenizer)
            for record in loaded["evaluation"]
        ]
        token_summary = {
            "records_checked": len(checked),
            "max_full_tokens": max(item["full_tokens"] for item in checked),
            "max_prompt_completion_tokens": max(
                item["max_prompt_completion_tokens"] for item in checked
            ),
            "assistant_turns": sum(item["assistant_turns"] for item in checked),
            "status": "within_declared_limits",
        }
    elif require_token_checks:
        raise DataError(
            "tokenizer is required for token-length and prompt-completion checks"
        )

    if require_complete and len(expand_split(loaded["train"])) < len(loaded["train"]):
        raise DataError("assistant-turn expansion is incomplete", "messages")

    summary = {
        "counts": {
            "train": len(loaded["train"]),
            "validation": len(loaded["validation"]),
            "heldout": len(loaded["heldout"]),
            "evaluation": len(loaded["evaluation"]),
        },
        "capability_counts": total_capabilities,
        "evaluation_capability_counts": evaluation_counts,
        "composition": composition_summary(combined),
        "audit": audit,
        "contamination": contamination,
        "token_checks": token_summary,
        "train_expanded_records": len(expand_split(loaded["train"])),
        "validation_expanded_records": len(expand_split(loaded["validation"])),
        "reviewed": bool(require_approved),
    }
    return PilotDataset(
        train=loaded["train"],
        validation=loaded["validation"],
        heldout=loaded["heldout"],
        evaluation=loaded["evaluation"],
        provenance=provenance,
        provenance_sha256=sha256_file(provenance_path),
        hashes=actual_hashes,
        summary=summary,
        paths={
            **{key: str(path) for key, path in paths.items()},
            "provenance": str(provenance_path),
        },
    )
