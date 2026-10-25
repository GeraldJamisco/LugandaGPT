"""Controlled values for the bounded Gemma 3 1B LoRA gate.

Changing a value here changes the approved experimental identity. Such a
change needs a documented decision and owner approval before it is used for
a paid run. The config validator compares the YAML file against these values
so a pinned base, tokenizer, adapter shape, or budget cannot drift silently.
"""

PINNED_BASE_ID = "google/gemma-3-1b-it"
PINNED_BASE_REVISION = "dcc83ea841ab6100d6b47a070329e1ba4cf78752"
PINNED_TOKENIZER_REVISION = PINNED_BASE_REVISION
PINNED_CHAT_TEMPLATE_SHA256 = (
    "7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4"
)
PINNED_PARAMETER_COUNT = 999_885_952
PINNED_PARAMETERS = {
    "hidden_size": 1152,
    "num_hidden_layers": 26,
    "vocab_size": 262_144,
    "context_limit": 32_768,
}
PINNED_EOS_TOKEN_ID = 1
PINNED_END_OF_TURN_TOKEN_ID = 106
PINNED_PAD_TOKEN_ID = 0
PINNED_BOS_TOKEN_ID = 2
PINNED_EOS_IDS = (PINNED_EOS_TOKEN_ID, PINNED_END_OF_TURN_TOKEN_ID)

PINNED_LORA = {
    "task_type": "CAUSAL_LM",
    "r": 16,
    "alpha": 32,
    "dropout": 0.05,
    "bias": "none",
    "use_dora": False,
    "use_rslora": False,
    "init_lora_weights": True,
    "modules_to_save": [],
    "expected_trainable_parameters": 13_045_760,
}
PINNED_LORA_TARGETS = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)

PINNED_DEPENDENCIES = {
    "python": "3.11",
    "torch": "2.7.1",
    "torch_cuda": "12.6",
    "transformers": "4.53.2",
    "peft": "0.18.1",
    "accelerate": "1.8.1",
    "bitsandbytes": "0.50.2",
    "datasets": "5.0.1",
    "trl": "0.20.0",
    "huggingface_hub": "0.34.3",
    "tokenizers": "0.21.4",
    "safetensors": "0.8.0",
    "sentencepiece": "0.2.2",
}
DISTRIBUTION_NAMES = {
    "huggingface_hub": "huggingface-hub",
}

CAPABILITIES = (
    "formal_comprehension",
    "formal_generation",
    "rewriting_formal_luganda",
    "question_answering",
    "instruction_following",
    "short_conversation",
)
CAPABILITY_COUNTS = {
    "formal_comprehension": 17,
    "formal_generation": 17,
    "rewriting_formal_luganda": 17,
    "question_answering": 17,
    "instruction_following": 16,
    "short_conversation": 16,
}
CAPABILITIES_REQUIRING_REFERENCE = frozenset(
    {
        "formal_comprehension",
        "rewriting_formal_luganda",
        "question_answering",
        "instruction_following",
    }
)
SPLITS = ("train", "validation", "heldout")
SPLIT_COUNTS = {"train": 70, "validation": 15, "heldout": 15}
PILOT_TOTAL = 100
EVALUATION_TOTAL = 24
EVALUATION_CAPABILITY_COUNTS = {name: 4 for name in CAPABILITIES}
AUDIT_FRACTION = 0.10

LANGUAGES = ("lg", "lg-en")
REGISTERS = ("formal", "everyday", "mixed")
REVIEW_STATUSES = (
    "draft",
    "ambiguity_checked",
    "native_reviewed",
    "approved",
    "excluded",
)
REVIEWER_ROLES = ("independent_review", "audit", "adjudicator")
REVIEW_DECISIONS = ("approved", "revise", "exclude")
REFERENCE_STATUSES = ("authored", "reviewed", "not_required")
SOURCE_TYPES = ("teacher_authored", "adapted", "project_original")
PII_STATUSES = ("none", "redacted", "needs_review")
UNCERTAINTY_BEHAVIORS = (
    "not_applicable",
    "state_uncertainty_if_unanswerable",
    "ask_clarifying_question_if_ambiguous",
)
VALIDATION_CHECKS = (
    "schema",
    "language",
    "instruction_response",
    "duplicate",
    "contamination",
    "pii",
    "token_length",
    "review_complete",
)

CASH_CAP_USD = 20.0
CREDIT_PURCHASE_USD = 10.0
HARD_CREDIT_STOP_USD = 8.0
LOW_BALANCE_ALERT_USD = 4.0
HARD_RUNTIME_HOURS = 6.0
GPU_HOURLY_USD = 0.89
CONTAINER_DISK_HOURLY_USD = 0.00410959
VOLUME_DISK_HOURLY_USD = 0.00273973
HOURLY_TOTAL_USD = 0.89684932
SIX_HOUR_TOTAL_USD = 5.38
MAX_STEPS = 30

NON_CONVERSATION_MAX_TOKENS = 512
CONVERSATION_MAX_TOKENS = 1024
TRAINING_MAX_LENGTH = 1024
NGRAM_SIZE = 8
