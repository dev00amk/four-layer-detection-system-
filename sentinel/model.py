"""Supervised, anomaly, rule, and graph ensemble."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from .anomaly import IsolationForestDetector, ensemble_score, risk_band_router
from .config import MODELS, ensure_directories
from .features import BEHAVIORAL_FEATURES, build_behavioral_features


class SentinelModel:
    XGB_FEATURES = [
        "TransactionAmt", "dist1", "C1", "C2", "C5", "C13", "D1", "D10", "V12", "V53", "V258",
        "geofence_dist_m", "emulator_flag", "gps_mock_flag", "rooted_device_flag",
        "incentive_trip_count", "refund_count_30d", "payout_change_72h", "off_hours_flag",
        "trip_distance_km", "trip_duration_min",
    ] + BEHAVIORAL_FEATURES

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.xgb = XGBClassifier(
            n_estimators=180, max_depth=5, learning_rate=0.08, subsample=0.85,
            colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1, random_state=random_state,
        )
        self.iforest = IsolationForestDetector(random_state=random_state)
        self.metrics = {}

    def _matrix(self, df):
        featured = build_behavioral_features(df)
        return featured[self.XGB_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(-999).astype(float)

    def fit(self, df, y):
        X = self._matrix(df)
        train_idx, test_idx = train_test_split(
            np.arange(len(X)), test_size=0.25, stratify=y, random_state=self.random_state
        )
        ratio = max(1.0, (len(train_idx) - y.iloc[train_idx].sum()) / max(1, y.iloc[train_idx].sum()))
        self.xgb.set_params(scale_pos_weight=ratio)
        self.xgb.fit(X.iloc[train_idx], y.iloc[train_idx])
        self.iforest.fit(X.iloc[train_idx])
        prob = self.xgb.predict_proba(X.iloc[test_idx])[:, 1]
        self.metrics = {
            "auc_roc": float(roc_auc_score(y.iloc[test_idx], prob)),
            "auc_pr": float(average_precision_score(y.iloc[test_idx], prob)),
            "rows": int(len(df)),
            "fraud_rate": float(y.mean()),
        }
        ensure_directories()
        (MODELS / "metrics.json").write_text(json.dumps(self.metrics, indent=2), encoding="utf-8")
        return self

    def predict(self, df, graph_flags, sql_hits):
        X = self._matrix(df)
        xgb_prob = self.xgb.predict_proba(X)[:, 1]
        if_score = self.iforest.predict_score(X)
        score = ensemble_score(if_score, xgb_prob, np.asarray(graph_flags), np.asarray(sql_hits))
        return pd.DataFrame(
            {
                "driver_id": df["driver_id"].values,
                "trip_id": df["trip_id"].values,
                "xgb_probability": xgb_prob,
                "iforest_score": if_score,
                "graph_flag": np.asarray(graph_flags),
                "sql_hits": np.asarray(sql_hits),
                "score": score,
                "band": [risk_band_router(int(value)) for value in score],
            }
        )

    def explain(self, df, top_n: int = 5):
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


def main():
    from .db import get_connection, get_scored_inputs
    from .config import SILVER

    df = pd.read_parquet(SILVER / "spark_driver_trips.parquet")
    con = get_connection()
    graph_flags, sql_hits = get_scored_inputs(con, df)
    model = SentinelModel().fit(df, df["isFraud"].astype(int))
    print(json.dumps(model.metrics, indent=2))


if __name__ == "__main__":
    main()
