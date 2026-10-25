"""Import the validated English source draft without mutating it."""

from pathlib import Path

from training.source_pilot import (
    load_source_draft,
    validate_source_exports,
)
from training.storage import canonical_json, sha256_text

from .db import record_audit, set_meta, utc_now

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"


def import_source(connection, source_path=None, actor_id=None):
    path = Path(source_path or DEFAULT_SOURCE).resolve()
    loaded = load_source_draft(path)
    exports = validate_source_exports(loaded, path.parent)
    inserted = 0
    skipped = 0
    conflicts = []
    try:
        for record in loaded["pilot"] + loaded["evaluation"]:
            item_id = record["item_id"]
            source_json = canonical_json(record)
            source_hash = sha256_text(source_json)
            existing = connection.execute(
                "SELECT source_sha256 FROM items WHERE item_id = ?", (item_id,)
            ).fetchone()
            if existing:
                if existing["source_sha256"] == source_hash:
                    skipped += 1
                    continue
                conflicts.append(
                    {
                        "item_id": item_id,
                        "message": "The imported source differs from the stored source. The stored record was preserved.",
                    }
                )
                continue
            connection.execute(
                """
                INSERT INTO items(
                    item_id, collection, primary_capability, proposed_split,
                    source_sha256, source_json, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    record["collection"],
                    record["primary_capability"],
                    record["proposed_split"],
                    source_hash,
                    source_json,
                    utc_now(),
                ),
            )
            inserted += 1
        set_meta(connection, "source_path", str(path))
        set_meta(connection, "source_sha256", loaded["sha256"])
        set_meta(connection, "source_dataset_name", loaded["summary"]["dataset_name"])
        set_meta(connection, "source_status", loaded["summary"]["status"])
        set_meta(connection, "last_import_at", utc_now())
        record_audit(
            connection,
            actor_id,
            "source_import",
            "source",
            "pilot-v1",
            {
                "inserted": inserted,
                "skipped": skipped,
                "conflicts": len(conflicts),
                "source_sha256": loaded["sha256"],
            },
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "imported" if not conflicts else "imported_with_conflicts",
        "path": str(path),
        "source_sha256": loaded["sha256"],
        "inserted": inserted,
        "skipped": skipped,
        "conflicts": conflicts,
        "pilot_count": loaded["summary"]["pilot_count"],
        "evaluation_count": loaded["summary"]["evaluation_count"],
        "exports": exports,
    }


def item_count(connection):
    return connection.execute("SELECT COUNT(*) AS count FROM items").fetchone()["count"]


def collection_counts(connection):
    rows = connection.execute(
        "SELECT collection, COUNT(*) AS count FROM items GROUP BY collection"
    ).fetchall()
    return {row["collection"]: row["count"] for row in rows}
