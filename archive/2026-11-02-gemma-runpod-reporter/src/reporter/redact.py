"""Redaction applied before any collected data reaches a report.

Secret shaped values are replaced with [REDACTED]. The configured bot
token, if present in the environment, is removed from any text as well.
"""

import os
import re

from . import config

REDACTED = "[REDACTED]"

_PATTERNS = [
    # Telegram bot tokens: digits, colon, then the token body.
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_\-]{25,60}\b"),
    # Common provider key shapes.
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    # Assignment style leaks: api_key = "..."
    re.compile(
        r"(?i)\b(api[_\-]?key|secret|password|passwd|token|credential)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}[\"']?"
    ),
]


def redact(text: str) -> str:
    """Return text with secret shaped values replaced."""
    if not isinstance(text, str):
        return text
    out = text
    token = os.environ.get(config.TOKEN_ENV, "")
    if token:
        out = out.replace(token, REDACTED)
    for pattern in _PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def contains_secret(text: str) -> bool:
    """True when text still holds something that looks like a credential."""
    if not isinstance(text, str):
        return False
    token = os.environ.get(config.TOKEN_ENV, "")
    if token and token in text:
        return True
    for pattern in _PATTERNS:
        if pattern.search(text):
            return True
    return False


def redact_value(value):
    """Recursively redact every string inside dicts, lists and tuples."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value
