"""Exit-criteria verification against recorded evidence.

Automated checks can prove one of two things on their own: that a required
artifact is clearly missing (incomplete), or that supporting artifacts exist
while completeness still depends on judgement (needs review). They never
mark a criterion verified complete, because the reporter cannot prove that
documentation is internally consistent or that no secret was ever committed.
Only an explicit human verification record does that. A criterion with no
registered check is reported as not verified, which is honest about the gap
in automated coverage rather than silently passing it.
"""

import json
import re

from . import config, gitcollect


STATUS_VERIFIED_COMPLETE = "verified_complete"
STATUS_INCOMPLETE = "incomplete"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_NOT_VERIFIED = "not_verified"

STATUS_LABELS = {
    STATUS_VERIFIED_COMPLETE: "verified complete",
    STATUS_INCOMPLETE: "incomplete",
    STATUS_NEEDS_REVIEW: "needs review",
    STATUS_NOT_VERIFIED: "not verified",
}

# Statuses that always need a human decision before the phase can advance.
REQUIRES_HUMAN_REVIEW = (STATUS_NEEDS_REVIEW, STATUS_NOT_VERIFIED)

# Deliverables named by the Phase 0 section of docs/ROADMAP.md.
DOCUMENT_DELIVERABLES = ("AGENTS.md", "README.md", "data/README.md", ".gitignore")

ENVIRONMENT_HEADING = re.compile(r"^#{1,6}\s+.*environment", re.IGNORECASE)
ENVIRONMENT_DETAIL = re.compile(
    r"\bpython\b|\bram\b|\bmemory\b|\bdisk\b|\bhardware\b|\bgpu\b|\bcpu\b",
    re.IGNORECASE,
)

HUMAN_STATUS_WORDS = {
    "verified complete": STATUS_VERIFIED_COMPLETE,
    "verified_complete": STATUS_VERIFIED_COMPLETE,
    "complete": STATUS_VERIFIED_COMPLETE,
    "incomplete": STATUS_INCOMPLETE,
    "needs review": STATUS_NEEDS_REVIEW,
    "needs_review": STATUS_NEEDS_REVIEW,
    "not verified": STATUS_NOT_VERIFIED,
    "not_verified": STATUS_NOT_VERIFIED,
}


def _normalize(text):
    return re.sub(r"\s+", " ", str(text).strip().rstrip(".")).lower()


def _clean(value):
    """Keep generated evidence free of em and en dashes (project rule)."""
    return str(value).replace("\u2014", "-").replace("\u2013", "-")


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _documentation_check(context):
    """Phase 0 documentation deliverable check."""
    root = context.get("repo_root")
    docs_dir = context.get("docs_dir")
    present = []
    missing = []
    for relative in DOCUMENT_DELIVERABLES:
        path = (root / relative) if root else None
        if path is not None and path.exists():
            present.append(relative)
        else:
            missing.append(relative)
    docs_files = []
    if docs_dir is not None and docs_dir.exists():
        docs_files = sorted(path.name for path in docs_dir.glob("*.md"))
    evidence = []
    if present:
        evidence.append("present: " + ", ".join(present))
    if docs_files:
        evidence.append(f"docs Markdown files: {len(docs_files)}")
    if missing:
        evidence.append("missing: " + ", ".join(missing))
        return (
            STATUS_INCOMPLETE,
            evidence,
            "Required Phase 0 document(s) are missing.",
        )
    return (
        STATUS_NEEDS_REVIEW,
        evidence,
        "The inventory exists, but internal consistency is a judgement "
        "automation cannot confirm; human review required.",
    )


def _git_hygiene_check(context):
    """Phase 0 Git hygiene check: ignore rules and tracked generated data."""
    gitignore = context.get("gitignore_path")
    git = context.get("git") or {}
    tracked = context.get("tracked_reporter_files")
    evidence = []
    if gitignore is None or not gitignore.exists():
        evidence.append(".gitignore is missing")
        return (
            STATUS_INCOMPLETE,
            evidence,
            "Ignore rules are not in place.",
        )
    evidence.append(".gitignore present")
    if tracked:
        evidence.append("tracked reporter paths: " + ", ".join(sorted(tracked)))
        return (
            STATUS_INCOMPLETE,
            evidence,
            "Generated reporter data is tracked by Git; ignore rules are not "
            "in effect for it.",
        )
    if not git.get("available"):
        evidence.append("git inspection unavailable: " + str(git.get("error") or "unknown"))
    elif tracked is None:
        evidence.append("tracked file listing unavailable")
    else:
        evidence.append("no tracked path under reports/reporter/")
    return (
        STATUS_NEEDS_REVIEW,
        evidence,
        "Automation cannot prove that no secret was ever committed; human "
        "review required.",
    )


def _environment_check(context):
    """Phase 0 environment requirements check.

    Only a real Markdown heading about the environment counts, and the same
    file must mention concrete environment detail. A prose mention of
    "requirements" is not treated as an environment record.
    """
    docs_dir = context.get("docs_dir")
    found = []
    if docs_dir is not None and docs_dir.exists():
        for path in sorted(docs_dir.glob("*.md")):
            text = _read_text(path)
            if not ENVIRONMENT_DETAIL.search(text):
                continue
            heading = next(
                (
                    line.strip()
                    for line in text.splitlines()
                    if ENVIRONMENT_HEADING.search(line)
                ),
                None,
            )
            if heading:
                found.append(f"{path.name}: {heading}")
    if not found:
        return (
            STATUS_INCOMPLETE,
            [],
            "No documentation file records environment requirements.",
        )
    return (
        STATUS_NEEDS_REVIEW,
        found,
        "Environment requirements are recorded, but whether they are "
        "complete and current needs human review.",
    )


