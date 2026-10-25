"""Translation, review, dataset-preparation, and export rules."""

import csv
import io
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path

from training.constants import CAPABILITIES_REQUIRING_REFERENCE, VALIDATION_CHECKS
from training.pilot import validate_pilot_record
from training.storage import atomic_write_text, sha256_text, write_json, write_jsonl

from .db import get_item, get_user, item_source, record_audit, utc_now
from .reward_rules import COMPLETED_REVIEW_CENTS, TRANSLATION_APPROVAL_CENTS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "data" / "studio" / "exports"
TRANSLATION_STATUSES = (
    "not_started",
    "in_progress",
    "ready_for_review",
    "needs_revision",
    "under_dispute",
    "reviewed",
)
REVIEW_DECISIONS = ("approved", "needs_revision", "cannot_assess")
UNRESOLVED_MARKERS = ("pending", "tbd", "todo", "unresolved", "needs review")


class WorkflowError(ValueError):
    def __init__(self, message, errors=None):
        self.errors = list(errors or [])
        super().__init__(message)


def _is_unresolved(value):
    if not isinstance(value, str):
        return True
    lowered = value.strip().casefold()
    return not lowered or any(marker in lowered for marker in UNRESOLVED_MARKERS)


def get_translation(connection, item_id):
    return connection.execute(
        "SELECT * FROM translations WHERE item_id = ?", (item_id,)
    ).fetchone()


def get_training_metadata(connection, item_id):
    return connection.execute(
        "SELECT * FROM training_metadata WHERE item_id = ?", (item_id,)
    ).fetchone()


def training_metadata_view(connection, item_id):
    row = get_training_metadata(connection, item_id)
    if row:
        return dict(row)
    return {
        "item_id": item_id,
        "licence": "",
        "licence_status": "unresolved",
        "consent_ref": "",
        "consent_status": "not_recorded",
        "pii_check": "needs_review",
        "contamination_notes": "",
        "validation_json": "{}",
        "dataset_status": "not_ready",
        "approved_by": None,
        "approved_at": None,
        "updated_at": None,
    }


