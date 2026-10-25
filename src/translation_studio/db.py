"""Database helpers for the local Translation Studio."""

import json
import os
import sqlite3
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path

from .reward_rules import COMPLETED_REVIEW_CENTS, TRANSLATION_APPROVAL_CENTS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "studio" / "studio.sqlite3"


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_db_path():
    return Path(os.environ.get("STUDIO_DB", DEFAULT_DB))


def connect(path=None):
    db_path = Path(path or default_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    public_id TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'translator', 'reviewer')),
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    collection TEXT NOT NULL CHECK (collection IN ('pilot', 'evaluation')),
    primary_capability TEXT NOT NULL,
    proposed_split TEXT,
    source_sha256 TEXT NOT NULL,
    source_json TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS items_collection_idx ON items(collection);
CREATE INDEX IF NOT EXISTS items_capability_idx ON items(primary_capability);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_type TEXT NOT NULL CHECK (assignment_type IN ('translation', 'review')),
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE(item_id, user_id, assignment_type)
);

CREATE UNIQUE INDEX IF NOT EXISTS one_translator_per_item
    ON assignments(item_id) WHERE assignment_type = 'translation';
CREATE INDEX IF NOT EXISTS assignments_user_idx ON assignments(user_id, assignment_type);

CREATE TABLE IF NOT EXISTS translations (
    item_id TEXT PRIMARY KEY REFERENCES items(item_id) ON DELETE CASCADE,
    translator_id INTEGER NOT NULL REFERENCES users(id),
    context_lg TEXT NOT NULL DEFAULT '',
    turns_lg TEXT NOT NULL DEFAULT '[]',
    prompt_lg TEXT NOT NULL DEFAULT '',
    response_lg TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (
        status IN (
            'not_started', 'in_progress', 'ready_for_review',
            'needs_revision', 'under_dispute', 'reviewed'
        )
    ),
    version INTEGER NOT NULL DEFAULT 1,
    resolution_required INTEGER NOT NULL DEFAULT 0,
    resolution_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    submitted_at TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    translation_version INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'needs_revision', 'cannot_assess')),
    comments TEXT NOT NULL DEFAULT '',
    suggested_correction TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(item_id, reviewer_id, translation_version)
);

CREATE INDEX IF NOT EXISTS reviews_item_idx ON reviews(item_id, translation_version);

CREATE TABLE IF NOT EXISTS resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    translation_version INTEGER NOT NULL,
    admin_id INTEGER NOT NULL REFERENCES users(id),
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'needs_revision')),
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_metadata (
    item_id TEXT PRIMARY KEY REFERENCES items(item_id) ON DELETE CASCADE,
    licence TEXT NOT NULL DEFAULT '',
    licence_status TEXT NOT NULL DEFAULT 'unresolved'
        CHECK (licence_status IN ('unresolved', 'recorded')),
    consent_ref TEXT NOT NULL DEFAULT '',
    consent_status TEXT NOT NULL DEFAULT 'not_recorded'
        CHECK (consent_status IN ('not_recorded', 'owner_reported', 'recorded')),
    pii_check TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (pii_check IN ('none', 'redacted', 'needs_review')),
    contamination_notes TEXT NOT NULL DEFAULT '',
    validation_json TEXT NOT NULL DEFAULT '{}',
    dataset_status TEXT NOT NULL DEFAULT 'not_ready'
        CHECK (dataset_status IN ('not_ready', 'approved_for_dataset')),
    approved_by INTEGER REFERENCES users(id),
    approved_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translation_versions (
    item_id TEXT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    translator_id INTEGER NOT NULL REFERENCES users(id),
    context_lg TEXT NOT NULL DEFAULT '',
    turns_lg TEXT NOT NULL DEFAULT '[]',
    prompt_lg TEXT NOT NULL DEFAULT '',
    response_lg TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL,
    PRIMARY KEY (item_id, version)
);

CREATE TABLE IF NOT EXISTS reward_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    recipient_role TEXT NOT NULL CHECK (recipient_role IN ('translator', 'reviewer')),
    amount_usd REAL NOT NULL CHECK (amount_usd > 0),
    amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_cents >= 0),
    work_count INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    paid_at TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS reward_payments_recipient_idx
    ON reward_payments(recipient_id, recipient_role, paid_at);

