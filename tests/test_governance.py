import json
import math

import sentinel.drift as drift
import sentinel.fairness as fairness
import sentinel.feedback as feedback


def test_drift_establishes_baseline_and_detects_shift(tmp_path, monkeypatch):
    baseline_file = tmp_path / "baseline.json"
    alerts_file = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(drift, "DRIFT_DIR", tmp_path)
    monkeypatch.setattr(drift, "BASELINE_FILE", baseline_file)
    monkeypatch.setattr(drift, "ALERTS_FILE", alerts_file)

    first = drift.check_drift([1.0, 1.2, 1.4, 1.6] * 20, run_ts="2026-01-01T00:00:00Z")
    shifted = drift.check_drift([8.0, 8.2, 8.4, 8.6] * 20, run_ts="2026-01-02T00:00:00Z")

    assert first["baseline_exists"] is False
    assert shifted["psi_status"] == "alert"
    assert shifted["alert_written"] is True
    assert json.loads(alerts_file.read_text().splitlines()[0])["psi_status"] == "alert"


def test_fairness_flags_higher_adverse_rate(tmp_path, monkeypatch):
    monkeypatch.setattr(fairness, "FAIRNESS_DIR", tmp_path)
    monkeypatch.setattr(fairness, "ALERTS_FILE", tmp_path / "alerts.jsonl")
    records = [
        *[{"device_tier": "reference", "is_critical": index < 4} for index in range(40)],
        *[{"device_tier": "comparison", "is_critical": index < 16} for index in range(40)],
    ]

    report = fairness.check_fairness(records, group_cols=["device_tier"])

    comparison = report["dimensions"]["device_tier"]["comparison"]
    assert comparison["four_fifths"] == "FAIL"
    assert comparison["ratio"] == 0.25
    assert report["block_pipeline"] is True


def test_fairness_skips_groups_below_minimum_size():
    report = fairness.check_fairness(
        [{"device_tier": "small", "is_critical": False}] * 10,
        group_cols=["device_tier"],
    )

    small = report["dimensions"]["device_tier"]["small"]
    assert small["status"] == "needs_data"
    assert small["four_fifths"] == "skip"
    assert report["any_failures"] is False


def test_feedback_metrics_and_retraining_triggers():
    labels: list[dict[str, object]] = [
        {"disposition": "confirmed_fraud"},
        {"disposition": "confirmed_fraud"},
        {"disposition": "false_positive"},
        {"disposition": "appeal_upheld"},
        {"disposition": "appeal_denied"},
    ]

    assert feedback.precision(labels) == 2 / 3
    assert feedback.appeal_overturn_rate(labels) == 0.5
    triggers = feedback.check_retraining_triggers(labels)
    assert triggers["trigger_precision_alert"] is True
    assert triggers["trigger_appeal_alert"] is True
    assert triggers["trigger_retrain"] is False


def test_feedback_metrics_are_nan_without_decisions():
    assert math.isnan(feedback.precision([]))
    assert math.isnan(feedback.appeal_overturn_rate([]))
