"""Review, calibration, disagreement, and agreement records.

Item review and response scoring are separate. An item must pass ambiguity,
reference, and native item review before it can be approved. Response reviews
carry the seven rubric scores and are linked to an evaluation run.
"""

import re
from dataclasses import asdict, dataclass
from itertools import combinations
from statistics import median, quantiles
from typing import Any, Iterable, Mapping

from .constants import (
    AMBIGUITY_OUTCOMES,
    AMBIGUITY_REVIEWER_ROLES,
    DIMENSION_NAMES,
    FAILURE_CODES,
    ITEM_REVIEW_DECISIONS,
    REVIEW_ROLES,
    REVIEWER_NOTE_FLAGS,
)
from .errors import ValidationError, WorkflowError
from .item import ITEM_ID_RE, validate_iso_date
from .storage import sha256_text

HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _get(value, key, default=None):
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("must be a non-empty string", field)
    return value


def _item_ref(value, field):
    if not isinstance(value, str) or not ITEM_ID_RE.match(value):
        raise ValidationError("must match LGP-BENCH-<CATEGORY>-<NNN>", field)
    return value


def _score(value, field, nullable=False):
    if value is None and nullable:
        return value
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValidationError("must be an integer from 1 to 5", field)
    return value


@dataclass(frozen=True)
class AmbiguityCheck:
    check_id: str
    item_id: str
    reviewer_id: str
    reviewer_role: str
    date: str
    outcome: str
    notes: str

    def __post_init__(self):
        _text(self.check_id, "check_id")
        _item_ref(self.item_id, "item_id")
        _text(self.reviewer_id, "reviewer_id")
        if self.reviewer_role not in AMBIGUITY_REVIEWER_ROLES:
            raise ValidationError(
                f"must be one of {AMBIGUITY_REVIEWER_ROLES}", "reviewer_role"
            )
        validate_iso_date(self.date, "date")
        if self.outcome not in AMBIGUITY_OUTCOMES:
            raise ValidationError(f"must be one of {AMBIGUITY_OUTCOMES}", "outcome")
        _text(self.notes, "notes")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ReferenceReview:
    review_id: str
    item_id: str
    reviewer_id: str
    role: str
    date: str
    approved: bool
    note: str
    reference_sha256: str

    def __post_init__(self):
        _text(self.review_id, "review_id")
        _item_ref(self.item_id, "item_id")
        _text(self.reviewer_id, "reviewer_id")
        if self.role != "native_reviewer":
            raise ValidationError("reference review role must be native_reviewer", "role")
        validate_iso_date(self.date, "date")
        if not isinstance(self.approved, bool):
            raise ValidationError("must be a boolean", "approved")
        _text(self.note, "note")
        if not isinstance(self.reference_sha256, str) or not HEX_RE.match(
            self.reference_sha256
        ):
            raise ValidationError("must be a lowercase SHA-256 hex digest", "reference_sha256")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ItemReview:
    review_id: str
    item_id: str
    reviewer_id: str
    role: str
    date: str
    decision: str
    notes: str
    calibration_completed: bool
    cultural_note_ok: bool
    reference_ok: bool

    def __post_init__(self):
        _text(self.review_id, "review_id")
        _item_ref(self.item_id, "item_id")
        _text(self.reviewer_id, "reviewer_id")
        if self.role not in REVIEW_ROLES:
            raise ValidationError(f"must be one of {REVIEW_ROLES}", "role")
        validate_iso_date(self.date, "date")
        if self.decision not in ITEM_REVIEW_DECISIONS:
            raise ValidationError(f"must be one of {ITEM_REVIEW_DECISIONS}", "decision")
        _text(self.notes, "notes")
        for field in ("calibration_completed", "cultural_note_ok", "reference_ok"):
            if not isinstance(getattr(self, field), bool):
                raise ValidationError("must be a boolean", field)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class CalibrationSession:
    session_id: str
    date: str
    reviewer_ids: tuple[str, ...]
    calibration_item_ids: tuple[str, ...]
    completed: bool
    notes: str

    def __post_init__(self):
        _text(self.session_id, "session_id")
        validate_iso_date(self.date, "date")
        if not isinstance(self.reviewer_ids, tuple) or len(set(self.reviewer_ids)) < 2:
            raise ValidationError(
                "must contain at least two distinct reviewer IDs", "reviewer_ids"
            )
        for reviewer_id in self.reviewer_ids:
            _text(reviewer_id, "reviewer_ids")
        if not isinstance(self.calibration_item_ids, tuple) or not self.calibration_item_ids:
            raise ValidationError("must contain at least one item", "calibration_item_ids")
        if not isinstance(self.completed, bool):
            raise ValidationError("must be a boolean", "completed")
        _text(self.notes, "notes")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ResponseReview:
    review_id: str
    item_id: str
    run_id: str
    reviewer_id: str
    role: str
    date: str
    calibration_completed: bool
    dimension: str
    score: int | None
    note: str
    flag: str
    failure_codes: tuple[str, ...]
    adjudication_required: bool
    adjudicated_score: int | None
    adjudicator_id: str | None
    adjudication_note: str | None

    def __post_init__(self):
        _text(self.review_id, "review_id")
        _item_ref(self.item_id, "item_id")
        _text(self.run_id, "run_id")
        _text(self.reviewer_id, "reviewer_id")
        if self.role not in REVIEW_ROLES:
            raise ValidationError(f"must be one of {REVIEW_ROLES}", "role")
        validate_iso_date(self.date, "date")
        if not isinstance(self.calibration_completed, bool):
            raise ValidationError("must be a boolean", "calibration_completed")
        if self.dimension not in DIMENSION_NAMES:
            raise ValidationError(f"must be one of {DIMENSION_NAMES}", "dimension")
        _score(self.score, "score", nullable=True)
        if not isinstance(self.note, str):
            raise ValidationError("must be a string", "note")
        if self.flag not in REVIEWER_NOTE_FLAGS:
            raise ValidationError(f"must be one of {REVIEWER_NOTE_FLAGS}", "flag")
        if not isinstance(self.failure_codes, tuple):
            raise ValidationError("must be a tuple", "failure_codes")
        for code in self.failure_codes:
            if code not in FAILURE_CODES:
                raise ValidationError(f"unknown failure code: {code!r}", "failure_codes")
        if not isinstance(self.adjudication_required, bool):
            raise ValidationError("must be a boolean", "adjudication_required")
        _score(self.adjudicated_score, "adjudicated_score", nullable=True)

        if self.role == "native_reviewer":
            if self.score is None:
                raise ValidationError("native reviewers must supply a score", "score")
            if self.adjudicated_score is not None or self.adjudicator_id or self.adjudication_note:
                raise ValidationError(
                    "only an adjudicator record may carry adjudication fields", "score"
                )
            if self.score in (1, 2, 4, 5) and not self.note.strip():
                raise ValidationError(
                    "a note is required for scores of 1, 2, 4, and 5", "note"
                )
        else:
            if self.score is not None:
                raise ValidationError("an adjudicator record must not carry an original score", "score")
            if self.adjudicated_score is None:
                raise ValidationError("an adjudicator record must carry adjudicated_score", "adjudicated_score")
            _text(self.adjudicator_id, "adjudicator_id")
            if self.adjudicator_id != self.reviewer_id:
                raise ValidationError("adjudicator_id must match reviewer_id", "adjudicator_id")
            _text(self.adjudication_note, "adjudication_note")
            if not self.adjudication_required:
                raise ValidationError(
                    "an adjudicator record must set adjudication_required to true",
                    "adjudication_required",
                )

    def to_dict(self):
        return asdict(self)


