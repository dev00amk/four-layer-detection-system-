"""Generate evidence-filled investigation case files."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from .config import CASES, ensure_directories


def generate_cases_from_scores(scored: pd.DataFrame, shap_df: pd.DataFrame, cross_role_df: pd.DataFrame, limit: int = 25) -> int:
    ensure_directories()
    critical = scored[scored["band"].str.startswith("CRITICAL")].drop_duplicates("driver_id").head(limit)
    collusion = cross_role_df.set_index("driver_id") if not cross_role_df.empty else pd.DataFrame()
    for row in critical.itertuples():
        evidence = shap_df[shap_df["row_index"] == row.Index].head(5)
        shap_table = "\n".join(
            f"| {r.feature} | {r.value:.3f} | {r.importance:.4f} |" for r in evidence.itertuples()
        ) or "| unavailable | — | — |"
        c = collusion.loc[row.driver_id] if not collusion.empty and row.driver_id in collusion.index else None
        collusion_count = int(c["collusion_signal_count"]) if c is not None else 0
        body = f"""# Sentinel Investigation Case — {row.driver_id}

**Created:** {datetime.now(timezone.utc).isoformat()}  
**Risk band:** {row.band} | **Ensemble score:** {row.score}/10

## Four-layer evidence

| Layer | Result |
|---|---:|
| XGBoost probability | {row.xgb_probability:.3f} |
| Isolation Forest | {row.iforest_score:.3f} |
| SQL signal hits | {int(row.sql_hits)} |
| Graph ring membership | {int(row.graph_flag)} |
| Cross-role collusion conditions | {collusion_count} |

## Top model drivers

| Feature | Observed value | Global importance |
|---|---:|---:|
{shap_table}

## Recommended action

Preserve telemetry, place the payout under manual review, and compare device, bank, IP,
store, and campaign links. If collusion conditions are present, escalate to Legal/Compliance
for FTC-sensitive adverse-action review before deactivation.

## Investigator checklist

- [ ] Validate GPS and device telemetry
- [ ] Review linked accounts and payout instruments
- [ ] Confirm incentive and refund history
- [ ] Document false-positive mitigations
- [ ] Record disposition and customer/driver impact

## Resolution

**Owner:** Unassigned  
**Disposition:** Pending  
**Notes:**  
"""
        (CASES / f"CASE_{row.driver_id}.md").write_text(body, encoding="utf-8")
    return len(critical)

