"""sentinel/drift.py
Score Distribution Drift Monitor
=================================
Detects when the ensemble composite score distribution shifts significantly
from a stored baseline, indicating model degradation, a new fraud pattern,
or a population change in the contractor cohort.

Uses Population Stability Index (PSI) as the primary drift metric.
PSI < 0.10  -- no significant shift (stable)
PSI 0.10-0.20 -- moderate shift (monitor, consider recalibration)
PSI > 0.20  -- significant shift (alert, flag for investigation)

Additionally tracks:
- Mean and standard deviation of composite scores (run-over-run)
- Fraction of scores in each risk band (LOW / MEDIUM / HIGH / CRITICAL)
- CRITICAL-band rate vs baseline

Outputs alerts to data/drift/alerts.jsonl and a baseline snapshot to
data/drift/baseline.json on first run.
"""

from __future__ import annotations

import itertools
import json
import logging
import math
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .config import DATA, settings

if TYPE_CHECKING:
    import pandas as pd

log = logging.getLogger("sentinel.drift")

DRIFT_DIR = DATA / "drift"
BASELINE_FILE = DRIFT_DIR / "baseline.json"
ALERTS_FILE = DRIFT_DIR / "alerts.jsonl"

# PSI thresholds. PSI_ALERT is single-sourced from settings.psi_threshold so the
# governance config and the live drift check can never disagree.
PSI_MONITOR = 0.10
PSI_ALERT = settings.psi_threshold

# Risk band boundaries (composite score 0-10)
BAND_BOUNDARIES = [0.0, 3.0, 5.0, 7.0, 10.01]
BAND_NAMES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

N_BINS = 10  # bins for PSI calculation across [0, 10]
BIN_WIDTH = 10.0 / N_BINS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bin_scores(scores: Sequence[float], n_bins: int = N_BINS) -> list[float]:
    """Return normalised frequency per bin (length = n_bins)."""
    counts = [0] * n_bins
    for s in scores:
        idx = min(int(s / BIN_WIDTH), n_bins - 1)
        counts[idx] += 1
    total = len(scores) or 1
    # Apply small smoothing to avoid log(0)
    return [(c + 1e-4) / (total + n_bins * 1e-4) for c in counts]


def _psi(expected: list[float], actual: list[float]) -> float:
    """Compute Population Stability Index between two normalised distributions."""
    psi = 0.0
    for e, a in zip(expected, actual, strict=True):
        psi += (a - e) * math.log(a / e)
    return psi


def _band_rates(scores: Sequence[float]) -> dict[str, float]:
    """Return fraction of scores in each risk band."""
    counts = dict.fromkeys(BAND_NAMES, 0)
    for s in scores:
        for i, (lo, hi) in enumerate(itertools.pairwise(BAND_BOUNDARIES)):
            if lo <= s < hi:
                counts[BAND_NAMES[i]] += 1
                break
    total = len(scores) or 1
    return {b: counts[b] / total for b in BAND_NAMES}


def _summary(scores: Sequence[float]) -> dict:
    n = len(scores)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "band_rates": {}}
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std = math.sqrt(variance)
    return {
        "n": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "band_rates": {k: round(v, 4) for k, v in _band_rates(scores).items()},
        "bins": _bin_scores(scores),
    }


# ---------------------------------------------------------------------------
# Baseline management
# ---------------------------------------------------------------------------

def save_baseline(
    scores: Sequence[float], run_ts: str | None = None, drift_dir: Path = DRIFT_DIR
) -> dict:
    """Persist the current score distribution as the baseline."""
    drift_dir.mkdir(parents=True, exist_ok=True)
    baseline = {
        "run_ts": run_ts or datetime.now(timezone.utc).isoformat(),
        **_summary(scores),
    }
    (drift_dir / "baseline.json").write_text(json.dumps(baseline, indent=2))
    return baseline


def load_baseline(drift_dir: Path = DRIFT_DIR) -> dict | None:
    """Load the stored baseline, or None if not yet saved."""
    baseline_file = drift_dir / "baseline.json"
    if not baseline_file.exists():
        return None
    baseline: dict = json.loads(baseline_file.read_text())
    return baseline


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