def effective_score(record):
    return _get(record, "adjudicated_score") if _get(record, "role") == "adjudicator" else _get(record, "score")


def validate_response_review(record, item):
    """Check that a response review is about an applicable dimension."""
    if _get(record, "item_id") != item["id"]:
        raise ValidationError("review item_id does not match the item", "item_id")
    dimension = _get(record, "dimension")
    if dimension not in item["scoring_dimensions"]:
        raise ValidationError(
            f"dimension {dimension} is not applicable to this item", "dimension"
        )
    return record


def _as_record(value, record_type, field, *, tuple_fields=()):
    if isinstance(value, record_type):
        return value
    if not isinstance(value, Mapping):
        raise ValidationError("must be an object", field)
    data = dict(value)
    for name in tuple_fields:
        if name in data and isinstance(data[name], list):
            data[name] = tuple(data[name])
    try:
        return record_type(**data)
    except TypeError as error:
        raise ValidationError(f"has unexpected fields: {error}", field) from error


def _item_checks(item, evidence, key, record_type):
    value = evidence.get(key, [])
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"evidence.{key} must be a list")
    records = [
        _as_record(record, record_type, f"evidence.{key}[{index}]")
        for index, record in enumerate(value)
    ]
    return [record for record in records if record.item_id == item["id"]]


