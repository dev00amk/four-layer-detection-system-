import numpy as np

from sentinel.anomaly import ensemble_score, risk_band_router
from sentinel.signals import MAX_FRAUD_SIGNALS, MONITORING_SIGNALS


def test_score_ceiling():
    assert ensemble_score(0.99, 0.99, 1, 22, ring_size=99) <= 10


def test_band_routing():
    assert [risk_band_router(x) for x in (1, 3, 5, 7, 9)] == ["LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL+"]


def test_sql_normalization_and_vectorization():
    scores = ensemble_score(np.array([0.5, 0.5]), np.array([0.5, 0.5]), np.array([0, 0]), np.array([0, 22]))
    assert scores[1] > scores[0]
    assert scores.min() >= 0 and scores.max() <= 10


def test_ring_multiplier_proportional():
    score_pair = ensemble_score(0.5, 0.5, 1, 11, ring_size=2)
    score_ring5 = ensemble_score(0.5, 0.5, 1, 11, ring_size=5)
    assert score_ring5 > score_pair


def test_ring_multiplier_requires_graph_flag():
    score_with_size = ensemble_score(0.5, 0.5, 0, 11, ring_size=5)
    score_without_size = ensemble_score(0.5, 0.5, 0, 11, ring_size=0)
    assert score_with_size == score_without_size


def test_monitoring_controls_are_excluded_from_fraud_hit_denominator():
    assert MAX_FRAUD_SIGNALS == 22
    assert {"04_emulator_device", "05_rooted_device", "21_signal_qa"} <= MONITORING_SIGNALS
