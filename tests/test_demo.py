"""Demo data generator tests: shape, determinism, label plausibility."""
from __future__ import annotations

import pandas as pd

from sentinel.demo import generate_demo


def test_shapes_and_columns():
    txn, identity = generate_demo(rows=300, seed=1)
    assert len(txn) == 300
    assert len(identity) == int(300 * 0.28)
    assert txn["TransactionID"].is_unique
    assert identity["TransactionID"].isin(txn["TransactionID"]).all()


def test_deterministic_per_seed():
    first_txn, first_id = generate_demo(rows=300, seed=1)
    second_txn, second_id = generate_demo(rows=300, seed=1)
    pd.testing.assert_frame_equal(first_txn, second_txn)
    pd.testing.assert_frame_equal(first_id, second_id)


def test_different_seed_differs():
    base, _ = generate_demo(rows=300, seed=1)
    other, _ = generate_demo(rows=300, seed=2)
    assert not base["TransactionAmt"].equals(other["TransactionAmt"])


def test_fraud_rate_plausible():
    txn, _ = generate_demo(rows=5000, seed=42)
    rate = txn["isFraud"].mean()
    assert 0.02 <= rate <= 0.06
