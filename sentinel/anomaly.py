from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

from .config import settings
from .signals import MAX_FRAUD_SIGNALS

WEIGHTS = {
    "xgb": settings.xgb_weight,
    "iforest": settings.iforest_weight,
    "sql": settings.sql_weight,
    "graph": settings.graph_weight,
}


@dataclass(frozen=True)
class FatalSignal:
    """A high-confidence signal that bypasses the weighted score."""

    signal_id: str
    label: str
    evidence: str


def evaluate_fatal_signals(row) -> list[FatalSignal]:
    """Evaluate the narrowly scoped fatal-tier controls for one trip."""
    signals: list[FatalSignal] = []
    duration_hours = max(float(row.get("trip_duration_min", 0)) / 60.0, 1 / 3600)
    speed_kph = float(row.get("trip_distance_km", 0)) / duration_hours
    if speed_kph > 300:
        signals.append(FatalSignal("F01", "Impossible travel speed", f"{speed_kph:.1f} kph"))
    device_flags = [
        int(row.get("emulator_flag", 0)),
        int(row.get("rooted_device_flag", row.get("root_flag", 0))),
        int(row.get("gps_mock_flag", 0)),
    ]
    if all(device_flags):
        signals.append(
            FatalSignal("F02", "Compound device compromise", "emulator + root + mock GPS")
        )
    if int(row.get("payout_change_72h", 0)) and int(row.get("new_device_flag", 0)):
        signals.append(
            FatalSignal(
                "F03",
                "Payout redirection on new device",
                "payout changed within 72h and new device observed near settlement",
            )
        )
    return signals


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


def ensemble_score(if_score, xgb_prob, graph_flag, sql_hits, ring_size=0, fatal_signals=None):
    """
    Blend the four detection layers into a bounded 0-10 score.

    Ring uplift is proportional to coordination scale: 1.2x for a pair,
    increasing by 0.1 per member to a 1.5x cap for rings of five or more.
    SQL input is a raw fraud-signal hit count and is normalized against the
    22 enforcement signals; monitoring-only controls are excluded upstream.
    """
    sql_norm = np.clip(np.asarray(sql_hits, dtype=float) / MAX_FRAUD_SIGNALS, 0, 1)
    raw = (
        WEIGHTS["xgb"] * np.asarray(xgb_prob)
        + WEIGHTS["iforest"] * np.asarray(if_score)
        + WEIGHTS["sql"] * sql_norm
        + WEIGHTS["graph"] * np.asarray(graph_flag)
    )
    graph = np.asarray(graph_flag)
    size = np.asarray(ring_size)
    multiplier = np.where(
        (graph > 0) & (size >= 2),
        1.0 + 0.1 * np.minimum(size, 5),
        1.0,
    )
    raw *= multiplier
    score = np.rint(np.clip(raw * 10, 0, 10)).astype(int)
    is_fatal = bool(fatal_signals)
    if is_fatal:
        score = np.full_like(score, 10)
    result = int(score) if score.ndim == 0 else score
    return result, is_fatal


def risk_band_router(score: int, is_fatal: bool = False) -> str:
    if is_fatal or score >= settings.critical_plus_threshold:
        return "CRITICAL+"
    if score >= settings.critical_risk_threshold:
        return "CRITICAL"
    if score >= settings.high_risk_threshold:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"
