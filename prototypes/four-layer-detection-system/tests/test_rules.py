import unittest

from src.layer1_ingestion.validator import Transaction
from src.layer2_heuristics.rules import (
    check_dormancy_break,
    check_rapid_amount_escalation,
    check_round_amount_suspicion,
    check_structuring_pattern,
    evaluate_rules,
)


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
            transaction("TXN-1", 1_234.5, "2026-07-03T12:00:00Z"),
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


class DormancyBreakTests(unittest.TestCase):
    def test_fires_after_long_gap_with_large_amount(self) -> None:
        history = [transaction("TXN-1", 80.0, "2026-05-01T09:00:00Z")]

        signal = check_dormancy_break(
            transaction("TXN-2", 250.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "DORMANCY_BREAK")
        self.assertEqual(signal["severity"], "HIGH")
        self.assertEqual(signal["metadata"]["days_since_last_transaction"], 63)
        self.assertEqual(signal["metadata"]["dormancy_threshold_days"], 45)
        self.assertEqual(signal["metadata"]["amount"], 250.0)

    def test_does_not_fire_without_history(self) -> None:
        signal = check_dormancy_break(
            transaction("TXN-1", 250.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertIsNone(signal)

    def test_does_not_fire_for_small_amount_after_gap(self) -> None:
        history = [transaction("TXN-1", 80.0, "2026-05-01T09:00:00Z")]

        signal = check_dormancy_break(
            transaction("TXN-2", 150.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNone(signal)

    def test_does_not_fire_when_gap_is_below_threshold(self) -> None:
        history = [transaction("TXN-1", 80.0, "2026-06-01T09:00:00Z")]

        signal = check_dormancy_break(
            transaction("TXN-2", 250.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNone(signal)


class StructuringPatternTests(unittest.TestCase):
    def history(self) -> list[Transaction]:
        return [
            transaction("TXN-1", 900.0, "2026-07-01T10:00:00Z"),
            transaction("TXN-2", 850.0, "2026-07-01T18:00:00Z"),
            transaction("TXN-3", 950.0, "2026-07-02T09:00:00Z"),
            transaction("TXN-4", 800.0, "2026-07-02T20:00:00Z"),
        ]

    def test_fires_for_sub_threshold_transactions_above_aggregate(self) -> None:
        signal = check_structuring_pattern(
            transaction("TXN-5", 700.0, "2026-07-03T12:00:00Z"),
            self.history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "STRUCTURING_PATTERN")
        self.assertEqual(signal["severity"], "HIGH")
        self.assertEqual(signal["metadata"]["transaction_count"], 5)
        self.assertEqual(signal["metadata"]["aggregate_amount"], 4_200.0)
        self.assertEqual(signal["metadata"]["window_hours"], 72)

    def test_does_not_fire_with_too_few_prior_transactions(self) -> None:
        signal = check_structuring_pattern(
            transaction("TXN-5", 700.0, "2026-07-03T12:00:00Z"),
            self.history()[:3],
        )

        self.assertIsNone(signal)

    def test_does_not_fire_below_aggregate_threshold(self) -> None:
        low_history = [
            transaction(f"TXN-{index}", 400.0, timestamp)
            for index, timestamp in enumerate(
                [
                    "2026-07-01T10:00:00Z",
                    "2026-07-01T18:00:00Z",
                    "2026-07-02T09:00:00Z",
                    "2026-07-02T20:00:00Z",
                ],
                start=1,
            )
        ]

        signal = check_structuring_pattern(
            transaction("TXN-5", 400.0, "2026-07-03T12:00:00Z"),
            low_history,
        )

        self.assertIsNone(signal)

    def test_does_not_count_transactions_outside_window(self) -> None:
        stale_history = [
            transaction("TXN-1", 900.0, "2026-06-20T10:00:00Z"),
            transaction("TXN-2", 850.0, "2026-06-21T18:00:00Z"),
            transaction("TXN-3", 950.0, "2026-07-02T09:00:00Z"),
            transaction("TXN-4", 800.0, "2026-07-02T20:00:00Z"),
        ]

        signal = check_structuring_pattern(
            transaction("TXN-5", 700.0, "2026-07-03T12:00:00Z"),
            stale_history,
        )

        self.assertIsNone(signal)


class RapidAmountEscalationTests(unittest.TestCase):
    def test_fires_when_amount_exceeds_multiplier_of_mean(self) -> None:
        history = [
            transaction("TXN-1", 100.0, "2026-07-01T10:00:00Z"),
            transaction("TXN-2", 110.0, "2026-07-01T18:00:00Z"),
            transaction("TXN-3", 90.0, "2026-07-02T09:00:00Z"),
        ]

        signal = check_rapid_amount_escalation(
            transaction("TXN-4", 450.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "RAPID_AMOUNT_ESCALATION")
        self.assertEqual(signal["severity"], "MEDIUM")
        self.assertEqual(signal["metadata"]["user_mean_amount"], 100.0)
        self.assertEqual(signal["metadata"]["multiplier"], 4.5)
        self.assertEqual(signal["metadata"]["history_count"], 3)

    def test_does_not_fire_with_insufficient_history(self) -> None:
        history = [
            transaction("TXN-1", 100.0, "2026-07-01T10:00:00Z"),
            transaction("TXN-2", 110.0, "2026-07-01T18:00:00Z"),
        ]

        signal = check_rapid_amount_escalation(
            transaction("TXN-3", 450.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNone(signal)

    def test_does_not_fire_for_high_spender_within_baseline(self) -> None:
        history = [
            transaction("TXN-1", 2_000.0, "2026-07-01T10:00:00Z"),
            transaction("TXN-2", 2_200.0, "2026-07-01T18:00:00Z"),
            transaction("TXN-3", 1_800.0, "2026-07-02T09:00:00Z"),
        ]

        signal = check_rapid_amount_escalation(
            transaction("TXN-4", 3_000.0, "2026-07-03T12:00:00Z"),
            history,
        )

        self.assertIsNone(signal)


class RoundAmountSuspicionTests(unittest.TestCase):
    def test_fires_for_round_amount_at_or_above_minimum(self) -> None:
        signal = check_round_amount_suspicion(
            transaction("TXN-1", 1_500.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "ROUND_AMOUNT_SUSPICION")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["amount"], 1_500.0)
        self.assertEqual(signal["metadata"]["round_divisor"], 500)

    def test_does_not_fire_for_non_round_amount(self) -> None:
        signal = check_round_amount_suspicion(
            transaction("TXN-1", 1_250.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertIsNone(signal)

    def test_does_not_fire_for_round_amount_below_minimum(self) -> None:
        signal = check_round_amount_suspicion(
            transaction("TXN-1", 250.0, "2026-07-03T12:00:00Z"),
            [],
        )

        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()