def check_drift(
    scores: Sequence[float],
    run_ts: str | None = None,
    drift_dir: Path = DRIFT_DIR,
) -> dict:
    """
    Compare current score distribution against baseline.

    Returns a result dict with:
      psi                 : float  Population Stability Index
      psi_status          : str    stable | monitor | alert
      mean_delta          : float  mean(current) - mean(baseline)
      critical_rate_delta : float  CRITICAL rate change vs baseline
      baseline_exists     : bool
      alert_written       : bool
      recommended_action  : str
    """
    run_ts = run_ts or datetime.now(timezone.utc).isoformat()
    current = _summary(scores)
    baseline = load_baseline(drift_dir)

    if baseline is None:
        # First run — establish baseline and return a no-drift result
        save_baseline(scores, run_ts, drift_dir)
        return {
            "psi": 0.0,
            "psi_status": "stable",
            "mean_delta": 0.0,
            "critical_rate_delta": 0.0,
            "baseline_exists": False,
            "alert_written": False,
            "recommended_action": "Baseline saved. No drift comparison possible yet.",
        }

    psi = _psi(baseline["bins"], current["bins"])

    if psi < PSI_MONITOR:
        status = "stable"
    elif psi < PSI_ALERT:
        status = "monitor"
    else:
        status = "alert"

    mean_delta = (current["mean"] or 0.0) - (baseline["mean"] or 0.0)
    critical_delta = (
        current["band_rates"].get("CRITICAL", 0.0)
        - baseline["band_rates"].get("CRITICAL", 0.0)
    )

    actions = {
        "stable": "Score distribution stable. Continue normal operation.",
        "monitor": (
            f"PSI={psi:.3f}: moderate drift detected. Review recent signal "
            "thresholds and contractor cohort changes. Consider recalibration."
        ),
        "alert": (
            f"PSI={psi:.3f}: significant drift detected. Escalate to model "
            "owner. Suspend threshold changes until root cause is identified."
        ),
    }

    alert_written = False
    if status in ("monitor", "alert"):
        drift_dir.mkdir(parents=True, exist_ok=True)
        alert = {
            "run_ts": run_ts,
            "psi": round(psi, 4),
            "psi_status": status,
            "mean_delta": round(mean_delta, 4),
            "critical_rate_delta": round(critical_delta, 4),
            "current_n": current["n"],
            "baseline_n": baseline.get("n"),
            "recommended_action": actions[status],
        }
        with (drift_dir / "alerts.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert) + "\n")
        alert_written = True

    return {
        "psi": round(psi, 4),
        "psi_status": status,
        "mean_delta": round(mean_delta, 4),
        "critical_rate_delta": round(critical_delta, 4),
        "baseline_exists": True,
        "alert_written": alert_written,
        "recommended_action": actions[status],
    }


# ---------------------------------------------------------------------------
# Convenience wrapper for run.py integration
# ---------------------------------------------------------------------------

def run_drift_check(scored_df: pd.DataFrame, score_col: str = "score") -> dict:
    """
    Accept a pandas/polars DataFrame and run drift check.
    Returns drift result dict. Call after ensemble scoring in run.py.
    """
    scores = scored_df[score_col].dropna().tolist()
    result = check_drift(scores)
    log.info(
        "drift_check",
        extra={"psi": result["psi"], "psi_status": result["psi_status"]},
    )
    if result["alert_written"]:
        log.warning("drift_alert_written", extra={"alerts_file": str(ALERTS_FILE)})
    return result


if __name__ == "__main__":
    import random

    from .logger import configure_logging

    configure_logging()
    # Smoke-test: generate baseline then simulate a shifted distribution
    baseline_scores = [random.gauss(3.0, 1.5) for _ in range(1000)]
    baseline_scores = [max(0.0, min(10.0, s)) for s in baseline_scores]
    save_baseline(baseline_scores)

    shifted_scores = [random.gauss(5.5, 2.0) for _ in range(1000)]
    shifted_scores = [max(0.0, min(10.0, s)) for s in shifted_scores]
    log.info("drift_smoke_test", extra={"result": check_drift(shifted_scores)})
