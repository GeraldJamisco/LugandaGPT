"""Errors raised before or during a training run."""


class TrainingError(ValueError):
    """Base class for training preparation and execution errors."""


class ConfigError(TrainingError):
    """The training configuration is missing, unknown, or inconsistent."""

    def __init__(self, message, field=None):
        self.field = field
        if field:
            message = f"{field}: {message}"
        super().__init__(message)


class DataError(TrainingError):
    """A pilot or evaluation record is not trainable as supplied."""

    def __init__(self, message, field=None, record_id=None):
        self.field = field
        self.record_id = record_id
        context = []
        if record_id:
            context.append(str(record_id))
        if field:
            context.append(str(field))
        if context:
            message = f"[{', '.join(context)}] {message}"
        super().__init__(message)


class ProvenanceError(DataError):
    """Dataset provenance, consent, licence, or review evidence is incomplete."""


class AuthorizationError(TrainingError):
    """Execution is not authorized by the configuration and project record."""


class EnvironmentError(TrainingError):
    """The local or Pod runtime does not match the pinned environment."""


class ArtifactError(TrainingError):
    """A run artifact is missing, unsafe, or does not match its checksum."""
