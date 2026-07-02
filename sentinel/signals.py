"""Execute the versioned SQL signal library and aggregate driver hits."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from .config import SQL_SIGNALS
from .exceptions import SignalExecutionError

log = logging.getLogger("sentinel.signals")

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

_EMPTY_COLUMNS = ["driver_id", "hit_count", "triggered_signals"]


def run_signals(
    con: duckdb.DuckDBPyConnection, signals_dir: Path = SQL_SIGNALS
) -> pd.DataFrame:
    """Run every signal query and aggregate non-monitoring hits per driver.

    A failing signal is logged and skipped so one bad query cannot take down
    the whole batch; ``SignalExecutionError`` is raised only when every
    signal fails, which indicates an environment problem rather than a
    single broken query.
    """
    frames = []
    failed: list[str] = []
    paths = sorted(signals_dir.glob("*.sql"))
    for path in paths:
        try:
            result = con.execute(path.read_text(encoding="utf-8")).df()
        except duckdb.Error as exc:
            failed.append(path.stem)
            log.warning(
                "signal_failed",
                extra={"signal_code": path.stem, "error": str(exc)},
            )
            continue
        if "driver_id" not in result:
            continue
        result = result[["driver_id"]].drop_duplicates()
        result["signal_code"] = path.stem
        result["monitoring_only"] = path.stem in MONITORING_SIGNALS
        frames.append(result)
    if paths and len(failed) == len(paths):
        raise SignalExecutionError(
            f"All {len(paths)} SQL signals failed; check the spark_trips view and schema.",
            failed_signals=failed,
        )
    log.info(
        "signals_completed",
        extra={"executed": len(paths) - len(failed), "failed": len(failed)},
    )
    if not frames:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)
    hits = pd.concat(frames, ignore_index=True)
    fraud_hits = hits[~hits["monitoring_only"]]
    if fraud_hits.empty:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)
    return (
        fraud_hits.groupby("driver_id")
        .agg(
            hit_count=("signal_code", "nunique"),
            triggered_signals=("signal_code", lambda s: ", ".join(sorted(s))),
        )
        .reset_index()
    )
