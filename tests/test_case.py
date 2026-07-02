"""Case file generation tests: queue cap, evidence content, integrity hash."""
from __future__ import annotations

import hashlib
import re

import pandas as pd
import pytest

from sentinel.case import generate_cases_from_scores
from sentinel.exceptions import DataValidationError

CROSS_ROLE_EMPTY = pd.DataFrame(
    columns=["driver_id", "collusion_signal_count", "collusion_flag"]
)


def _scored_frame(n_critical: int, n_low: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n_critical + n_low):
        critical = i < n_critical
        rows.append(
            {
                "driver_id": f"D{i:06d}",
                "trip_id": f"T{i:06d}",
                "xgb_probability": 0.95 if critical else 0.05,
                "iforest_score": 0.8 if critical else 0.1,
                "graph_flag": 0,
                "ring_size": 0,
                "sql_hits": 5.0 if critical else 0.0,
                "score": 9 if critical else 1,
                "is_fatal": False,
                "fatal_signal_ids": "",
                "fatal_evidence": "",
                "band": "CRITICAL+" if critical else "LOW",
            }
        )
    return pd.DataFrame(rows)


def _shap_frame(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for idx in scored.index:
        for feature in ("geofence_dist_m", "refund_count_30d", "TransactionAmt"):
            rows.append(
                {
                    "row_index": idx,
                    "feature": feature,
                    "importance": 0.5,
                    "value": 100.0,
                }
            )
    return pd.DataFrame(rows)


def test_only_critical_bands_generate_cases(tmp_path):
    scored = _scored_frame(n_critical=2, n_low=4)
    count = generate_cases_from_scores(
        scored, _shap_frame(scored), CROSS_ROLE_EMPTY, output_dir=tmp_path
    )
    assert count == 2
    files = sorted(tmp_path.glob("CASE_*.md"))
    assert [f.name for f in files] == ["CASE_D000000.md", "CASE_D000001.md"]


def test_queue_cap_respected(tmp_path):
    scored = _scored_frame(n_critical=6)
    count = generate_cases_from_scores(
        scored, _shap_frame(scored), CROSS_ROLE_EMPTY, limit=3, output_dir=tmp_path
    )
    assert count == 3
    assert len(list(tmp_path.glob("CASE_*.md"))) == 3


def test_case_content_and_integrity_hash(tmp_path):
    scored = _scored_frame(n_critical=1)
    generate_cases_from_scores(
        scored, _shap_frame(scored), CROSS_ROLE_EMPTY, output_dir=tmp_path
    )
    body = (tmp_path / "CASE_D000000.md").read_text(encoding="utf-8")
    assert "## Four-layer evidence" in body
    assert "## False-positive exclusion logic" in body
    assert "geofence_dist_m" in body
    assert "## Investigator checklist" in body
    match = re.search(r"\*\*Evidence integrity SHA-256:\*\* `([0-9a-f]{64})`", body)
    assert match, "integrity hash footer missing"
    # The hash covers the body up to (excluding) the hash footer and its
    # leading newline separator.
    hashed_portion = body[: body.rindex("\n**Evidence integrity SHA-256:")]
    assert (
        hashlib.sha256(hashed_portion.encode("utf-8")).hexdigest() == match.group(1)
    )


def test_fatal_case_includes_override_section(tmp_path):
    scored = _scored_frame(n_critical=1)
    scored.loc[0, ["is_fatal", "fatal_signal_ids", "fatal_evidence"]] = [
        True,
        "F01",
        "Impossible travel speed: 800.0 kph",
    ]
    generate_cases_from_scores(
        scored, _shap_frame(scored), CROSS_ROLE_EMPTY, output_dir=tmp_path
    )
    body = (tmp_path / "CASE_D000000.md").read_text(encoding="utf-8")
    assert "## Fatal-tier override" in body
    assert "F01" in body


def test_collusion_count_embedded(tmp_path):
    scored = _scored_frame(n_critical=1)
    cross_role = pd.DataFrame(
        {"driver_id": ["D000000"], "collusion_signal_count": [3], "collusion_flag": [1]}
    )
    generate_cases_from_scores(
        scored, _shap_frame(scored), cross_role, output_dir=tmp_path
    )
    body = (tmp_path / "CASE_D000000.md").read_text(encoding="utf-8")
    assert "| Cross-role collusion conditions | 3 |" in body


def test_duplicate_drivers_deduplicated(tmp_path):
    scored = pd.concat([_scored_frame(n_critical=2)] * 2, ignore_index=True)
    count = generate_cases_from_scores(
        scored, _shap_frame(scored), CROSS_ROLE_EMPTY, output_dir=tmp_path
    )
    assert count == 2


def test_misaligned_shap_frame_rejected(tmp_path):
    scored = _scored_frame(n_critical=2)
    shap = _shap_frame(scored)
    shap["row_index"] += 10_000  # indexes from a different scoring run
    with pytest.raises(DataValidationError, match="misalignment"):
        generate_cases_from_scores(scored, shap, CROSS_ROLE_EMPTY, output_dir=tmp_path)
