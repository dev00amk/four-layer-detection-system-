import unittest
from datetime import datetime

from config import SUSPICIOUS_HOUR_END, SUSPICIOUS_HOUR_START
from generate_traffic import build_scenarios
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


if __name__ == "__main__":
    unittest.main()
