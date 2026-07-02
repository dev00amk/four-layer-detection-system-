"""Domain exceptions exposed by Project Sentinel."""


class SentinelError(Exception):
    """Base class for expected, actionable pipeline failures."""


class ConfigurationError(SentinelError):
    """Raised when runtime configuration is invalid."""


class DataValidationError(SentinelError):
    """Raised when data violates a boundary or alignment contract."""


class SignalExecutionError(SentinelError):
    """Raised when the SQL signal library cannot produce any result."""


class ModelError(SentinelError):
    """Raised when model training, loading, or scoring cannot proceed."""


class EnrichmentError(SentinelError):
    """Raised when enrichment cannot preserve its required contract."""
