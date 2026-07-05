"""Generate evidence-filled, integrity-hashed investigation case files."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import CASES, ensure_directories, settings
from .exceptions import DataValidationError
from .logger import set_correlation_id
from .osint import enrich_driver

log = logging.getLogger(__name__)


def _evidence_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _generate_allegation(row) -> tuple[str, str]:
    if getattr(row, "is_fatal", False):
        allegation = "Fatal-Tier Threat: Immediate Account & Settlement Hold"
        summary = f"Severe threat vector identified. Fatal Override: {getattr(row, 'fatal_evidence', '')}. Immediate deactivation and manual compliance escalation are required."
    elif getattr(row, "graph_flag", 0) > 0 and getattr(row, "sql_hits", 0) >= 3:
        allegation = "Coordinated Multi-Account Fraud Ring"
        summary = f"Account belongs to an active collusion network of size {int(getattr(row, 'ring_size', 0))} showing systemic telemetry manipulation and shared device/bank infrastructure. Recommended action: Payout suspension pending ring review."
    elif getattr(row, "sql_hits", 0) >= 4 or getattr(row, "xgb_probability", 0) > 0.8:
        allegation = "Telemetry Manipulation & Spoofing Attempt"
        summary = f"Account shows highly indicative patterns of GPS spoofing and geofence misses, confirmed by machine learning feature analysis. Recommended action: Manual review of trip details and photo verification."
    else:
        allegation = "High-Risk Account Anomaly"
        summary = f"Account has been flagged due to anomalous behavioral metrics that deviate significantly from typical driver baselines. Recommended action: Place account under close monitoring."
    return allegation, summary


def _generate_narrative(row, collusion_count) -> str:
    parts = []
    if getattr(row, "is_fatal", False):
        parts.append(f"A Fatal-tier override was triggered because: {getattr(row, 'fatal_evidence', '')}.")
    
    if getattr(row, "graph_flag", 0) > 0:
        parts.append(f"The driver is linked to a coordinated collusion network (ring size: {int(getattr(row, 'ring_size', 0))}). Sharing device or payout details across multiple accounts indicates organized exploitation.")
    else:
        parts.append("No active multi-account network connections were detected in the graph layer.")
        
    if getattr(row, "sql_hits", 0) > 0:
        parts.append(f"We observed {int(row.sql_hits)} distinct SQL signal hits, showing deterministic anomalies in trip telemetry (such as impossible speed or geofence violations).")
        
    if getattr(row, "xgb_probability", 0) > 0.5:
        parts.append(f"The supervised XGBoost model indicates a high fraud probability of {row.xgb_probability:.3f}, signaling that the trip feature sequence is highly similar to previously confirmed fraud cases.")
    elif getattr(row, "iforest_score", 0) > 0.3:
        parts.append(f"The unsupervised Isolation Forest model flagged the behavior as an outlier (anomaly score: {row.iforest_score:.3f}), showing an abnormal behavioral deviation even if it doesn't match typical historical fraud models.")
        
    if collusion_count > 0:
        parts.append(f"Additionally, {collusion_count} cross-role collusion conditions were met, indicating potential coordination between account actors.")
        
    return " ".join(parts)


def _generate_fp_table(osint_package, row) -> str:
    triggered_str = getattr(row, "triggered_signals", "")
    triggered_set = {s.strip() for s in triggered_str.split(",") if s.strip()}
    
    fatal_ids = getattr(row, "fatal_signal_ids", "")
    fatal_set = {s.strip() for s in fatal_ids.split(",") if s.strip()}
    
    rows = []
    
    if any(s in triggered_set for s in ["03_device_compromise", "06_shared_device", "17_device_hopping"]) or "F02" in fatal_set:
        rows.append(
            "| **Family Sharing / Device Upgrade** | Device risk and shared hardware check | **UNVERIFIED** (SIMULATED — illustrative only) | Review active device history logs for driver name hopping |"
        )
        
    if any(s in triggered_set for s in ["07_shared_payout", "19_payout_bank_change"]) or "F03" in fatal_set or int(getattr(row, "payout_change_72h", 0)) > 0:
        rows.append(
            "| **Legitimate Payout Mutation** | Bank account tenure check | **UNVERIFIED** (SIMULATED — illustrative only) | Contact driver to confirm bank details change and check signature |"
        )
        
    if any(s in triggered_set for s in ["23_gps_spoofing_impossible_transit", "01_impossible_travel", "02_geofence_miss", "15_trip_distance_anomaly", "16_store_geofence_cluster"]) or "F01" in fatal_set:
        rows.append(
            "| **GPS Canyon / Degradation** | GPS accuracy & mock location check | **UNVERIFIED** (SIMULATED — illustrative only) | Verify physical delivery photo metadata and customer delivery receipt |"
        )
        
    if any(s in triggered_set for s in ["08_refund_velocity", "11_transaction_amount_outlier", "25_device_forensics_account_hopping"]):
        rows.append(
            "| **Bulk Grocery / Store Mistakes** | Store peer cohort purchase check | **UNVERIFIED** (SIMULATED — illustrative only) | Review items list for corporate purchase markers or system double-charge errors |"
        )
        
    if any(s in triggered_set for s in ["09_incentive_threshold", "12_campaign_concentration_abuse"]):
        rows.append(
            "| **Power User Bonus Conversion** | Campaign activity cohort comparison | **UNVERIFIED** (SIMULATED — illustrative only) | Check driver's historical rolling campaign activity to rule out natural hard work |"
        )
        
    if any(s in triggered_set for s in ["10_off_hours_claim", "14_night_activity_shift"]):
        rows.append(
            "| **Night-Shift Profile Shift** | Shift preferences and history check | **UNVERIFIED** (SIMULATED — illustrative only) | Review historic trip start hour distributions for seasonal shifts |"
        )
        
    if not rows:
        rows.append(
            "| **Baseline Identity Anomaly** | Contractor presence / identity match check | **UNVERIFIED** (SIMULATED — illustrative only) | Verify contractor business registration matches the identity document |"
        )
        
    lines = [
        "| Legitimate Behavior | Exclusion Logic / Check | Automated Status (Simulation Mode) | Action Required |",
        "| :--- | :--- | :--- | :--- |"
    ] + rows
    return "\n".join(lines)


def _generate_red_team_section(row) -> str:
    lines = ["Before final disposition, consider how a sophisticated actor could evade these checks:"]
    
    if "F01" in getattr(row, "fatal_signal_ids", "") or getattr(row, "sql_hits", 0) > 2:
        lines.append("- **GPS Spoofing Evasion Path:** Fraudsters use high-end hardware wrappers (e.g. Raspberry Pi GPS relays) that inject low-speed drift GPS data instead of standard developer mock GPS flags. This evades `F02` (Compound device compromise) and `gps_mock_flag` controls.")
        lines.append("  *Countermeasure:* Cross-correlate implied route speed with network IP latency and physical delivery photo exif metadata.")
        
    if getattr(row, "graph_flag", 0) > 0:
        lines.append("- **Collusion Ring Evasion Path:** Organized rings use proxy networks (residential IPs) and synthetic identities with unique bank accounts (mule networks) to avoid common entity edges in the graph layer.")
        lines.append("  *Countermeasure:* Expand graph edges to include shared referral codes, device brand/model combinations, and location-proximity patterns.")
        
    if "F03" in getattr(row, "fatal_signal_ids", "") or getattr(row, "payout_change_72h", 0):
        lines.append("- **Account Takeover Evasion Path:** Attackers compromise accounts, but wait 4-5 days after modifying payout info before accepting high-value trips, bypassing the simple `payout_change_72h` velocity check.")
        lines.append("  *Countermeasure:* Introduce anomaly check on driver's typical active zones (geography shifts) immediately following a bank account update.")
        
    if len(lines) == 1:
        lines.append("- **Evasion Path:** Fraudsters slowly build normal user profiles over weeks before executing large-scale refund or payout abuse, bypassing model drift and anomaly baseline scoring.")
        lines.append("  *Countermeasure:* Monitor changes in behavior relative to the user's historical rolling standard deviation.")
        
    return "\n".join(lines)


def generate_cases_from_scores(
    scored: pd.DataFrame,
    shap_df: pd.DataFrame,
    cross_role_df: pd.DataFrame,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> int:
    """Generate the bounded critical-case queue and return its case count."""
    ensure_directories()
    required = {"driver_id", "band", "score"}
    missing = sorted(required - set(scored.columns))
    if missing:
        raise DataValidationError("Scored data missing columns: " + ", ".join(missing))
    if not shap_df.empty and not set(shap_df["row_index"]).issubset(set(scored.index)):
        raise DataValidationError("SHAP row_index values are not aligned to scored rows")
    target = output_dir or CASES
    target.mkdir(parents=True, exist_ok=True)
    critical = (
        scored[scored["band"].str.startswith("CRITICAL")]
        .drop_duplicates("driver_id")
        .head(limit or settings.max_case_queue)
    )
    collusion = cross_role_df.set_index("driver_id") if not cross_role_df.empty else pd.DataFrame()
    for row in critical.itertuples():
        set_correlation_id(str(row.driver_id))
        osint_package = enrich_driver(driver_id=str(row.driver_id))
        evidence = shap_df[shap_df["row_index"] == row.Index].head(5)
        shap_table = "\n".join(
            f"| {item.feature} | {item.value:.3f} | {item.importance:.4f} |"
            for item in evidence.itertuples()
        ) or "| unavailable | — | — |"
        collusion_row = (
            collusion.loc[row.driver_id]
            if not collusion.empty and row.driver_id in collusion.index
            else None
        )
        collusion_count = (
            int(collusion_row["collusion_signal_count"]) if collusion_row is not None else 0
        )
        allegation, summary = _generate_allegation(row)
        narrative = _generate_narrative(row, collusion_count)
        fp_table = _generate_fp_table(osint_package, row)
        red_team_section = _generate_red_team_section(row)

        fatal_section = ""
        if getattr(row, "is_fatal", False):
            fatal_section = f"""
