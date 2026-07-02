"""SentinelModel fit/predict/explain contract tests."""
from __future__ import annotations

import json

import numpy as np
import pytest

from sentinel.model import SentinelModel

EXPECTED_METRIC_KEYS = {"auc_roc", "auc_pr", "rows", "fraud_rate"}
BANDS = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL+"}


@pytest.fixture()
def fitted(synthetic_trips, tmp_path):
    model = SentinelModel().fit(
        synthetic_trips,
        synthetic_trips["isFraud"].astype(int),
        metrics_path=tmp_path / "metrics.json",
    )
    return model, tmp_path / "metrics.json"


def test_fit_writes_governance_metrics(fitted, synthetic_trips):
    model, metrics_path = fitted
    assert set(model.metrics) == EXPECTED_METRIC_KEYS
    assert model.metrics["rows"] == len(synthetic_trips)
    assert 0.0 <= model.metrics["auc_roc"] <= 1.0
    assert 0.0 <= model.metrics["auc_pr"] <= 1.0
    assert json.loads(metrics_path.read_text(encoding="utf-8")) == model.metrics


def test_predict_columns_and_bounds(fitted, synthetic_trips):
    model, _ = fitted
    n = len(synthetic_trips)
    zeros = np.zeros(n)
    scored = model.predict(synthetic_trips, zeros, zeros, zeros)
    assert len(scored) == n
    for column in (
        "driver_id", "trip_id", "xgb_probability", "iforest_score",
        "score", "band", "is_fatal", "fatal_signal_ids",
    ):
        assert column in scored.columns
    assert scored["score"].between(0, 10).all()
    assert scored["xgb_probability"].between(0, 1).all()
    assert set(scored["band"]).issubset(BANDS)


def test_fatal_signal_overrides_score(fitted, synthetic_trips):
    model, _ = fitted
    df = synthetic_trips.copy()
    # 400 km in 30 minutes = 800 kph: fatal-tier F01 impossible travel.
    df.loc[df.index[0], "trip_distance_km"] = 400.0
    df.loc[df.index[0], "trip_duration_min"] = 30.0
    zeros = np.zeros(len(df))
    scored = model.predict(df, zeros, zeros, zeros)
    first = scored.iloc[0]
    assert bool(first["is_fatal"])
    assert first["score"] == 10
    assert first["band"] == "CRITICAL+"
    assert "F01" in first["fatal_signal_ids"]


def test_ring_multiplier_amplifies_score(fitted, synthetic_trips):
    model, _ = fitted
    n = len(synthetic_trips)
    zeros = np.zeros(n)
    baseline = model.predict(synthetic_trips, zeros, zeros, zeros)
    ringed = model.predict(
        synthetic_trips, np.ones(n), np.full(n, 5), np.full(n, 10.0)
    )
    assert (ringed["score"] >= baseline["score"]).all()
    assert (ringed["score"] > baseline["score"]).any()


def test_explain_returns_top_n_per_row(fitted, synthetic_trips):
    model, _ = fitted
    subset = synthetic_trips.head(10)
    explained = model.explain(subset, top_n=3)
    assert len(explained) == 30
    assert set(explained.columns) == {"row_index", "feature", "importance", "value"}
    assert explained.groupby("row_index").size().eq(3).all()


def test_matrix_imputes_nan_and_inf(fitted, synthetic_trips):
    model, _ = fitted
    df = synthetic_trips.copy()
    df.loc[df.index[0], "TransactionAmt"] = np.nan
    df.loc[df.index[1], "dist1"] = np.inf
    matrix = model._matrix(df)
    assert matrix.loc[df.index[0], "TransactionAmt"] == -999
    assert matrix.loc[df.index[1], "dist1"] == -999
    assert np.isfinite(matrix.to_numpy()).all()
