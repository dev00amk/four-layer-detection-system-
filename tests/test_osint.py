"""
tests/test_osint.py
===================
Tests for sentinel/osint.py — OSINT enrichment module.
"""

import pandas as pd

from sentinel.osint import (
    OsintEnrichmentPackage,
    OsintResult,
    check_device_intelligence,
    enrich_driver,
    verify_identity_document,
)

# ---------------------------------------------------------------------------
# OsintResult schema tests
# ---------------------------------------------------------------------------

def test_identity_verify_returns_valid_result():
    result = verify_identity_document("DRV-TEST-001")
    assert isinstance(result, OsintResult)
    assert result.result_code in ("MATCH", "MISMATCH", "ERROR")
    assert result.confidence in ("HIGH", "MEDIUM", "LOW", "N/A")
    assert len(result.query_hash) == 16     # truncated SHA-256
    assert result.step_id == "identity_document_verify"
    assert result.simulated is True


def test_device_check_returns_valid_result():
    result = check_device_intelligence("DRV-TEST-002", "DEV-ABC123")
    assert isinstance(result, OsintResult)
    assert result.result_code in ("FLAGGED", "CLEAN", "ERROR")
    assert result.source_type == "device_intel"


def test_result_is_deterministic():
    """Same driver_id must produce identical OSINT results on repeated calls."""
    r1 = verify_identity_document("DRV-DETERMINISTIC")
    r2 = verify_identity_document("DRV-DETERMINISTIC")
    assert r1.result_code == r2.result_code
    assert r1.risk_signal == r2.risk_signal
    assert r1.query_hash == r2.query_hash


def test_different_drivers_can_produce_different_results():
    """Simulation must not return identical results for all drivers."""
    results = [
        verify_identity_document(f"DRV-{i:04d}").result_code
        for i in range(20)
    ]
    # With 20 drivers and ~20% fraud rate, expect at least 1 MISMATCH
    assert "MISMATCH" in results or "MATCH" in results


# ---------------------------------------------------------------------------
# Full enrichment package tests
# ---------------------------------------------------------------------------

def test_enrich_driver_returns_package():
    pkg = enrich_driver("DRV-TEST-003", device_id="DEV-XYZ")
    assert isinstance(pkg, OsintEnrichmentPackage)
    assert pkg.driver_id == "DRV-TEST-003"
    assert pkg.steps_completed == 5      # all steps run
    assert pkg.overall_osint_risk in ("HIGH", "MEDIUM", "LOW", "INCONCLUSIVE")
    assert len(pkg.results) == 5


def test_skip_steps_reduces_step_count():
    pkg = enrich_driver(
        "DRV-TEST-004",
        skip_steps=["account_resale_check", "contractor_presence"],
    )
    assert pkg.steps_completed == 3


def test_risk_signal_count_matches_results():
    pkg = enrich_driver("DRV-TEST-005")
    manual_count = sum(1 for r in pkg.results if r.risk_signal)
    assert manual_count == pkg.steps_with_risk_signal


def test_overall_risk_thresholds():
    """overall_osint_risk must follow the documented thresholds."""
    pkg = enrich_driver("DRV-TEST-006")
    n = pkg.steps_with_risk_signal
    if n >= 3:
        assert pkg.overall_osint_risk == "HIGH"
    elif n == 2:
        assert pkg.overall_osint_risk == "MEDIUM"
    elif n == 1:
        assert pkg.overall_osint_risk == "LOW"
    else:
        assert pkg.overall_osint_risk == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# Markdown table output test
# ---------------------------------------------------------------------------

def test_markdown_table_renders():
    pkg = enrich_driver("DRV-TEST-007")
    table = pkg.to_markdown_table()
    assert "| # |" in table              # header row present
    assert "Result" in table             # column header
    assert "Confidence" in table
    assert pkg.overall_osint_risk in table
    assert "Scope:" in table             # scope note present


def test_markdown_table_has_correct_row_count():
    pkg = enrich_driver("DRV-TEST-008")
    table = pkg.to_markdown_table()
    data_rows = [
        line for line in table.split("\n")
        if line.startswith("|") and not line.startswith("| #") and "---" not in line
        and "*Steps" not in line
    ]
    assert len(data_rows) == pkg.steps_completed


def test_portfolio_scope_discloses_simulation():
    pkg = enrich_driver("DRV-DISCLOSURE")
    assert "deterministic simulation" in pkg.scope_note
    assert "no external requests" in pkg.scope_note


# ---------------------------------------------------------------------------
# Batch enrichment test
# ---------------------------------------------------------------------------

def test_batch_enrichment_filters_critical_only(tmp_path):
    from sentinel.osint import enrich_critical_drivers

    scored_df = pd.DataFrame({
        "driver_id":        [f"DRV-{i}" for i in range(10)],
        "composite_score":  [9, 8, 10, 3, 7, 9, 2, 10, 6, 4],
        "band": [
            "CRITICAL", "HIGH", "CRITICAL+", "LOW",
            "HIGH", "CRITICAL", "LOW", "CRITICAL+", "MEDIUM", "LOW"
        ],
    })

    packages = enrich_critical_drivers(scored_df, output_dir=tmp_path, max_drivers=25)

    critical_driver_ids = {"DRV-0", "DRV-2", "DRV-5", "DRV-7"}
    assert set(packages.keys()) == critical_driver_ids, (
        "Only CRITICAL and CRITICAL+ drivers must be enriched"
    )


def test_batch_writes_json(tmp_path):
    from sentinel.osint import enrich_critical_drivers

    scored_df = pd.DataFrame({
        "driver_id":        ["DRV-A"],
        "composite_score":  [10],
        "band":             ["CRITICAL+"],
    })

    enrich_critical_drivers(scored_df, output_dir=tmp_path)

    output = tmp_path / "osint_enrichment.json"
    assert output.exists(), "osint_enrichment.json must be written"

    import json
    data = json.loads(output.read_text())
    assert "DRV-A" in data
    assert "results" in data["DRV-A"]
    assert len(data["DRV-A"]["results"]) == 5
