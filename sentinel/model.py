"""Supervised, anomaly, rule, and graph ensemble."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from .anomaly import (
    IsolationForestDetector,
    ensemble_score,
    evaluate_fatal_signals,
    risk_band_router,
)
from .config import MODELS, ensure_directories
from .features import BEHAVIORAL_FEATURES, ROLLING_FEATURES, build_behavioral_features

log = logging.getLogger("sentinel.model")

# Sentinel imputation marker for NaN/inf feature values. XGBoost treats it as
# just another split value; audits need to know when it dominates a column.
FILL_VALUE = -999
FILL_WARN_RATE = 0.05

# XGBoost feature matrix: three groups with an explicit production migration path.
#
# Group A is the abstract IEEE-CIS benchmark surface. Remove it in production
# and replace it with real processor transaction features.
_FEAT_A = [
    "TransactionAmt",
    "dist1",
    "C1",
    "C2",
    "C5",
    "C13",
    "D1",
    "D10",
    "V12",
    "V53",
    "V258",
]

# Group B is delivery telemetry. Retain the semantics in production while
# replacing deterministic demo values with governed operational telemetry.
_FEAT_B = [
    "geofence_dist_m",
    "emulator_flag",
    "gps_mock_flag",
    "rooted_device_flag",
    "incentive_trip_count",
    "refund_count_30d",
    "payout_change_72h",
    "off_hours_flag",
    "trip_distance_km",
    "trip_duration_min",
]

# Group C is data-source-agnostic behavioral segmentation. Retain the feature
# logic and recalibrate peer/cohort baselines on representative operational data.
_FEAT_C = list(BEHAVIORAL_FEATURES)
_FEAT_D = list(ROLLING_FEATURES)

XGB_FEATURES: list[str] = _FEAT_A + _FEAT_B + _FEAT_C + _FEAT_D


class SentinelModel:
    # Production migration: remove A, replace B values, retain C, retrain on
    # sufficient labeled operational cases, then recalibrate IF contamination.
    XGB_FEATURES = XGB_FEATURES

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.xgb = XGBClassifier(
            n_estimators=180, max_depth=5, learning_rate=0.08, subsample=0.85,
            colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1, random_state=random_state,
        )
        self.iforest = IsolationForestDetector(random_state=random_state)
        self.metrics: dict[str, float | int] = {}

    def _matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        featured = build_behavioral_features(df)
        matrix = featured[self.XGB_FEATURES].replace([np.inf, -np.inf], np.nan)
        fill_rates = matrix.isna().mean()
        heavy = fill_rates[fill_rates > FILL_WARN_RATE]
        if not heavy.empty:
            log.warning(
                "feature_imputation_heavy",
                extra={
                    "fill_value": FILL_VALUE,
                    "columns": {name: round(rate, 4) for name, rate in heavy.items()},
                },
            )
        return matrix.fillna(FILL_VALUE).astype(float)

    def fit(
        self, df: pd.DataFrame, y: pd.Series, metrics_path: Path | None = None
    ) -> SentinelModel:
        X = self._matrix(df)
        train_idx, test_idx = train_test_split(
            np.arange(len(X)), test_size=0.25, stratify=y, random_state=self.random_state
        )
        positives = max(1, y.iloc[train_idx].sum())
        ratio = max(1.0, (len(train_idx) - y.iloc[train_idx].sum()) / positives)
        self.xgb.set_params(scale_pos_weight=ratio)
        self.xgb.fit(X.iloc[train_idx], y.iloc[train_idx])
        self.iforest.fit(X.iloc[train_idx])
        prob = self.xgb.predict_proba(X.iloc[test_idx])[:, 1]
        self.metrics = {
            "auc_roc": float(roc_auc_score(y.iloc[test_idx], prob)),
            "auc_pr": float(average_precision_score(y.iloc[test_idx], prob)),
            "rows": len(df),
            "fraud_rate": float(y.mean()),
        }
        target = metrics_path or (MODELS / "metrics.json")
        if metrics_path is None:
            ensure_directories()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.metrics, indent=2), encoding="utf-8")
        return self

    def predict(
        self,
        df: pd.DataFrame,
        graph_flags: pd.Series | np.ndarray,
        ring_sizes: pd.Series | np.ndarray,
        sql_hits: pd.Series | np.ndarray,
    ) -> pd.DataFrame:
        X = self._matrix(df)
        xgb_prob = self.xgb.predict_proba(X)[:, 1]
        if_score = self.iforest.predict_score(X)
        score, _ = ensemble_score(
            if_score,
            xgb_prob,
            np.asarray(graph_flags),
            np.asarray(sql_hits),
            np.asarray(ring_sizes),
        )
        fatal_lists = [evaluate_fatal_signals(row) for _, row in df.iterrows()]
        is_fatal = np.array([bool(signals) for signals in fatal_lists])
        score = np.where(is_fatal, 10, score)
        fatal_ids = [",".join(signal.signal_id for signal in signals) for signals in fatal_lists]
        fatal_evidence = [
            "; ".join(f"{signal.label}: {signal.evidence}" for signal in signals)
            for signals in fatal_lists
        ]
        return pd.DataFrame(
            {
                "driver_id": df["driver_id"].values,
                "trip_id": df["trip_id"].values,
                "xgb_probability": xgb_prob,
                "iforest_score": if_score,
                "graph_flag": np.asarray(graph_flags),
                "ring_size": np.asarray(ring_sizes),
                "sql_hits": np.asarray(sql_hits),
                "score": score,
                "is_fatal": is_fatal,
                "fatal_signal_ids": fatal_ids,
                "fatal_evidence": fatal_evidence,
                "band": [
                    risk_band_router(int(value), bool(fatal))
                    for value, fatal in zip(score, is_fatal, strict=True)
                ],
            }
        )

    def explain(self, df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        X = self._matrix(df)
        contributions = self.xgb.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]
        rows = []
        for position, idx in enumerate(df.index):
            top_positions = np.argsort(np.abs(contributions[position]))[-top_n:][::-1]
            for feature_position in top_positions:
                feature = self.XGB_FEATURES[feature_position]
                rows.append(
                    {
                        "row_index": idx,
                        "feature": feature,
                        "importance": float(contributions[position, feature_position]),
                        "value": float(X.loc[idx, feature]),
                    }
                )
        return pd.DataFrame(rows)


def main() -> None:
    from .config import SILVER
    from .db import get_connection, get_scored_inputs

    df = pd.read_parquet(SILVER / "spark_driver_trips.parquet")
    # Exercises the full input bridge even though fit only needs the frame.
    with get_connection() as con:
        _graph_flags, _ring_sizes, _sql_hits = get_scored_inputs(con, df)
    model = SentinelModel().fit(df, df["isFraud"].astype(int))
    print(json.dumps(model.metrics, indent=2))


if __name__ == "__main__":
    main()