def validate_item_review_evidence(item, evidence):
    """Validate the human evidence supporting a non-draft item status.

    The function does not recruit reviewers. It only accepts records that
    already exist and rejects status claims without them.
    """
    if not isinstance(evidence, Mapping):
        raise ValidationError("evidence must be an object")
    status = item["review_status"]
    checks = _item_checks(item, evidence, "ambiguity_checks", AmbiguityCheck)
    reviews = _item_checks(item, evidence, "item_reviews", ItemReview)
    references = _item_checks(item, evidence, "reference_reviews", ReferenceReview)
    session_value = evidence.get("calibration_sessions", [])
    if not isinstance(session_value, (list, tuple)):
        raise ValidationError("evidence.calibration_sessions must be a list")
    sessions = [
        _as_record(
            record,
            CalibrationSession,
            f"evidence.calibration_sessions[{index}]",
            tuple_fields=("reviewer_ids", "calibration_item_ids"),
        )
        for index, record in enumerate(session_value)
    ]
    if any(item["id"] in session.calibration_item_ids for session in sessions):
        raise ValidationError(
            "calibration items must be separate from benchmark items",
            "calibration_item_ids",
        )

    resolved_checks = [
        check
        for check in checks
        if _get(check, "outcome") in ("clear", "revised", "intrinsic_ambiguity")
        and _get(check, "reviewer_id") != item["author"]["id"]
    ]
    if not resolved_checks:
        raise ValidationError(
            "a second reviewer must record a resolved ambiguity check", "review_status"
        )
    if any(check.outcome == "intrinsic_ambiguity" for check in resolved_checks):
        if item["reference_status"] != "not_applicable":
            raise ValidationError(
                "intrinsic ambiguity requires reference_status not_applicable",
                "reference_status",
            )
    if status == "ambiguity_checked":
        return True

    if item["category"] == "cultural_interpretation":
        if not any(
            _get(review, "role") == "native_reviewer"
            and _get(review, "cultural_note_ok") is True
            for review in reviews
        ):
            raise ValidationError(
                "cultural_note requires native reviewer approval", "cultural_note"
            )

    if item["reference_status"] == "authored":
        reference_hash = sha256_text(item["reference_answer"])
        if not any(
            _get(review, "role") == "native_reviewer"
            and _get(review, "approved") is True
            and _get(review, "reference_sha256") == reference_hash
            for review in references
        ):
            raise ValidationError(
                "authored reference requires a matching native ReferenceReview",
                "reference_answer",
            )

    native_reviews = [
        review
        for review in reviews
        if _get(review, "role") == "native_reviewer"
        and _get(review, "calibration_completed") is True
    ]
    reviewer_ids = {_get(review, "reviewer_id") for review in native_reviews}
    if len(reviewer_ids) < 2:
        raise ValidationError(
            "at least two native reviewers with completed calibration are required",
            "review_status",
        )

    decisions = {_get(review, "decision") for review in native_reviews}
    if decisions - {"accept"}:
        adjudicators = [
            review
            for review in reviews
            if _get(review, "role") == "adjudicator"
            and _get(review, "decision") == "accept"
            and str(_get(review, "notes") or "").strip()
        ]
        if not adjudicators:
            raise ValidationError(
                "non-accepting item review requires an adjudicator record",
                "review_status",
            )

    completed_sessions = [
        session
        for session in sessions
        if _get(session, "completed") is True
        and set(_get(session, "reviewer_ids") or ()) >= reviewer_ids
    ]
    if not completed_sessions:
        raise ValidationError(
            "a completed calibration session covering the native reviewers is required",
            "review_status",
        )

    if status == "approved":
        from .versioning import ApprovalRecord, NativeReviewSignoff

        approval_value = evidence.get("approval_record")
        if approval_value is None:
            raise ValidationError(
                "approved items require an owner approval record", "review_status"
            )
        if isinstance(approval_value, ApprovalRecord):
            approval = approval_value
        elif isinstance(approval_value, Mapping):
            try:
                signoff_value = approval_value["native_review_signoff"]
                if not isinstance(signoff_value, Mapping):
                    raise ValidationError(
                        "native_review_signoff must be an object", "approval_record"
                    )
                panel = signoff_value["reviewer_panel"]
                reviewed = signoff_value["items_reviewed"]
                if not isinstance(panel, (list, tuple)) or not isinstance(
                    reviewed, (list, tuple)
                ):
                    raise ValidationError(
                        "native_review_signoff must contain reviewer and item lists",
                        "approval_record",
                    )
                signoff = NativeReviewSignoff(
                    reviewer_panel=tuple(panel),
                    calibration_date=signoff_value["calibration_date"],
                    agreement_statistic=signoff_value["agreement_statistic"],
                    items_reviewed=tuple(reviewed),
                    signoff_date=signoff_value["signoff_date"],
                )
                item_ids = approval_value["item_ids"]
                if not isinstance(item_ids, (list, tuple)):
                    raise ValidationError(
                        "item_ids must be a list", "approval_record"
                    )
                approval = ApprovalRecord(
                    specification_version=approval_value["specification_version"],
                    benchmark_version=approval_value["benchmark_version"],
                    approved_by=approval_value["approved_by"],
                    role=approval_value["role"],
                    date=approval_value["date"],
                    scope=approval_value["scope"],
                    conditions=approval_value["conditions"],
                    item_file_sha256=approval_value["item_file_sha256"],
                    item_ids=tuple(item_ids),
                    native_review_signoff=signoff,
                )
            except KeyError as error:
                raise ValidationError(
                    f"approval_record is missing field: {error}", "approval_record"
                ) from error
            except TypeError as error:
                raise ValidationError(
                    f"approval_record has an invalid field: {error}", "approval_record"
                ) from error
        else:
            raise ValidationError(
                "approval_record must be an object or ApprovalRecord",
                "approval_record",
            )
        if approval.benchmark_version != item["benchmark_version"]:
            raise ValidationError(
                "approval record benchmark_version does not match the item",
                "review_status",
            )
        if item["id"] not in approval.item_ids:
            raise ValidationError(
                "approval record does not list this item", "review_status"
            )
        if item["id"] not in approval.native_review_signoff.items_reviewed:
            raise ValidationError(
                "native review sign-off does not list this item", "review_status"
            )
        if approval.role != "project_owner":
            raise ValidationError(
                "approval record must be signed by the project owner", "review_status"
            )
    return True


