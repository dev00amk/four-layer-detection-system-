import numpy as np

from sentinel.anomaly import ensemble_score, risk_band_router


def test_score_ceiling():
    assert ensemble_score(0.99, 0.99, 1, 22) <= 10


def test_band_routing():
    assert [risk_band_router(x) for x in (1, 3, 5, 7, 9)] == ["LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL+"]


def test_sql_normalization_and_vectorization():
    scores = ensemble_score(np.array([0.5, 0.5]), np.array([0.5, 0.5]), np.array([0, 0]), np.array([0, 22]))
    assert scores[1] > scores[0]
    assert scores.min() >= 0 and scores.max() <= 10

