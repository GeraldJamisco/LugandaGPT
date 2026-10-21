"""Benchmark versions, exclusions, and owner approval records.

An approved benchmark is never inferred from the presence of an item file.
It requires a manifest, a matching item-file hash, an owner approval record,
a native-review sign-off, and approved items.
"""

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from .constants import REVIEW_STATUSES
from .errors import ApprovalError, ValidationError, WorkflowError
from .item import (
    ITEM_ID_RE,
    validate_iso_date,
    validate_item_set,
    validate_version,
)
from .storage import (
    canonical_json,
    read_json,
    read_jsonl,
    sha256_file,
    sha256_text,
    write_json,
    write_jsonl,
)

APPROVED_VERSION_RE = re.compile(r"^\d+\.\d+$")
DRAFT_VERSION_RE = re.compile(r"^0\.\d+-draft$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")

EDITORIAL = "editorial"
MINOR = "minor"
MAJOR = "major"
CHANGE_CLASSES = (EDITORIAL, MINOR, MAJOR)


def _text(value, field, allow_empty=False):
    if not isinstance(value, str):
        raise ValidationError("must be a string", field)
    if not allow_empty and not value.strip():
        raise ValidationError("must not be empty", field)
    return value


def _item_ref(value, field):
    if not isinstance(value, str) or not ITEM_ID_RE.match(value):
        raise ValidationError("must match LGP-BENCH-<CATEGORY>-<NNN>", field)
    return value


def _hash(value, field):
    if not isinstance(value, str) or not HEX_RE.match(value):
        raise ValidationError("must be a lowercase SHA-256 hex digest", field)
    return value


@dataclass(frozen=True)
class NativeReviewSignoff:
    reviewer_panel: tuple[str, ...]
    calibration_date: str
    agreement_statistic: str
    items_reviewed: tuple[str, ...]
    signoff_date: str

    def __post_init__(self):
        if not isinstance(self.reviewer_panel, tuple) or len(self.reviewer_panel) < 2:
            raise ValidationError(
                "must name at least two distinct reviewers", "reviewer_panel"
            )
        if len(set(self.reviewer_panel)) != len(self.reviewer_panel):
            raise ValidationError("must not contain duplicate reviewers", "reviewer_panel")
        for reviewer_id in self.reviewer_panel:
            _text(reviewer_id, "reviewer_panel")
        validate_iso_date(self.calibration_date, "calibration_date")
        _text(self.agreement_statistic, "agreement_statistic")
        if not isinstance(self.items_reviewed, tuple) or not self.items_reviewed:
            raise ValidationError("must list reviewed items", "items_reviewed")
        if len(set(self.items_reviewed)) != len(self.items_reviewed):
            raise ValidationError("must not contain duplicate item IDs", "items_reviewed")
        for item_id in self.items_reviewed:
            _item_ref(item_id, "items_reviewed")
        validate_iso_date(self.signoff_date, "signoff_date")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ApprovalRecord:
    specification_version: str
    benchmark_version: str
    approved_by: str
    role: str
    date: str
    scope: str
    conditions: str
    item_file_sha256: str
    item_ids: tuple[str, ...]
    native_review_signoff: NativeReviewSignoff

    def __post_init__(self):
        _text(self.specification_version, "specification_version")
        validate_version(self.benchmark_version)
        if DRAFT_VERSION_RE.match(self.benchmark_version):
            raise ValidationError(
                "approval requires a non-draft benchmark version",
                "benchmark_version",
            )
        _text(self.approved_by, "approved_by")
        if self.role != "project_owner":
            raise ValidationError("approval role must be project_owner", "role")
        validate_iso_date(self.date, "date")
        _text(self.scope, "scope")
        if not isinstance(self.conditions, str):
            raise ValidationError("must be a string", "conditions")
        _hash(self.item_file_sha256, "item_file_sha256")
        if not isinstance(self.item_ids, tuple) or not self.item_ids:
            raise ValidationError("must list approved item IDs", "item_ids")
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValidationError("must not contain duplicate item IDs", "item_ids")
        for item_id in self.item_ids:
            _item_ref(item_id, "item_ids")
        if not isinstance(self.native_review_signoff, NativeReviewSignoff):
            raise ValidationError(
                "must be a NativeReviewSignoff", "native_review_signoff"
            )

    def to_dict(self):
        return {
            "specification_version": self.specification_version,
            "benchmark_version": self.benchmark_version,
            "approved_by": self.approved_by,
            "role": self.role,
            "date": self.date,
            "scope": self.scope,
            "conditions": self.conditions,
            "item_file_sha256": self.item_file_sha256,
            "item_ids": list(self.item_ids),
            "native_review_signoff": self.native_review_signoff.to_dict(),
        }


