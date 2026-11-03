"""Conservative spelling normaliser for group-written Luganda.

Only the standards the group decided on 2026-11-03 are applied:
ssaawa (hours; saawa means the clock), ez'emisana, kkumi, kkumi na bbiri,
ez'okumakya, ez'ekiro and eza kawungeezi.
Everything else is left exactly as written. The raw text is always kept.
"""

import re

_RULES = (
    (re.compile(r"\bkk?umi\s*na\s*bbiri\b", re.I), "kkumi na bbiri"),
    (re.compile(r"\bkk?umi\s*nabbiri\b", re.I), "kkumi na bbiri"),
    (re.compile(r"\bkuminabbiri\b", re.I), "kkumi na bbiri"),
    (re.compile(r"\bkumi\b"), "kkumi"),
    (re.compile(r"\bKumi\b"), "Kkumi"),
    (re.compile(r"\bsaawa\b"), "ssaawa"),
    (re.compile(r"\bSaawa\b"), "Ssaawa"),
    (re.compile(r"\bezemisana\b"), "ez'emisana"),
    (re.compile(r"\bEzemisana\b"), "Ez'emisana"),
    (re.compile(r"\bezokumakya\b"), "ez'okumakya"),
    (re.compile(r"\bezekiro\b"), "ez'ekiro"),
    (re.compile(r"\bezakawungeezi\b"), "eza kawungeezi"),
    # singular hour "emu" (ssaawa emu), consistent with the agreed plural forms
    (re.compile(r"\beyokumakya\b"), "ey'okumakya"),
    (re.compile(r"\beyakawungeezi\b"), "eya kawungeezi"),
)


def normalize(text):
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text