### Fatal-Tier Override Trigger
**Triggered:** YES<br>
**Signal IDs:** {row.fatal_signal_ids}<br>
**Evidence:** {row.fatal_evidence}
*This override controls queue priority only; it never authorizes automated adverse action.*
"""

        body = f"""# Sentinel Investigation Case — {row.driver_id}

**Created:** {datetime.now(timezone.utc).isoformat()}  
**Risk band:** {row.band} | **Ensemble score:** {row.score}/10

---

## 1. Allegation & Executive Summary [Compliance Reads First]

*   **Allegation:** {allegation}
*   **Summary:** {summary}

---

## 2. Investigation Narrative [Fusion & Corroboration]

*The following narrative synthesizes the findings across the four detection layers:*

{narrative}

---

## 3. False-Positive Exclusions & Mitigations [False-Positive Discipline]

Before taking adverse action, the following legitimate behaviors must be evaluated and ruled out:

{fp_table}

*No adverse action should occur until an investigator manually reviews and documents these checks.*

---

## 4. Red-Teaming & Evasion Analysis [Red-Teamer's Chair]

{red_team_section}

---

## 5. Telemetry & Scoring Data [Technical Details]

### Four-Layer Evidence Matrix
| Layer | Result | Description |
|---|---:|:---|
| XGBoost probability | {row.xgb_probability:.3f} | Supervised fraud propensity score |
| Isolation Forest | {row.iforest_score:.3f} | Unsupervised behavioral anomaly score |
| SQL signal hits | {int(row.sql_hits)} | Count of triggered deterministic rules |
| Graph ring membership | {int(row.graph_flag)} | Confirmed entity linkage in collusion graph |
| Cross-role collusion conditions | {collusion_count} | Combined role conflict indicator |
{fatal_section}
### Top model drivers

