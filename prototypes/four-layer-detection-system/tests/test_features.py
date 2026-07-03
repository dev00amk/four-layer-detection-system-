import unittest

from src.layer1_ingestion.validator import Transaction
from src.layer3_ml.features import (
    check_baseline_amount_deviation,
    check_transaction_gap_compression,
    check_unusual_hour_activity,
    evaluate_baseline_deviation,
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


def steady_history() -> list[Transaction]:
    """Five daily transactions near 100.0, all inside working hours."""
    return [
        transaction("TXN-1", 95.0, "2026-06-25T10:00:00Z"),
        transaction("TXN-2", 105.0, "2026-06-26T11:00:00Z"),
        transaction("TXN-3", 100.0, "2026-06-27T12:00:00Z"),
        transaction("TXN-4", 110.0, "2026-06-28T10:30:00Z"),
        transaction("TXN-5", 90.0, "2026-06-29T11:30:00Z"),
    ]


class BaselineAmountDeviationTests(unittest.TestCase):
    def test_fires_beyond_std_threshold(self) -> None:
        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "BASELINE_AMOUNT_DEVIATION")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["user_mean_amount"], 100.0)
        self.assertGreater(signal["metadata"]["deviation_std"], 2.5)
        self.assertEqual(signal["metadata"]["history_count"], 5)

    def test_does_not_fire_within_baseline(self) -> None:
        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 112.0, "2026-06-30T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNone(signal)

    def test_does_not_fire_with_insufficient_history(self) -> None:
        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T12:00:00Z"),
            steady_history()[:4],
        )

        self.assertIsNone(signal)

    def test_does_not_fire_when_history_has_zero_variance(self) -> None:
        flat_history = [
            transaction(f"TXN-{index}", 100.0, item["timestamp"])
            for index, item in enumerate(steady_history(), start=1)
        ]

        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T12:00:00Z"),
            flat_history,
        )

        self.assertIsNone(signal)


class UnusualHourActivityTests(unittest.TestCase):
    def test_fires_for_never_observed_hour(self) -> None:
        signal = check_unusual_hour_activity(
            transaction("TXN-6", 100.0, "2026-06-30T03:00:00Z"),
            steady_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "UNUSUAL_HOUR_ACTIVITY")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["transaction_hour"], 3)
        self.assertEqual(signal["metadata"]["observed_hours"], [10, 11, 12])

    def test_does_not_fire_for_observed_hour(self) -> None:
        signal = check_unusual_hour_activity(
            transaction("TXN-6", 100.0, "2026-06-30T11:45:00Z"),
            steady_history(),
        )

        self.assertIsNone(signal)

    def test_does_not_fire_with_insufficient_history(self) -> None:
        signal = check_unusual_hour_activity(
            transaction("TXN-6", 100.0, "2026-06-30T03:00:00Z"),
            steady_history()[:4],
        )

        self.assertIsNone(signal)


class TransactionGapCompressionTests(unittest.TestCase):
    def test_fires_when_gap_is_far_below_median_cadence(self) -> None:
        signal = check_transaction_gap_compression(
            transaction("TXN-6", 100.0, "2026-06-29T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "TRANSACTION_GAP_COMPRESSION")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["current_gap_minutes"], 30.0)
        self.assertEqual(signal["metadata"]["history_count"], 5)

    def test_does_not_fire_at_normal_cadence(self) -> None:
        signal = check_transaction_gap_compression(
            transaction("TXN-6", 100.0, "2026-06-30T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNone(signal)

    def test_does_not_fire_with_insufficient_history(self) -> None:
        signal = check_transaction_gap_compression(
            transaction("TXN-6", 100.0, "2026-06-29T12:00:00Z"),
            steady_history()[:3],
        )

        self.assertIsNone(signal)


class EvaluateBaselineDeviationTests(unittest.TestCase):
    def test_composes_all_triggered_features(self) -> None:
        signals = evaluate_baseline_deviation(
            transaction("TXN-6", 400.0, "2026-06-29T14:00:00Z"),
            steady_history(),
        )

        rule_ids = {signal["rule_id"] for signal in signals}
        self.assertIn("BASELINE_AMOUNT_DEVIATION", rule_ids)
        self.assertIn("UNUSUAL_HOUR_ACTIVITY", rule_ids)

    def test_returns_no_signals_for_typical_transaction(self) -> None:
        signals = evaluate_baseline_deviation(
            transaction("TXN-6", 101.0, "2026-06-30T11:00:00Z"),
            steady_history(),
        )

        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
