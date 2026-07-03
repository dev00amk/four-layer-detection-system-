"""Investigator assignment and closure operations for persisted risk alerts."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH


def assign_alert(
    alert_id: str,
    analyst_id: str,
    database_path: Path = DATABASE_PATH,
) -> None:
    """Assign an open alert to an analyst and move it into active review."""
    if not alert_id.strip():
        raise ValueError("alert_id must be a non-empty string")
    if not analyst_id.strip():
        raise ValueError("analyst_id must be a non-empty string")

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            cursor = connection.execute(
                """
                UPDATE risk_alerts
                SET status = ?, assigned_to = ?
                WHERE alert_id = ? AND status = ?
                """,
                ("IN_PROGRESS", analyst_id.strip(), alert_id, "OPEN"),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    f"Alert {alert_id!r} does not exist or is not in OPEN status"
                )


def close_alert(
    alert_id: str,
    disposition: str,
    notes: str,
    database_path: Path = DATABASE_PATH,
) -> None:
    """Close an open or in-progress alert with an auditable disposition."""
    if not alert_id.strip():
        raise ValueError("alert_id must be a non-empty string")
    if not disposition.strip():
        raise ValueError("disposition must be a non-empty string")

    reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            cursor = connection.execute(
                """
                UPDATE risk_alerts
                SET
                    status = ?,
                    disposition = ?,
                    investigator_notes = ?,
                    reviewed_at = ?
                WHERE alert_id = ? AND status IN (?, ?)
                """,
                (
                    "CLOSED",
                    disposition.strip(),
                    notes.strip(),
                    reviewed_at,
                    alert_id,
                    "OPEN",
                    "IN_PROGRESS",
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    f"Alert {alert_id!r} does not exist or is not eligible for closure"
                )
