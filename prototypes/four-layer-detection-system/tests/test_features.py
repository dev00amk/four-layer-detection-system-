import unittest

from src.layer1_ingestion.validator import Transaction
from src.layer3_ml.features import (
    check_baseline_amount_deviation,
    check_hour_of_day_anomaly,
    check_transaction_frequency_spike,
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
    def test_fires_on_large_z_score(self) -> None:
        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "BASELINE_AMOUNT_DEVIATION")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["current_amount"], 400.0)
        self.assertEqual(signal["metadata"]["user_mean"], 100.0)
        self.assertGreater(signal["metadata"]["z_score"], 2.5)

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

    def test_zero_variance_history_does_not_crash_or_fire(self) -> None:
        flat_history = [
            transaction(f"TXN-{index}", 100.0, item["timestamp"])
            for index, item in enumerate(steady_history(), start=1)
        ]

        signal = check_baseline_amount_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T12:00:00Z"),
            flat_history,
        )

        self.assertIsNone(signal)


class HourOfDayAnomalyTests(unittest.TestCase):
    def test_fires_for_first_off_hours_event(self) -> None:
        signal = check_hour_of_day_anomaly(
            transaction("TXN-6", 100.0, "2026-06-30T03:00:00Z"),
            steady_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "HOUR_OF_DAY_ANOMALY")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["transaction_hour_utc"], 3)
        self.assertEqual(signal["metadata"]["suspicious_hour_start"], 0)
        self.assertEqual(signal["metadata"]["suspicious_hour_end"], 5)

    def test_does_not_fire_outside_suspicious_band(self) -> None:
        signal = check_hour_of_day_anomaly(
            transaction("TXN-6", 100.0, "2026-06-30T12:00:00Z"),
            steady_history(),
        )

        self.assertIsNone(signal)

    def test_does_not_fire_when_user_has_prior_off_hours_activity(self) -> None:
        history = steady_history() + [
            transaction("TXN-6", 100.0, "2026-06-29T02:00:00Z"),
        ]

        signal = check_hour_of_day_anomaly(
            transaction("TXN-7", 100.0, "2026-06-30T03:00:00Z"),
            history,
        )

        self.assertIsNone(signal)


class TransactionFrequencySpikeTests(unittest.TestCase):
    def burst_history(self) -> list[Transaction]:
        """Five transactions inside the same day."""
        return [
            transaction("TXN-1", 60.0, "2026-06-30T06:00:00Z"),
            transaction("TXN-2", 70.0, "2026-06-30T09:00:00Z"),
            transaction("TXN-3", 65.0, "2026-06-30T12:00:00Z"),
            transaction("TXN-4", 75.0, "2026-06-30T15:00:00Z"),
            transaction("TXN-5", 80.0, "2026-06-30T18:00:00Z"),
        ]

    def test_fires_when_window_count_exceeded(self) -> None:
        signal = check_transaction_frequency_spike(
            transaction("TXN-6", 70.0, "2026-06-30T21:00:00Z"),
            self.burst_history(),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal["rule_id"], "TRANSACTION_FREQUENCY_SPIKE")
        self.assertEqual(signal["severity"], "LOW")
        self.assertEqual(signal["metadata"]["transactions_in_window"], 6)
        self.assertEqual(signal["metadata"]["window_hours"], 24)
        self.assertEqual(signal["metadata"]["threshold"], 5)

    def test_does_not_fire_at_threshold(self) -> None:
        signal = check_transaction_frequency_spike(
            transaction("TXN-6", 70.0, "2026-06-30T21:00:00Z"),
            self.burst_history()[:4],
        )

        self.assertIsNone(signal)

    def test_does_not_count_transactions_outside_window(self) -> None:
        stale_history = [
            transaction("TXN-1", 60.0, "2026-06-27T06:00:00Z"),
            transaction("TXN-2", 70.0, "2026-06-27T09:00:00Z"),
        ] + self.burst_history()[:3]

        signal = check_transaction_frequency_spike(
            transaction("TXN-6", 70.0, "2026-06-30T21:00:00Z"),
            stale_history,
        )

        self.assertIsNone(signal)


class EvaluateBaselineDeviationTests(unittest.TestCase):
    def test_composes_all_triggered_features(self) -> None:
        signals = evaluate_baseline_deviation(
            transaction("TXN-6", 400.0, "2026-06-30T03:00:00Z"),
            steady_history(),
        )

        rule_ids = {signal["rule_id"] for signal in signals}
        self.assertIn("BASELINE_AMOUNT_DEVIATION", rule_ids)
        self.assertIn("HOUR_OF_DAY_ANOMALY", rule_ids)

    def test_returns_no_signals_for_typical_transaction(self) -> None:
        signals = evaluate_baseline_deviation(
            transaction("TXN-6", 101.0, "2026-06-30T11:00:00Z"),
            steady_history(),
        )

        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
