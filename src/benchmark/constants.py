"""Controlled values copied from the benchmark specification.

Keep these names aligned with ``docs/BENCHMARK-SPECIFICATION.md``. A change
to a category or dimension is a major benchmark change under section 15.
"""

CATEGORY_TO_PREFIX = {
    "formal_luganda": "FORMAL",
    "everyday_luganda": "EVERYDAY",
    "colloquial": "COLLOQUIAL",
    "code_switching": "CODESWITCH",
    "instruction_following": "INSTRUCTION",
    "multi_turn": "MULTITURN",
    "explanation_reasoning": "EXPLANATION",
    "cultural_interpretation": "CULTURAL",
    "factuality_uncertainty": "FACTUALITY",
}

CATEGORY_CODES = tuple(CATEGORY_TO_PREFIX)
ID_PREFIXES = tuple(CATEGORY_TO_PREFIX.values())

DIMENSION_NAMES = (
    "semantic_correctness",
    "grammar_naturalness",
    "instruction_compliance",
    "relevance",
    "context_retention",
    "factual_reliability",
    "appropriate_register",
)

TRACKS = ("conversational", "translation_probe")
PROMPT_LANGUAGES = ("lg", "lg-en", "en")
RESPONSE_LANGUAGES = ("lg", "lg-en", "en", "model_choice")
REFERENCE_STATUSES = ("authored", "pending", "not_applicable")
REVIEW_STATUSES = (
    "draft",
    "ambiguity_checked",
    "native_reviewed",
    "approved",
    "excluded",
)
SOURCE_TYPES = ("original", "salt", "flores", "mafand", "wikipedia", "other")
AUTHOR_ROLES = (
    "benchmark_author",
    "native_reviewer",
    "adjudicator",
    "project_owner",
)
REVIEWER_NOTE_FLAGS = ("none", "ambiguity", "contamination", "safety", "other")

REVIEW_ROLES = ("native_reviewer", "adjudicator")
AMBIGUITY_REVIEWER_ROLES = ("native_reviewer", "fluent_reviewer")
AMBIGUITY_OUTCOMES = ("clear", "revised", "intrinsic_ambiguity", "unresolved")
ITEM_REVIEW_DECISIONS = ("accept", "revise", "exclude")

FAILURE_CODES = (
    "wrong_language",
    "refusal",
    "hallucination",
    "truncation",
    "unsafe",
    "off_topic",
    "format_violation",
    "empty",
)

RUN_STATUSES = ("planned", "running", "completed", "failed", "incomplete", "excluded")
COST_KINDS = ("none", "local_compute", "paid_api", "native_review", "storage", "other")

REVIEW_TRANSITIONS = {
    "draft": ("ambiguity_checked", "excluded"),
    "ambiguity_checked": ("native_reviewed", "excluded"),
    "native_reviewed": ("approved", "excluded"),
    "approved": ("excluded",),
    "excluded": (),
}

ITEM_ALLOWED_FIELDS = frozenset(
    {
        "id",
        "benchmark_version",
        "track",
        "category",
        "prompt_language",
        "response_language",
        "prompt",
        "turns",
        "expected_behavior",
        "reference_answer",
        "reference_status",
        "accepted_alternatives",
        "scoring_dimensions",
        "ambiguity_notes",
        "cultural_note",
        "contamination_notes",
        "review_status",
        "reviewer_notes",
        "source",
        "author",
        "created_at",
        "updated_at",
    }
)

ITEM_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "benchmark_version",
        "track",
        "category",
        "prompt_language",
        "response_language",
        "prompt",
        "turns",
        "expected_behavior",
        "reference_status",
        "scoring_dimensions",
        "ambiguity_notes",
        "contamination_notes",
        "review_status",
        "reviewer_notes",
        "source",
        "author",
        "created_at",
        "updated_at",
    }
)

REVIEWER_NOTE_FIELDS = frozenset(
    {"reviewer_id", "role", "date", "dimension", "score", "note", "flag"}
)

REVIEW_RECORD_FIELDS = frozenset(
    {
        "review_id",
        "item_id",
        "run_id",
        "reviewer_id",
        "role",
        "date",
        "calibration_completed",
        "dimension",
        "score",
        "note",
        "flag",
        "failure_codes",
        "adjudication_required",
        "adjudicated_score",
        "adjudicator_id",
        "adjudication_note",
    }
)
