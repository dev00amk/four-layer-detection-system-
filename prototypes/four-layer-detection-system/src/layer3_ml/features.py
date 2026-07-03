"""Layer 3: transparent statistical-baseline placeholder."""
from __future__ import annotations

from config import BASELINE_MULTIPLIER
from src.layer1_ingestion.validator import Transaction
from src.layer2_heuristics.rules import Signal


def evaluate_baseline_deviation(
    transaction: Transaction,
    user_history: list[Transaction],
) -> list[Signal]:
    """Flag amounts at or above the configured multiple of historical average."""
    historical_amounts = [item["amount"] for item in user_history]
    if not historical_amounts:
        return []

    historical_average = sum(historical_amounts) / len(historical_amounts)
    threshold = historical_average * BASELINE_MULTIPLIER
    if transaction["amount"] < threshold:
        return []

    return [
        {
            "rule_id": "ML_BASELINE_DEVIATION",
            "severity": "HIGH",
            "reason": (
                f"Transaction amount {transaction['amount']:.2f} is at least "
                f"{BASELINE_MULTIPLIER:.1f}x the user's historical average "
                f"of {historical_average:.2f}."
            ),
            "metadata": {
                "observed_amount": transaction["amount"],
                "historical_average": round(historical_average, 2),
                "baseline_multiplier": BASELINE_MULTIPLIER,
                "history_count": len(historical_amounts),
            },
        }
    ]