def validation_values(metadata):
    try:
        values = json.loads(metadata["validation_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return {name: bool(values.get(name)) for name in VALIDATION_CHECKS}


def reviews_for_version(connection, item_id, version):
    return connection.execute(
        """
        SELECT r.*, u.display_name AS reviewer_name, u.public_id AS reviewer_public_id
        FROM reviews r
        JOIN users u ON u.id = r.reviewer_id
        WHERE r.item_id = ? AND r.translation_version = ?
        ORDER BY r.created_at, r.id
        """,
        (item_id, version),
    ).fetchall()


def review_history(connection, item_id):
    return connection.execute(
        """
        SELECT r.*, u.display_name AS reviewer_name, u.public_id AS reviewer_public_id
        FROM reviews r
        JOIN users u ON u.id = r.reviewer_id
        WHERE r.item_id = ?
        ORDER BY r.translation_version, r.created_at, r.id
        """,
        (item_id,),
    ).fetchall()


def version_history(connection, item_id):
    return connection.execute(
        """
        SELECT v.*, u.display_name AS translator_name, u.public_id AS translator_public_id
        FROM translation_versions v
        JOIN users u ON u.id = v.translator_id
        WHERE v.item_id = ?
        ORDER BY v.version DESC
        """,
        (item_id,),
    ).fetchall()


def resolution_history(connection, item_id):
    return connection.execute(
        """
        SELECT x.*, u.display_name AS admin_name, u.public_id AS admin_public_id
        FROM resolutions x
        JOIN users u ON u.id = x.admin_id
        WHERE x.item_id = ?
        ORDER BY x.created_at, x.id
        """,
        (item_id,),
    ).fetchall()


def assignments_for_item(connection, item_id):
    return connection.execute(
        """
        SELECT a.*, u.display_name, u.public_id, u.role
        FROM assignments a
        JOIN users u ON u.id = a.user_id
        WHERE a.item_id = ?
        ORDER BY a.assignment_type, u.display_name
        """,
        (item_id,),
    ).fetchall()


def is_assigned(connection, item_id, user_id, assignment_type):
    return bool(
        connection.execute(
            """
            SELECT 1 FROM assignments
            WHERE item_id = ? AND user_id = ? AND assignment_type = ?
            """,
            (item_id, user_id, assignment_type),
        ).fetchone()
    )


def _source_turns(source):
    return list(source.get("conversation_turns") or [])


def _load_turns(raw, expected_count):
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError as error:
        raise WorkflowError("The saved conversation turns are not readable.", [str(error)])
    if not isinstance(value, list):
        raise WorkflowError("The saved conversation turns are not a list.")
    if len(value) != expected_count:
        raise WorkflowError("The conversation turns do not match the source example.")
    return [str(item) for item in value]


def translation_view(connection, item_id):
    translation = get_translation(connection, item_id)
    if not translation:
        return None
    data = dict(translation)
    source = item_source(get_item(connection, item_id))
    data["turns"] = _load_turns(translation["turns_lg"], len(_source_turns(source)))
    return data


def _validate_translation_fields(
    source, context_lg, turns_lg, prompt_lg, response_lg, notes, require_complete
):
    errors = []
    source_turns = _source_turns(source)
    if len(turns_lg) != len(source_turns):
        errors.append("Every earlier conversation turn needs a Luganda translation.")
    if require_complete:
        if source.get("source_context") and not context_lg.strip():
            errors.append("Translate the background passage before saving.")
        for index, value in enumerate(turns_lg):
            if not str(value).strip():
                errors.append(f"Earlier turn {index + 1} needs a Luganda translation.")
        has_source_prompt = bool((source.get("source_prompt") or "").strip())
        has_expected_response = bool(source.get("expected_response_criteria"))
        if has_source_prompt and not prompt_lg.strip():
            errors.append("Translate the English user message or instruction before submitting.")
        if has_expected_response and not response_lg.strip():
            errors.append("Write the Luganda response.")
    if len(notes) > 5000:
        errors.append("Translation notes must be at most 5,000 characters.")
    if errors:
        raise WorkflowError("Please complete the missing fields.", errors)


def save_translation(
    connection,
    item_id,
    translator_id,
    context_lg,
    turns_lg,
    prompt_lg,
    response_lg,
    notes,
    submit=False,
):
    item = get_item(connection, item_id)
    if not item:
        raise WorkflowError("Example not found.")
    if not is_assigned(connection, item_id, translator_id, "translation"):
        raise WorkflowError("You are not assigned to translate this example.")
    source = item_source(item)
    turns = [str(value) for value in (turns_lg or [])]
    _validate_translation_fields(
        source,
        context_lg or "",
        turns,
        prompt_lg or "",
        response_lg or "",
        notes or "",
        require_complete=submit,
    )
    existing = get_translation(connection, item_id)
    metadata = get_training_metadata(connection, item_id)
    if metadata and metadata["dataset_status"] == "approved_for_dataset":
        raise WorkflowError(
            "This item is approved for dataset preparation. Ask an administrator to revoke that approval before editing."
        )
    if existing:
        if existing["translator_id"] != translator_id:
            raise WorkflowError("This translation belongs to another translator.")
        if existing["status"] in ("ready_for_review", "under_dispute", "reviewed"):
            raise WorkflowError(
                "This translation is locked because it is already submitted or reviewed."
            )
    now = utc_now()
    if existing:
        previous_status = existing["status"]
        version = existing["version"]
        submitted_at = existing["submitted_at"]
        created_at = existing["created_at"]
    else:
        previous_status = "not_started"
        version = 1
        submitted_at = None
        created_at = now
    has_content = bool(
        (context_lg or "").strip()
        or any(str(value).strip() for value in turns)
        or (prompt_lg or "").strip()
        or (response_lg or "").strip()
        or (notes or "").strip()
    )
    next_status = "in_progress" if has_content else (
        existing["status"] if existing else "not_started"
    )
    if submit:
        if previous_status == "needs_revision" or submitted_at:
            version += 1
        next_status = "ready_for_review"
        submitted_at = now
    values = (
        translator_id,
        context_lg or "",
        json.dumps(turns, ensure_ascii=False),
        prompt_lg or "",
        response_lg or "",
        notes or "",
        next_status,
        version,
        0,
        "",
        created_at,
        now,
        submitted_at,
        item_id,
    )
    if existing:
        connection.execute(
            """
            UPDATE translations
            SET translator_id = ?, context_lg = ?, turns_lg = ?, prompt_lg = ?,
                response_lg = ?, notes = ?, status = ?, version = ?,
                resolution_required = ?, resolution_reason = ?,
                created_at = ?, updated_at = ?, submitted_at = ?
            WHERE item_id = ?
            """,
            values,
        )
    else:
        connection.execute(
            """
            INSERT INTO translations(
                translator_id, context_lg, turns_lg, prompt_lg, response_lg,
                notes, status, version, resolution_required, resolution_reason,
                created_at, updated_at, submitted_at, item_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    if submit:
        connection.execute(
            """
            INSERT INTO translation_versions(
                item_id, version, translator_id, context_lg, turns_lg,
                prompt_lg, response_lg, notes, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                version,
                translator_id,
                context_lg or "",
                json.dumps(turns, ensure_ascii=False),
                prompt_lg or "",
                response_lg or "",
                notes or "",
                now,
            ),
        )
    record_audit(
        connection,
        translator_id,
        "translation_submitted" if submit else "translation_saved",
        "item",
        item_id,
        {"status": next_status, "version": version},
    )
    connection.commit()
    return get_translation(connection, item_id)


def _refresh_review_state(connection, item_id, version):
    reviews = reviews_for_version(connection, item_id, version)
    decisions = {row["decision"] for row in reviews}
    status = "ready_for_review"
    resolution_required = 0
    reason = ""
    if "approved" in decisions and "needs_revision" in decisions:
        status = "under_dispute"
        resolution_required = 1
        reason = "Two reviewers disagree. An administrator must resolve the record."
    elif "needs_revision" in decisions:
        status = "needs_revision"
    elif "approved" in decisions:
        status = "reviewed"
    connection.execute(
        """
        UPDATE translations
        SET status = ?, resolution_required = ?, resolution_reason = ?, updated_at = ?
        WHERE item_id = ? AND version = ?
        """,
        (status, resolution_required, reason, utc_now(), item_id, version),
    )
    return status


def submit_review(
    connection,
    item_id,
    reviewer_id,
    decision,
    comments,
    suggested_correction="",
):
    if decision not in REVIEW_DECISIONS:
        raise WorkflowError("Choose a valid review decision.")
    if not is_assigned(connection, item_id, reviewer_id, "review"):
        raise WorkflowError("You are not assigned to review this example.")
    translation = get_translation(connection, item_id)
    if not translation:
        raise WorkflowError("There is no translation to review.")
    if reviewer_id == translation["translator_id"]:
        raise WorkflowError("You cannot review your own translation.")
    if translation["status"] not in ("ready_for_review", "reviewed"):
        raise WorkflowError("This translation is not waiting for review.")
    metadata = get_training_metadata(connection, item_id)
    if metadata and metadata["dataset_status"] == "approved_for_dataset":
        raise WorkflowError(
            "This item is already approved for dataset preparation. Ask an administrator to revoke that approval before adding a review."
        )
    comments = (comments or "").strip()
    suggested_correction = (suggested_correction or "").strip()
    if decision in ("needs_revision", "cannot_assess") and not comments:
        raise WorkflowError("Explain your decision in the comments field.")
    if decision == "approved":
        item = get_item(connection, item_id)
        source = item_source(item)
        if source.get("source_context") and not (translation["context_lg"] or "").strip():
            raise WorkflowError(
                "You cannot approve this translation because the required background passage is missing. Request revision."
            )
        has_source_prompt = bool((source.get("source_prompt") or "").strip())
        has_expected_response = bool(source.get("expected_response_criteria"))
        if has_source_prompt and not (translation["prompt_lg"] or "").strip():
            raise WorkflowError(
                "You cannot approve this translation because the source user message has not been translated. Request revision."
            )
        if has_expected_response and not (translation["response_lg"] or "").strip():
            raise WorkflowError(
                "You cannot approve this translation because the expected assistant reply is missing. Request revision."
            )
    if len(comments) > 5000 or len(suggested_correction) > 10000:
        raise WorkflowError("Review comments are too long.")
    version = translation["version"]
    if connection.execute(
        """
        SELECT 1 FROM reviews
        WHERE item_id = ? AND reviewer_id = ? AND translation_version = ?
        """,
        (item_id, reviewer_id, version),
    ).fetchone():
        raise WorkflowError("You have already reviewed this version.")
    now = utc_now()
    connection.execute(
        """
        INSERT INTO reviews(
            item_id, reviewer_id, translation_version, decision,
            comments, suggested_correction, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (item_id, reviewer_id, version, decision, comments, suggested_correction, now),
    )
    review_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    record_reward_earning(
        connection, reviewer_id, "reviewer", "review", item_id, version, now, review_id=review_id
    )
    status = _refresh_review_state(connection, item_id, version)
    if status == "reviewed" and is_reward_eligible(connection, item_id):
        record_reward_earning(
            connection, translation["translator_id"], "translator", "translation", item_id, version, now
        )
    record_audit(
        connection,
        reviewer_id,
        "review_submitted",
        "item",
        item_id,
        {"decision": decision, "version": version, "status": status},
    )
    connection.commit()
    return get_translation(connection, item_id), status


def resolve_dispute(connection, item_id, admin_id, decision, notes):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can resolve a disagreement.")
    if decision not in ("approved", "needs_revision"):
        raise WorkflowError("Choose approved or needs revision.")
    notes = (notes or "").strip()
    if not notes:
        raise WorkflowError("Explain the resolution.")
    translation = get_translation(connection, item_id)
    if not translation or not translation["resolution_required"]:
        raise WorkflowError("This item does not need a disagreement resolution.")
    now = utc_now()
    connection.execute(
        """
        INSERT INTO resolutions(item_id, translation_version, admin_id, decision, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, translation["version"], admin_id, decision, notes, now),
    )
    status = "reviewed" if decision == "approved" else "needs_revision"
    connection.execute(
        """
        UPDATE translations
        SET status = ?, resolution_required = 0, resolution_reason = '', updated_at = ?
        WHERE item_id = ?
        """,
        (status, now, item_id),
    )
    if status == "reviewed" and is_reward_eligible(connection, item_id):
        record_reward_earning(
            connection,
            translation["translator_id"],
            "translator",
            "translation",
            item_id,
            translation["version"],
            now,
        )
    record_audit(
        connection,
        admin_id,
        "disagreement_resolved",
        "item",
        item_id,
        {"decision": decision, "version": translation["version"]},
    )
    connection.commit()
    return status


def update_training_metadata(connection, item_id, admin_id, values):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can update dataset preparation fields.")
    item = get_item(connection, item_id)
    if not item:
        raise WorkflowError("Example not found.")
    pii_check = values.get("pii_check", "needs_review")
    if pii_check not in ("none", "redacted", "needs_review"):
        raise WorkflowError("Choose a valid privacy check result.")
    licence_status = values.get("licence_status", "unresolved")
    if licence_status not in ("unresolved", "recorded"):
        raise WorkflowError("Choose a valid licence status.")
    consent_status = values.get("consent_status", "not_recorded")
    if consent_status not in ("not_recorded", "owner_reported", "recorded"):
        raise WorkflowError("Choose a valid collaboration and consent status.")
    licence = (values.get("licence") or "").strip()
    consent_ref = (values.get("consent_ref") or "").strip()
    if licence_status == "recorded" and _is_unresolved(licence):
        raise WorkflowError("Record the licence reference before marking the licence as recorded.")
    if consent_status == "recorded" and _is_unresolved(consent_ref):
        raise WorkflowError("Record the consent reference before marking consent as recorded.")
    validation = {name: bool(values.get(f"validation_{name}")) for name in VALIDATION_CHECKS}
    now = utc_now()
    connection.execute(
        """
        INSERT INTO training_metadata(
            item_id, licence, licence_status, consent_ref, consent_status,
            pii_check, contamination_notes, validation_json, dataset_status,
            approved_by, approved_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'not_ready', NULL, NULL, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            licence = excluded.licence,
            licence_status = excluded.licence_status,
            consent_ref = excluded.consent_ref,
            consent_status = excluded.consent_status,
            pii_check = excluded.pii_check,
            contamination_notes = excluded.contamination_notes,
            validation_json = excluded.validation_json,
            updated_at = excluded.updated_at
        """,
        (
            item_id,
            licence,
            licence_status,
            consent_ref,
            consent_status,
            pii_check,
            (values.get("contamination_notes") or "").strip(),
            json.dumps(validation, sort_keys=True),
            now,
        ),
    )
    record_audit(
        connection,
        admin_id,
        "training_metadata_updated",
        "item",
        item_id,
        {
            "pii_check": pii_check,
            "licence_status": licence_status,
            "consent_status": consent_status,
        },
    )
    connection.commit()


def _approved_reviews(connection, item_id, version):
    return [
        row
        for row in reviews_for_version(connection, item_id, version)
        if row["decision"] == "approved"
    ]


def _dataset_blockers(connection, item_id, source, translation, metadata):
    blockers = []
    if source["collection"] != "pilot":
        blockers.append("Evaluation items cannot be approved for training dataset preparation.")
        return blockers
    if not translation:
        blockers.append("No translation exists.")
        return blockers
    if source.get("source_context") and not (translation["context_lg"] or "").strip():
        blockers.append("The required background passage is missing from the Luganda translation.")
    has_source_prompt = bool((source.get("source_prompt") or "").strip())
    has_expected_response = bool(source.get("expected_response_criteria"))
    if has_source_prompt and not (translation["prompt_lg"] or "").strip():
        blockers.append("The source user message in Luganda is missing.")
    if has_expected_response and not (translation["response_lg"] or "").strip():
        blockers.append("The assistant reply in Luganda is missing.")
    if translation["status"] != "reviewed":
        blockers.append("The translation is not in the reviewed state.")
    if translation["resolution_required"]:
        blockers.append("A reviewer disagreement still needs an owner resolution.")
    reviews = reviews_for_version(connection, item_id, translation["version"])
    resolution = connection.execute(
        """
        SELECT decision FROM resolutions
        WHERE item_id = ? AND translation_version = ?
        ORDER BY created_at DESC, id DESC LIMIT 1
        """,
        (item_id, translation["version"]),
    ).fetchone()
    resolved_approved = bool(resolution and resolution["decision"] == "approved")
    approved = [row for row in reviews if row["decision"] == "approved"]
    if not approved and not resolved_approved:
        blockers.append("At least one reviewer must approve the current translation version.")
    if any(row["decision"] == "needs_revision" for row in reviews) and not resolved_approved:
        blockers.append("A reviewer requested revision for the current version.")
    assigned_reviewers = {
        row["user_id"]
        for row in connection.execute(
            "SELECT user_id FROM assignments WHERE item_id = ? AND assignment_type = 'review'",
            (item_id,),
        ).fetchall()
    }
    submitted_reviewers = {row["reviewer_id"] for row in reviews}
    if assigned_reviewers - submitted_reviewers:
        blockers.append("An assigned reviewer has not submitted a review for the current version.")
    if not metadata:
        blockers.append("Dataset preparation fields are not recorded.")
        return blockers
    if metadata["licence_status"] != "recorded":
        blockers.append("Licence status is not recorded.")
    if metadata["consent_status"] != "recorded":
        blockers.append("Collaboration and consent status is not recorded.")
    if _is_unresolved(metadata["licence"]):
        blockers.append("Licence reference is unresolved.")
    if _is_unresolved(metadata["consent_ref"]):
        blockers.append("Consent reference is unresolved.")
    if metadata["pii_check"] not in ("none", "redacted"):
        blockers.append("Privacy check is not complete.")
    if _is_unresolved(metadata["contamination_notes"]):
        blockers.append("Contamination check is unresolved.")
    values = validation_values(metadata)
    missing = [name for name in VALIDATION_CHECKS if not values.get(name)]
    if missing:
        blockers.append("Validation checks are incomplete: " + ", ".join(missing) + ".")
    return blockers


def dataset_blockers(connection, item_id, source, translation, metadata):
    """Public read-only view of the dataset preparation blockers."""
    return _dataset_blockers(connection, item_id, source, translation, metadata)


def _usd_from_cents(cents):
    return (Decimal(int(cents)) / Decimal(100)).quantize(Decimal("0.01"))


def record_reward_earning(
    connection,
    recipient_id,
    recipient_role,
    contribution_type,
    item_id,
    translation_version,
    earned_at,
    review_id=None,
):
    amount_cents = (
        TRANSLATION_APPROVAL_CENTS
        if contribution_type == "translation"
        else COMPLETED_REVIEW_CENTS
    )
    if (contribution_type, recipient_role, review_id is not None) not in (
        ("translation", "translator", False),
        ("review", "reviewer", True),
    ):
        raise WorkflowError("Invalid reward contribution type.")
    connection.execute(
        """
        INSERT INTO reward_earnings(
            recipient_id, recipient_role, contribution_type, item_id,
            translation_version, review_id, amount_cents, earned_at, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        (
            recipient_id,
            recipient_role,
            contribution_type,
            item_id,
            translation_version,
            review_id,
            amount_cents,
            earned_at,
            utc_now(),
        ),
    )


def _reward_entries(connection, recipient_id, role):
    rows = connection.execute(
        """
        SELECT e.*, r.decision, r.created_at AS review_created_at
        FROM reward_earnings e
        LEFT JOIN reviews r ON r.id = e.review_id
        WHERE e.recipient_id = ? AND e.recipient_role = ?
        ORDER BY e.earned_at, e.id
        """,
        (recipient_id, role),
    ).fetchall()
    entries = [dict(row) for row in rows]
    for entry in entries:
        entry["amount_usd"] = _usd_from_cents(entry["amount_cents"])
    return entries


def _attach_payment_status(earnings, payments):
    for earning in sorted(earnings, key=lambda row: (row["earned_at"], row["id"])):
        earning["paid_cents"] = 0
        earning["payment_references"] = []
        earning["payment_status"] = "unpaid"
    remaining = [
        {"payment": payment, "cents": int(payment["amount_cents"])}
        for payment in sorted(payments, key=lambda row: (row["paid_at"], row["id"]))
    ]
    payment_index = 0
    for earning in sorted(earnings, key=lambda row: (row["earned_at"], row["id"])):
        unpaid = int(earning["amount_cents"])
        references = []
        while unpaid > 0 and payment_index < len(remaining):
            available = remaining[payment_index]["cents"]
            if available <= 0:
                payment_index += 1
                continue
            applied = min(unpaid, available)
            payment = remaining[payment_index]["payment"]
            remaining[payment_index]["cents"] -= applied
            unpaid -= applied
            reference = (payment["note"] or "").strip() or f"Payment #{payment['id']}"
            references.append(reference)
            if remaining[payment_index]["cents"] == 0:
                payment_index += 1
        paid = int(earning["amount_cents"]) - unpaid
        earning["paid_cents"] = paid
        earning["amount_usd"] = _usd_from_cents(earning["amount_cents"])
        earning["paid_usd"] = _usd_from_cents(paid)
        earning["payment_references"] = references
        if unpaid == 0:
            earning["payment_status"] = "paid"
        elif paid:
            earning["payment_status"] = "partially paid"
        else:
            earning["payment_status"] = "unpaid"
    return earnings


def reward_summary(contribution_count, cents_per_contribution):
    count = max(0, int(contribution_count))
    accrued_cents = count * int(cents_per_contribution)
    return {
        "contribution_count": count,
        "per_contribution_cents": int(cents_per_contribution),
        "per_contribution_usd": _usd_from_cents(cents_per_contribution),
        "accrued_cents": accrued_cents,
        "accrued_usd": _usd_from_cents(accrued_cents),
    }


def is_reward_eligible(connection, item_id):
    translation = get_translation(connection, item_id)
    if not translation:
        return False
    if translation["status"] != "reviewed" or translation["resolution_required"]:
        return False
    version = translation["version"]
    if not connection.execute(
        "SELECT 1 FROM translation_versions WHERE item_id = ? AND version = ?",
        (item_id, version),
    ).fetchone():
        return False
    reviews = reviews_for_version(connection, item_id, version)
    if not any(row["decision"] == "approved" for row in reviews):
        return False
    resolution = connection.execute(
        """
        SELECT decision FROM resolutions
        WHERE item_id = ? AND translation_version = ?
        ORDER BY created_at DESC, id DESC LIMIT 1
        """,
        (item_id, version),
    ).fetchone()
    resolved_approved = bool(resolution and resolution["decision"] == "approved")
    if any(row["decision"] == "needs_revision" for row in reviews) and not resolved_approved:
        return False
    assigned = {
        row["user_id"]
        for row in connection.execute(
            "SELECT user_id FROM assignments WHERE item_id = ? AND assignment_type = 'review'",
            (item_id,),
        ).fetchall()
    }
    submitted = {row["reviewer_id"] for row in reviews}
    if assigned - submitted:
        return False
    return True


def translator_reward(connection, translator_id):
    earnings = _reward_entries(connection, translator_id, "translator")
    summary = reward_summary(len(earnings), TRANSLATION_APPROVAL_CENTS)
    summary["approved_count"] = len(earnings)
    for earning in earnings:
        item = get_item(connection, earning["item_id"])
        source = item_source(item)
        earning["source_prompt"] = source.get("source_prompt", "")
        earning["capability"] = source.get("primary_capability", "")
        earning["approved_at"] = earning["earned_at"]
    items = list(reversed(earnings))
    summary["kind"] = "translator"
    summary["approved_items"] = items
    payments = payment_history(connection, translator_id, "translator")
    paid_cents = sum(int(payment["amount_cents"]) for payment in payments)
    summary["paid_cents"] = paid_cents
    summary["paid_usd"] = _usd_from_cents(paid_cents)
    available_cents = max(0, summary["accrued_cents"] - paid_cents)
    summary["available_cents"] = available_cents
    summary["available_usd"] = _usd_from_cents(available_cents)
    summary["pending_count"] = progress_counts(connection, translator_id, "translator")["ready"]
    summary["revision_count"] = progress_counts(connection, translator_id, "translator")["returned"]
    _attach_payment_status(items, payments)
    summary["payments"] = payments
    return summary


def reviewer_reward(connection, reviewer_id):
    earnings = _reward_entries(connection, reviewer_id, "reviewer")
    count = len(earnings)
    accrued_cents = count * COMPLETED_REVIEW_CENTS
    payments = payment_history(connection, reviewer_id, "reviewer")
    paid_cents = sum(int(payment["amount_cents"]) for payment in payments)
    summary = {
        "kind": "reviewer",
        "review_count": count,
        "contribution_count": count,
        "per_review_cents": COMPLETED_REVIEW_CENTS,
        "per_review_usd": _usd_from_cents(COMPLETED_REVIEW_CENTS),
        "accrued_cents": accrued_cents,
        "accrued_usd": _usd_from_cents(accrued_cents),
        "paid_cents": paid_cents,
        "paid_usd": _usd_from_cents(paid_cents),
        "available_cents": max(0, accrued_cents - paid_cents),
        "available_usd": _usd_from_cents(max(0, accrued_cents - paid_cents)),
        "payments": payments,
        "reviews": list(reversed(earnings)),
        "pending_count": progress_counts(connection, reviewer_id, "reviewer")["waiting"],
    }
    _attach_payment_status(summary["reviews"], payments)
    return summary


def payment_history(connection, recipient_id, role):
    rows = connection.execute(
        """
        SELECT p.*, u.display_name AS created_by_name, u.public_id AS created_by_public_id
        FROM reward_payments p
        LEFT JOIN users u ON u.id = p.created_by
        WHERE p.recipient_id = ? AND p.recipient_role = ?
        ORDER BY p.paid_at DESC, p.id DESC
        """,
        (recipient_id, role),
    ).fetchall()
    payments = [dict(row) for row in rows]
    for payment in payments:
        payment["amount_cents"] = int(payment["amount_cents"])
        payment["amount_usd"] = _usd_from_cents(payment["amount_cents"])
    return payments


def record_payment(connection, recipient_id, role, amount, note, admin_id):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can mark a payment as cleared.")
    recipient = get_user(connection, recipient_id)
    if not recipient or recipient["role"] != role:
        raise WorkflowError("The selected account does not match that reward role.")
    if role == "translator":
        reward = translator_reward(connection, recipient_id)
        work_count = reward["approved_count"]
    elif role == "reviewer":
        reward = reviewer_reward(connection, recipient_id)
        work_count = reward["review_count"]
    else:
        raise WorkflowError("Choose a valid reward role.")
    available_cents = reward["available_cents"]
    if available_cents <= 0:
        raise WorkflowError("There is no cleared amount available for this account.")
    try:
        amount_decimal = Decimal(str(amount).strip())
        if not amount_decimal.is_finite() or amount_decimal <= 0:
            raise InvalidOperation
        quantized_amount = amount_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount_decimal != quantized_amount:
            raise InvalidOperation
        amount_cents = int(quantized_amount * 100)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise WorkflowError("Enter a valid payment amount.") from error
    if amount_cents > available_cents:
        available = _usd_from_cents(available_cents)
        raise WorkflowError(f"Payment cannot exceed the available amount of ${available:.2f}.")
    note = (note or "").strip()
    if not note:
        raise WorkflowError("Add a short payment note or reference.")
    now = utc_now()
    connection.execute(
        """
        INSERT INTO reward_payments(
            recipient_id, recipient_role, amount_usd, amount_cents, work_count, note,
            paid_at, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (recipient_id, role, float(_usd_from_cents(amount_cents)), amount_cents,
         work_count, note, now, admin_id, now),
    )
    record_audit(
        connection,
        admin_id,
        "reward_payment_cleared",
        "user",
        recipient_id,
        {"role": role, "amount_cents": amount_cents, "work_count": work_count, "note": note},
    )
    connection.commit()
    return {
        "recipient_id": recipient_id,
        "recipient_role": role,
        "amount_cents": amount_cents,
        "amount_usd": _usd_from_cents(amount_cents),
        "work_count": work_count,
        "paid_at": now,
    }


def all_payables(connection):
    rows = connection.execute(
        """
        SELECT id, display_name, public_id, role
        FROM users
        WHERE role IN ('translator', 'reviewer') AND active = 1
        ORDER BY role, display_name
        """
    ).fetchall()
    payables = []
    for row in rows:
        reward = (
            translator_reward(connection, row["id"])
            if row["role"] == "translator"
            else reviewer_reward(connection, row["id"])
        )
        payables.append(
            {
                "user_id": row["id"],
                "display_name": row["display_name"],
                "public_id": row["public_id"],
                "role": row["role"],
                "work_count": reward.get("approved_count", reward.get("review_count", 0)),
                "accrued_usd": reward["accrued_usd"],
                "paid_usd": reward["paid_usd"],
                "available_usd": reward["available_usd"],
                "payments": reward["payments"],
            }
        )
    return payables


def all_translator_rewards(connection):
    translators = connection.execute(
        "SELECT id, display_name, public_id FROM users WHERE role = 'translator' AND active = 1 ORDER BY display_name"
    ).fetchall()
    return [
        {
            "user_id": row["id"],
            "display_name": row["display_name"],
            "public_id": row["public_id"],
            **translator_reward(connection, row["id"]),
        }
        for row in translators
    ]


def approve_dataset(connection, item_id, admin_id):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can approve dataset preparation.")
    item = get_item(connection, item_id)
    if not item:
        raise WorkflowError("Example not found.")
    source = item_source(item)
    translation = get_translation(connection, item_id)
    metadata = get_training_metadata(connection, item_id)
    blockers = _dataset_blockers(connection, item_id, source, translation, metadata)
    if blockers:
        raise WorkflowError("This item is not ready for dataset preparation.", blockers)
    now = utc_now()
    connection.execute(
        """
        UPDATE training_metadata
        SET dataset_status = 'approved_for_dataset', approved_by = ?, approved_at = ?, updated_at = ?
        WHERE item_id = ?
        """,
        (admin_id, now, now, item_id),
    )
    record_audit(
        connection, admin_id, "dataset_approved", "item", item_id, {"version": translation["version"]}
    )
    connection.commit()


def revoke_dataset(connection, item_id, admin_id):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can revoke dataset approval.")
    connection.execute(
        """
        UPDATE training_metadata
        SET dataset_status = 'not_ready', approved_by = NULL, approved_at = NULL, updated_at = ?
        WHERE item_id = ?
        """,
        (utc_now(), item_id),
    )
    record_audit(connection, admin_id, "dataset_approval_revoked", "item", item_id, {})
    connection.commit()


def return_translation(connection, item_id, admin_id, reason):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can return a translation for correction.")
    translation = get_translation(connection, item_id)
    if not translation:
        raise WorkflowError("There is no translation to return.")
    if translation["status"] not in ("ready_for_review", "under_dispute", "reviewed"):
        raise WorkflowError("This translation is already open for editing or correction.")
    metadata = get_training_metadata(connection, item_id)
    if metadata and metadata["dataset_status"] == "approved_for_dataset":
        raise WorkflowError("Revoke dataset preparation approval before returning this translation.")
    reason = (reason or "").strip()
    if not reason:
        raise WorkflowError("Explain what the translator needs to correct.")
    connection.execute(
        """
        UPDATE translations
        SET status = 'needs_revision', resolution_required = 0,
            resolution_reason = ?, updated_at = ?
        WHERE item_id = ?
        """,
        (reason, utc_now(), item_id),
    )
    record_audit(
        connection,
        admin_id,
        "translation_returned_for_correction",
        "item",
        item_id,
        {"reason": reason, "version": translation["version"]},
    )
    connection.commit()
    return "needs_revision"


def build_training_record(connection, item_id):
    item = get_item(connection, item_id)
    if not item:
        raise WorkflowError("Example not found.")
    source = item_source(item)
    if source["collection"] != "pilot":
        raise WorkflowError("Evaluation items are not included in training exports.")
    translation = get_translation(connection, item_id)
    if not translation:
        raise WorkflowError("No translation exists.")
    metadata = get_training_metadata(connection, item_id)
    blockers = _dataset_blockers(connection, item_id, source, translation, metadata)
    if blockers:
        raise WorkflowError("The item is not ready for a training record.", blockers)
    version = translation["version"]
    approved = _approved_reviews(connection, item_id, version)
    reviewer_rows = []
    seen = set()
    for review in approved:
        reviewer = get_user(connection, review["reviewer_id"])
        if not reviewer or reviewer["public_id"] in seen:
            continue
        if reviewer["id"] == translation["translator_id"]:
            continue
        seen.add(reviewer["public_id"])
        reviewer_rows.append(
            {
                "reviewer_id": reviewer["public_id"],
                "role": "independent_review",
                "date": review["created_at"][:10],
                "decision": "approved",
                "notes": review["comments"] or "",
            }
        )
    if not reviewer_rows:
        raise WorkflowError("No eligible approved reviewer is available for the record.")
    translator = get_user(connection, translation["translator_id"])
    if not translator:
        raise WorkflowError("The translator account is missing.")
    turns = _load_turns(translation["turns_lg"], len(_source_turns(source)))
    messages = []
    for index, turn in enumerate(_source_turns(source)):
        messages.append({"role": turn["role"], "content": turns[index]})
    final_user_content = translation["prompt_lg"]
    if source.get("source_context"):
        context_lg = (translation["context_lg"] or "").strip()
        if not context_lg:
            raise WorkflowError("The required background passage is missing from the Luganda translation.")
        final_user_content = context_lg + "\n\n" + final_user_content
    messages.append({"role": "user", "content": final_user_content})
    messages.append({"role": "assistant", "content": translation["response_lg"]})
    criteria = list(source.get("expected_response_criteria") or [])
    if not criteria:
        raise WorkflowError("The source example has no response criteria.")
    validation = validation_values(metadata)
    record = {
        "pilot_id": item_id,
        "capability": source["primary_capability"],
        "messages": messages,
        "language": "lg",
        "register": source["intended_register"],
        "expected_response": {
            "must_include": criteria,
            "must_not_include": [],
            "max_words": 500,
            "format": "natural_luganda_response",
            "uncertainty_behavior": source["uncertainty_behavior"],
        },
        "reference_answer": (
            translation["response_lg"]
            if source["primary_capability"] in CAPABILITIES_REQUIRING_REFERENCE
            else None
        ),
        "reference_status": (
            "reviewed"
            if source["primary_capability"] in CAPABILITIES_REQUIRING_REFERENCE
            else "not_required"
        ),
        "accepted_alternatives": [],
        "author_id": translator["public_id"],
        "reviewers": reviewer_rows,
        "review_status": "approved",
        "source": "project_original",
        "source_notes": "Original English source translated and reviewed in the Translation Studio.",
        "licence": metadata["licence"],
        "consent_ref": metadata["consent_ref"],
        "pii_check": metadata["pii_check"],
        "contamination_notes": metadata["contamination_notes"],
        "validation": validation,
        "split": source["proposed_split"],
        "notes": translation["notes"] or "",
    }
    try:
        validate_pilot_record(record, expected_split=source["proposed_split"])
    except Exception as error:
        raise WorkflowError(
            "The exported record does not pass the existing training-record validator.",
            [str(error)],
        ) from error
    return record


def export_training_jsonl(connection, admin_id, output_dir=None):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can export training preparation data.")
    rows = connection.execute(
        """
        SELECT i.item_id
        FROM items i
        JOIN training_metadata m ON m.item_id = i.item_id
        WHERE i.collection = 'pilot' AND m.dataset_status = 'approved_for_dataset'
        ORDER BY i.item_id
        """
    ).fetchall()
    if not rows:
        raise WorkflowError(
            "No pilot items are approved for dataset preparation. Approve at least one reviewed item first."
        )
    records = []
    all_errors = []
    for row in rows:
        try:
            records.append(build_training_record(connection, row["item_id"]))
        except WorkflowError as error:
            all_errors.extend(f"{row['item_id']}: {message}" for message in error.errors or [str(error)])
    if all_errors:
        raise WorkflowError(
            "No export was written because some approved items do not pass the training schema.",
            all_errors,
        )
    output = Path(output_dir or DEFAULT_EXPORT_DIR)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    jsonl_path = output / f"training-preparation-{stamp}.jsonl"
    manifest_path = output / f"training-preparation-{stamp}.manifest.json"
    write_jsonl(jsonl_path, records)
    manifest = {
        "created_at": utc_now(),
        "record_count": len(records),
        "collection": "pilot",
        "evaluation_excluded": True,
        "training_authorized": False,
        "note": (
            "Prepared from reviewed records approved for dataset preparation. "
            "This file is not training authorization. The full training data gate "
            "and provenance checks still apply."
        ),
        "sha256": sha256_text(jsonl_path.read_text(encoding="utf-8")),
        "record_ids": [record["pilot_id"] for record in records],
    }
    write_json(manifest_path, manifest)
    record_audit(
        connection,
        admin_id,
        "training_export_created",
        "export",
        jsonl_path.name,
        {"record_count": len(records)},
    )
    connection.commit()
    return jsonl_path, manifest_path, manifest


CSV_COLUMNS = (
    "item_id",
    "collection",
    "primary_capability",
    "proposed_split",
    "translation_status",
    "dataset_status",
    "translator_public_id",
    "translator_name",
    "source_context_en",
    "prior_turns_en",
    "source_prompt_en",
    "expected_response_criteria_en",
    "reference_answer_or_rubric_en",
    "required_constraints_en",
    "source_context_lg",
    "prior_turns_lg",
    "source_prompt_lg",
    "final_assistant_response_lg",
    "translation_notes",
    "submitted_at",
    "reviews",
    "dataset_approved_at",
)


def export_review_csv(connection, admin_id, output_dir=None, collection=None):
    admin = get_user(connection, admin_id)
    if not admin or admin["role"] != "admin":
        raise WorkflowError("Only an administrator can export studio records.")
    query = """
        SELECT i.*, t.translator_id, t.context_lg, t.turns_lg, t.prompt_lg,
               t.response_lg, t.notes, t.status, t.submitted_at,
               m.dataset_status, m.approved_at,
               u.public_id AS translator_public_id, u.display_name AS translator_name
        FROM items i
        LEFT JOIN translations t ON t.item_id = i.item_id
        LEFT JOIN training_metadata m ON m.item_id = i.item_id
        LEFT JOIN users u ON u.id = t.translator_id
    """
    params = []
    if collection:
        query += " WHERE i.collection = ?"
        params.append(collection)
    query += " ORDER BY i.item_id"
    rows = connection.execute(query, params).fetchall()
    output = Path(output_dir or DEFAULT_EXPORT_DIR)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = output / f"studio-review-{stamp}.csv"
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        source = item_source(row)
        reviews = review_history(connection, row["item_id"])
        writer.writerow(
            {
                "item_id": row["item_id"],
                "collection": row["collection"],
                "primary_capability": row["primary_capability"],
                "proposed_split": row["proposed_split"] or "",
                "translation_status": row["status"] or "not_started",
                "dataset_status": row["dataset_status"] or "not_ready",
                "translator_public_id": row["translator_public_id"] or "",
                "translator_name": row["translator_name"] or "",
                "source_context_en": source.get("source_context") or "",
                "prior_turns_en": json.dumps(source.get("conversation_turns") or [], ensure_ascii=False),
                "source_prompt_en": source.get("source_prompt") or "",
                "expected_response_criteria_en": json.dumps(
                    source.get("expected_response_criteria") or [], ensure_ascii=False
                ),
                "reference_answer_or_rubric_en": source["reference_answer_or_rubric"]["content"],
                "required_constraints_en": json.dumps(
                    source.get("required_constraints") or [], ensure_ascii=False
                ),
                "source_context_lg": row["context_lg"] or "",
                "prior_turns_lg": row["turns_lg"] or "",
                "source_prompt_lg": row["prompt_lg"] or "",
                "final_assistant_response_lg": row["response_lg"] or "",
                "translation_notes": row["notes"] or "",
                "submitted_at": row["submitted_at"] or "",
                "reviews": json.dumps(
                    [
                        {
                            "reviewer": review["reviewer_public_id"],
                            "date": review["created_at"],
                            "decision": review["decision"],
                            "comments": review["comments"],
                            "suggested_correction": review["suggested_correction"],
                        }
                        for review in reviews
                    ],
                    ensure_ascii=False,
                ),
                "dataset_approved_at": row["approved_at"] or "",
            }
        )
    atomic_write_text(path, buffer.getvalue())
    record_audit(
        connection, admin_id, "studio_csv_export_created", "export", path.name, {"row_count": len(rows)}
    )
    connection.commit()
    return path, len(rows)


def progress_counts(connection, user_id, role):
    if role == "translator":
        total = connection.execute(
            "SELECT COUNT(*) AS count FROM assignments WHERE user_id = ? AND assignment_type = 'translation'",
            (user_id,),
        ).fetchone()["count"]
        status_rows = connection.execute(
            """
            SELECT COALESCE(t.status, 'not_started') AS status, COUNT(*) AS count
            FROM assignments a
            LEFT JOIN translations t ON t.item_id = a.item_id
            WHERE a.user_id = ? AND a.assignment_type = 'translation'
            GROUP BY COALESCE(t.status, 'not_started')
            """,
            (user_id,),
        ).fetchall()
        counts = {row["status"]: row["count"] for row in status_rows}
        return {
            "total": total,
            "waiting": counts.get("not_started", 0),
            "saved": counts.get("in_progress", 0),
            "returned": counts.get("needs_revision", 0),
            "ready": counts.get("ready_for_review", 0),
            "pending_approval": counts.get("ready_for_review", 0),
            "revision_requested": counts.get("needs_revision", 0),
            "reviewed": counts.get("reviewed", 0),
            "disputed": counts.get("under_dispute", 0),
        }
    if role == "reviewer":
        total = connection.execute(
            "SELECT COUNT(*) AS count FROM assignments WHERE user_id = ? AND assignment_type = 'review'",
            (user_id,),
        ).fetchone()["count"]
        completed = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM reviews r
            JOIN translation_versions v
              ON v.item_id = r.item_id AND v.version = r.translation_version
            WHERE r.reviewer_id = ?
            """,
            (user_id,),
        ).fetchone()["count"]
        pending = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM assignments a
            JOIN translations t ON t.item_id = a.item_id
            WHERE a.user_id = ? AND a.assignment_type = 'review'
              AND t.status = 'ready_for_review'
              AND NOT EXISTS (
                SELECT 1 FROM reviews r
                WHERE r.item_id = a.item_id AND r.reviewer_id = a.user_id
                  AND r.translation_version = t.version
              )
            """,
            (user_id,),
        ).fetchone()["count"]
        return {"total": total, "waiting": pending, "completed": completed}
    return {}


def assigned_items(connection, user_id, assignment_type, query=None, status=None):
    sql = """
        SELECT i.*, t.status AS translation_status, t.version AS translation_version,
               t.resolution_required, u.display_name AS translator_name,
               u.public_id AS translator_public_id
        FROM assignments a
        JOIN items i ON i.item_id = a.item_id
        LEFT JOIN translations t ON t.item_id = i.item_id
        LEFT JOIN users u ON u.id = t.translator_id
        WHERE a.user_id = ? AND a.assignment_type = ?
    """
    params = [user_id, assignment_type]
    if assignment_type == "review":
        sql += " AND t.item_id IS NOT NULL"
    if status:
        if status == "not_started":
            sql += " AND COALESCE(t.status, 'not_started') = 'not_started'"
        else:
            sql += " AND t.status = ?"
            params.append(status)
    if query:
        sql += " AND (i.source_json LIKE ? OR i.primary_capability LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like])
    sql += " ORDER BY i.item_id"
    return connection.execute(sql, params).fetchall()


def admin_items(connection, collection=None, status=None, dataset_status=None, query=None):
    sql = """
        SELECT i.*, t.status AS translation_status, t.version AS translation_version,
               t.resolution_required, m.dataset_status,
               u.display_name AS translator_name, u.public_id AS translator_public_id
        FROM items i
        LEFT JOIN translations t ON t.item_id = i.item_id
        LEFT JOIN training_metadata m ON m.item_id = i.item_id
        LEFT JOIN users u ON u.id = t.translator_id
        WHERE 1 = 1
    """
    params = []
    if collection:
        sql += " AND i.collection = ?"
        params.append(collection)
    if status:
        if status == "not_started":
            sql += " AND COALESCE(t.status, 'not_started') = 'not_started'"
        else:
            sql += " AND t.status = ?"
            params.append(status)
    if dataset_status:
        if dataset_status == "not_ready":
            sql += " AND COALESCE(m.dataset_status, 'not_ready') = 'not_ready'"
        else:
            sql += " AND m.dataset_status = ?"
            params.append(dataset_status)
    if query:
        sql += " AND (i.source_json LIKE ? OR i.item_id LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like])
    sql += " ORDER BY i.item_id"
    return connection.execute(sql, params).fetchall()


def next_translation_item(connection, user_id, after_item_id=None):
    rows = assigned_items(connection, user_id, "translation")
    ids = [row["item_id"] for row in rows]
    if not ids:
        return None
    if after_item_id and after_item_id in ids:
        index = ids.index(after_item_id)
        if index + 1 < len(ids):
            return ids[index + 1]
        return None
    for row in rows:
        if (row["translation_status"] or "not_started") in ("needs_revision", "in_progress", "not_started"):
            return row["item_id"]
    return ids[0]


def previous_translation_item(connection, user_id, item_id):
    rows = assigned_items(connection, user_id, "translation")
    ids = [row["item_id"] for row in rows]
    if item_id in ids:
        index = ids.index(item_id)
        if index > 0:
            return ids[index - 1]
    return None


def _eligible_translation_items(connection, collection=None, limit=10, capability=None):
    sql = """
        SELECT i.item_id
        FROM items i
        LEFT JOIN assignments a ON a.item_id = i.item_id AND a.assignment_type = 'translation'
        WHERE a.id IS NULL
    """
    params = []
    if collection:
        sql += " AND i.collection = ?"
        params.append(collection)
    if capability:
        sql += " AND i.primary_capability = ?"
        params.append(capability)
    sql += " ORDER BY i.item_id LIMIT ?"
    params.append(int(limit))
    return connection.execute(sql, params).fetchall()


def assign_translation(connection, item_id, user_id, actor_id):
    user = get_user(connection, user_id)
    if not user or user["role"] != "translator":
        raise WorkflowError("Choose a translator account.")
    if connection.execute(
        "SELECT 1 FROM assignments WHERE item_id = ? AND assignment_type = 'translation'",
        (item_id,),
    ).fetchone():
        raise WorkflowError("This example already has a translator.")
    connection.execute(
        """
        INSERT INTO assignments(item_id, user_id, assignment_type, created_by, created_at)
        VALUES (?, ?, 'translation', ?, ?)
        """,
        (item_id, user_id, actor_id, utc_now()),
    )
    record_audit(connection, actor_id, "translation_assigned", "item", item_id, {"user_id": user_id})
    connection.commit()


def assign_review(connection, item_id, user_id, actor_id):
    user = get_user(connection, user_id)
    if not user or user["role"] != "reviewer":
        raise WorkflowError("Choose a reviewer account.")
    translation = get_translation(connection, item_id)
    if not translation or translation["status"] not in ("ready_for_review", "needs_revision", "under_dispute", "reviewed"):
        raise WorkflowError("This example does not have a submitted translation to review.")
    if translation["translator_id"] == user_id:
        raise WorkflowError("A translator cannot be assigned to review their own translation.")
    try:
        connection.execute(
            """
            INSERT INTO assignments(item_id, user_id, assignment_type, created_by, created_at)
            VALUES (?, ?, 'review', ?, ?)
            """,
            (item_id, user_id, actor_id, utc_now()),
        )
    except Exception as error:
        if "UNIQUE" in str(error):
            raise WorkflowError("That reviewer is already assigned to this example.") from error
        raise
    record_audit(connection, actor_id, "review_assigned", "item", item_id, {"user_id": user_id})
    connection.commit()


def bulk_assign_translation(connection, user_id, actor_id, collection=None, limit=10, capability=None):
    user = get_user(connection, user_id)
    if not user or user["role"] != "translator":
        raise WorkflowError("Choose a translator account.")
    rows = _eligible_translation_items(connection, collection, limit, capability)
    assigned = []
    for row in rows:
        try:
            assign_translation(connection, row["item_id"], user_id, actor_id)
            assigned.append(row["item_id"])
        except WorkflowError:
            continue
    return assigned


def _eligible_review_items(connection, user_id, collection=None, limit=10, capability=None):
    sql = """
        SELECT i.item_id
        FROM items i
        JOIN translations t ON t.item_id = i.item_id
        WHERE t.status = 'ready_for_review'
          AND NOT EXISTS (
            SELECT 1 FROM assignments a
            WHERE a.item_id = i.item_id AND a.user_id = ? AND a.assignment_type = 'review'
          )
          AND NOT EXISTS (
            SELECT 1 FROM reviews r
            WHERE r.item_id = i.item_id AND r.reviewer_id = ?
              AND r.translation_version = t.version
          )
          AND t.translator_id <> ?
    """
    params = [user_id, user_id, user_id]
    if collection:
        sql += " AND i.collection = ?"
        params.append(collection)
    if capability:
        sql += " AND i.primary_capability = ?"
        params.append(capability)
    sql += " ORDER BY i.item_id LIMIT ?"
    params.append(int(limit))
    return connection.execute(sql, params).fetchall()


def bulk_assign_review(connection, user_id, actor_id, collection=None, limit=10, capability=None):
    user = get_user(connection, user_id)
    if not user or user["role"] != "reviewer":
        raise WorkflowError("Choose a reviewer account.")
    rows = _eligible_review_items(connection, user_id, collection, limit, capability)
    assigned = []
    for row in rows:
        try:
            assign_review(connection, row["item_id"], user_id, actor_id)
            assigned.append(row["item_id"])
        except WorkflowError:
            continue
    return assigned


def admin_counts(connection):
    def count(sql, params=()):
        return connection.execute(sql, params).fetchone()["count"]

    return {
        "users": count("SELECT COUNT(*) AS count FROM users"),
        "contributors": count(
            "SELECT COUNT(*) AS count FROM users WHERE role IN ('translator', 'reviewer')"
        ),
        "items": count("SELECT COUNT(*) AS count FROM items"),
        "pilot": count("SELECT COUNT(*) AS count FROM items WHERE collection = 'pilot'"),
        "evaluation": count("SELECT COUNT(*) AS count FROM items WHERE collection = 'evaluation'"),
        "translations": count("SELECT COUNT(*) AS count FROM translations"),
        "ready": count("SELECT COUNT(*) AS count FROM translations WHERE status = 'ready_for_review'"),
        "reviewed": count("SELECT COUNT(*) AS count FROM translations WHERE status = 'reviewed'"),
        "disputes": count(
            "SELECT COUNT(*) AS count FROM translations WHERE resolution_required = 1"
        ),
        "dataset_approved": count(
            "SELECT COUNT(*) AS count FROM training_metadata WHERE dataset_status = 'approved_for_dataset'"
        ),
        "unassigned": count(
            """
            SELECT COUNT(*) AS count FROM items i
            LEFT JOIN assignments a ON a.item_id = i.item_id AND a.assignment_type = 'translation'
            WHERE a.id IS NULL
            """
        ),
    }


def recent_audit(connection, limit=20):
    return connection.execute(
        """
        SELECT e.*, u.display_name AS actor_name, u.public_id AS actor_public_id
        FROM audit_events e
        LEFT JOIN users u ON u.id = e.actor_id
        ORDER BY e.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def item_audit(connection, item_id):
    return connection.execute(
        """
        SELECT e.*, u.display_name AS actor_name, u.public_id AS actor_public_id
        FROM audit_events e
        LEFT JOIN users u ON u.id = e.actor_id
        WHERE e.entity_type = 'item' AND e.entity_id = ?
        ORDER BY e.id DESC
        """,
        (item_id,),
    ).fetchall()
