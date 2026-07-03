from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from main import run
from src.layer4_orchestration.case_workflow import assign_alert, close_alert
from src.layer4_orchestration.db_logger import initialize_database, insert_alert


def sample_alert(
    alert_id: str = "ALERT-1",
    transaction_id: str = "TXN-1",
) -> dict[str, Any]:
    return {
        "alert_id": alert_id,
        "transaction": {
            "transaction_id": transaction_id,
            "user_id": "USER-1",
            "amount": 1_500.0,
            "currency": "USD",
            "timestamp": "2026-07-03T12:00:00Z",
        },
        "risk_level": "MEDIUM",
        "signal_count": 1,
        "signals": [
            {
                "rule_id": "HIGH_AMOUNT_THRESHOLD",
                "severity": "MEDIUM",
                "reason": "Amount exceeded the configured threshold.",
                "metadata": {"threshold": 1_000.0},
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class CaseWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(database_path=self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def fetch_alert(self, alert_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM risk_alerts WHERE alert_id = ?",
                (alert_id,),
            ).fetchone()
        if row is None:
            self.fail(f"Expected alert {alert_id!r} to exist")
        return row

    def test_assign_alert_moves_open_to_in_progress(self) -> None:
        insert_alert(sample_alert(), database_path=self.database_path)

        assign_alert("ALERT-1", "analyst-7", database_path=self.database_path)

        alert = self.fetch_alert("ALERT-1")
        self.assertEqual(alert["status"], "IN_PROGRESS")
        self.assertEqual(alert["assigned_to"], "analyst-7")

    def test_close_alert_sets_disposition_notes_and_timestamp(self) -> None:
        insert_alert(sample_alert(), database_path=self.database_path)

        close_alert(
            "ALERT-1",
            "CONFIRMED_FRAUD",
            "Linked velocity and amount signals confirmed.",
            database_path=self.database_path,
        )

        alert = self.fetch_alert("ALERT-1")
        self.assertEqual(alert["status"], "CLOSED")
        self.assertEqual(alert["disposition"], "CONFIRMED_FRAUD")
        self.assertEqual(
            alert["investigator_notes"],
            "Linked velocity and amount signals confirmed.",
        )
        self.assertIsNotNone(alert["reviewed_at"])
        self.assertTrue(alert["reviewed_at"].endswith("Z"))

    def test_assign_alert_raises_when_alert_missing_or_not_open(self) -> None:
        insert_alert(sample_alert(), database_path=self.database_path)
        assign_alert("ALERT-1", "analyst-7", database_path=self.database_path)

        with self.assertRaisesRegex(ValueError, "not in OPEN status"):
            assign_alert("ALERT-1", "analyst-8", database_path=self.database_path)
        with self.assertRaisesRegex(ValueError, "does not exist"):
            assign_alert("MISSING", "analyst-8", database_path=self.database_path)

    def test_duplicate_transaction_is_rejected_by_database(self) -> None:
        insert_alert(sample_alert(), database_path=self.database_path)

        with self.assertRaises(sqlite3.IntegrityError):
            insert_alert(
                sample_alert(alert_id="ALERT-2", transaction_id="TXN-1"),
                database_path=self.database_path,
            )

    def test_main_rerun_skips_duplicate_transactions(self) -> None:
        first_run = run(database_path=self.database_path)
        second_run = run(database_path=self.database_path)

        self.assertEqual(len(first_run), 2)
        self.assertEqual(second_run, [])
        with closing(sqlite3.connect(self.database_path)) as connection:
            alert_count = connection.execute(
                "SELECT COUNT(*) FROM risk_alerts"
            ).fetchone()[0]
            signal_count = connection.execute(
                "SELECT COUNT(*) FROM risk_alert_signals"
            ).fetchone()[0]
        self.assertEqual(alert_count, 2)
        self.assertEqual(signal_count, 3)


if __name__ == "__main__":
    unittest.main()
