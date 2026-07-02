"""Typed exception hierarchy for Project Sentinel.

Every expected failure mode in the pipeline raises a subclass of
``SentinelError`` so entry points can distinguish operational failures
(logged and exited cleanly) from programming errors (allowed to propagate
with a full traceback).
"""
from __future__ import annotations


class SentinelError(Exception):
    """Base class for all expected Sentinel pipeline failures."""


class ConfigurationError(SentinelError):
    """Invalid or missing runtime configuration."""


class DataValidationError(SentinelError):
    """A data contract was violated: schema, row count, or alignment."""


class SignalExecutionError(SentinelError):
    """SQL signal execution failed beyond the tolerated threshold."""

    def __init__(self, message: str, failed_signals: list[str] | None = None):
        super().__init__(message)
        self.failed_signals = failed_signals or []


class ModelError(SentinelError):
    """Model fit, predict, or persistence failure."""


class EnrichmentError(SentinelError):
    """OSINT or feature-enrichment failure."""