@dataclass(frozen=True)
class ExclusionRecord:
    exclusion_id: str
    item_id: str
    version: str
    date: str
    actor: str
    reason: str

    def __post_init__(self):
        _text(self.exclusion_id, "exclusion_id")
        _item_ref(self.item_id, "item_id")
        validate_version(self.version)
        validate_iso_date(self.date, "date")
        _text(self.actor, "actor")
        _text(self.reason, "reason")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class SourceException:
    item_id: str
    approved_by: str
    role: str
    date: str
    reason: str

    def __post_init__(self):
        _item_ref(self.item_id, "item_id")
        _text(self.approved_by, "approved_by")
        if self.role != "project_owner":
            raise ValidationError("source exception role must be project_owner", "role")
        validate_iso_date(self.date, "date")
        _text(self.reason, "reason")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkManifest:
    version: str
    date: str
    changelog: str
    item_file_sha256: str
    status: str
    approval: ApprovalRecord | None = None
    changed_items: tuple[str, ...] = ()
    parent_version: str | None = None

    def __post_init__(self):
        validate_version(self.version)
        validate_iso_date(self.date, "date")
        _text(self.changelog, "changelog")
        _hash(self.item_file_sha256, "item_file_sha256")
        if self.status not in ("draft", "approved"):
            raise ValidationError("must be draft or approved", "status")
        is_draft = bool(DRAFT_VERSION_RE.match(self.version))
        if self.status == "draft" and not is_draft:
            raise ValidationError("a draft manifest must use a draft version", "version")
        for item_id in self.changed_items:
            _item_ref(item_id, "changed_items")
        if self.parent_version is not None:
            validate_version(self.parent_version)

        if self.status == "approved":
            if is_draft:
                raise ApprovalError("an approved benchmark cannot use a draft version")
            if self.approval is None:
                raise ApprovalError("an approved manifest requires an ApprovalRecord")
            if self.approval.benchmark_version != self.version:
                raise ApprovalError("approval benchmark_version does not match manifest")
            if self.approval.item_file_sha256 != self.item_file_sha256:
                raise ApprovalError("approval item_file_sha256 does not match manifest")
        elif self.approval is not None:
            raise ApprovalError("a draft manifest must not carry an approval record")

    def to_dict(self):
        return {
            "version": self.version,
            "date": self.date,
            "changelog": self.changelog,
            "item_file_sha256": self.item_file_sha256,
            "status": self.status,
            "approval": self.approval.to_dict() if self.approval else None,
            "changed_items": list(self.changed_items),
            "parent_version": self.parent_version,
        }


def hash_items(items: Iterable[Mapping[str, Any]]):
    lines = [canonical_json(item) for item in items]
    return sha256_text("\n".join(lines) + ("\n" if lines else ""))


def load_item_file(
    path,
    *,
    expected_version=None,
    evidence_by_id=None,
    source_exceptions=None,
):
    items = read_jsonl(path)
    return validate_item_set(
        items,
        expected_version=expected_version,
        evidence_by_id=evidence_by_id,
        source_exceptions=source_exceptions,
    )


def write_item_file(
    path,
    items,
    *,
    expected_version=None,
    evidence_by_id=None,
    source_exceptions=None,
):
    validated = validate_item_set(
        items,
        expected_version=expected_version,
        evidence_by_id=evidence_by_id,
        source_exceptions=source_exceptions,
    )
    write_jsonl(path, validated)
    return sha256_file(path)


