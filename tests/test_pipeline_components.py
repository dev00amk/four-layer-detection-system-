from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd
import pytest

from sentinel.case import generate_cases_from_scores
from sentinel.db import get_cross_role_df
from sentinel.demo import generate_demo
from sentinel.exceptions import DataValidationError, ModelError, SignalExecutionError
from sentinel.ingest import ingest
from sentinel.model import SentinelModel
from sentinel.model_store import load_model, save_model
from sentinel.signals import run_signals


def test_demo_and_ingest_preserve_rows(tmp_path):
    raw, bronze = tmp_path / "raw", tmp_path / "bronze"
    raw.mkdir()
    txn, identity = generate_demo(100, 7)
    txn.to_csv(raw / "train_transaction.csv", index=False)
    identity.to_csv(raw / "train_identity.csv", index=False)
    result = ingest(raw, bronze)
    assert len(result) == 100
    assert (bronze / "train_transaction.parquet").exists()
    assert json.loads((bronze / "lineage.json").read_text())["output"]["rows"] == 100


def test_model_fit_predict_explain_and_store(synthetic_trips, tmp_path):
    model = SentinelModel().fit(
        synthetic_trips,
        synthetic_trips["isFraud"].astype(int),
        metrics_dir=tmp_path,
    )
    zeros = np.zeros(len(synthetic_trips), dtype=int)
    scored = model.predict(synthetic_trips, zeros, zeros, zeros)
    assert {"score", "band", "xgb_probability", "is_fatal"}.issubset(scored)
    assert scored["score"].between(0, 10).all()
    explained = model.explain(synthetic_trips.head(2), top_n=3)
    assert len(explained) == 6
    save_model(model, tmp_path)
    loaded = load_model(tmp_path)
    assert loaded.XGB_FEATURES == model.XGB_FEATURES


def test_load_model_rejects_missing_bundle(tmp_path):
    with pytest.raises(ModelError):
        load_model(tmp_path)


def test_signals_isolate_failure_and_exclude_monitoring(tmp_path):
    (tmp_path / "01_valid.sql").write_text(
        "SELECT driver_id FROM spark_trips", encoding="utf-8"
    )
    (tmp_path / "04_emulator_device.sql").write_text(
        "SELECT driver_id FROM spark_trips", encoding="utf-8"
    )
    (tmp_path / "99_broken.sql").write_text("SELECT nope FROM missing", encoding="utf-8")
    con = duckdb.connect()
    con.register("spark_trips", pd.DataFrame({"driver_id": ["D1", "D1", "D2"]}))
    result = run_signals(con, tmp_path)
    assert result.set_index("driver_id").loc["D1", "hit_count"] == 1


def test_signals_raise_only_when_all_fail(tmp_path):
    (tmp_path / "bad.sql").write_text("not sql", encoding="utf-8")
    with pytest.raises(SignalExecutionError):
        run_signals(duckdb.connect(), tmp_path)


def test_cross_role_fallback_is_stable():
    result = get_cross_role_df(duckdb.connect())
    assert list(result.columns) == ["driver_id", "collusion_signal_count", "collusion_flag"]


def test_case_generation_and_alignment(tmp_path):
    scored = pd.DataFrame(
        [{
            "driver_id": "D1", "trip_id": "T1", "band": "CRITICAL", "score": 8,
            "xgb_probability": 0.9, "iforest_score": 0.7, "sql_hits": 3,
            "graph_flag": 1, "is_fatal": False, "fatal_signal_ids": "",
            "fatal_evidence": "",
        }]
    )
    shap = pd.DataFrame(
        [{"row_index": 0, "feature": "C1", "value": 2.0, "importance": 0.4}]
    )
    assert generate_cases_from_scores(scored, shap, pd.DataFrame(), output_dir=tmp_path) == 1
    body = (tmp_path / "CASE_D1.md").read_text(encoding="utf-8")
    assert "Evidence integrity SHA-256" in body
    bad = shap.assign(row_index=99)
    with pytest.raises(DataValidationError):
        generate_cases_from_scores(scored, bad, pd.DataFrame(), output_dir=tmp_path)
