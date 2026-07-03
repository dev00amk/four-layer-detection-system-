"""Run the lightweight four-layer detection prototype end to end."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import DATABASE_PATH, SAMPLE_DATA_PATH
from src.layer1_ingestion.validator import Transaction, validate_transaction
from src.layer2_heuristics.rules import Signal, evaluate_rules
from src.layer3_ml.features import evaluate_baseline_deviation
from src.layer4_orchestration.db_logger import initialize_database, insert_alert

SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def build_alert(transaction: Transaction, signals: list[Signal]) -> dict[str, Any]:
    """Build a normalized alert from explainable signals."""
    risk_level = max(
        (signal["severity"] for signal in signals),
        key=lambda severity: SEVERITY_RANK[severity],
    )
    return {
        "alert_id": str(uuid4()),
        "transaction": transaction,
        "risk_level": risk_level,
        "signal_count": len(signals),
        "signals": signals,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _is_duplicate_transaction_error(error: sqlite3.IntegrityError) -> bool:
    """Return whether an integrity error is the expected idempotency conflict."""
    return "UNIQUE constraint failed: risk_alerts.transaction_id" in str(error)


def run(
    database_path: Path = DATABASE_PATH,
    sample_data_path: Path = SAMPLE_DATA_PATH,
) -> list[dict[str, Any]]:
    """Validate, score, persist, and return alerts from the sample data."""
    raw_transactions = json.loads(sample_data_path.read_text(encoding="utf-8"))
    if not isinstance(raw_transactions, list):
        raise ValueError("sample_transactions.json must contain a JSON array")

    transactions = [validate_transaction(item) for item in raw_transactions]
    transactions.sort(key=lambda item: item["timestamp"])
    initialize_database(database_path=database_path)

    history_by_user: dict[str, list[Transaction]] = {}
    alerts: list[dict[str, Any]] = []
    duplicates_skipped = 0
    for transaction in transactions:
        user_history = history_by_user.setdefault(transaction["user_id"], [])
        signals = evaluate_rules(transaction, user_history)
        signals.extend(evaluate_baseline_deviation(transaction, user_history))
        if signals:
            alert = build_alert(transaction, signals)
            try:
                insert_alert(alert, database_path=database_path)
            except sqlite3.IntegrityError as error:
                # Delivery retries and batch reruns must not create duplicate cases.
                if not _is_duplicate_transaction_error(error):
                    raise
                duplicates_skipped += 1
            else:
                alerts.append(alert)
        user_history.append(transaction)

    print(f"Persisted {len(alerts)} new alert(s) to {database_path}.")
    if duplicates_skipped:
        print(
            f"Skipped {duplicates_skipped} duplicate transaction(s) "
            "due to UNIQUE constraints."
        )
    return alerts


if __name__ == "__main__":
    import sys

    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SAMPLE_DATA_PATH
    generated_alerts = run(sample_data_path=input_path)
    print(json.dumps(generated_alerts, indent=2))