BLIND_PACKET_FORBIDDEN_KEYS = frozenset(
    {
        "model",
        "model_id",
        "model_revision",
        "provider",
        "tokenizer_id",
        "tokenizer_revision",
        "base_model_id",
        "base_model_revision",
        "adapter_id",
        "adapter_revision",
        "run_id",
        "operator",
        "hardware",
        "cost",
        "timestamp",
        "latency_ms",
    }
)


def assert_blind_packet(packet):
    """Reject a review packet that exposes model or run identity."""
    if not isinstance(packet, Mapping):
        raise ValidationError("review packet must be an object")
    if packet.get("blind") is not True:
        raise ValidationError("review packet must be marked blind", "blind")

    def walk(value):
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in BLIND_PACKET_FORBIDDEN_KEYS:
                    raise ValidationError(
                        f"review packet exposes forbidden field {key!r}", "packet"
                    )
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)

    walk(packet)
    return True


def build_review_packet(item, raw_response, *, packet_id):
    """Build a blinded packet for independent response scoring.

    The packet keeps the item content, expected behavior, scoring dimensions,
    and the exact response text. It deliberately omits model, tokenizer, run,
    timestamp, and cost metadata.
    """
    if not isinstance(item, Mapping):
        raise ValidationError("item must be an object")
    _text(packet_id, "packet_id")
    _text(item.get("id"), "item.id")
    _text(item.get("prompt"), "item.prompt")
    _text(item.get("expected_behavior"), "item.expected_behavior")
    dimensions = item.get("scoring_dimensions")
    if not isinstance(dimensions, (list, tuple)) or not dimensions:
        raise ValidationError("item must declare scoring dimensions", "scoring_dimensions")
    if any(dimension not in DIMENSION_NAMES for dimension in dimensions):
        raise ValidationError("item has an unknown scoring dimension", "scoring_dimensions")
    response_text = _get(raw_response, "raw_response")
    if not isinstance(response_text, str):
        raise ValidationError("raw response text must be a string", "response")

    packet = {
        "packet_id": packet_id,
        "blind": True,
        "item_id": item["id"],
        "track": item.get("track"),
        "category": item.get("category"),
        "prompt_language": item.get("prompt_language"),
        "response_language": item.get("response_language"),
        "prompt": item["prompt"],
        "turns": list(item.get("turns") or []),
        "expected_behavior": item["expected_behavior"],
        "reference_status": item.get("reference_status"),
        "accepted_alternatives": list(item.get("accepted_alternatives") or []),
        "scoring_dimensions": list(dimensions),
        "allowed_scores": [1, 2, 3, 4, 5],
        "failure_codes": sorted(FAILURE_CODES),
        "response": response_text,
        "instructions": (
            "Score each applicable dimension independently. Use the rubric "
            "anchors, record a note for scores of 1, 2, 4, and 5, and record "
            "failure codes separately from dimension scores."
        ),
    }
    if item.get("reference_status") == "authored" and item.get("reference_answer"):
        packet["reference_answer"] = item["reference_answer"]
    if item.get("ambiguity_notes"):
        packet["ambiguity_notes"] = item["ambiguity_notes"]
    if item.get("cultural_note"):
        packet["cultural_note"] = item["cultural_note"]
    assert_blind_packet(packet)
    return packet


