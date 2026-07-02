"""sentinel/fairness.py
Disparate Impact Monitor
=========================
Checks whether the CRITICAL-band adverse-action rate differs significantly
across protected-class proxies, as required before any production deployment
of an adverse-action system affecting gig-economy workers.

Proxy dimensions monitored
--------------------------
  device_tier   : older_android | newer_android | ios | other
                  (proxy for socioeconomic status — device age correlates
                   with income bracket in gig-economy contractor populations)
  geography     : derived from GPS centroid cluster or postcode prefix
                  (proxy for race/ethnicity in jurisdictions with residential
                   segregation patterns)

Tests applied
-------------
  Four-fifths rule (EEOC 80 % rule)
      adverse_rate(group) / adverse_rate(best_group) >= 0.80
      Failure = potential disparate impact requiring review.

  Statistical parity difference
      |adverse_rate(group) - adverse_rate(reference)| <= tolerance
      Default tolerance = 0.05 (5 percentage points).

  Flag threshold: any group with < MIN_GROUP_SIZE contractors is excluded
  from the test (insufficient data) and flagged as "needs_data".

Outputs a report dict and writes alerts to data/fairness/alerts.jsonl.
Hard-blocks production deployment if any group fails the four-fifths rule
(controlled by BLOCK_ON_FAILURE flag — default True).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FAIRNESS_DIR = Path("data/fairness")
ALERTS_FILE = FAIRNESS_DIR / "alerts.jsonl"

MIN_GROUP_SIZE = 30          # minimum contractors for a reliable rate
PARITY_TOLERANCE = 0.05      # max allowed rate gap vs reference group
FOUR_FIFTHS_THRESHOLD = 0.80 # EEOC 80 % rule threshold
BLOCK_ON_FAILURE = True      # halt pipeline if any group fails


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _adverse_rates(
    records: list[dict],
    group_col: str,
    adverse_col: str = "is_critical",
) -> dict[str, dict]:
    """
    Compute adverse-action rates per group.

    Each record must have group_col and adverse_col keys.
    Returns dict: group_value -> {n, adverse_n, rate, status}
    """
    groups: dict[str, dict] = {}
    for rec in records:
        g = str(rec.get(group_col, "unknown"))
        if g not in groups:
            groups[g] = {"n": 0, "adverse_n": 0}
        groups[g]["n"] += 1
        if rec.get(adverse_col):
            groups[g]["adverse_n"] += 1

    result = {}
    for g, vals in groups.items():
        n, k = vals["n"], vals["adverse_n"]
        rate = k / n if n >= MIN_GROUP_SIZE else None
        status = "computed" if n >= MIN_GROUP_SIZE else "needs_data"
        result[g] = {"n": n, "adverse_n": k, "rate": rate, "status": status}

    return result


def _four_fifths_test(rates: dict[str, dict]) -> dict[str, dict]:
    """
    Apply the EEOC four-fifths rule.
    Returns per-group pass/fail/skip verdict.
    """
    computed = {g: v for g, v in rates.items() if v["rate"] is not None}
    if not computed:
        return {g: {**v, "four_fifths": "skip"} for g, v in rates.items()}

    best_rate = min(v["rate"] for v in computed.values())  # lowest adverse rate = best
    results = {}
    for g, v in rates.items():
        if v["rate"] is None:
            results[g] = {**v, "four_fifths": "skip", "ratio": None}
            continue
        ratio = v["rate"] / best_rate if best_rate > 0 else None
        passed = (ratio is None) or (ratio >= FOUR_FIFTHS_THRESHOLD)
        results[g] = {**v, "four_fifths": "pass" if passed else "FAIL", "ratio": ratio}

    return results


def _parity_test(rates: dict[str, dict], reference_group: str | None = None) -> dict[str, dict]:
    """
    Apply statistical parity difference test against a reference group
    (defaults to the group with the lowest adverse rate — the most-favoured).
    """
    computed = {g: v for g, v in rates.items() if v["rate"] is not None}
    if not computed:
        return {g: {**v, "parity": "skip", "parity_delta": None} for g, v in rates.items()}

    if reference_group and reference_group in computed:
        ref_rate = computed[reference_group]["rate"]
    else:
        ref_rate = min(v["rate"] for v in computed.values())

    results = {}
    for g, v in rates.items():
        if v["rate"] is None:
            results[g] = {**v, "parity": "skip", "parity_delta": None}
            continue
        delta = abs(v["rate"] - ref_rate)
        passed = delta <= PARITY_TOLERANCE
        results[g] = {
            **v,
            "parity": "pass" if passed else "FAIL",
            "parity_delta": round(delta, 4),
        }

    return results


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def check_fairness(
    records: list[dict],
    group_cols: list[str] | None = None,
    adverse_col: str = "is_critical",
    reference_groups: dict[str, str] | None = None,
    run_ts: str | None = None,
) -> dict:
    """
    Run disparate impact analysis across all specified group columns.

    Parameters
    ----------
    records       : list of dicts, one per contractor scored in this run
    group_cols    : columns to group by (default: ["device_tier", "geography"])
    adverse_col   : column indicating CRITICAL/adverse outcome (bool)
    reference_groups : optional {col: reference_group_value} overrides
    run_ts        : ISO timestamp (defaults to now)

    Returns
    -------
    dict with:
      run_ts         : str
      overall_rate   : float
      dimensions     : {col: {group: {n, adverse_n, rate, four_fifths, parity, ...}}}
      any_failures   : bool
      block_pipeline : bool
      recommended_action : str
    """
    run_ts = run_ts or datetime.now(timezone.utc).isoformat()
    group_cols = group_cols or ["device_tier", "geography"]
    reference_groups = reference_groups or {}

    n_total = len(records)
    n_adverse = sum(1 for r in records if r.get(adverse_col))
    overall_rate = n_adverse / n_total if n_total > 0 else 0.0

    dimensions: dict[str, dict] = {}
    any_failures = False

    for col in group_cols:
        rates = _adverse_rates(records, col, adverse_col)
        rates = _four_fifths_test(rates)
        rates = _parity_test(rates, reference_groups.get(col))
        dimensions[col] = rates

        col_failures = [g for g, v in rates.items()
                        if v.get("four_fifths") == "FAIL" or v.get("parity") == "FAIL"]
        if col_failures:
            any_failures = True

    block = BLOCK_ON_FAILURE and any_failures

    if any_failures:
        rec_action = (
            "DISPARATE IMPACT DETECTED. Review failing groups before adverse actions are taken. "
            "Engage Legal and Policy. Do not deploy to production without resolution."
        )
    else:
        rec_action = "No disparate impact detected. Fairness check passed."

    report = {
        "run_ts": run_ts,
        "n_total": n_total,
        "n_adverse": n_adverse,
        "overall_rate": round(overall_rate, 4),
        "dimensions": {
            col: {
                g: {
                    k: (round(v2, 4) if isinstance(v2, float) else v2)
                    for k, v2 in gv.items()
                }
                for g, gv in dim.items()
            }
            for col, dim in dimensions.items()
        },
        "any_failures": any_failures,
        "block_pipeline": block,
        "recommended_action": rec_action,
    }

    if any_failures:
        FAIRNESS_DIR.mkdir(parents=True, exist_ok=True)
        with ALERTS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report) + "\n")

    return report


# ---------------------------------------------------------------------------
# DataFrame convenience wrapper
# ---------------------------------------------------------------------------

def run_fairness_check(scored_df, score_col: str = "composite_score") -> dict:
    """
    Accept a pandas DataFrame with composite_score, device_tier, geography columns.
    Adds is_critical flag and runs the fairness check.
    Raises RuntimeError if BLOCK_ON_FAILURE and failures found.
    """
    df = scored_df.copy()
    df["is_critical"] = df[score_col] >= 7.0  # CRITICAL threshold

    records = df[["is_critical", "device_tier", "geography"]].to_dict(orient="records")
    report = check_fairness(records)

    status = "FAIL" if report["any_failures"] else "PASS"
    print(f"[fairness] overall_rate={report['overall_rate']:.1%} status={status}")

    if report["block_pipeline"]:
        raise RuntimeError(
            "Fairness check FAILED — pipeline blocked. "
            "See data/fairness/alerts.jsonl for details."
        )

    return report


if __name__ == "__main__":
    import random
    random.seed(42)
    groups = ["older_android", "newer_android", "ios"]
    geos = ["north", "south", "east", "west"]
    # Simulate a biased dataset where older_android has 2x CRITICAL rate
    records = []
    for _ in range(500):
        dv = random.choice(groups)
        geo = random.choice(geos)
        base_rate = 0.30 if dv == "older_android" else 0.15
        records.append({
            "device_tier": dv,
            "geography": geo,
            "is_critical": random.random() < base_rate,
        })
    report = check_fairness(records)
    print(json.dumps({
        "any_failures": report["any_failures"],
        "recommended_action": report["recommended_action"],
        "dimensions_summary": {
            col: {g: v["four_fifths"] for g, v in dim.items()}
            for col, dim in report["dimensions"].items()
        },
    }, indent=2))
