from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

WEIGHTS = {"xgb": 0.45, "iforest": 0.25, "sql": 0.20, "graph": 0.10}
RING_MULTIPLIER = 1.40
MAX_SQL_SIGNALS = 22


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.04, random_state: int = 42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state, n_jobs=-1)
        self.scaler = MinMaxScaler()

    def fit(self, features):
        raw = -self.model.fit(features).score_samples(features)
        self.scaler.fit(raw.reshape(-1, 1))
        return self

    def predict_score(self, features):
        raw = -self.model.score_samples(features)
        return self.scaler.transform(raw.reshape(-1, 1)).ravel().clip(0, 1)


def ensemble_score(if_score, xgb_prob, graph_flag, sql_hits):
    sql_norm = np.clip(np.asarray(sql_hits, dtype=float) / MAX_SQL_SIGNALS, 0, 1)
    raw = (
        WEIGHTS["xgb"] * np.asarray(xgb_prob)
        + WEIGHTS["iforest"] * np.asarray(if_score)
        + WEIGHTS["sql"] * sql_norm
        + WEIGHTS["graph"] * np.asarray(graph_flag)
    )
    raw *= np.where(np.asarray(graph_flag) > 0, RING_MULTIPLIER, 1.0)
    score = np.rint(np.clip(raw * 10, 0, 10)).astype(int)
    return int(score) if score.ndim == 0 else score


def risk_band_router(score: int) -> str:
    if score >= 9:
        return "CRITICAL+"
    if score >= 7:
        return "CRITICAL"
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"

