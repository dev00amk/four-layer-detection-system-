import unittest

from src.layer1_ingestion.validator import Transaction
from src.layer2_heuristics.rules import evaluate_rules


def transaction(
    transaction_id: str,
    amount: float,
    timestamp: str,
) -> Transaction:
    return {
        "transaction_id": transaction_id,
        "user_id": "USER-1",
        "amount": amount,
        "currency": "USD",
        "timestamp": timestamp,
    }


class RuleTests(unittest.TestCase):
    """Exercise triggered and non-triggered Layer 2 rules."""
    def test_high_amount_rule_is_triggered(self) -> None:
        signals = evaluate_rules(
            transaction("TXN-1", 1_500.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["rule_id"], "HIGH_AMOUNT_THRESHOLD")
        self.assertEqual(signals[0]["severity"], "MEDIUM")
        self.assertTrue(signals[0]["reason"])

    def test_normal_transaction_triggers_no_rules(self) -> None:
        signals = evaluate_rules(
            transaction("TXN-1", 50.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertEqual(signals, [])

    def test_rapid_transaction_rule_is_triggered(self) -> None:
        history = [
            transaction("TXN-1", 50.0, "2026-07-03T12:00:00Z"),
            transaction("TXN-2", 50.0, "2026-07-03T12:02:00Z"),
            transaction("TXN-3", 50.0, "2026-07-03T12:04:00Z"),
        ]
        signals = evaluate_rules(
            transaction("TXN-4", 50.0, "2026-07-03T12:06:00Z"),
            history,
        )

        self.assertEqual(signals[0]["rule_id"], "RAPID_TRANSACTION_COUNT")


if __name__ == "__main__":
    unittest.main()