def validate_independent_reviews(records: Iterable[Any], *, minimum_reviewers=2):
    """Reject duplicate scores, uncalibrated reviewers, and short panels."""
    if isinstance(minimum_reviewers, bool) or not isinstance(minimum_reviewers, int):
        raise ValidationError("minimum_reviewers must be an integer", "minimum_reviewers")
    if minimum_reviewers < 2:
        raise ValidationError("minimum_reviewers must be at least 2", "minimum_reviewers")
    seen = set()
    panel = {}
    for index, value in enumerate(records):
        record = _as_record(
            value,
            ResponseReview,
            f"records[{index}]",
            tuple_fields=("failure_codes",),
        )
        if record.role != "native_reviewer":
            continue
        if record.calibration_completed is not True:
            raise ValidationError(
                "native reviewers must complete calibration before scoring",
                "calibration_completed",
            )
        key = (
            _get(record, "item_id"),
            _get(record, "run_id"),
            _get(record, "dimension"),
            _get(record, "reviewer_id"),
        )
        if key in seen:
            raise ValidationError(
                "the same reviewer scored the same item, run, and dimension twice",
                "reviewer_id",
            )
        seen.add(key)
        panel_key = key[:3]
        panel.setdefault(panel_key, set()).add(key[3])
    if not panel:
        raise ValidationError("at least one native review record is required", "records")
    for panel_key, reviewers in panel.items():
        if len(reviewers) < minimum_reviewers:
            raise ValidationError(
                f"independent scoring requires at least {minimum_reviewers} reviewers for {panel_key}",
                "reviewer_id",
            )
    return True


