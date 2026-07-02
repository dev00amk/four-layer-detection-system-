"""Execute the versioned SQL signal library and aggregate driver hits."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from .config import SQL_SIGNALS
from .exceptions import SignalExecutionError

log = logging.getLogger(__name__)

MONITORING_SIGNALS = frozenset(
    {
        "04_emulator_device",
        "05_rooted_device",
        "21_appeal_overturn_rate",
        "21_signal_qa",
        "signal_21",
    }
)
MAX_FRAUD_SIGNALS = 22


def run_signals(
    con: duckdb.DuckDBPyConnection,
    signal_dir: Path | None = None,
) -> pd.DataFrame:
    """Run independent SQL signals, isolating failures to one signal file."""
    frames: list[pd.DataFrame] = []
    paths = sorted((signal_dir or SQL_SIGNALS).glob("*.sql"))
    failed = 0
    for path in paths:
        try:
            result = con.execute(path.read_text(encoding="utf-8")).df()
        except duckdb.Error:
            failed += 1
            log.warning("signal_failed", extra={"signal_code": path.stem}, exc_info=True)
            continue
        if "driver_id" not in result:
            continue
        result = result[["driver_id"]].drop_duplicates()
        result["signal_code"] = path.stem
        result["monitoring_only"] = path.stem in MONITORING_SIGNALS
        frames.append(result)
    if paths and failed == len(paths):
        raise SignalExecutionError(f"All {failed} SQL signals failed")
    log.info("signals_completed", extra={"executed": len(paths) - failed, "failed": failed})
    if not frames:
        return pd.DataFrame(columns=["driver_id", "hit_count", "triggered_signals"])
    hits = pd.concat(frames, ignore_index=True)
    fraud_hits = hits[~hits["monitoring_only"]]
    return (
        fraud_hits.groupby("driver_id")
        .agg(hit_count=("signal_code", "nunique"), triggered_signals=("signal_code", lambda s: ", ".join(sorted(s))))
        .reset_index()
    )
