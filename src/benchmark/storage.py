"""Deterministic JSON and JSONL storage with atomic replacement."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .errors import ValidationError


def canonical_json(value):
    """Return a stable JSON representation used for hashes and manifests."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_text(path, text):
    _atomic_write(path, text)


def write_json(path, value):
    _atomic_write(path, pretty_json(value))


def read_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValidationError(f"file not found: {path}")
    except json.JSONDecodeError as error:
        raise ValidationError(f"invalid JSON in {path}: {error}") from error


def write_jsonl(path, records):
    """Write one JSON object per line. Existing files are replaced atomically."""
    lines = []
    for index, record in enumerate(records, 1):
        try:
            lines.append(canonical_json(record))
        except TypeError as error:
            raise ValidationError(f"record {index} is not JSON serialisable: {error}") from error
    _atomic_write(path, "\n".join(lines) + ("\n" if lines else ""))


def read_jsonl(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValidationError(f"file not found: {path}")
    records = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValidationError(f"{path}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise ValidationError(f"{path}:{line_number}: record must be an object")
        records.append(value)
    return records


def append_jsonl(path, record):
    """Append one record without rewriting earlier lines.

    Raw model responses use this path so a later response cannot alter an
    earlier response by accident.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(record)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
