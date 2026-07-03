"""Layer 4: atomic SQLite persistence for alerts and signals."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config import DATABASE_PATH, SCHEMA_PATH
from src.layer2_heuristics.rules import Signal


def initialize_database(
    database_path: Path = DATABASE_PATH,
    schema_path: Path = SCHEMA_PATH,
) -> None:
    """Initialize SQLite from the versioned schema file."""
    schema = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)


def insert_alert(
    alert: dict[str, Any],
    database_path: Path = DATABASE_PATH,
) -> None:
    """Persist an alert and all related signals atomically."""
    signals: list[Signal] = alert["signals"]
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute(
                """
                INSERT INTO risk_alerts (
                    alert_id,
                    transaction_id,
                    user_id,
                    risk_level,
                    transaction_payload,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["alert_id"],
                    alert["transaction"]["transaction_id"],
                    alert["transaction"]["user_id"],
                    alert["risk_level"],
                    json.dumps(alert["transaction"], sort_keys=True),
                    alert["created_at"],
                ),
            )
            connection.executemany(
                """
                INSERT INTO risk_alert_signals (
                    alert_id,
                    rule_id,
                    severity,
                    reason,
                    signal_metadata
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        alert["alert_id"],
                        signal["rule_id"],
                        signal["severity"],
                        signal["reason"],
                        json.dumps(signal["metadata"], sort_keys=True),
                    )
                    for signal in signals
                ],
            )
