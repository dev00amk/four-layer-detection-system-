"""Layer 3: transparent per-user statistical baseline features.

Each feature emits a LOW-severity Signal rather than a score so it composes
with Layer 2 output and gives investigators behavioral context instead of an
opaque number.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import pstdev

from config import (
    BASELINE_MIN_HISTORY,
    BASELINE_STD_THRESHOLD,
    FREQUENCY_SPIKE_THRESHOLD,
    FREQUENCY_SPIKE_WINDOW_HOURS,
    SUSPICIOUS_HOUR_END,
    SUSPICIOUS_HOUR_START,
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
    user_mean = sum(amounts) / len(amounts)
    user_std = pstdev(amounts)
    if user_std == 0:
        return None

    z_score = abs(transaction["amount"] - user_mean) / user_std
    if z_score <= BASELINE_STD_THRESHOLD:
        return None

    return {
        "rule_id": "BASELINE_AMOUNT_DEVIATION",
        "severity": "LOW",
        "reason": (
            f"Transaction amount deviates {z_score:.1f} standard deviations "
            f"from the user's historical mean of {user_mean:.2f}."
        ),
        "metadata": {
            "current_amount": transaction["amount"],
            "user_mean": round(user_mean, 2),
            "user_std": round(user_std, 2),
            "z_score": round(z_score, 2),
        },
    }


def check_hour_of_day_anomaly(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag a first-ever transaction in the overnight UTC hour band."""
    transaction_hour = _parse_timestamp(transaction["timestamp"]).hour
    if not SUSPICIOUS_HOUR_START <= transaction_hour <= SUSPICIOUS_HOUR_END:
        return None

    seen_in_band = any(
        SUSPICIOUS_HOUR_START
        <= _parse_timestamp(item["timestamp"]).hour
        <= SUSPICIOUS_HOUR_END
        for item in user_history
    )
    if seen_in_band:
        return None

    return {
        "rule_id": "HOUR_OF_DAY_ANOMALY",
        "severity": "LOW",
        "reason": (
            f"Transaction at {transaction_hour:02d}:00 UTC is the user's "
            f"first activity in the overnight {SUSPICIOUS_HOUR_START:02d}:00-"
            f"{SUSPICIOUS_HOUR_END:02d}:59 UTC window."
        ),
        "metadata": {
            "transaction_hour_utc": transaction_hour,
            "suspicious_hour_start": SUSPICIOUS_HOUR_START,
            "suspicious_hour_end": SUSPICIOUS_HOUR_END,
        },
    }


def check_transaction_frequency_spike(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag bursts of activity well above a normal daily transaction count."""
    current_time = _parse_timestamp(transaction["timestamp"])
    window_start = current_time - timedelta(hours=FREQUENCY_SPIKE_WINDOW_HOURS)
    transactions_in_window = 1 + sum(
        1
        for item in user_history
        if window_start <= _parse_timestamp(item["timestamp"]) <= current_time
    )
    if transactions_in_window <= FREQUENCY_SPIKE_THRESHOLD:
        return None

    return {
        "rule_id": "TRANSACTION_FREQUENCY_SPIKE",
        "severity": "LOW",
        "reason": (
            f"{transactions_in_window} transactions within the last "
            f"{FREQUENCY_SPIKE_WINDOW_HOURS} hours exceeds the expected "
            f"maximum of {FREQUENCY_SPIKE_THRESHOLD}."
        ),
        "metadata": {
            "transactions_in_window": transactions_in_window,
            "window_hours": FREQUENCY_SPIKE_WINDOW_HOURS,
            "threshold": FREQUENCY_SPIKE_THRESHOLD,
        },
    }


BASELINE_FEATURES = (
    check_baseline_amount_deviation,
    check_hour_of_day_anomaly,
    check_transaction_frequency_spike,
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
