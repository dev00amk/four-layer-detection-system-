from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.layer4_orchestration.case_workflow import close_alert
from src.layer4_orchestration.db_logger import initialize_database, insert_alert
from src.layer4_orchestration.rule_analytics import compute_rule_effectiveness


def alert_with_rules(
    alert_id: str,
    transaction_id: str,
    rule_ids: list[str],
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
        "risk_level": "HIGH",
        "signal_count": len(rule_ids),
        "signals": [
            {
                "rule_id": rule_id,
                "severity": "HIGH",
                "reason": "Synthetic signal for analytics tests.",
                "metadata": {},
            }
            for rule_id in rule_ids
        ],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class RuleAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(database_path=self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_returns_empty_metrics_for_empty_database(self) -> None:
        self.assertEqual(
            compute_rule_effectiveness(database_path=self.database_path),
            [],
        )

    def test_computes_hit_and_disposition_rates_per_rule(self) -> None:
        insert_alert(
            alert_with_rules("ALERT-1", "TXN-1", ["DORMANCY_BREAK"]),
            database_path=self.database_path,
        )
        insert_alert(
            alert_with_rules(
                "ALERT-2",
                "TXN-2",
                ["DORMANCY_BREAK", "ROUND_AMOUNT_SUSPICION"],
            ),
            database_path=self.database_path,
        )
        insert_alert(
            alert_with_rules("ALERT-3", "TXN-3", ["ROUND_AMOUNT_SUSPICION"]),
            database_path=self.database_path,
        )
        close_alert(
            "ALERT-1",
            "CONFIRMED_FRAUD",
            "Verified with the customer.",
            database_path=self.database_path,
        )
        close_alert(
            "ALERT-2",
            "FALSE_POSITIVE",
            "Legitimate seasonal purchase.",
            database_path=self.database_path,
        )

        metrics = {
            row["rule_id"]: row
            for row in compute_rule_effectiveness(database_path=self.database_path)
        }

        dormancy = metrics["DORMANCY_BREAK"]
        self.assertEqual(dormancy["alert_count"], 2)
        self.assertEqual(dormancy["hit_rate"], round(2 / 3, 4))
        self.assertEqual(dormancy["closed_count"], 2)
        self.assertEqual(dormancy["confirmed_fraud_count"], 1)
        self.assertEqual(dormancy["false_positive_count"], 1)
        self.assertEqual(dormancy["confirmed_fraud_rate"], 0.5)
        self.assertEqual(dormancy["false_positive_rate"], 0.5)

        round_amount = metrics["ROUND_AMOUNT_SUSPICION"]
        self.assertEqual(round_amount["alert_count"], 2)
        self.assertEqual(round_amount["closed_count"], 1)
        self.assertEqual(round_amount["confirmed_fraud_count"], 0)
        self.assertEqual(round_amount["false_positive_count"], 1)
        self.assertEqual(round_amount["confirmed_fraud_rate"], 0.0)
        self.assertEqual(round_amount["false_positive_rate"], 1.0)

    def test_rates_are_none_until_an_alert_is_reviewed(self) -> None:
        insert_alert(
            alert_with_rules("ALERT-1", "TXN-1", ["STRUCTURING_PATTERN"]),
            database_path=self.database_path,
        )

        metrics = compute_rule_effectiveness(database_path=self.database_path)

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["rule_id"], "STRUCTURING_PATTERN")
        self.assertEqual(metrics[0]["alert_count"], 1)
        self.assertEqual(metrics[0]["closed_count"], 0)
        self.assertIsNone(metrics[0]["confirmed_fraud_rate"])
        self.assertIsNone(metrics[0]["false_positive_rate"])


if __name__ == "__main__":
    unittest.main()
