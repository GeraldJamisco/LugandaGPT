"""Errors raised when a benchmark record cannot be used as supplied."""


class BenchmarkError(ValueError):
    """Base class for benchmark record and workflow errors."""


class ValidationError(BenchmarkError):
    """A record is malformed or violates a controlled-value rule."""

    def __init__(self, message, field=None):
        self.field = field
        if field:
            message = f"{field}: {message}"
        super().__init__(message)


class WorkflowError(BenchmarkError):
    """A review, approval, or version transition is not supported."""


class ApprovalError(BenchmarkError):
    """An approval claim lacks a matching owner record or evidence."""


class RunError(BenchmarkError):
    """An evaluation run is incomplete, failed, or inconsistently recorded."""
