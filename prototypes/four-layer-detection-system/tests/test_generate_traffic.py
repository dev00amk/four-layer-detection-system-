import json
import tempfile
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

from config import SUSPICIOUS_HOUR_END, SUSPICIOUS_HOUR_START
from generate_traffic import build_scenarios
from main import run
from src.layer1_ingestion.validator import Transaction, validate_transaction
from src.layer2_heuristics.rules import evaluate_rules
from src.layer3_ml.features import evaluate_baseline_deviation


def rules_fired_by_user(transactions: list[dict]) -> dict[str, set[str]]:
    """Replay the stream through the engine exactly like main.run() does."""
    validated = sorted(
        (validate_transaction(item) for item in transactions),
        key=lambda item: item["timestamp"],
    )
    history_by_user: dict[str, list[Transaction]] = {}
    fired: dict[str, set[str]] = {}
    for transaction in validated:
        user_history = history_by_user.setdefault(transaction["user_id"], [])
        signals = evaluate_rules(transaction, user_history)
        signals.extend(evaluate_baseline_deviation(transaction, user_history))
        fired.setdefault(transaction["user_id"], set()).update(
            signal["rule_id"] for signal in signals
        )
        user_history.append(transaction)
    return fired


class GenerateTrafficTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stream = build_scenarios(seed=42)
        cls.fired = rules_fired_by_user(cls.stream)

    def test_every_transaction_passes_layer1_validation(self) -> None:
        for payload in self.stream:
            validate_transaction(payload)

    def test_structuring_scenario_fires(self) -> None:
        self.assertIn("STRUCTURING_PATTERN", self.fired["USER-STRUCTURING"])

    def test_dormancy_scenario_fires(self) -> None:
        self.assertIn("DORMANCY_BREAK", self.fired["USER-DORMANT"])

    def test_velocity_scenario_fires(self) -> None:
        self.assertIn("RAPID_TRANSACTION_COUNT", self.fired["USER-VELOCITY"])

    def test_escalation_scenario_fires_both_amount_rules(self) -> None:
        self.assertIn("RAPID_AMOUNT_ESCALATION", self.fired["USER-ESCALATION"])
        self.assertIn("BASELINE_AMOUNT_DEVIATION", self.fired["USER-ESCALATION"])

    def test_frequency_spike_scenario_fires(self) -> None:
        self.assertIn("TRANSACTION_FREQUENCY_SPIKE", self.fired["USER-BURST"])

    def test_round_amount_scenario_fires(self) -> None:
        self.assertIn("ROUND_AMOUNT_SUSPICION", self.fired["USER-ROUND"])

    def test_off_hours_scenario_fires(self) -> None:
        self.assertIn("HOUR_OF_DAY_ANOMALY", self.fired["USER-NIGHT-OWL"])

    def test_noise_users_trigger_nothing(self) -> None:
        for user_id, rule_ids in self.fired.items():
            if user_id.startswith("USER-NOISE-"):
                self.assertEqual(
                    rule_ids, set(), f"{user_id} unexpectedly fired {rule_ids}"
                )

    def test_only_night_owl_lands_in_overnight_band(self) -> None:
        # Guards against scenario offsets drifting into the 00:00-05:59 UTC
        # band and firing unintended HOUR_OF_DAY_ANOMALY signals.
        for payload in self.stream:
            hour = datetime.fromisoformat(
                payload["timestamp"].replace("Z", "+00:00")
            ).hour
            if SUSPICIOUS_HOUR_START <= hour <= SUSPICIOUS_HOUR_END:
                self.assertEqual(payload["user_id"], "USER-NIGHT-OWL")

    def test_same_seed_is_reproducible(self) -> None:
        first = build_scenarios(seed=7)
        second = build_scenarios(seed=7)
        self.assertEqual(
            [(item["user_id"], item["amount"]) for item in first],
            [(item["user_id"], item["amount"]) for item in second],
        )


class GeneratedStreamEndToEndTests(unittest.TestCase):
    """Prove the generated stream's alert contract through the real pipeline."""

    def test_exactly_one_alert_per_scripted_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            stream_path = Path(temporary_directory) / "generated.json"
            database_path = Path(temporary_directory) / "test.db"
            stream_path.write_text(
                json.dumps(build_scenarios(seed=42)), encoding="utf-8"
            )

            alerts = run(
                database_path=database_path, sample_data_path=stream_path
            )

        alerts_by_user = Counter(
            alert["transaction"]["user_id"] for alert in alerts
        )
        self.assertEqual(
            dict(alerts_by_user),
            {
                "USER-STRUCTURING": 1,
                "USER-DORMANT": 1,
                "USER-VELOCITY": 1,
                "USER-ESCALATION": 1,
                "USER-BURST": 1,
                "USER-ROUND": 1,
                "USER-NIGHT-OWL": 1,
            },
        )

        fired_rule_ids = {
            signal["rule_id"]
            for alert in alerts
            for signal in alert["signals"]
        }
        self.assertEqual(
            fired_rule_ids,
            {
                "STRUCTURING_PATTERN",
                "DORMANCY_BREAK",
                "RAPID_TRANSACTION_COUNT",
                "RAPID_AMOUNT_ESCALATION",
                "BASELINE_AMOUNT_DEVIATION",
                "TRANSACTION_FREQUENCY_SPIKE",
                "ROUND_AMOUNT_SUSPICION",
                "HIGH_AMOUNT_THRESHOLD",
                "HOUR_OF_DAY_ANOMALY",
            },
        )


if __name__ == "__main__":
    unittest.main()
