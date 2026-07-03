"""Layer 3: transparent per-user statistical baseline features.

Each feature emits a LOW-severity Signal rather than a score so it composes
with Layer 2 output and gives investigators behavioral context instead of an
opaque number.
"""
from __future__ import annotations

from datetime import datetime
from statistics import median, pstdev

from config import (
    BASELINE_MIN_HISTORY,
    BASELINE_STD_THRESHOLD,
    GAP_COMPRESSION_RATIO,
    GAP_MIN_HISTORY,
    UNUSUAL_HOUR_MIN_HISTORY,
)
from src.layer1_ingestion.validator import Transaction
from src.layer2_heuristics.rules import Signal


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_baseline_amount_deviation(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag amounts beyond the configured z-score of the user's own baseline."""
    if len(user_history) < BASELINE_MIN_HISTORY:
        return None

    amounts = [item["amount"] for item in user_history]
    mean_amount = sum(amounts) / len(amounts)
    std_amount = pstdev(amounts)
    if std_amount == 0:
        return None

    deviation = abs(transaction["amount"] - mean_amount) / std_amount
    if deviation <= BASELINE_STD_THRESHOLD:
        return None

    return {
        "rule_id": "BASELINE_AMOUNT_DEVIATION",
        "severity": "LOW",
        "reason": (
            f"Transaction amount deviates {deviation:.1f} standard deviations "
            f"from the user's historical mean of {mean_amount:.2f}."
        ),
        "metadata": {
            "current_amount": transaction["amount"],
            "user_mean_amount": round(mean_amount, 2),
            "user_std_amount": round(std_amount, 2),
            "deviation_std": round(deviation, 2),
            "std_threshold": BASELINE_STD_THRESHOLD,
            "history_count": len(user_history),
        },
    }


def check_unusual_hour_activity(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag activity at an hour of day (UTC) never seen in the user's history."""
    if len(user_history) < UNUSUAL_HOUR_MIN_HISTORY:
        return None

    observed_hours = sorted(
        {_parse_timestamp(item["timestamp"]).hour for item in user_history}
    )
    transaction_hour = _parse_timestamp(transaction["timestamp"]).hour
    if transaction_hour in observed_hours:
        return None

    return {
        "rule_id": "UNUSUAL_HOUR_ACTIVITY",
        "severity": "LOW",
        "reason": (
            f"Transaction at hour {transaction_hour:02d}:00 UTC falls outside "
            f"the user's historically observed activity hours."
        ),
        "metadata": {
            "transaction_hour": transaction_hour,
            "observed_hours": observed_hours,
            "history_count": len(user_history),
        },
    }


def check_transaction_gap_compression(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag an inter-transaction gap far shorter than the user's median cadence."""
    if len(user_history) < GAP_MIN_HISTORY:
        return None

    timestamps = sorted(
        _parse_timestamp(item["timestamp"]) for item in user_history
    )
    gaps = [
        (later - earlier).total_seconds()
        for earlier, later in zip(timestamps, timestamps[1:])
    ]
    median_gap = median(gaps)
    if median_gap <= 0:
        return None

    current_gap = (
        _parse_timestamp(transaction["timestamp"]) - timestamps[-1]
    ).total_seconds()
    if current_gap < 0 or current_gap >= median_gap * GAP_COMPRESSION_RATIO:
        return None

    return {
        "rule_id": "TRANSACTION_GAP_COMPRESSION",
        "severity": "LOW",
        "reason": (
            "Time since the user's previous transaction is far below their "
            "median transaction cadence."
        ),
        "metadata": {
            "current_gap_minutes": round(current_gap / 60, 2),
            "median_gap_minutes": round(median_gap / 60, 2),
            "compression_ratio": GAP_COMPRESSION_RATIO,
            "history_count": len(user_history),
        },
    }


BASELINE_FEATURES = (
    check_baseline_amount_deviation,
    check_unusual_hour_activity,
    check_transaction_gap_compression,
)


def evaluate_baseline_deviation(
    transaction: Transaction,
    user_history: list[Transaction],
) -> list[Signal]:
    """Evaluate every per-user statistical baseline feature."""
    signals: list[Signal] = []
    for feature in BASELINE_FEATURES:
        signal = feature(transaction, user_history)
        if signal is not None:
            signals.append(signal)
    return signals