def build_manifest(
    items,
    *,
    version,
    date,
    changelog,
    status="draft",
    approval=None,
    changed_items=(),
    parent_version=None,
    evidence_by_id=None,
    source_exceptions=None,
):
    validated = validate_item_set(
        items,
        expected_version=version,
        evidence_by_id=evidence_by_id,
        source_exceptions=source_exceptions,
    )
    item_hash = hash_items(validated)
    manifest = BenchmarkManifest(
        version=version,
        date=date,
        changelog=changelog,
        item_file_sha256=item_hash,
        status=status,
        approval=approval,
        changed_items=tuple(changed_items),
        parent_version=parent_version,
    )
    if status == "approved":
        approved_ids = {item["id"] for item in validated if item["review_status"] == "approved"}
        all_ids = {item["id"] for item in validated}
        if approved_ids != all_ids:
            raise ApprovalError(
                "every item must have review_status approved before a benchmark is approved"
            )
        if set(approval.item_ids) != all_ids:
            raise ApprovalError("approval record must list exactly the benchmark item IDs")
        reviewed = set(approval.native_review_signoff.items_reviewed)
        if reviewed != all_ids:
            raise ApprovalError("native review sign-off must cover exactly the benchmark items")
    return manifest


def write_manifest(path, manifest):
    write_json(path, manifest.to_dict())