def material_disagreements(records: Iterable[Any]):
    """Return material score, acceptability, or failure-code disagreements."""
    groups = {}
    for record in records:
        if _get(record, "role") != "native_reviewer":
            continue
        key = (_get(record, "item_id"), _get(record, "run_id"), _get(record, "dimension"))
        groups.setdefault(key, []).append(record)

    findings = []
    for (item_id, run_id, dimension), group in groups.items():
        for left, right in combinations(group, 2):
            if _get(left, "reviewer_id") == _get(right, "reviewer_id"):
                continue
            left_score = _get(left, "score")
            right_score = _get(right, "score")
            if left_score is None or right_score is None:
                continue
            _score(left_score, "score")
            _score(right_score, "score")
            reasons = []
            if abs(left_score - right_score) >= 2:
                reasons.append("score difference of at least two points")
            if (left_score >= 3) != (right_score >= 3):
                reasons.append("acceptability disagreement")
            if set(_get(left, "failure_codes") or ()) != set(_get(right, "failure_codes") or ()):
                reasons.append("failure-code disagreement")
            if reasons:
                findings.append(
                    {
                        "item_id": item_id,
                        "run_id": run_id,
                        "dimension": dimension,
                        "reviewer_ids": [
                            _get(left, "reviewer_id"),
                            _get(right, "reviewer_id"),
                        ],
                        "reasons": reasons,
                    }
                )
    return findings


def build_adjudication(
    *,
    records,
    review_id,
    item,
    run_id,
    reviewer_id,
    date,
    dimension,
    adjudicated_score,
    note,
    failure_codes=(),
    calibration_completed=True,
):
    """Create one adjudicator review record after a material disagreement."""
    records = list(records)
    findings = [
        finding
        for finding in material_disagreements(records)
        if finding["item_id"] == item["id"]
        and finding["run_id"] == run_id
        and finding["dimension"] == dimension
    ]
    if not findings:
        raise WorkflowError(
            "no material disagreement was found for this item, run, and dimension"
        )
    original_reviewers = {
        _get(record, "reviewer_id")
        for record in records
        if _get(record, "role") == "native_reviewer"
        and _get(record, "item_id") == item["id"]
        and _get(record, "run_id") == run_id
        and _get(record, "dimension") == dimension
    }
    if reviewer_id in original_reviewers:
        raise WorkflowError(
            "the adjudicator must be a third reviewer, not one of the original scorers"
        )
    if calibration_completed is not True:
        raise ValidationError(
            "the adjudicator must complete calibration before review",
            "calibration_completed",
        )
    record = ResponseReview(
        review_id=review_id,
        item_id=item["id"],
        run_id=run_id,
        reviewer_id=reviewer_id,
        role="adjudicator",
        date=date,
        calibration_completed=calibration_completed,
        dimension=dimension,
        score=None,
        note="",
        flag="none",
        failure_codes=tuple(failure_codes),
        adjudication_required=True,
        adjudicated_score=adjudicated_score,
        adjudicator_id=reviewer_id,
        adjudication_note=note,
    )
    validate_response_review(record, item)
    return record


def quadratic_weighted_kappa(left_scores, right_scores):
    """Cohen's kappa with quadratic weights for ordinal 1 to 5 scores."""
    if len(left_scores) != len(right_scores) or not left_scores:
        return None
    left = [_score(score, "kappa score") for score in left_scores]
    right = [_score(score, "kappa score") for score in right_scores]
    size = 5
    observed = [[0.0] * size for _ in range(size)]
    for a, b in zip(left, right):
        observed[a - 1][b - 1] += 1
    total = float(len(left))
    for row in range(size):
        for column in range(size):
            observed[row][column] /= total
    left_marginal = [sum(observed[row]) for row in range(size)]
    right_marginal = [sum(observed[row][column] for row in range(size)) for column in range(size)]
    expected = [
        [left_marginal[row] * right_marginal[column] for column in range(size)]
        for row in range(size)
    ]
    weights = [
        [((row - column) ** 2) / ((size - 1) ** 2) for column in range(size)]
        for row in range(size)
    ]
    observed_disagreement = sum(
        weights[row][column] * observed[row][column]
        for row in range(size)
        for column in range(size)
    )
    expected_disagreement = sum(
        weights[row][column] * expected[row][column]
        for row in range(size)
        for column in range(size)
    )
    if expected_disagreement == 0:
        return None
    return 1.0 - observed_disagreement / expected_disagreement


