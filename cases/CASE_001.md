# Sentinel Investigation Case — CASE_001

**Risk band:** CRITICAL+ | **Ensemble score:** 10/10  
**Scenario:** Two driver accounts share one device, payout account, and incentive campaign.

## Four-layer evidence

| Layer | Result |
|---|---:|
| XGBoost probability | 1.000 |
| Isolation Forest | 0.681 |
| SQL signal hits | 12 |
| Graph ring membership | 1 |
| Cross-role collusion conditions | 3 |

## Top model drivers

| Feature | Observed value | SHAP contribution |
|---|---:|---:|
| incentive_trip_count | 21.000 | 7.2126 |
| geofence_dist_m | 632.092 | 1.0762 |
| C5 | 8.000 | 0.4344 |
| C1 | 12.000 | 0.2254 |
| refund_count_30d | 3.000 | 0.1108 |

## Linked entities

| Entity type | Entity | Linked drivers |
|---|---|---|
| Device | DEV_CASE001 | D000000, D000001 |
| Payout account | BANK_CASE001 | D000000, D000001 |
| Incentive campaign | CMP_CASE001 | D000000, D000001 |

## Recommended action

Preserve telemetry and place related payouts under manual review. Validate whether the shared
infrastructure reflects an authorized operational relationship or coordinated account control.
Escalate any adverse-action recommendation through Legal/Compliance review.

## Investigator checklist

- [ ] Validate GPS and device telemetry
- [ ] Review linked accounts and payout instruments
- [ ] Confirm campaign and incentive history
- [ ] Document false-positive mitigations
- [ ] Record disposition and driver impact

## Resolution

**Owner:** Unassigned  
**Disposition:** Pending  
**Notes:**

