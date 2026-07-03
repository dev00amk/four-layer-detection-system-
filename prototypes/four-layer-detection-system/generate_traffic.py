"""Generate a synthetic transaction stream that exercises every detection rule.

Writes to generated_transactions.json (the curated sample_transactions.json is
left untouched so the exact-count tests keep passing). Amounts are seeded and
deterministic; timestamps are anchored to the most recent 20:00 UTC so the
stream looks fresh while scenario hours stay deterministic; transaction IDs
are unique per run so repeated runs ingest as new activity instead of being
deduplicated.

Usage:
    python generate_traffic.py [--seed 42] [--output generated_transactions.json]
    python main.py generated_transactions.json
    streamlit run dashboard.py
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from config import (
    DORMANCY_AMOUNT_THRESHOLD,
    DORMANCY_THRESHOLD_DAYS,
    FREQUENCY_SPIKE_THRESHOLD,
    MAX_TRANSACTIONS_PER_WINDOW,
    ROUND_AMOUNT_DIVISOR,
    STRUCTURING_MIN_PRIOR_TRANSACTIONS,
    STRUCTURING_SINGLE_THRESHOLD,
)

MINUTES_PER_DAY = 24 * 60


def _most_recent_evening_anchor() -> datetime:
    """Most recent 20:00 UTC, so relative offsets keep deterministic
    hours-of-day and scripted scenarios never drift into the overnight
    anomaly band regardless of when the generator runs."""
    current = datetime.now(timezone.utc)
    anchor = current.replace(hour=20, minute=0, second=0, microsecond=0)
    if anchor > current:
        anchor -= timedelta(days=1)
    return anchor


def _transaction(
    user_id: str,
    amount: float,
    timestamp: datetime,
) -> dict:
    return {
        "transaction_id": f"TXN-{uuid4().hex[:12].upper()}",
        "user_id": user_id,
        "amount": round(amount, 2),
        "currency": "USD",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
    }


def build_scenarios(
    seed: int = 42,
    base_time: datetime | None = None,
) -> list[dict]:
    """Return a chronologically sorted stream of scripted fraud scenarios.

    Each scenario is tuned against the thresholds in config.py so its target
    rule provably fires; tests/test_generate_traffic.py asserts this.
    """
    rng = random.Random(seed)
    now = base_time or _most_recent_evening_anchor()

    def at(minutes_ago: float) -> datetime:
        return now - timedelta(minutes=minutes_ago)

    transactions: list[dict] = []

    # Background noise: steady daily spenders that trigger nothing.
    # Five transactions each (below the 5-prior baseline minimum) in a
    # 40.0-90.0 band, so no amount can exceed 4x any possible running mean.
    for noise_index in range(3):
        user_id = f"USER-NOISE-{noise_index + 1}"
        start_day = 25 - noise_index * 7
        for day in range(5):
            transactions.append(
                _transaction(
                    user_id,
                    rng.uniform(40.0, 90.0),
                    at((start_day - day) * MINUTES_PER_DAY + rng.uniform(0, 300)),
                )
            )

    # STRUCTURING_PATTERN: enough sub-threshold priors inside the 72-hour
    # window that the aggregate (including current) clears the reporting bar.
    smurf_amount = STRUCTURING_SINGLE_THRESHOLD * 0.9
    for index in range(STRUCTURING_MIN_PRIOR_TRANSACTIONS):
        transactions.append(
            _transaction(
                "USER-STRUCTURING",
                smurf_amount + rng.uniform(-30.0, 30.0),
                at((62 - index * 16) * 60),
            )
        )
    transactions.append(_transaction("USER-STRUCTURING", 750.0, at(5)))

    # DORMANCY_BREAK: one small transaction well past the dormancy threshold,
    # then a large one now.
    transactions.append(
        _transaction(
            "USER-DORMANT",
            45.0,
            at((DORMANCY_THRESHOLD_DAYS + 15) * MINUTES_PER_DAY),
        )
    )
    transactions.append(
        _transaction("USER-DORMANT", DORMANCY_AMOUNT_THRESHOLD * 4.25, at(2))
    )

    # RAPID_TRANSACTION_COUNT: a card-testing burst inside the 10-minute window
    # (one more transaction than the per-window maximum).
    for index in range(MAX_TRANSACTIONS_PER_WINDOW + 1):
        transactions.append(
            _transaction(
                "USER-VELOCITY", rng.uniform(5.0, 15.0), at(9 - index * 2.5)
            )
        )

    # RAPID_AMOUNT_ESCALATION + BASELINE_AMOUNT_DEVIATION: six days of ~50.0
    # spending, then 450.0 today (9x the mean, far beyond 2.5 standard
    # deviations).
    for day in range(6, 0, -1):
        transactions.append(
            _transaction(
                "USER-ESCALATION",
                rng.uniform(45.0, 60.0),
                at(day * MINUTES_PER_DAY),
            )
        )
    transactions.append(_transaction("USER-ESCALATION", 450.0, at(1)))

    # TRANSACTION_FREQUENCY_SPIKE: one more transaction inside 24 hours than
    # the threshold allows, spaced widely enough to stay under the velocity
    # rule.
    for index in range(FREQUENCY_SPIKE_THRESHOLD + 1):
        transactions.append(
            _transaction(
                "USER-BURST", rng.uniform(45.0, 65.0), at(780 - index * 144)
            )
        )

    # ROUND_AMOUNT_SUSPICION (plus HIGH_AMOUNT_THRESHOLD): a large,
    # suspiciously round payment with no history.
    transactions.append(
        _transaction(
            "USER-ROUND", float(ROUND_AMOUNT_DIVISOR * 4), at(15)
        )
    )

    # HOUR_OF_DAY_ANOMALY: five daytime transactions, then the user's first
    # overnight activity at 03:14 UTC yesterday.
    for day in range(7, 2, -1):
        transactions.append(
            _transaction(
                "USER-NIGHT-OWL",
                rng.uniform(40.0, 90.0),
                at(day * MINUTES_PER_DAY).replace(hour=14, minute=30),
            )
        )
    transactions.append(
        _transaction(
            "USER-NIGHT-OWL",
            60.0,
            (now - timedelta(days=1)).replace(hour=3, minute=14),
        )
    )

    transactions.sort(key=lambda item: item["timestamp"])
    return transactions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=Path, default=Path("generated_transactions.json")
    )
    arguments = parser.parse_args()

    stream = build_scenarios(seed=arguments.seed)
    arguments.output.write_text(json.dumps(stream, indent=2), encoding="utf-8")

    users = sorted({item["user_id"] for item in stream})
    print(f"Wrote {len(stream)} transactions for {len(users)} users to "
          f"{arguments.output}.")
    print("Scenarios: structuring, dormancy break, velocity burst, amount "
          "escalation + baseline deviation, frequency spike, round amount, "
          "off-hours anomaly, plus silent background noise.")
    print(f"Next: python main.py {arguments.output}")


if __name__ == "__main__":
    main()