def agreement_report(records: Iterable[Any]):
    """Report exact, within-one, and quadratic-weighted agreement per dimension."""
    groups = {}
    for record in records:
        if _get(record, "role") != "native_reviewer":
            continue
        key = (_get(record, "dimension"), _get(record, "item_id"), _get(record, "run_id"))
        groups.setdefault(key, []).append(record)

    by_dimension = {}
    for (dimension, _item_id, _run_id), group in groups.items():
        entry = by_dimension.setdefault(
            dimension,
            {
                "left": [],
                "right": [],
                "pairs": 0,
                "missing_pairs": 0,
                "exact": 0,
                "within_one": 0,
            },
        )
        for left, right in combinations(group, 2):
            if _get(left, "reviewer_id") == _get(right, "reviewer_id"):
                continue
            left_score = _get(left, "score")
            right_score = _get(right, "score")
            if left_score is None or right_score is None:
                entry["missing_pairs"] += 1
                continue
            _score(left_score, "score")
            _score(right_score, "score")
            entry["left"].append(left_score)
            entry["right"].append(right_score)
            entry["pairs"] += 1
            entry["exact"] += int(left_score == right_score)
            entry["within_one"] += int(abs(left_score - right_score) <= 1)

    report = {}
    for dimension, entry in by_dimension.items():
        pairs = entry["pairs"]
        report[dimension] = {
            "pairs": pairs,
            "missing_pairs": entry["missing_pairs"],
            "exact_agreement": entry["exact"] / pairs if pairs else None,
            "within_one_agreement": entry["within_one"] / pairs if pairs else None,
            "quadratic_weighted_kappa": (
                quadratic_weighted_kappa(entry["left"], entry["right"])
                if pairs
                else None
            ),
            "statistic": "quadratic_weighted_kappa",
        }
    return report


def _quartiles(values):
    if not values:
        return None, None, None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0]
    if len(ordered) == 2:
        return ordered[0], sum(ordered) / 2, ordered[1]
    q1, _q2, q3 = quantiles(ordered, n=4)
    return q1, median(ordered), q3


def summarize_scores(records: Iterable[Any], items_by_id: Mapping[str, Mapping]):
    """Return per-dimension distributions and enforce track separation.

    No overall score, average across dimensions, or leaderboard rank is
    produced. That is required by section 11.4 of the specification.
    """
    records = list(records)
    tracks = {items_by_id[_get(record, "item_id")]["track"] for record in records}
    if len(tracks) > 1:
        raise WorkflowError(
            f"conversational and translation results must be reported separately: {sorted(tracks)}"
        )
    track = next(iter(tracks)) if tracks else None

    groups = {}
    for record in records:
        key = (_get(record, "item_id"), _get(record, "run_id"), _get(record, "dimension"))
        groups.setdefault(key, []).append(record)

    values = {dimension: [] for dimension in DIMENSION_NAMES}
    for (item_id, _run_id, dimension), group in groups.items():
        adjudicators = [
            record for record in group if _get(record, "role") == "adjudicator"
        ]
        if adjudicators:
            values[dimension].append(_get(adjudicators[-1], "adjudicated_score"))
        else:
            values[dimension].extend(
                _get(record, "score")
                for record in group
                if _get(record, "role") == "native_reviewer"
            )

    applicable = {
        dimension: sum(
            1
            for item in items_by_id.values()
            if item.get("track") == track
            and dimension in item.get("scoring_dimensions", [])
        )
        for dimension in DIMENSION_NAMES
    }
    summary = {}
    for dimension, scores in values.items():
        scores = [score for score in scores if score is not None]
        q1, middle, q3 = _quartiles(scores)
        summary[dimension] = {
            "applicable_items": applicable[dimension],
            "count": len(scores),
            "scores": scores,
            "median": middle,
            "q1": q1,
            "q3": q3,
        }
    return {"track": track, "dimensions": summary}
