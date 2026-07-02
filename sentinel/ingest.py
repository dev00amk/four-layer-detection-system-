"""Ingest IEEE-CIS CSV files into an immutable bronze layer."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import BRONZE, RAW, ensure_directories
from .schema import BronzeTransaction, validate_dataframe

log = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest(raw_dir: Path = RAW, bronze_dir: Path = BRONZE) -> pd.DataFrame:
    ensure_directories()
    bronze_dir.mkdir(parents=True, exist_ok=True)
    txn_path, id_path = raw_dir / "train_transaction.csv", raw_dir / "train_identity.csv"
    if not txn_path.exists() or not id_path.exists():
        raise FileNotFoundError(
            "Place IEEE-CIS train_transaction.csv and train_identity.csv in data/raw/, "
            "or run `python -m sentinel.demo`."
        )
    txn, identity = pd.read_csv(txn_path), pd.read_csv(id_path)
    merged = txn.merge(identity, on="TransactionID", how="left", validate="one_to_one")
    # Bounded row sample: full IEEE-CIS is ~590k rows and the column check
    # plus merge cardinality guard already cover the frame-level contract.
    validate_dataframe(merged, BronzeTransaction, sample_size=10_000)
    output = bronze_dir / "train_transaction.parquet"
    merged.to_parquet(output, index=False)
    try:
        output_ref = str(output.relative_to(bronze_dir.parent.parent))
    except ValueError:
        output_ref = str(output)
    lineage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            txn_path.name: {"rows": len(txn), "sha256": _sha256(txn_path)},
            id_path.name: {"rows": len(identity), "sha256": _sha256(id_path)},
        },
        "output": {"path": output_ref, "rows": len(merged), "columns": len(merged.columns)},
        "fraud_rate": float(merged["isFraud"].mean()),
    }
    (bronze_dir / "lineage.json").write_text(json.dumps(lineage, indent=2), encoding="utf-8")
    log.info(
        "bronze_written",
        extra={"path": output, "rows": len(merged), "fraud_rate": lineage["fraud_rate"]},
    )
    return merged


if __name__ == "__main__":
    ingest()