CREATE TABLE IF NOT EXISTS reward_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    recipient_role TEXT NOT NULL CHECK (recipient_role IN ('translator', 'reviewer')),
    contribution_type TEXT NOT NULL CHECK (contribution_type IN ('translation', 'review')),
    item_id TEXT NOT NULL REFERENCES items(item_id),
    translation_version INTEGER NOT NULL,
    review_id INTEGER REFERENCES reviews(id),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    earned_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    CHECK (
        (contribution_type = 'translation' AND recipient_role = 'translator' AND review_id IS NULL)
        OR
        (contribution_type = 'review' AND recipient_role = 'reviewer' AND review_id IS NOT NULL)
    ),
    FOREIGN KEY (item_id, translation_version)
        REFERENCES translation_versions(item_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS one_translation_earning_per_item
    ON reward_earnings(item_id) WHERE contribution_type = 'translation';
CREATE UNIQUE INDEX IF NOT EXISTS one_review_earning_per_review
    ON reward_earnings(review_id) WHERE contribution_type = 'review';
CREATE INDEX IF NOT EXISTS reward_earnings_recipient_idx
    ON reward_earnings(recipient_id, recipient_role, earned_at, id);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_item_idx ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS audit_created_idx ON audit_events(created_at);

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db(connection):
    connection.executescript(SCHEMA)
    connection.execute("BEGIN IMMEDIATE")
    try:
        payment_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reward_payments)").fetchall()
        }
        if "amount_cents" not in payment_columns:
            connection.execute(
                "ALTER TABLE reward_payments ADD COLUMN amount_cents INTEGER NOT NULL DEFAULT 0"
            )
        # Retry zero-valued rows too, since a previous migration attempt may
        # have added the column before it could finish converting payments.
        for row in connection.execute(
            "SELECT id, amount_usd, amount_cents FROM reward_payments"
        ).fetchall():
            try:
                stored_amount = Decimal(str(row["amount_usd"]))
                cents_value = stored_amount * 100
                cents = int(cents_value)
            except (InvalidOperation, TypeError, ValueError, OverflowError) as error:
                raise RuntimeError(
                    f"Existing payment {row['id']} cannot be converted to cents safely."
                ) from error
            if cents <= 0 or cents_value != cents:
                raise RuntimeError(f"Existing payment {row['id']} cannot be converted to cents safely.")
            if int(row["amount_cents"]) == 0:
                connection.execute(
                    "UPDATE reward_payments SET amount_cents = ? WHERE id = ?", (cents, row["id"])
                )
            elif int(row["amount_cents"]) != cents:
                raise RuntimeError(
                    f"Existing payment {row['id']} has inconsistent dollar and cent amounts."
                )
        _backfill_reward_earnings(connection)
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(training_metadata)").fetchall()
        }
        if "licence_status" not in columns:
            connection.execute(
                "ALTER TABLE training_metadata ADD COLUMN licence_status TEXT NOT NULL DEFAULT 'unresolved'"
            )
        if "consent_status" not in columns:
            connection.execute(
                "ALTER TABLE training_metadata ADD COLUMN consent_status TEXT NOT NULL DEFAULT 'not_recorded'"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _backfill_reward_earnings(connection):
    """Record only historical contributions supported by durable workflow rows."""
    now = utc_now()
    connection.execute(
        """
        INSERT OR IGNORE INTO reward_earnings(
            recipient_id, recipient_role, contribution_type, item_id,
            translation_version, review_id, amount_cents, earned_at, recorded_at
        )
        SELECT r.reviewer_id, 'reviewer', 'review', r.item_id,
               r.translation_version, r.id, ?, r.created_at, ?
        FROM reviews r
        JOIN users reviewer ON reviewer.id = r.reviewer_id AND reviewer.role = 'reviewer'
        JOIN translation_versions v
          ON v.item_id = r.item_id AND v.version = r.translation_version
        JOIN assignments a
          ON a.item_id = r.item_id AND a.user_id = r.reviewer_id
         AND a.assignment_type = 'review'
        WHERE r.reviewer_id <> v.translator_id
          AND (r.decision = 'approved' OR length(trim(r.comments)) > 0)
        """,
        (COMPLETED_REVIEW_CENTS, now),
    )
    connection.execute(
        """
        WITH eligible_versions AS (
            SELECT v.item_id, v.version, v.translator_id,
                   COALESCE(
                       (SELECT x.created_at FROM resolutions x
                        WHERE x.item_id = v.item_id AND x.translation_version = v.version
                          AND x.decision = 'approved'
                        ORDER BY x.id DESC LIMIT 1),
                       (SELECT MAX(r.created_at) FROM reviews r
                        WHERE r.item_id = v.item_id AND r.translation_version = v.version),
                       v.submitted_at
                   ) AS earned_at
            FROM translation_versions v
            WHERE EXISTS (
                SELECT 1 FROM reviews r
                WHERE r.item_id = v.item_id AND r.translation_version = v.version
                  AND r.decision = 'approved'
            )
              AND (
                  NOT EXISTS (
                      SELECT 1 FROM reviews r
                      WHERE r.item_id = v.item_id AND r.translation_version = v.version
                        AND r.decision = 'needs_revision'
                  )
                  OR EXISTS (
                      SELECT 1 FROM resolutions x
                      WHERE x.item_id = v.item_id AND x.translation_version = v.version
                        AND x.decision = 'approved'
                        AND x.id = (SELECT MAX(x2.id) FROM resolutions x2
                                    WHERE x2.item_id = x.item_id
                                      AND x2.translation_version = x.translation_version)
                  )
              )
              AND NOT EXISTS (
                  SELECT 1 FROM assignments a
                  WHERE a.item_id = v.item_id AND a.assignment_type = 'review'
                    AND NOT EXISTS (
                        SELECT 1 FROM reviews r
                        WHERE r.item_id = v.item_id AND r.reviewer_id = a.user_id
                          AND r.translation_version = v.version
                    )
              )
        )
        INSERT OR IGNORE INTO reward_earnings(
            recipient_id, recipient_role, contribution_type, item_id,
            translation_version, review_id, amount_cents, earned_at, recorded_at
        )
        SELECT eligible.translator_id, 'translator', 'translation', eligible.item_id,
               eligible.version, NULL, ?, eligible.earned_at, ?
        FROM eligible_versions eligible
        WHERE NOT EXISTS (
            SELECT 1 FROM eligible_versions earlier
            WHERE earlier.item_id = eligible.item_id
              AND (earlier.earned_at < eligible.earned_at
                   OR (earlier.earned_at = eligible.earned_at
                       AND earlier.version < eligible.version))
        )
        """,
        (TRANSLATION_APPROVAL_CENTS, now),
    )


def record_audit(connection, actor_id, action, entity_type, entity_id, details=None):
    connection.execute(
        """
        INSERT INTO audit_events(actor_id, action, entity_type, entity_id, details_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            actor_id,
            action,
            entity_type,
            str(entity_id),
            json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
            utc_now(),
        ),
    )


def set_meta(connection, key, value):
    connection.execute(
        "INSERT INTO app_meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(connection, key, default=None):
    row = connection.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_item(connection, item_id):
    return connection.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()


def item_source(row):
    return json.loads(row["source_json"])


def get_user(connection, user_id):
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_username(connection, username):
    return connection.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
    ).fetchone()


def list_users(connection):
    return connection.execute(
        "SELECT id, username, display_name, public_id, role, active, created_at "
        "FROM users ORDER BY role, display_name"
    ).fetchall()
