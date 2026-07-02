"""Investigator feedback loop tests: ledger, metrics, retraining triggers."""
from __future__ import annotations

import json
import math

import pytest

from sentinel.feedback import (
    appeal_overturn_rate,
    check_retraining_triggers,
    generate_feedback_report,
    label_counts,
    load_labels,
    precision,
    record_disposition,
)


def _label(disposition: str) -> dict[str, object]:
    return {"disposition": disposition}


def test_record_disposition_appends_to_ledger(tmp_path):
    ledger = tmp_path / "dispositions.jsonl"
    for disposition in ("confirmed_fraud", "false_positive"):
        record_disposition(
            contractor_id="D000001",
            case_id="CASE_D000001",
            run_ts="2026-01-01T00:00:00Z",
            disposition=disposition,
            action_taken="no_action",
            investigator_id="INV01",
            ledger_path=ledger,
        )
    labels = load_labels(ledger)
    assert len(labels) == 2
    assert {label["disposition"] for label in labels} == {
        "confirmed_fraud",
        "false_positive",
    }
    assert all("record_id" in label for label in labels)


def test_invalid_disposition_rejected(tmp_path):
    with pytest.raises(ValueError, match="disposition"):
        record_disposition(
            contractor_id="D1",
            case_id="C1",
            run_ts="t",
            disposition="not_a_thing",
            action_taken="no_action",
            investigator_id="I1",
            ledger_path=tmp_path / "ledger.jsonl",
        )
    with pytest.raises(ValueError, match="action_taken"):
        record_disposition(
            contractor_id="D1",
            case_id="C1",
            run_ts="t",
            disposition="confirmed_fraud",
            action_taken="banished",
            investigator_id="I1",
            ledger_path=tmp_path / "ledger.jsonl",
        )


def test_precision_and_overturn_rates():
    labels = (
        [_label("confirmed_fraud")] * 8
        + [_label("false_positive")] * 2
        + [_label("appeal_upheld")] * 1
        + [_label("appeal_denied")] * 3
    )
    assert precision(labels) == pytest.approx(0.8)
    assert appeal_overturn_rate(labels) == pytest.approx(0.25)
    counts = label_counts(labels)
    assert counts["confirmed_fraud"] == 8
    assert counts["false_positive"] == 2


def test_empty_labels_yield_nan_metrics():
    assert math.isnan(precision([]))
    assert math.isnan(appeal_overturn_rate([]))


def test_retraining_triggers():
    low_precision = [_label("confirmed_fraud")] * 5 + [_label("false_positive")] * 5
    triggers = check_retraining_triggers(low_precision)
    assert triggers["trigger_precision_alert"] is True
    assert triggers["trigger_retrain"] is False

    high_volume = [_label("confirmed_fraud")] * 500
    triggers = check_retraining_triggers(high_volume)
    assert triggers["trigger_retrain"] is True
    assert triggers["trigger_precision_alert"] is False


def test_generate_feedback_report(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        "\n".join(
            json.dumps(_label(d))
            for d in ("confirmed_fraud", "confirmed_fraud", "false_positive")
        )
        + "\n",
        encoding="utf-8",
    )
    text = generate_feedback_report(path=ledger, output_dir=tmp_path)
    assert "Total dispositions: 3" in text
    assert "Confirmed fraud: 2" in text
    assert "False positives: 1" in text
    assert (tmp_path / "feedback_report.md").read_text(encoding="utf-8") == text


def test_report_handles_no_data(tmp_path):
    text = generate_feedback_report(
        path=tmp_path / "missing.jsonl", output_dir=tmp_path
    )
    assert "Total dispositions: 0" in text
    assert "N/A" in text
