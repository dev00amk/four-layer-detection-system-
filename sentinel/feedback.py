"""sentinel/feedback.py
Investigator Disposition Feedback Loop
=======================================
Captures investigator outcomes for every actioned case and writes them to
data/labels/ as newline-delimited JSON.  Labels feed:
  - XGBoost threshold recalibration (monthly cadence)
  - Signal FP-rate recalculation (quarterly cadence)
  - Loss model update (settlement-cycle cadence)

Disposition schema
------------------
  contractor_id   : str   - matches case file subject
  case_id         : str   - e.g. "CASE_001"
  run_ts          : str   - ISO-8601 timestamp of the detection run
  disposition     : str   - one of: confirmed_fraud | false_positive |
                             inconclusive | appealed | appeal_upheld |
                             appeal_denied
  action_taken    : str   - deactivated | restricted | warning | no_action
  investigator_id : str   - anonymised analyst identifier
  notes           : str   - free-text (optional, max 500 chars)
  review_ts       : str   - ISO-8601 timestamp of investigator decision
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

LABEL_DIR = Path("data/labels")
LABEL_FILE = LABEL_DIR / "dispositions.jsonl"

VALID_DISPOSITIONS = {
    "confirmed_fraud",
    "false_positive",
    "inconclusive",
    "appealed",
    "appeal_upheld",
    "appeal_denied",
}

VALID_ACTIONS = {
    "deactivated",
    "restricted",
    "warning",
    "no_action",
}


def record_disposition(
    *,
    contractor_id: str,
    case_id: str,
    run_ts: str,
    disposition: str,
    action_taken: str,
    investigator_id: str,
    notes: str = "",
    review_ts: str | None = None,
) -> dict:
    """Write a single investigator disposition record and return it."""
    if disposition not in VALID_DISPOSITIONS:
        raise ValueError(f"disposition must be one of {VALID_DISPOSITIONS}")
    if action_taken not in VALID_ACTIONS:
        raise ValueError(f"action_taken must be one of {VALID_ACTIONS}")

    record = {
        "record_id": str(uuid.uuid4()),
        "contractor_id": contractor_id,
        "case_id": case_id,
        "run_ts": run_ts,
        "disposition": disposition,
        "action_taken": action_taken,
        "investigator_id": investigator_id,
        "notes": notes[:500],
        "review_ts": review_ts or datetime.now(timezone.utc).isoformat(),
    }

    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    with LABEL_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    return record


def load_labels() -> list[dict]:
    """Return all disposition records as a list of dicts."""
    if not LABEL_FILE.exists():
        return []
    records = []
    with LABEL_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def label_counts(labels: list[dict] | None = None) -> dict:
    """Return disposition counts."""
    labels = labels if labels is not None else load_labels()
    counts = {d: 0 for d in VALID_DISPOSITIONS}
    for rec in labels:
        d = rec.get("disposition", "")
        if d in counts:
            counts[d] += 1
    return counts


def fp_rate(labels: list[dict] | None = None) -> float:
    """Overall false-positive rate: FP / (FP + confirmed_fraud)."""
    labels = labels if labels is not None else load_labels()
    counts = label_counts(labels)
    denom = counts["confirmed_fraud"] + counts["false_positive"]
    if denom == 0:
        return float("nan")
    return counts["false_positive"] / denom


def appeal_overturn_rate(labels: list[dict] | None = None) -> float:
    """Fraction of closed appeals that were upheld."""
    labels = labels if labels is not None else load_labels()
    counts = label_counts(labels)
    denom = counts["appeal_upheld"] + counts["appeal_denied"]
    if denom == 0:
        return float("nan")
    return counts["appeal_upheld"] / denom


RETRAIN_LABEL_THRESHOLD = 500
RETRAIN_FP_THRESHOLD = 0.15
RETRAIN_OVERTURN_THRESHOLD = 0.10


def check_retraining_triggers(labels: list[dict] | None = None) -> dict:
    """
    Evaluate whether retraining or threshold recalibration should be triggered.
    Returns dict with trigger flags and recommended_action string.
    """
    labels = labels if labels is not None else load_labels()
    n = len(labels)
    fpr = fp_rate(labels)
    aor = appeal_overturn_rate(labels)

    trigger_retrain = n >= RETRAIN_LABEL_THRESHOLD
    trigger_fp = (fpr == fpr) and fpr > RETRAIN_FP_THRESHOLD
    trigger_appeal = (aor == aor) and aor > RETRAIN_OVERTURN_THRESHOLD

    actions = []
    if trigger_retrain:
        actions.append(
            f"Label count {n}>={RETRAIN_LABEL_THRESHOLD}: schedule XGBoost retraining."
        )
    if trigger_fp:
        actions.append(
            f"FP rate {fpr:.1%}>{RETRAIN_FP_THRESHOLD:.0%}: review signal thresholds."
        )
    if trigger_appeal:
        actions.append(
            f"Appeal overturn rate {aor:.1%}>{RETRAIN_OVERTURN_THRESHOLD:.0%}: "
            "escalate to program lead."
        )
    if not actions:
        actions.append("No retraining triggers met. Continue normal operation.")

    return {
        "label_count": n,
        "fp_rate": fpr,
        "appeal_overturn_rate": aor,
        "trigger_retrain": trigger_retrain,
        "trigger_fp_alert": trigger_fp,
        "trigger_appeal_alert": trigger_appeal,
        "recommended_action": " | ".join(actions),
    }


if __name__ == "__main__":
    rec = record_disposition(
        contractor_id="C_DEMO",
        case_id="CASE_DEMO",
        run_ts="2026-06-29T00:00:00Z",
        disposition="false_positive",
        action_taken="no_action",
        investigator_id="INV_DEMO",
        notes="Smoke-test record.",
    )
    print("Recorded:", rec)
    print("Triggers:", check_retraining_triggers())
