"""Execute the versioned SQL signal library and aggregate driver hits."""
from __future__ import annotations

import pandas as pd

from .config import SQL_SIGNALS

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


def run_signals(con) -> pd.DataFrame:
    frames = []
    for path in sorted(SQL_SIGNALS.glob("*.sql")):
        result = con.execute(path.read_text(encoding="utf-8")).df()
        if "driver_id" not in result:
            continue
        result = result[["driver_id"]].drop_duplicates()
        result["signal_code"] = path.stem
        result["monitoring_only"] = path.stem in MONITORING_SIGNALS
        frames.append(result)
    if not frames:
        return pd.DataFrame(columns=["driver_id", "hit_count", "triggered_signals"])
    hits = pd.concat(frames, ignore_index=True)
    fraud_hits = hits[~hits["monitoring_only"]]
    return (
        fraud_hits.groupby("driver_id")
        .agg(hit_count=("signal_code", "nunique"), triggered_signals=("signal_code", lambda s: ", ".join(sorted(s))))
        .reset_index()
    )
