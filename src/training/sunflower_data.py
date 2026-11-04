"""Load and check the chat-format training rows for the Sunflower fine-tune.

No heavy imports. The runtime trainer applies the tokenizer chat template;
this module only validates structure and runs two safety nets:
  1. the held-out clock hours (D-020) must not leak into training, and
  2. no credential-looking string may be present in any example.
"""

import json
import re

from .errors import DataError

# Held-out clock times that must stay out of all training data (D-020), so the
# benchmark can test that the model generalises rather than memorises.
HELDOUT_PATTERN = re.compile(r"\b(8:00am|9:00am|10:00am|1:00pm|2:00pm)\b")

# Credential shapes that must never appear in training text.
_CREDENTIAL_PATTERNS = (
    re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"SUNBIRD_API_TOKEN"),
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),
)


def _scan_credentials(text, record_id):
    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(text):
            raise DataError("credential-like string in training text", record_id=record_id)


def load_training_rows(path):
    """Read a chat-format JSONL file. Each line must be
    {"id", "source", "messages":[{"role":"user"...},{"role":"assistant"...}]}.
    Returns the list of validated rows."""
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataError(f"line {line_no}: invalid JSON: {exc}")
            rid = row.get("id") or f"line-{line_no}"
            msgs = row.get("messages")
            if not isinstance(msgs, list) or len(msgs) < 2:
                raise DataError("needs at least a user and assistant message", record_id=rid)
            roles = [m.get("role") for m in msgs]
            if roles[0] != "user" or roles[-1] != "assistant":
                raise DataError("must start with user and end with assistant", record_id=rid)
            blob = " ".join(str(m.get("content", "")) for m in msgs)
            if not blob.strip():
                raise DataError("empty message content", record_id=rid)
            if HELDOUT_PATTERN.search(blob):
                raise DataError("held-out clock hour present (D-020)", record_id=rid)
            _scan_credentials(blob, rid)
            rows.append(row)
    if not rows:
        raise DataError("no training rows found")
    return rows


def summarise(rows):
    by_source = {}
    for row in rows:
        by_source[row.get("source", "?")] = by_source.get(row.get("source", "?"), 0) + 1
    return {"rows": len(rows), "by_source": by_source}
