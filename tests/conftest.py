from __future__ import annotations

import pandas as pd
import pytest

from sentinel.demo import generate_demo
from sentinel.enrich import enrich


@pytest.fixture(scope="session")
def synthetic_trips(tmp_path_factory: pytest.TempPathFactory) -> pd.DataFrame:
    root = tmp_path_factory.mktemp("synthetic")
    txn, identity = generate_demo(rows=240, seed=42)
    merged = txn.merge(identity, on="TransactionID", how="left", validate="one_to_one")
    source = root / "bronze.parquet"
    merged.to_parquet(source, index=False)
    return enrich(seed=42, source_path=source, output_dir=root / "silver")
