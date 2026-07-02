"""Investigator disposition capture, quality metrics, and retraining triggers."""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from .config import FEEDBACK, settings

LABEL_FILE = FEEDBACK / "dispositions.jsonl"
VALID_DISPOSITIONS = {
    "confirmed_fraud", "false_positive", "inconclusive",
    "appealed", "appeal_upheld", "appeal_denied",
}
VALID_ACTIONS = {"deactivated", "restricted", "warning", "no_action"}


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
    ledger_path: Path | None = None,
) -> dict[str, object]:
    """Append one validated investigator outcome to the immutable JSONL ledger."""
    if disposition not in VALID_DISPOSITIONS:
        raise ValueError(f"disposition must be one of {sorted(VALID_DISPOSITIONS)}")
    if action_taken not in VALID_ACTIONS:
        raise ValueError(f"action_taken must be one of {sorted(VALID_ACTIONS)}")
    record: dict[str, object] = {
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
    target = ledger_path or LABEL_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def load_labels(path: Path | None = None) -> list[dict[str, object]]:
    """Load all investigator labels from the JSONL ledger."""
    target = path or LABEL_FILE
    if not target.exists():
        return []
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def label_counts(labels: list[dict[str, object]] | None = None) -> dict[str, int]:
    """Count each supported disposition."""
    counts = dict.fromkeys(VALID_DISPOSITIONS, 0)
    for record in labels if labels is not None else load_labels():
        value = str(record.get("disposition", ""))
        if value in counts:
            counts[value] += 1
    return counts


def precision(labels: list[dict[str, object]] | None = None) -> float:
    """Return confirmed-fraud precision across decided fraud reviews."""
    counts = label_counts(labels)
    decided = counts["confirmed_fraud"] + counts["false_positive"]
    return counts["confirmed_fraud"] / decided if decided else float("nan")


def appeal_overturn_rate(labels: list[dict[str, object]] | None = None) -> float:
    """Return the upheld share of closed appeals."""
    counts = label_counts(labels)
    closed = counts["appeal_upheld"] + counts["appeal_denied"]
    return counts["appeal_upheld"] / closed if closed else float("nan")


def check_retraining_triggers(
    labels: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Evaluate label-volume, precision, and appeal-governance triggers."""
    records = labels if labels is not None else load_labels()
    measured_precision = precision(records)
    overturn = appeal_overturn_rate(records)
    return {
        "label_count": len(records),
        "precision": measured_precision,
        "appeal_overturn_rate": overturn,
        "trigger_retrain": len(records) >= 500,
        "trigger_precision_alert": (
            not math.isnan(measured_precision)
            and measured_precision < settings.precision_target
        ),
        "trigger_appeal_alert": not math.isnan(overturn) and overturn > 0.10,
    }


def generate_feedback_report(
    path: Path | None = None, output_dir: Path | None = None
) -> str:
    """Write a reviewer-friendly Markdown summary of the feedback loop."""
    labels = load_labels(path)
    counts = label_counts(labels)
    triggers = check_retraining_triggers(labels)
    measured_precision = cast(float, triggers["precision"])
    precision_text = "N/A" if math.isnan(measured_precision) else f"{measured_precision:.1%}"
    text = "\n".join([
        "# Sentinel investigator feedback report",
        "",
        f"- Total dispositions: {len(labels)}",
        f"- Confirmed fraud: {counts['confirmed_fraud']}",
        f"- False positives: {counts['false_positive']}",
        f"- Decided-case precision: {precision_text}",
        f"- Retraining required: {'YES' if triggers['trigger_retrain'] else 'NO'}",
        "",
    ])
    target_dir = output_dir or FEEDBACK
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "feedback_report.md").write_text(text, encoding="utf-8")
    return text
