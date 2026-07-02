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


def generate_cases_from_scores(
    scored: pd.DataFrame,
    shap_df: pd.DataFrame,
    cross_role_df: pd.DataFrame,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> int:
    """Generate the bounded critical-case queue and return its case count."""
    ensure_directories()
    target_dir = output_dir or CASES
    target_dir.mkdir(parents=True, exist_ok=True)
    critical = (
        scored[scored["band"].str.startswith("CRITICAL")]
        .drop_duplicates("driver_id")
        .head(limit or settings.max_case_queue)
    )
    # A populated SHAP frame that shares no rows with the critical queue means
    # the two inputs came from different scoring runs — evidence would be
    # silently absent from every case file.
    if len(critical) and len(shap_df) and not shap_df["row_index"].isin(critical.index).any():
        raise DataValidationError(
            "scored/shap misalignment: no critical row has SHAP evidence; "
            "regenerate both artifacts from the same scoring run"
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
        fatal_section = ""
        if getattr(row, "is_fatal", False):
            fatal_section = f"""
## Fatal-tier override

**Triggered:** YES<br>
**Signal IDs:** {row.fatal_signal_ids}<br>
**Evidence:** {row.fatal_evidence}

This override controls queue priority only; it never authorizes automated adverse action.
"""
        body = f"""# Sentinel Investigation Case — {row.driver_id}

**Created:** {datetime.now(timezone.utc).isoformat()}<br>
**Risk band:** {row.band} | **Ensemble score:** {row.score}/10

## Four-layer evidence

| Layer | Result |
|---|---:|
| XGBoost probability | {row.xgb_probability:.3f} |
| Isolation Forest | {row.iforest_score:.3f} |
| SQL signal hits | {int(row.sql_hits)} |
| Graph ring membership | {int(row.graph_flag)} |
| Cross-role collusion conditions | {collusion_count} |
{fatal_section}
## Top model drivers

| Feature | Observed value | SHAP contribution |
|---|---:|---:|
{shap_table}

## False-positive exclusion logic

- Shared-household or approved fleet relationship: **not yet verified**
- Coarse GPS lock or known clock skew: **not yet verified**
- Authorized device replacement: **not yet verified**
- Pre-staged or accessibility-assisted offer acceptance: **not yet verified**

No adverse action should occur until an investigator documents these checks.

## Structured OSINT and identity verification

**Execution mode:** {settings.osint_mode.value}. In `sim` mode every result is deterministic
and no vendor, registry, social-network, or web lookup is performed.

**Overall OSINT risk:** {osint_package.overall_osint_risk}<br>
**Risk signals:** {osint_package.steps_with_risk_signal} of {osint_package.steps_completed}

{osint_package.to_markdown_table()}

## Recommended action

Preserve telemetry, place the payout under manual review, and compare device, bank, IP,
store, and campaign links. Escalate sensitive adverse-action decisions to Legal/Compliance.

## Investigator checklist

- [ ] Validate GPS and device telemetry
- [ ] Review linked accounts and payout instruments
- [ ] Confirm incentive and refund history
- [ ] Document false-positive mitigations
- [ ] Record disposition and customer/driver impact

## Resolution

**Owner:** Unassigned<br>
**Disposition:** Pending<br>
**Notes:**
"""
        body += f"\n**Evidence integrity SHA-256:** `{_evidence_hash(body)}`\n"
        (target_dir / f"CASE_{row.driver_id}.md").write_text(body, encoding="utf-8")
        log.info("case_generated", extra={"driver_id": row.driver_id, "band": row.band})
    return len(critical)