def _no_check(context):  # noqa: ARG001 - checker signature parity
    return (
        STATUS_NOT_VERIFIED,
        [],
        "No automated check is registered for this criterion and no evidence "
        "source is available; human review required.",
    )


def _checker_for(text):
    lowered = str(text).lower()
    if "documentation" in lowered:
        return _documentation_check
    if "git hygiene" in lowered or "no secrets" in lowered:
        return _git_hygiene_check
    if "environment" in lowered:
        return _environment_check
    return None


def _human_evidence(record):
    author = str(record.get("author") or "unrecorded author")
    verified_at = str(record.get("verified_at") or "time unavailable")
    note = str(record.get("note") or "").strip()
    if not note:
        return None
    return f"human verification by {author} at {verified_at}: {note}"


def _human_record(context, criterion):
    verifications = context.get("human_verifications") or {}
    return verifications.get(_normalize(criterion))


def verify_criteria(criteria, context):
    """Return one verification record per criterion text.

    Precedence: an explicit human verification record wins. Otherwise a
    registered automated check supplies the status. An unrecognized
    criterion is reported as not verified rather than assumed complete.
    """
    records = []
    for raw in criteria or []:
        criterion = str(raw).strip()
        human = _human_record(context, criterion)
        if human is not None:
            status_word = str(human.get("status") or "").strip().lower()
            status = HUMAN_STATUS_WORDS.get(status_word, STATUS_NEEDS_REVIEW)
            evidence = _human_evidence(human)
            if evidence:
                evidence_list = [evidence]
                reason = "Human verification record applied."
            else:
                evidence_list = []
                reason = (
                    "The human verification record has no supporting note; "
                    "evidence is unavailable."
                )
                if status == STATUS_VERIFIED_COMPLETE:
                    status = STATUS_NEEDS_REVIEW
                    reason += (
                        " The criterion is therefore not treated as verified "
                        "complete."
                    )
        else:
            checker = _checker_for(criterion)
            if checker is None:
                status, evidence_list, reason = _no_check(context)
            else:
                status, evidence_list, reason = checker(context)
        records.append(
            {
                "criterion": criterion,
                "status": status,
                "status_label": STATUS_LABELS[status],
                "evidence": [_clean(item) for item in evidence_list],
                "evidence_available": bool(evidence_list),
                "reason": _clean(reason),
                "human_review_required": status in REQUIRES_HUMAN_REVIEW,
            }
        )
    return records


def summarize(records):
    """Roll up verification records. A phase is complete only when every
    recorded criterion is verified complete, and there is at least one."""
    counts = {status: 0 for status in STATUS_LABELS}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    total = len(records)
    return {
        "total": total,
        "counts": counts,
        "verified_complete": counts[STATUS_VERIFIED_COMPLETE],
        "pending": total - counts[STATUS_VERIFIED_COMPLETE],
        "phase_complete": total > 0 and counts[STATUS_VERIFIED_COMPLETE] == total,
    }


def highest_priority(records):
    """Name a single highest-priority criterion only when evidence supports it.

    A lone incomplete criterion is an unambiguous gap and is named. A lone
    pending criterion of any status is also unambiguous. With several pending
    criteria, or several incomplete ones, no ordering is established and none
    is claimed.
    """
    incomplete = [r for r in records if r["status"] == STATUS_INCOMPLETE]
    pending = [r for r in records if r["status"] != STATUS_VERIFIED_COMPLETE]
    if len(incomplete) == 1:
        return {
            "criterion": incomplete[0]["criterion"],
            "basis": "the only criterion recorded as incomplete",
        }
    if not incomplete and len(pending) == 1:
        return {
            "criterion": pending[0]["criterion"],
            "basis": "the only criterion not verified complete",
        }
    if len(incomplete) > 1:
        return {
            "criterion": None,
            "basis": (
                f"{len(incomplete)} criteria are recorded as incomplete; the "
                "available evidence does not establish an ordering"
            ),
        }
    return {
        "criterion": None,
        "basis": (
            f"{len(pending)} criteria are not verified complete; the available "
            "evidence does not establish an ordering"
        ),
    }


def load_human_verifications():
    """Read optional owner verification records. Never writes the file.

    Shape: {"Phase 0": {"<criterion text>": {"status": "verified complete",
    "verified_at": ..., "author": ..., "note": ...}}}. A flat
    {"<criterion text>": {...}} map is also accepted.
    """
    path = config.EXIT_CRITERIA_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    records = {}
    for key, value in data.items():
        if isinstance(value, dict) and any(
            isinstance(inner, dict) for inner in value.values()
        ):
            for criterion, record in value.items():
                if isinstance(record, dict):
                    records[_normalize(criterion)] = record
        elif isinstance(value, dict):
            records[_normalize(key)] = value
    return records


def _tracked_reporter_files():
    """Tracked paths under reports/reporter/, or None when Git cannot answer."""
    try:
        raw = gitcollect._git(["ls-files", "--", "reports/reporter"])
    except Exception:  # GitError or any unexpected failure: evidence unavailable
        return None
    return [line.strip() for line in raw.splitlines() if line.strip()]


def build_context(data=None, verifications=None):
    """Assemble the evidence a verification check may read. Read-only."""
    git = (data or {}).get("git") or {}
    if verifications is None:
        verifications = load_human_verifications()
    return {
        "docs_dir": config.DOCS_DIR,
        "repo_root": config.REPO_ROOT,
        "gitignore_path": config.REPO_ROOT / ".gitignore",
        "git": git,
        "tracked_reporter_files": (
            _tracked_reporter_files() if git.get("available") else None
        ),
        "human_verifications": verifications,
    }
