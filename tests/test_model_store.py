"""Model persistence tests: round-trip, metadata, and compatibility guards."""
from __future__ import annotations

import json

import numpy as np
import pytest

from sentinel.exceptions import ModelError
from sentinel.model import SentinelModel
from sentinel.model_store import load_metadata, load_model, save_model


@pytest.fixture()
def fitted_model(synthetic_trips, tmp_path):
    return SentinelModel().fit(
        synthetic_trips,
        synthetic_trips["isFraud"].astype(int),
        metrics_path=tmp_path / "metrics.json",
    )


def test_round_trip_produces_identical_scores(fitted_model, synthetic_trips, tmp_path):
    save_model(fitted_model, model_dir=tmp_path)
    loaded = load_model(model_dir=tmp_path)
    zeros = np.zeros(len(synthetic_trips))
    original = fitted_model.predict(synthetic_trips, zeros, zeros, zeros)
    restored = loaded.predict(synthetic_trips, zeros, zeros, zeros)
    assert (original["score"] == restored["score"]).all()
    assert np.allclose(original["xgb_probability"], restored["xgb_probability"])


def test_metadata_contents(fitted_model, tmp_path):
    save_model(fitted_model, model_dir=tmp_path)
    metadata = load_metadata(tmp_path)
    assert metadata["feature_list"] == list(SentinelModel.XGB_FEATURES)
    assert set(metadata["lib_versions"]) == {"python", "xgboost", "sklearn"}
    assert metadata["metrics"] == fitted_model.metrics
    raw = json.loads((tmp_path / "model_metadata.json").read_text(encoding="utf-8"))
    assert raw == metadata


def test_unfitted_model_refused(tmp_path):
    with pytest.raises(ModelError, match="unfitted"):
        save_model(SentinelModel(), model_dir=tmp_path)


def test_missing_artifact_raises(tmp_path):
    with pytest.raises(ModelError, match="train"):
        load_model(model_dir=tmp_path)


def test_feature_drift_refused(fitted_model, tmp_path):
    save_model(fitted_model, model_dir=tmp_path)
    metadata_path = tmp_path / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["feature_list"] = metadata["feature_list"][:-1]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ModelError, match="feature list"):
        load_model(model_dir=tmp_path)


def test_major_version_mismatch_refused(fitted_model, tmp_path):
    save_model(fitted_model, model_dir=tmp_path)
    metadata_path = tmp_path / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["lib_versions"]["xgboost"] = "0.90"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ModelError, match="major version mismatch"):
        load_model(model_dir=tmp_path)
