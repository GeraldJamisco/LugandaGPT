"""Shared helpers for authoring the English source pilot draft.

All examples in this package are original project material. They are English
source drafts only, not Luganda training data or native-reviewed references.
"""

import copy

CREATED_DATE = "2026-10-21"
SOURCE_PROVENANCE = {
    "origin": "project_original",
    "third_party_source": False,
    "created_date": CREATED_DATE,
    "author_role": "LugandaGPT engineering workflow",
    "rights_note": (
        "Original English source authored for this project. Translation and "
        "native-review terms are not yet recorded as formal agreements."
    ),
    "approval_reference": None,
}
OWNER_CONFIRMATION = {
    "reported_by": "Project Director",
    "report_date": CREATED_DATE,
    "statement": (
        "Native Luganda speakers are available and have agreed to collaborate. "
        "Working arrangements were discussed. Compensation is intended after "
        "the project earns its first dollar."
    ),
    "formal_agreements": (
        "Not documented yet. No signed agreement or formal consent record is "
        "present in the repository."
    ),
}


def item(
    item_id,
    collection,
    capability,
    prompt,
    criteria,
    reference_kind,
    reference,
    *,
    split=None,
    context=None,
    constraints=None,
    uncertainty="not_applicable",
    turns=None,
    register="formal",
    response_length="single_sentence",
    requires_prior_context=False,
    secondary=None,
    notes="Draft English source; translation and native review pending.",
):
    return {
        "item_id": item_id,
        "collection": collection,
        "primary_capability": capability,
        "secondary_capabilities": list(secondary or []),
        "source_language": "en",
        "source_prompt": prompt,
        "source_context": context,
        "expected_response_criteria": list(criteria),
        "reference_answer_or_rubric": {
            "kind": reference_kind,
            "content": reference,
        },
        "required_constraints": list(constraints or []),
        "uncertainty_behavior": uncertainty,
        "conversation_turns": list(turns or []),
        "intended_register": register,
        "proposed_split": split,
        "translation_status": "pending",
        "native_review_status": "pending",
        "source_provenance": copy.deepcopy(SOURCE_PROVENANCE),
        "response_length": response_length,
        "requires_prior_context": requires_prior_context,
        "notes": notes,
    }