| Feature | Observed value | SHAP contribution |
|---|---:|---:|
{shap_table}

---

## 6. Structured OSINT and Identity Verification

**Execution mode:** {settings.osint_mode.value}. In `sim` mode every result is deterministic and no vendor, registry, social-network, or web lookup is performed.

**Overall OSINT risk:** {osint_package.overall_osint_risk}<br>
**Risk signals:** {osint_package.steps_with_risk_signal} of {osint_package.steps_completed}

{osint_package.to_markdown_table()}

---

## 7. Deposition Glossary & Metrics Definitions

*To ensure legal and regulatory defensibility, all key metrics and abbreviations used in this case pack are defined below:*

*   **Ensemble Score:** A calibrated index (0 to 10) combining supervised propensity models (45%), unsupervised anomalies (25%), structured SQL heuristics (20%), and graph network clusters (10%).
*   **XGBoost Probability:** The supervised machine learning model's output indicating the statistical similarity of this driver's feature vector to past confirmed fraud patterns.
*   **Isolation Forest Score:** An unsupervised anomaly metric. Higher values (approaching 0.5) denote extreme behavioral deviations from typical driver baselines.
*   **SQL Signal Hits:** The count of triggered deterministic behavioral rules version-controlled under `sql/signals/`.
*   **Graph Flag / Ring Membership:** Binary indicator (1 = True) of entity-level link sharing (device, bank, IP) with another active contractor account.
*   **SHAP Contribution:** SHAP (SHapley Additive exPlanations) values indicating how much a specific feature shifted the XGBoost score from the baseline. Positive values increase fraud probability; negative values decrease it.
*   **Fatal-Tier Overrides:** Critical threat definitions bypassing the machine learning blend to guarantee immediate manual review.
    *   *F01:* Impossible travel speed (implied speed > 300 kph).
    *   *F02:* Compound device compromise (emulator + root + mock GPS).
    *   *F03:* Payout redirection on new device (payout changed within 72h and new device observed near settlement).

---

## 8. Resolution Queue Workflow

*   **Recommended Action:** Preserve telemetry, place the payout under manual review, and compare device, bank, IP, store, and campaign links. Escalate sensitive adverse-action decisions to Legal/Compliance.

### Investigator checklist

- [ ] Validate GPS and device telemetry
- [ ] Review linked accounts and payout instruments
- [ ] Confirm incentive and refund history
- [ ] Document false-positive mitigations
- [ ] Record disposition and customer/driver impact

### Resolution Status

**Owner:** Unassigned  
**Disposition:** Pending  
**Notes:**  
"""
        body += f"\n**Evidence integrity SHA-256:** `{_evidence_hash(body)}`\n"
        (target / f"CASE_{row.driver_id}.md").write_text(body, encoding="utf-8")
        log.info("case_generated", extra={"driver_id": row.driver_id, "band": row.band})
    return len(critical)
