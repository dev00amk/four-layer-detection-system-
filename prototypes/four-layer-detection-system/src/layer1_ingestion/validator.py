"""Layer 1: strictly validate and normalize incoming transaction payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


class Transaction(TypedDict):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    timestamp: str


class TransactionValidationError(ValueError):
    """Raised when a transaction violates the ingestion contract."""


REQUIRED_FIELDS = {
    "transaction_id",
    "user_id",
    "amount",
    "currency",
    "timestamp",
}


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise TransactionValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _normalize_timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise TransactionValidationError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransactionValidationError("timestamp must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise TransactionValidationError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_transaction(payload: Any) -> Transaction:
    """Return a clean, typed transaction or raise a validation error."""
    if not isinstance(payload, dict):
        raise TransactionValidationError("transaction payload must be an object")

    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        raise TransactionValidationError(
            f"missing required fields: {', '.join(missing)}"
        )

    amount = payload["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TransactionValidationError("amount must be numeric")
    if amount <= 0:
        raise TransactionValidationError("amount must be greater than zero")

    currency = _required_string(payload, "currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise TransactionValidationError(
            "currency must be a three-letter alphabetic code"
        )

    return {
        "transaction_id": _required_string(payload, "transaction_id"),
        "user_id": _required_string(payload, "user_id"),
        "amount": float(amount),
        "currency": currency,
        "timestamp": _normalize_timestamp(payload["timestamp"]),
    }