def read_manifest(path):
    value = read_json(path)
    if not isinstance(value, Mapping):
        raise ValidationError("manifest must be an object")
    allowed = {
        "version",
        "date",
        "changelog",
        "item_file_sha256",
        "status",
        "approval",
        "changed_items",
        "parent_version",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValidationError(f"manifest has unknown fields: {unknown}")
    changed_items = value.get("changed_items", ())
    if not isinstance(changed_items, (list, tuple)):
        raise ValidationError("manifest changed_items must be a list")
    try:
        approval_value = value.get("approval")
        approval = None
        if approval_value is not None:
            if not isinstance(approval_value, Mapping):
                raise ValidationError("manifest approval must be an object")
            signoff = approval_value.get("native_review_signoff") or {}
            if not isinstance(signoff, Mapping):
                raise ValidationError(
                    "manifest native_review_signoff must be an object"
                )
            item_ids = approval_value["item_ids"]
            panel = signoff["reviewer_panel"]
            reviewed = signoff["items_reviewed"]
            if not all(
                isinstance(value, (list, tuple)) for value in (item_ids, panel, reviewed)
            ):
                raise ValidationError(
                    "manifest approval item and reviewer fields must be lists"
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
                native_review_signoff=NativeReviewSignoff(
                    reviewer_panel=tuple(panel),
                    calibration_date=signoff["calibration_date"],
                    agreement_statistic=signoff["agreement_statistic"],
                    items_reviewed=tuple(reviewed),
                    signoff_date=signoff["signoff_date"],
                ),
            )
        return BenchmarkManifest(
            version=value["version"],
            date=value["date"],
            changelog=value["changelog"],
            item_file_sha256=value["item_file_sha256"],
            status=value["status"],
            approval=approval,
            changed_items=tuple(changed_items),
            parent_version=value.get("parent_version"),
        )
    except (KeyError, TypeError) as error:
        raise ValidationError(f"manifest is missing a required field: {error}") from error


def load_approved_benchmark(
    item_path,
    manifest_path,
    *,
    evidence_by_id=None,
    source_exceptions=None,
):
    """Load a benchmark only when its approval records match the item file."""
    manifest = read_manifest(manifest_path)
    if manifest.status != "approved" or manifest.approval is None:
        raise ApprovalError("benchmark manifest is not approved")
    items = load_item_file(
        item_path,
        expected_version=manifest.version,
        evidence_by_id=evidence_by_id,
        source_exceptions=source_exceptions,
    )
    actual_hash = sha256_file(item_path)
    if actual_hash != manifest.item_file_sha256:
        raise ApprovalError("item file hash does not match the approved manifest")
    if manifest.approval.item_file_sha256 != actual_hash:
        raise ApprovalError("approval hash does not match the item file")
    item_ids = {item["id"] for item in items}
    if set(manifest.approval.item_ids) != item_ids:
        raise ApprovalError("approval record does not cover exactly the item file")
    if any(item["review_status"] != "approved" for item in items):
        raise ApprovalError("approved benchmark contains an item that is not approved")
    if set(manifest.approval.native_review_signoff.items_reviewed) != item_ids:
        raise ApprovalError("native review sign-off does not cover exactly the item file")
    return {"manifest": manifest, "items": items}


def compare_versions(old_items, new_items):
    old_by_id = {item["id"]: item for item in old_items}
    new_by_id = {item["id"]: item for item in new_items}
    old_ids = set(old_by_id)
    new_ids = set(new_by_id)
    changed = sorted(
        item_id
        for item_id in old_ids & new_ids
        if canonical_json(old_by_id[item_id]) != canonical_json(new_by_id[item_id])
    )
    return {
        "added": sorted(new_ids - old_ids),
        "removed": sorted(old_ids - new_ids),
        "changed": changed,
        "unchanged": sorted((old_ids & new_ids) - set(changed)),
    }


def classify_change(
    old_items,
    new_items,
    *,
    category_definition_changed=False,
    dimension_changed=False,
    scale_changed=False,
    applicability_changed=False,
    allocation_changed=False,
    scoring_rules_changed=False,
    composite_added=False,
):
    if any(
        (
            category_definition_changed,
            dimension_changed,
            scale_changed,
            applicability_changed,
            allocation_changed,
            scoring_rules_changed,
            composite_added,
        )
    ):
        return MAJOR
    diff = compare_versions(old_items, new_items)
    if diff["added"] or diff["removed"] or diff["changed"]:
        return MINOR
    return EDITORIAL


def next_version(current, change_class):
    validate_version(current)
    if change_class not in CHANGE_CLASSES:
        raise ValidationError(f"must be one of {CHANGE_CLASSES}", "change_class")
    if change_class == EDITORIAL:
        return current
    is_draft = bool(DRAFT_VERSION_RE.match(current))
    major, minor = (int(part) for part in current.split("-")[0].split("."))
    if is_draft:
        # Pre-approval versions stay in the 0.x-draft series.
        return f"0.{minor + 1}-draft"
    if change_class == MINOR:
        return f"{major}.{minor + 1}"
    return f"{major + 1}.0"


def check_version_update(
    previous_manifest,
    old_items,
    new_items,
    new_version,
    change_class,
    **change_flags,
):
    """Check a proposed edit against the previous manifest and version rules."""
    old_items = list(old_items)
    new_items = list(new_items)
    if hash_items(old_items) != previous_manifest.item_file_sha256:
        raise WorkflowError("old item set does not match the previous manifest hash")
    diff = compare_versions(old_items, new_items)
    changed = bool(diff["added"] or diff["removed"] or diff["changed"])
    if new_version == previous_manifest.version:
        if previous_manifest.status == "approved" and changed:
            raise WorkflowError(
                "an approved item file cannot change without a new version"
            )
        return True
    assert_version_change_allowed(previous_manifest.version, new_version, change_class)
    expected = classify_change(old_items, new_items, **change_flags)
    if expected != change_class:
        raise WorkflowError(
            f"change is classified as {expected}, not the proposed {change_class}"
        )
    return True


def assert_version_change_allowed(current, new, change_class):
    validate_version(current)
    validate_version(new)
    if change_class not in CHANGE_CLASSES:
        raise ValidationError(f"must be one of {CHANGE_CLASSES}", "change_class")
    if change_class == EDITORIAL:
        if new != current and not _later_version(new, current):
            raise WorkflowError("an editorial change must keep the version or create a later version")
        return True
    if not _later_version(new, current):
        raise WorkflowError("the new version must be later than the current version")
    if DRAFT_VERSION_RE.match(current):
        if not DRAFT_VERSION_RE.match(new):
            raise WorkflowError("a draft benchmark must advance to another draft version")
        return True
    current_major, current_minor = (int(part) for part in current.split("."))
    new_major, new_minor = (int(part) for part in new.split("."))
    if change_class == MINOR:
        if new_major != current_major or new_minor <= current_minor:
            raise WorkflowError("a minor change requires the same major and a higher minor")
    elif new_major <= current_major:
        raise WorkflowError("a major change requires a higher major version")
    return True


def _later_version(new, current):
    new_base = new.split("-")[0]
    current_base = current.split("-")[0]
    new_major, new_minor = (int(part) for part in new_base.split("."))
    current_major, current_minor = (int(part) for part in current_base.split("."))
    return (new_major, new_minor) > (current_major, current_minor)
