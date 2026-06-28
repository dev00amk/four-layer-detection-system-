from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

WEIGHTS = {"xgb": 0.45, "iforest": 0.25, "sql": 0.20, "graph": 0.10}
RING_MULTIPLIER = 1.40
MAX_SQL_SIGNALS = 25


class IsolationForestDetector:
    """
    Layer 2 anomaly detector for novel patterns not yet covered by SQL rules
    (Layer 1) or the supervised model (Layer 3).

    Contamination calibration:
        The default 0.04 reflects the IEEE-CIS labeled fraud rate of about
        3.5%, rounded up slightly for unlabeled borderline cases. In
        production, recalibrate quarterly using:

            confirmed_fraud_cases / total_drivers_scored

        Keep the operating range between 0.01 (conservative) and 0.15
        (aggressive). Contamination does not change the unsupervised patterns
        the forest learns; it changes the decision boundary used to separate
        normal observations from anomalies.

    Why this layer exists:
        XGBoost learns previously labeled fraud. Isolation Forest learns the
        shape of normal behavior from the unlabeled population, preserving
        coverage for emerging attacks with no rule or training label.
    """

    def __init__(self, contamination: float = 0.04, random_state: int = 42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state, n_jobs=-1)
        self.scaler = MinMaxScaler()

    def fit(self, features):
        raw = -self.model.fit(features).score_samples(features)
        self.scaler.fit(raw.reshape(-1, 1))
        return self

    def predict_score(self, features):
        """
        Return a normalized anomaly score in [0, 1].

        Higher values are more anomalous and contribute more fraud risk. These
        MinMax-scaled scores are relative rankings within the scored population,
        not calibrated fraud probabilities. The ensemble therefore weights this
        layer below XGBoost, whose output is produced by ``predict_proba``.
        """
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
