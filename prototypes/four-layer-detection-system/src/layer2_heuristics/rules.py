"""Layer 2: deterministic and explainable transaction rules."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TypedDict

from config import (
    HIGH_AMOUNT_THRESHOLD,
    MAX_TRANSACTIONS_PER_WINDOW,
    WINDOW_SIZE_MINUTES,
)
from src.layer1_ingestion.validator import Transaction


class Signal(TypedDict):
    rule_id: str
    severity: str
    reason: str
    metadata: dict[str, Any]


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_rules(
    transaction: Transaction,
    user_history: list[Transaction],
) -> list[Signal]:
    """Evaluate Layer 2 rules against prior transactions for the same user."""
    signals: list[Signal] = []
    current_time = _parse_timestamp(transaction["timestamp"])
    window_start = current_time - timedelta(minutes=WINDOW_SIZE_MINUTES)
    recent_count = sum(
        1
        for previous in user_history
        if window_start <= _parse_timestamp(previous["timestamp"]) <= current_time
    )
    count_with_current = recent_count + 1

    if count_with_current > MAX_TRANSACTIONS_PER_WINDOW:
        signals.append(
            {
                "rule_id": "RAPID_TRANSACTION_COUNT",
                "severity": "HIGH",
                "reason": (
                    f"{count_with_current} transactions occurred within "
                    f"{WINDOW_SIZE_MINUTES} minutes; allowed maximum is "
                    f"{MAX_TRANSACTIONS_PER_WINDOW}."
                ),
                "metadata": {
                    "observed_count": count_with_current,
                    "window_minutes": WINDOW_SIZE_MINUTES,
                    "threshold": MAX_TRANSACTIONS_PER_WINDOW,
                },
            }
        )

    if transaction["amount"] >= HIGH_AMOUNT_THRESHOLD:
        signals.append(
            {
                "rule_id": "HIGH_AMOUNT_THRESHOLD",
                "severity": "MEDIUM",
                "reason": (
                    f"Transaction amount {transaction['amount']:.2f} "
                    f"{transaction['currency']} meets or exceeds the "
                    f"{HIGH_AMOUNT_THRESHOLD:.2f} threshold."
                ),
                "metadata": {
                    "observed_amount": transaction["amount"],
                    "threshold": HIGH_AMOUNT_THRESHOLD,
                },
            }
        )

    return signals
