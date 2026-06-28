"""Ingest IEEE-CIS CSV files into an immutable bronze layer."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import BRONZE, RAW, ensure_directories


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest() -> pd.DataFrame:
    ensure_directories()
    txn_path, id_path = RAW / "train_transaction.csv", RAW / "train_identity.csv"
    if not txn_path.exists() or not id_path.exists():
        raise FileNotFoundError(
            "Place IEEE-CIS train_transaction.csv and train_identity.csv in data/raw/, "
            "or run `python -m sentinel.demo`."
        )
    txn, identity = pd.read_csv(txn_path), pd.read_csv(id_path)
    merged = txn.merge(identity, on="TransactionID", how="left", validate="one_to_one")
    output = BRONZE / "train_transaction.parquet"
    merged.to_parquet(output, index=False)
    lineage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            txn_path.name: {"rows": len(txn), "sha256": _sha256(txn_path)},
            id_path.name: {"rows": len(identity), "sha256": _sha256(id_path)},
        },
        "output": {"path": str(output.relative_to(BRONZE.parent.parent)), "rows": len(merged), "columns": len(merged.columns)},
        "fraud_rate": float(merged["isFraud"].mean()),
    }
    (BRONZE / "lineage.json").write_text(json.dumps(lineage, indent=2), encoding="utf-8")
    print(f"Bronze written: {output} shape={merged.shape} fraud_rate={lineage['fraud_rate']:.3%}")
    return merged


if __name__ == "__main__":
    ingest()

