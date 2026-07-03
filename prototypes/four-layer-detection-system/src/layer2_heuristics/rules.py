"""Layer 2: deterministic and explainable transaction rules."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TypedDict

from config import (
    DORMANCY_AMOUNT_THRESHOLD,
    DORMANCY_THRESHOLD_DAYS,
    ESCALATION_MIN_HISTORY,
    ESCALATION_MULTIPLIER,
    HIGH_AMOUNT_THRESHOLD,
    MAX_TRANSACTIONS_PER_WINDOW,
    ROUND_AMOUNT_DIVISOR,
    ROUND_AMOUNT_MINIMUM,
    STRUCTURING_AGGREGATE_THRESHOLD,
    STRUCTURING_MIN_PRIOR_TRANSACTIONS,
    STRUCTURING_SINGLE_THRESHOLD,
    STRUCTURING_WINDOW_HOURS,
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


def check_dormancy_break(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag a large first transaction after a long inactive period."""
    if not user_history:
        return None
    if transaction["amount"] <= DORMANCY_AMOUNT_THRESHOLD:
        return None

    current_time = _parse_timestamp(transaction["timestamp"])
    last_time = max(
        _parse_timestamp(previous["timestamp"]) for previous in user_history
    )
    gap = current_time - last_time
    if gap <= timedelta(days=DORMANCY_THRESHOLD_DAYS):
        return None

    return {
        "rule_id": "DORMANCY_BREAK",
        "severity": "HIGH",
        "reason": (
            f"First transaction after {gap.days}-day dormancy period exceeds "
            f"amount threshold."
        ),
        "metadata": {
            "days_since_last_transaction": gap.days,
            "dormancy_threshold_days": DORMANCY_THRESHOLD_DAYS,
            "amount": transaction["amount"],
        },
    }


def check_structuring_pattern(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag many sub-threshold transactions that aggregate above the reporting bar.

    Models the structuring / smurfing typology: a subject deliberately keeps
    individual amounts below detection thresholds while moving large aggregate
    volume inside a short window.
    """
    if transaction["amount"] >= STRUCTURING_SINGLE_THRESHOLD:
        return None

    current_time = _parse_timestamp(transaction["timestamp"])
    window_start = current_time - timedelta(hours=STRUCTURING_WINDOW_HOURS)
    qualifying = [
        previous
        for previous in user_history
        if previous["amount"] < STRUCTURING_SINGLE_THRESHOLD
        and window_start <= _parse_timestamp(previous["timestamp"]) <= current_time
    ]
    if len(qualifying) < STRUCTURING_MIN_PRIOR_TRANSACTIONS:
        return None

    aggregate = sum(item["amount"] for item in qualifying) + transaction["amount"]
    if aggregate <= STRUCTURING_AGGREGATE_THRESHOLD:
        return None

    transaction_count = len(qualifying) + 1
    return {
        "rule_id": "STRUCTURING_PATTERN",
        "severity": "HIGH",
        "reason": (
            f"{transaction_count} transactions below individual threshold "
            f"aggregate above reporting threshold within "
            f"{STRUCTURING_WINDOW_HOURS}-hour window."
        ),
        "metadata": {
            "transaction_count": transaction_count,
            "aggregate_amount": round(aggregate, 2),
            "window_hours": STRUCTURING_WINDOW_HOURS,
            "single_threshold": STRUCTURING_SINGLE_THRESHOLD,
            "aggregate_threshold": STRUCTURING_AGGREGATE_THRESHOLD,
        },
    }


def check_rapid_amount_escalation(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag amounts far above the user's own historical mean.

    A user-relative threshold reduces false positives on legitimately
    high-spending users compared with a fixed global amount cutoff.
    """
    if len(user_history) < ESCALATION_MIN_HISTORY:
        return None

    mean_amount = sum(item["amount"] for item in user_history) / len(user_history)
    if transaction["amount"] <= mean_amount * ESCALATION_MULTIPLIER:
        return None

    multiplier = round(transaction["amount"] / mean_amount, 2)
    return {
        "rule_id": "RAPID_AMOUNT_ESCALATION",
        "severity": "MEDIUM",
        "reason": (
            f"Transaction amount is {multiplier}x the user's historical mean."
        ),
        "metadata": {
            "current_amount": transaction["amount"],
            "user_mean_amount": round(mean_amount, 2),
            "multiplier": multiplier,
            "history_count": len(user_history),
        },
    }


def check_round_amount_suspicion(
    transaction: Transaction,
    user_history: list[Transaction],
) -> Signal | None:
    """Flag suspiciously round amounts, a low-signal composite-scoring input."""
    amount = transaction["amount"]
    if amount < ROUND_AMOUNT_MINIMUM or amount % ROUND_AMOUNT_DIVISOR != 0:
        return None

    return {
        "rule_id": "ROUND_AMOUNT_SUSPICION",
        "severity": "LOW",
        "reason": (
            "Transaction is a suspiciously round amount, a common indicator "
            "of manual fraud or structured payments."
        ),
        "metadata": {
            "amount": amount,
            "round_divisor": ROUND_AMOUNT_DIVISOR,
        },
    }


BEHAVIORAL_RULES = (
    check_dormancy_break,
    check_structuring_pattern,
    check_rapid_amount_escalation,
    check_round_amount_suspicion,
)


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

    for rule in BEHAVIORAL_RULES:
        signal = rule(transaction, user_history)
        if signal is not None:
            signals.append(signal)

    return signals
