"""Evaluation-run manifests and verbatim raw-response storage."""

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .constants import COST_KINDS, RUN_STATUSES
from .errors import RunError, ValidationError
from .item import ITEM_ID_RE, validate_version
from .storage import (
    append_jsonl,
    canonical_json,
    pretty_json,
    read_json,
    read_jsonl,
    sha256_file,
    sha256_text,
    write_json,
    write_jsonl,
)

HEX_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^LGP-RUN-\d{4}-\d{3,}$")
MOVING_REVISIONS = {"main", "master", "latest", "head"}
TERMINAL_RUN_STATUSES = ("completed", "failed", "incomplete", "excluded")


def _text(value, field, allow_empty=False):
    if not isinstance(value, str):
        raise ValidationError("must be a string", field)
    if not allow_empty and not value.strip():
        raise ValidationError("must not be empty", field)
    return value


def _number(value, field, minimum=None, nullable=False):
    if value is None and nullable:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("must be a number", field)
    if minimum is not None and value < minimum:
        raise ValidationError(f"must be at least {minimum}", field)
    return value


def _timestamp(value, field):
    _text(value, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(f"is not an ISO timestamp: {error}", field) from error
    if parsed.tzinfo is None:
        raise ValidationError("must include a timezone offset", field)
    return parsed


def _hash(value, field):
    if not isinstance(value, str) or not HEX_RE.match(value):
        raise ValidationError("must be a lowercase SHA-256 hex digest", field)
    return value


def _revision(value, field):
    _text(value, field)
    if value.strip().lower() in MOVING_REVISIONS:
        raise ValidationError("must be a pinned revision, not a moving branch", field)
    return value


@dataclass(frozen=True)
class CostRecord:
    kind: str
    amount: float | None
    currency: str | None
    approved_budget: float | None
    approval_reference: str | None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in COST_KINDS:
            raise ValidationError(f"must be one of {COST_KINDS}", "kind")
        _number(self.amount, "amount", 0, nullable=True)
        _number(self.approved_budget, "approved_budget", 0, nullable=True)
        if self.currency is not None:
            _text(self.currency, "currency")
        if self.approval_reference is not None:
            _text(self.approval_reference, "approval_reference")
        if not isinstance(self.details, Mapping):
            raise ValidationError("must be an object", "details")
        if self.kind in ("paid_api", "native_review"):
            if not self.currency:
                raise ValidationError("requires a currency", "currency")
            if self.approved_budget is None:
                raise ValidationError("requires an approved_budget", "approved_budget")
        if self.kind == "paid_api":
            required = {
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "unit_price",
                "total",
                "cap",
            }
            missing = sorted(required - set(self.details))
            if missing:
                raise ValidationError(f"paid_api cost is missing fields: {missing}", "details")
            if not self.approval_reference:
                raise ValidationError(
                    "paid_api cost requires approval_reference", "approval_reference"
                )
            _text(self.details["provider"], "details.provider")
            _text(self.details["model"], "details.model")
            for field_name in ("input_tokens", "output_tokens"):
                value = self.details[field_name]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValidationError(
                        "must be a non-negative integer", f"details.{field_name}"
                    )
            for field_name in ("unit_price", "total", "cap"):
                _number(self.details[field_name], f"details.{field_name}", 0)
        if self.kind == "native_review":
            required = {"reviewer_hours", "rate"}
            missing = sorted(required - set(self.details))
            if missing:
                raise ValidationError(f"native_review cost is missing fields: {missing}", "details")
            if not self.approval_reference:
                raise ValidationError(
                    "native_review cost requires approval_reference", "approval_reference"
                )
            _number(self.details["reviewer_hours"], "details.reviewer_hours", 0)
            _number(self.details["rate"], "details.rate", 0)

    def to_dict(self):
        return {
            "kind": self.kind,
            "amount": self.amount,
            "currency": self.currency,
            "approved_budget": self.approved_budget,
            "approval_reference": self.approval_reference,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise ValidationError("cost must be an object", "cost")
        allowed = {
            "kind",
            "amount",
            "currency",
            "approved_budget",
            "approval_reference",
            "details",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValidationError(f"cost has unknown fields: {unknown}", "cost")
        return cls(
            kind=value.get("kind"),
            amount=value.get("amount"),
            currency=value.get("currency"),
            approved_budget=value.get("approved_budget"),
            approval_reference=value.get("approval_reference"),
            details=value.get("details") or {},
        )


@dataclass(frozen=True)
class RawResponse:
    run_id: str
    item_id: str
    turn_index: int
    sample_index: int
    model_id: str
    model_revision: str
    timestamp: str
    raw_response: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float | None
    error: Any

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not RUN_ID_RE.match(self.run_id):
            raise ValidationError("must match LGP-RUN-<year>-<number>", "run_id")
        if not isinstance(self.item_id, str) or not ITEM_ID_RE.match(self.item_id):
            raise ValidationError("must match LGP-BENCH-<CATEGORY>-<NNN>", "item_id")
        for field_name in ("turn_index", "sample_index"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError("must be a non-negative integer", field_name)
        _text(self.model_id, "model_id")
        _revision(self.model_revision, "model_revision")
        _timestamp(self.timestamp, "timestamp")
        if not isinstance(self.raw_response, str):
            raise ValidationError("must be a string", "raw_response")
        if self.finish_reason is not None:
            _text(self.finish_reason, "finish_reason")
        for field_name in ("prompt_tokens", "completion_tokens"):
            value = getattr(self, field_name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError("must be a non-negative integer or null", field_name)
        _number(self.latency_ms, "latency_ms", 0, nullable=True)
        if self.error is not None and (
            not isinstance(self.error, (str, Mapping)) or not self.error
        ):
            raise ValidationError(
                "must be a non-empty string, object, or null", "error"
            )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise ValidationError("raw response must be an object")
        try:
            return cls(**value)
        except TypeError as error:
            raise ValidationError(f"raw response has unexpected fields: {error}") from error


@dataclass
class RunManifest:
    run_id: str
    benchmark_version: str
    item_file_sha256: str
    model_id: str
    model_revision: str
    tokenizer_id: str
    tokenizer_revision: str
    chat_template: str
    quantization: str
    dtype: str
    device: str
    framework_versions: Mapping[str, str]
    decoding: Mapping[str, Any]
    samples_per_item: int
    batch_size: int
    hardware: Any
    operating_system: str
    started_at: str
    finished_at: str | None
    wall_clock_seconds: float | None
    cost: CostRecord
    approval_reference: str
    raw_response_path: str
    operator: str
    base_model_id: str | None = None
    base_model_revision: str | None = None
    adapter_id: str | None = None
    adapter_revision: str | None = None
    system_prompt: str | None = None
    seed: int | None = None
    peak_memory: str | None = None
    run_status: str = "planned"
    errors: tuple[Any, ...] = field(default_factory=tuple)
    exclusions: tuple[Any, ...] = field(default_factory=tuple)
    expected_item_count: int | None = None
    completed_item_count: int = 0

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not isinstance(self.run_id, str) or not RUN_ID_RE.match(self.run_id):
            raise ValidationError("must match LGP-RUN-<year>-<number>", "run_id")
        validate_version(self.benchmark_version)
        _hash(self.item_file_sha256, "item_file_sha256")
        _text(self.model_id, "model_id")
        _revision(self.model_revision, "model_revision")
        _text(self.tokenizer_id, "tokenizer_id")
        _revision(self.tokenizer_revision, "tokenizer_revision")
        _text(self.chat_template, "chat_template")
        adapter_fields = (
            self.base_model_id,
            self.base_model_revision,
            self.adapter_id,
            self.adapter_revision,
        )
        if any(adapter_fields):
            _text(self.base_model_id, "base_model_id")
            _revision(self.base_model_revision, "base_model_revision")
            _text(self.adapter_id, "adapter_id")
            _revision(self.adapter_revision, "adapter_revision")
        for field_name in ("quantization", "dtype", "device", "operating_system", "operator"):
            _text(getattr(self, field_name), field_name)
        if not isinstance(self.framework_versions, Mapping) or not self.framework_versions:
            raise ValidationError("must be a non-empty object", "framework_versions")
        for key, value in self.framework_versions.items():
            _text(key, "framework_versions")
            _text(value, f"framework_versions.{key}")
        if not isinstance(self.decoding, Mapping):
            raise ValidationError("must be an object", "decoding")
        required_decoding = {
            "temperature",
            "top_p",
            "top_k",
            "max_new_tokens",
            "stop_sequences",
            "repetition_penalty",
        }
        missing = sorted(required_decoding - set(self.decoding))
        if missing:
            raise ValidationError(f"decoding is missing fields: {missing}", "decoding")
        _number(self.decoding["temperature"], "decoding.temperature", 0)
        _number(self.decoding["top_p"], "decoding.top_p", 0)
        if not 0 <= self.decoding["top_p"] <= 1:
            raise ValidationError("must be between 0 and 1", "decoding.top_p")
        if isinstance(self.decoding["top_k"], bool) or not isinstance(self.decoding["top_k"], int):
            raise ValidationError("must be an integer", "decoding.top_k")
        if isinstance(self.decoding["max_new_tokens"], bool) or not isinstance(
            self.decoding["max_new_tokens"], int
        ) or self.decoding["max_new_tokens"] < 1:
            raise ValidationError("must be a positive integer", "decoding.max_new_tokens")
        if not isinstance(self.decoding["stop_sequences"], (list, tuple)):
            raise ValidationError("must be a list", "decoding.stop_sequences")
        _number(self.decoding["repetition_penalty"], "decoding.repetition_penalty", 0)
        for field_name in ("samples_per_item", "batch_size"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError("must be a positive integer", field_name)
        if not isinstance(self.hardware, (str, Mapping)) or not self.hardware:
            raise ValidationError("must be a non-empty string or object", "hardware")
        _timestamp(self.started_at, "started_at")
        if self.finished_at is not None:
            finished = _timestamp(self.finished_at, "finished_at")
            started = _timestamp(self.started_at, "started_at")
            if finished < started:
                raise ValidationError("must not be earlier than started_at", "finished_at")
        _number(self.wall_clock_seconds, "wall_clock_seconds", 0, nullable=True)
        if not isinstance(self.cost, CostRecord):
            raise ValidationError("must be a CostRecord", "cost")
        _text(self.approval_reference, "approval_reference")
        _text(self.raw_response_path, "raw_response_path")
        _text(self.operator, "operator")
        if self.system_prompt is not None:
            _text(self.system_prompt, "system_prompt", allow_empty=True)
        if self.seed is not None:
            if isinstance(self.seed, bool) or not isinstance(self.seed, int):
                raise ValidationError("must be an integer or null", "seed")
        if self.peak_memory is not None:
            _text(self.peak_memory, "peak_memory")
        if self.base_model_id is not None:
            _text(self.base_model_id, "base_model_id")
        if self.base_model_revision is not None:
            _revision(self.base_model_revision, "base_model_revision")
        if self.adapter_id is not None:
            _text(self.adapter_id, "adapter_id")
        if self.adapter_revision is not None:
            _revision(self.adapter_revision, "adapter_revision")
        if self.adapter_id and not (self.base_model_id and self.base_model_revision):
            raise ValidationError(
                "an adapter run must record base_model_id and base_model_revision",
                "adapter_id",
            )
        if self.run_status not in RUN_STATUSES:
            raise ValidationError(f"must be one of {RUN_STATUSES}", "run_status")
        if self.expected_item_count is not None:
            if isinstance(self.expected_item_count, bool) or not isinstance(
                self.expected_item_count, int
            ) or self.expected_item_count < 0:
                raise ValidationError("must be a non-negative integer", "expected_item_count")
        if isinstance(self.completed_item_count, bool) or not isinstance(
            self.completed_item_count, int
        ) or self.completed_item_count < 0:
            raise ValidationError("must be a non-negative integer", "completed_item_count")
        if not isinstance(self.errors, tuple) or not isinstance(self.exclusions, tuple):
            raise ValidationError("errors and exclusions must be tuples", "errors")
        for error in self.errors:
            if not isinstance(error, (str, Mapping)) or not error:
                raise ValidationError(
                    "each error must be a non-empty string or object", "errors"
                )
        for exclusion in self.exclusions:
            if not isinstance(exclusion, (str, Mapping)):
                raise ValidationError("each exclusion must be a string or object", "exclusions")
            if isinstance(exclusion, Mapping) and not str(exclusion.get("reason") or "").strip():
                raise ValidationError("each exclusion object needs a reason", "exclusions")

        if self.run_status == "completed":
            if self.finished_at is None or self.wall_clock_seconds is None:
                raise ValidationError(
                    "completed runs require finished_at and wall_clock_seconds", "run_status"
                )
            if self.errors:
                raise ValidationError("completed runs must not contain errors", "errors")
            if self.expected_item_count is None:
                raise ValidationError(
                    "completed runs require expected_item_count", "expected_item_count"
                )
            if self.completed_item_count != self.expected_item_count:
                raise ValidationError(
                    "completed run is missing expected items", "completed_item_count"
                )
        if self.run_status == "failed" and not self.errors:
            raise ValidationError("failed runs require at least one error", "errors")
        if self.run_status == "excluded" and not self.exclusions:
            raise ValidationError("excluded runs require a recorded reason", "exclusions")
        return True

    def to_dict(self):
        value = asdict(self)
        value["cost"] = self.cost.to_dict()
        value["errors"] = list(self.errors)
        value["exclusions"] = list(self.exclusions)
        return value

    def manifest_sha256(self):
        return sha256_text(canonical_json(self.to_dict()))

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise ValidationError("run manifest must be an object")
        data = dict(value)
        data["cost"] = CostRecord.from_dict(data.get("cost"))
        errors = data.get("errors") or ()
        exclusions = data.get("exclusions") or ()
        if not isinstance(errors, (list, tuple)):
            raise ValidationError("errors must be a list", "errors")
        if not isinstance(exclusions, (list, tuple)):
            raise ValidationError("exclusions must be a list", "exclusions")
        data["errors"] = tuple(errors)
        data["exclusions"] = tuple(exclusions)
        try:
            return cls(**data)
        except TypeError as error:
            raise ValidationError(f"run manifest has unexpected fields: {error}") from error


class RunStore:
    """Local store for run manifests, raw responses, and response reviews."""

    def __init__(self, root):
        self.root = Path(root)

    def run_dir(self, run_id):
        if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
            raise ValidationError("must match LGP-RUN-<year>-<number>", "run_id")
        return self.root / run_id

    def manifest_path(self, run_id):
        return self.run_dir(run_id) / "run_manifest.json"

    def raw_path(self, run_id):
        return self.run_dir(run_id) / "raw_responses.jsonl"

    def review_path(self, run_id):
        return self.run_dir(run_id) / "scores" / "review_records.jsonl"

    def cost_path(self, run_id):
        return self.run_dir(run_id) / "costs.jsonl"

    def create_manifest(self, manifest):
        path = self.manifest_path(manifest.run_id)
        if path.exists():
            raise RunError(f"run_id already exists: {manifest.run_id}")
        return self.write_manifest(manifest)

    def write_manifest(self, manifest):
        manifest.validate()
        path = self.manifest_path(manifest.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, manifest.to_dict())
        return path

    def read_manifest(self, run_id):
        return RunManifest.from_dict(read_json(self.manifest_path(run_id)))

    def append_raw_response(self, response):
        manifest = self.read_manifest(response.run_id)
        if manifest.run_status in TERMINAL_RUN_STATUSES:
            raise RunError("cannot add raw responses to a finalized run")
        if response.model_id != manifest.model_id:
            raise RunError("raw response model_id does not match the run manifest")
        if response.model_revision != manifest.model_revision:
            raise RunError("raw response model_revision does not match the run manifest")
        path = self.raw_path(response.run_id)
        append_jsonl(path, response.to_dict())
        return path

    def read_raw_responses(self, run_id):
        return [RawResponse.from_dict(record) for record in read_jsonl(self.raw_path(run_id))]

    def write_reviews(self, run_id, records):
        path = self.review_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(path, [record.to_dict() if hasattr(record, "to_dict") else record for record in records])
        return path

    def read_reviews(self, run_id):
        return read_jsonl(self.review_path(run_id))

    def append_cost(self, run_id, cost):
        self.read_manifest(run_id)
        if not isinstance(cost, CostRecord):
            raise ValidationError("cost must be a CostRecord")
        path = self.cost_path(run_id)
        append_jsonl(path, cost.to_dict())
        return path

    def read_costs(self, run_id):
        return [CostRecord.from_dict(record) for record in read_jsonl(self.cost_path(run_id))]

    def _completed_item_count(self, run_id):
        path = self.raw_path(run_id)
        if not path.exists():
            return 0
        return len(
            {
                response.item_id
                for response in self.read_raw_responses(run_id)
                if response.error is None
            }
        )

    def _finish_metadata(self, manifest, finished_at):
        finished = finished_at or datetime.now(timezone.utc).isoformat()
        started = datetime.fromisoformat(manifest.started_at.replace("Z", "+00:00"))
        finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
        return finished, (finished_dt - started).total_seconds()

    def finalize(self, run_id, *, expected_item_count=None, finished_at=None):
        manifest = self.read_manifest(run_id)
        if manifest.run_status in TERMINAL_RUN_STATUSES:
            raise RunError("run is already finalized")
        raw_path = self.raw_path(run_id)
        responses = self.read_raw_responses(run_id) if raw_path.exists() else []
        completed = len(
            {response.item_id for response in responses if response.error is None}
        )
        response_errors = tuple(
            {
                "item_id": response.item_id,
                "turn_index": response.turn_index,
                "sample_index": response.sample_index,
                "message": str(response.error),
            }
            for response in responses
            if response.error is not None
        )
        expected = expected_item_count
        if expected is None:
            expected = manifest.expected_item_count
        if expected is None:
            raise RunError("expected_item_count is required to finalize a run")
        finished, wall_clock_seconds = self._finish_metadata(manifest, finished_at)
        manifest.finished_at = finished
        manifest.wall_clock_seconds = wall_clock_seconds
        manifest.expected_item_count = expected
        manifest.completed_item_count = completed
        manifest.errors = manifest.errors + response_errors
        if manifest.errors:
            manifest.run_status = "failed"
        elif completed < expected:
            manifest.run_status = "incomplete"
        else:
            manifest.run_status = "completed"
        manifest.validate()
        self.write_manifest(manifest)
        return manifest

    def mark_failed(self, run_id, error, *, finished_at=None):
        manifest = self.read_manifest(run_id)
        if manifest.run_status in TERMINAL_RUN_STATUSES:
            raise RunError("run is already finalized")
        manifest.errors = manifest.errors + (error,)
        finished, wall_clock_seconds = self._finish_metadata(manifest, finished_at)
        manifest.finished_at = finished
        manifest.wall_clock_seconds = wall_clock_seconds
        manifest.completed_item_count = self._completed_item_count(run_id)
        manifest.run_status = "failed"
        manifest.validate()
        self.write_manifest(manifest)
        return manifest

    def mark_incomplete(self, run_id, reason, *, finished_at=None):
        manifest = self.read_manifest(run_id)
        if manifest.run_status in TERMINAL_RUN_STATUSES:
            raise RunError("run is already finalized")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("incomplete runs require a reason", "reason")
        manifest.exclusions = manifest.exclusions + ({"reason": reason},)
        finished, wall_clock_seconds = self._finish_metadata(manifest, finished_at)
        manifest.finished_at = finished
        manifest.wall_clock_seconds = wall_clock_seconds
        manifest.completed_item_count = self._completed_item_count(run_id)
        manifest.run_status = "incomplete"
        manifest.validate()
        self.write_manifest(manifest)
        return manifest

    def verify_reproducibility(self, manifest, item_file_path):
        if sha256_file(item_file_path) != manifest.item_file_sha256:
            raise RunError("item file hash does not match the run manifest")
        if manifest.model_revision.strip().lower() in MOVING_REVISIONS:
            raise RunError("model revision is a moving reference")
        if manifest.tokenizer_revision.strip().lower() in MOVING_REVISIONS:
            raise RunError("tokenizer revision is a moving reference")
        if not manifest.raw_response_path:
            raise RunError("raw_response_path is missing")
        if self.raw_path(manifest.run_id).exists():
            for response in self.read_raw_responses(manifest.run_id):
                if response.model_id != manifest.model_id:
                    raise RunError("raw response model_id does not match the run manifest")
                if response.model_revision != manifest.model_revision:
                    raise RunError(
                        "raw response model_revision does not match the run manifest"
                    )
        return True
