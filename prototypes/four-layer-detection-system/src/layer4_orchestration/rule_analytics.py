"""Per-rule effectiveness summaries from the rule_analytics outcome ledger.

Gives the investigator dashboard a feedback loop: for every rule, how often
it fires and how its alerts were dispositioned once reviewed. Kept free of
Streamlit so the aggregation logic is unit-testable on its own.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from config import DATABASE_PATH

_SUMMARY_QUERY = """
    SELECT
        rule_id,
        COUNT(*) AS total_hits,
        SUM(CASE WHEN disposition = 'CONFIRMED_FRAUD' THEN 1 ELSE 0 END)
            AS confirmed_fraud,
        SUM(CASE WHEN disposition = 'FALSE_POSITIVE' THEN 1 ELSE 0 END)
            AS false_positives,
        SUM(CASE WHEN disposition IS NULL THEN 1 ELSE 0 END)
            AS pending_review
    FROM rule_analytics
    GROUP BY rule_id
    ORDER BY total_hits DESC, rule_id
"""


def _hit_rate_pct(confirmed_fraud: int, total_hits: int) -> float:
    """Confirmed fraud as a percentage of every alert the rule fired on."""
    if total_hits == 0:
        return 0.0
    return round(confirmed_fraud / total_hits * 100, 1)


def summarize_rule_effectiveness(
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return one summary row per rule, busiest rules first."""
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(_SUMMARY_QUERY).fetchall()

    return [
        {
            "rule_id": row["rule_id"],
            "total_hits": row["total_hits"],
            "confirmed_fraud": row["confirmed_fraud"],
            "false_positives": row["false_positives"],
            "pending_review": row["pending_review"],
            "hit_rate_pct": _hit_rate_pct(
                row["confirmed_fraud"], row["total_hits"]
            ),
        }
        for row in rows
    ]
