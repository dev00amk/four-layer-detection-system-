"""Per-rule effectiveness metrics computed from persisted alert outcomes.

Gives the investigator dashboard a feedback loop: for every rule, how often
it fires, and how its alerts were dispositioned once reviewed.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from config import DATABASE_PATH

_ANALYTICS_QUERY = """
    SELECT
        s.rule_id,
        COUNT(DISTINCT s.alert_id) AS alert_count,
        COUNT(DISTINCT CASE
            WHEN a.status = 'CLOSED' THEN s.alert_id
        END) AS closed_count,
        COUNT(DISTINCT CASE
            WHEN a.disposition = 'CONFIRMED_FRAUD' THEN s.alert_id
        END) AS confirmed_fraud_count,
        COUNT(DISTINCT CASE
            WHEN a.disposition = 'FALSE_POSITIVE' THEN s.alert_id
        END) AS false_positive_count
    FROM risk_alert_signals AS s
    JOIN risk_alerts AS a ON a.alert_id = s.alert_id
    GROUP BY s.rule_id
    ORDER BY alert_count DESC, s.rule_id
"""


def compute_rule_effectiveness(
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return hit, confirmed-fraud, and false-positive metrics per rule.

    Rates over reviewed outcomes are ``None`` until at least one alert
    carrying the rule has been closed, so an unreviewed rule is not shown
    as having a perfect record.
    """
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        total_alerts = connection.execute(
            "SELECT COUNT(*) FROM risk_alerts"
        ).fetchone()[0]
        rows = connection.execute(_ANALYTICS_QUERY).fetchall()

    metrics: list[dict[str, Any]] = []
    for row in rows:
        closed_count = row["closed_count"]
        metrics.append(
            {
                "rule_id": row["rule_id"],
                "alert_count": row["alert_count"],
                "hit_rate": (
                    round(row["alert_count"] / total_alerts, 4)
                    if total_alerts
                    else None
                ),
                "closed_count": closed_count,
                "confirmed_fraud_count": row["confirmed_fraud_count"],
                "false_positive_count": row["false_positive_count"],
                "confirmed_fraud_rate": (
                    round(row["confirmed_fraud_count"] / closed_count, 4)
                    if closed_count
                    else None
                ),
                "false_positive_rate": (
                    round(row["false_positive_count"] / closed_count, 4)
                    if closed_count
                    else None
                ),
            }
        )
    return metrics
