"""PSI drift monitor tests."""
from __future__ import annotations

import json

import numpy as np
import pytest

from sentinel.config import settings
from sentinel.drift import PSI_ALERT, check_drift, load_baseline, save_baseline


@pytest.fixture()
def baseline_scores():
    rng = np.random.default_rng(3)
    return np.clip(rng.normal(3.0, 1.5, 2000), 0, 10).tolist()


def test_first_run_establishes_baseline(baseline_scores, tmp_path):
    result = check_drift(baseline_scores, drift_dir=tmp_path)
    assert result["baseline_exists"] is False
    assert result["psi"] == 0.0
    assert result["psi_status"] == "stable"
    assert (tmp_path / "baseline.json").exists()


def test_identical_distribution_is_stable(baseline_scores, tmp_path):
    save_baseline(baseline_scores, drift_dir=tmp_path)
    result = check_drift(baseline_scores, drift_dir=tmp_path)
    assert result["psi"] == pytest.approx(0.0, abs=1e-3)
    assert result["psi_status"] == "stable"
    assert result["alert_written"] is False
    assert not (tmp_path / "alerts.jsonl").exists()


def test_shifted_distribution_alerts(baseline_scores, tmp_path):
    save_baseline(baseline_scores, drift_dir=tmp_path)
    rng = np.random.default_rng(4)
    shifted = np.clip(rng.normal(6.5, 2.0, 2000), 0, 10).tolist()
    result = check_drift(shifted, drift_dir=tmp_path)
    assert result["psi"] > PSI_ALERT
    assert result["psi_status"] == "alert"
    assert result["alert_written"] is True
    assert result["mean_delta"] > 0
    alerts = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(alerts) == 1
    assert json.loads(alerts[0])["psi_status"] == "alert"


def test_alert_threshold_single_sourced_from_settings():
    assert PSI_ALERT == settings.psi_threshold


def test_load_baseline_roundtrip(baseline_scores, tmp_path):
    saved = save_baseline(baseline_scores, run_ts="2026-01-01T00:00:00Z", drift_dir=tmp_path)
    loaded = load_baseline(tmp_path)
    assert loaded == saved
    assert loaded["n"] == len(baseline_scores)
