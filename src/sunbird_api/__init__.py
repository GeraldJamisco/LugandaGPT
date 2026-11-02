"""Client and tools for the Sunbird AI API (Sunflower chat completions).

Importing this package makes no network request. The API token is read from
the environment only when a request is sent.
"""

from .client import (
    DEFAULT_MODEL,
    MODELS,
    ApiError,
    AuthError,
    BudgetGuardError,
    ChatResult,
    ConfigError,
    SunbirdClient,
    SunbirdError,
)

__all__ = [
    "DEFAULT_MODEL",
    "MODELS",
    "ApiError",
    "AuthError",
    "BudgetGuardError",
    "ChatResult",
    "ConfigError",
    "SunbirdClient",
    "SunbirdError",
]
