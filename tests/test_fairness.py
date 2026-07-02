"""Disparate-impact monitor tests: four-fifths rule and statistical parity."""
from __future__ import annotations

import pytest

from sentinel.fairness import check_fairness


def _records(rate_by_group: dict[str, float], n_per_group: int = 100) -> list[dict]:
    """Deterministic records: exactly rate*n adverse outcomes per group."""
    records = []
    for group, rate in rate_by_group.items():
        adverse_n = round(rate * n_per_group)
        for i in range(n_per_group):
            records.append(
                {
                    "device_tier": group,
                    "geography": "north",
                    "is_critical": i < adverse_n,
                }
            )
    return records


def test_double_adverse_rate_fails_four_fifths(tmp_path):
    report = check_fairness(
        _records({"ios": 0.05, "older_android": 0.10}),
        group_cols=["device_tier"],
        alerts_dir=tmp_path,
    )
    groups = report["dimensions"]["device_tier"]
    assert groups["ios"]["four_fifths"] == "pass"
    assert groups["older_android"]["four_fifths"] == "FAIL"
    assert groups["older_android"]["ratio"] == pytest.approx(0.5)
    assert report["any_failures"] is True
    assert report["block_pipeline"] is True
    assert (tmp_path / "alerts.jsonl").exists()


def test_near_parity_passes(tmp_path):
    report = check_fairness(
        _records({"ios": 0.10, "older_android": 0.11}),
        group_cols=["device_tier"],
        alerts_dir=tmp_path,
    )
    groups = report["dimensions"]["device_tier"]
    assert all(v["four_fifths"] == "pass" for v in groups.values())
    assert all(v["parity"] == "pass" for v in groups.values())
    assert report["any_failures"] is False
    assert report["block_pipeline"] is False
    assert not (tmp_path / "alerts.jsonl").exists()


def test_large_parity_gap_fails(tmp_path):
    # Both rates are >0.8 ratio-compatible? No: 0.30 vs 0.24 -> ratio 0.8 passes
    # four-fifths exactly, but the 6-point gap breaches the 5-point parity tolerance.
    report = check_fairness(
        _records({"ios": 0.24, "older_android": 0.30}),
        group_cols=["device_tier"],
        alerts_dir=tmp_path,
    )
    groups = report["dimensions"]["device_tier"]
    assert groups["older_android"]["four_fifths"] == "pass"
    assert groups["older_android"]["parity"] == "FAIL"
    assert report["any_failures"] is True


def test_small_groups_are_excluded(tmp_path):
    report = check_fairness(
        _records({"ios": 0.05, "rare_device": 0.50}, n_per_group=10),
        group_cols=["device_tier"],
        alerts_dir=tmp_path,
    )
    groups = report["dimensions"]["device_tier"]
    assert all(v["status"] == "needs_data" for v in groups.values())
    assert all(v["four_fifths"] == "skip" for v in groups.values())
    assert report["any_failures"] is False


def test_empty_records(tmp_path):
    report = check_fairness([], group_cols=["device_tier"], alerts_dir=tmp_path)
    assert report["n_total"] == 0
    assert report["overall_rate"] == 0.0
    assert report["any_failures"] is False
