"""Deterministic IEEE-CIS-shaped demo data for credential-free evaluation."""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

from .config import RAW, ensure_directories


def generate_demo(rows: int = 12_000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    fraud = rng.random(rows) < 0.035
    transaction = pd.DataFrame(
        {
            "TransactionID": np.arange(2_987_000, 2_987_000 + rows),
            "isFraud": fraud.astype(int),
            "TransactionDT": np.arange(rows) * 43 + rng.integers(0, 40, rows),
            "TransactionAmt": rng.lognormal(4.0 + fraud * 0.55, 0.85),
            "ProductCD": rng.choice(list("WHCRS"), rows),
            "card1": rng.integers(1000, 1800, rows),
            "card2": rng.integers(100, 600, rows),
            "addr1": rng.integers(100, 500, rows),
            "dist1": np.abs(rng.normal(8 + fraud * 30, 15, rows)),
            "C1": rng.poisson(3 + fraud * 7, rows),
            "C2": rng.poisson(2 + fraud * 5, rows),
            "C5": rng.poisson(1 + fraud * 4, rows),
            "C13": rng.poisson(4 + fraud * 6, rows),
            "D1": np.abs(rng.normal(30 - fraud * 15, 20, rows)),
            "D10": np.abs(rng.normal(20 - fraud * 8, 14, rows)),
            "V12": rng.normal(0.5 + fraud * 0.4, 0.25, rows),
            "V53": rng.normal(0.4 + fraud * 0.45, 0.3, rows),
            "V258": rng.normal(0.3 + fraud * 0.5, 0.3, rows),
        }
    )
    identity_rows = rng.choice(transaction.TransactionID, size=int(rows * 0.28), replace=False)
    identity = pd.DataFrame(
        {
            "TransactionID": identity_rows,
            "DeviceType": rng.choice(["desktop", "mobile"], len(identity_rows), p=[0.35, 0.65]),
            "DeviceInfo": rng.choice(["iOS", "Android", "Windows", "unknown"], len(identity_rows)),
            "id_31": rng.choice(["chrome", "safari", "edge", "mobile"], len(identity_rows)),
        }
    )
    return transaction, identity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=12_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    ensure_directories()
    txn, identity = generate_demo(args.rows, args.seed)
    txn.to_csv(RAW / "train_transaction.csv", index=False)
    identity.to_csv(RAW / "train_identity.csv", index=False)
    print(f"Demo dataset written: transactions={len(txn):,}, identity={len(identity):,}")


if __name__ == "__main__":
    main()

