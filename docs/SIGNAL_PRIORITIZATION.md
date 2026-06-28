# Signal prioritisation framework

> Operational triage framework for the 25 Sentinel SQL signals.
> Defines how to decide which signals to tune, which to sunset,
> and which to escalate to engineering for a product-level fix.

---

## The three-axis scoring model

Every signal is evaluated on three dimensions:

**Detection yield (DY):** What fraction of confirmed fraud cases would this
signal have caught if it had been running? Measured retrospectively on labeled
cases. High yield = high retention priority.

**False-positive cost (FPC):** What is the operational cost of one false positive
from this signal? Includes analyst review time (~30 min at loaded cost), driver
support contact ($8–$12), driver dissatisfaction, and potential wrongful
deactivation risk. Low FPC = lower threshold tolerance.

**Business impact (BI):** What is the average dollar value of the fraud this
signal targets? From the loss model in BUSINESS_IMPACT.md. High BI = higher
engineering investment priority.

Score each dimension 1–5. Overall priority = DY × 0.4 + (5 - FPC) × 0.3 + BI × 0.3.

---

## Signal prioritisation matrix

| # | Signal | Fraud family | DY (1–5) | FPC (1–5) | BI (1–5) | Priority score | Recommendation |
|---|--------|-------------|---------|---------|---------|---------------|----------------|
| 23 | GPS spoofing impossible transit | GPS / spoof | 5 | 2 | 5 | **4.6** | Protect — highest priority |
| 05 | Shared device across drivers | Ring / farm | 5 | 3 | 5 | **4.3** | Protect |
| 07 | Shared payout instrument | Ring / mule | 5 | 2 | 4 | **4.2** | Protect |
| 24 | Bot-assisted batch grabbing | Automation | 4 | 2 | 4 | **3.8** | Protect |
| 25 | Device forensics account hopping | Ban evasion | 4 | 3 | 4 | **3.5** | Protect |
| 01 | Impossible travel between trips | GPS / spoof | 4 | 3 | 4 | **3.5** | Protect |
| 02 | GPS teleportation in-trip | GPS / spoof | 4 | 3 | 4 | **3.5** | Protect |
| 19 | Bank change before payout | ATO | 3 | 3 | 4 | **3.2** | Tune threshold |
| 13 | Deactivated actor re-entry | Ban evasion | 4 | 2 | 3 | **3.2** | Tune threshold |
| 08 | Incentive threshold cliff | Promo abuse | 4 | 3 | 3 | **3.2** | Tune — high FP near campaigns |
| 20 | Driver-customer collusion pair | Collusion | 3 | 3 | 4 | **3.2** | Tune threshold |
| 11 | High claim rate by driver | Delivery fraud | 3 | 3 | 3 | **3.0** | Monitor |
| 03 | Pickup outside store geofence | Fake arrival | 3 | 4 | 3 | **2.7** | Tune — FP high near large stores |
| 09 | High payout reversal rate | Payout abuse | 3 | 3 | 3 | **3.0** | Monitor |
| 06 | Emulator or rooted device | Tooling | 3 | 4 | 3 | **2.7** | Use as multiplier only |
| 17 | Rapid device hopping | ATO precursor | 3 | 3 | 3 | **3.0** | Monitor |
| 10 | Referral farm detection | Promo abuse | 3 | 3 | 2 | **2.7** | Monitor |
| 04 | Zero-dwell pickup scan | Fake arrival | 3 | 4 | 3 | **2.7** | Tune — FP near small orders |
| 18 | Shared IP cluster | Farm | 2 | 4 | 3 | **2.3** | Tune — carrier NAT FP risk |
| 15 | Outlier trip distance | Manipulation | 2 | 3 | 2 | **2.3** | Monitor |
| 14 | Unusual night activity shift | ATO | 2 | 4 | 3 | **2.1** | Use as multiplier only |
| 12 | Reward-only activity pattern | Promo abuse | 2 | 4 | 2 | **2.0** | Monitor |
| 16 | Geofence miss by store | Collusion | 2 | 4 | 3 | **2.1** | Escalate to product |
| 22 | Composite risk score | Aggregate | N/A | N/A | N/A | — | Output only — not standalone |
| 21 | Appeal overturn rate (QA) | QA metric | N/A | N/A | N/A | — | Feedback loop only |

---

## Decision rules by priority tier

### Protect (score ≥ 4.0) — signals 23, 05, 07, 24, 25, 01, 02

Do not lower thresholds without Legal sign-off. These signals target the highest-value,
most defensible fraud patterns. If appeal overturn rate (signal 21) for any of
these exceeds 15%, escalate immediately for threshold review — do not silently
lower the threshold.

### Tune threshold (score 3.0–3.9) — signals 19, 13, 08, 20

Re-evaluate thresholds quarterly. For each signal, track:
- Precision at analyst review queue (target ≥ 65%)
- Appeal overturn rate (target < 10%)
- Volume trend (if firing > 2× baseline, check for telemetry change before
  assuming a new fraud wave)

### Monitor (score 2.0–2.9) — signals 11, 09, 17, 10, 18, 15, 12

These signals are included in the composite score but should not trigger
standalone adverse action. Use only as corroborating evidence for other signals.
Review quarterly. If precision below 40% for 2 consecutive quarters, sunset.

### Use as multiplier only — signals 06, 14

Root/emulator flag and night-activity shift carry meaningful information but
generate too many FPs as standalone triggers. They should increase the composite
score weight of other signals that co-fire, not trigger independent action.

### Escalate to product — signal 16 (store geofence miss cluster)

A high rate of geofence misses concentrated at specific stores may indicate
a product problem (inaccurate store polygons) rather than a fraud pattern.
Before treating this signal as enforcement, audit the store geofence data
quality for the flagged stores.

---

## Signal lifecycle governance

### Adding a new signal

1. Document hypothesis: what fraud behaviour does this detect?
2. Run in shadow mode (log only, no scoring impact) for 30 days
3. Measure precision on labeled cases
4. Document FP paths and mitigation
5. Present to fraud operations lead for threshold approval
6. Add to composite score only after 30-day shadow period passes

### Sunsetting a signal

Criteria for sunset consideration:
- Precision below 35% for 2 consecutive quarters
- Appeal overturn rate above 25% for 2 consecutive quarters
- Fraud pattern it targeted has been closed by a product fix

Sunset process:
1. Remove from composite score weight
2. Keep SQL file in version control with DEPRECATED header
3. Document sunset date and reason in signal header comment

### Emergency threshold adjustment

If a new fraud wave causes a signal to fire 5× baseline volume:
1. Do not lower the threshold to reduce volume — investigate the wave first
2. Check whether the increase is real fraud or a telemetry change
3. If real fraud: escalate to Senior Analyst and Engineering
4. If telemetry change: add suppression rule, document, notify data engineering

---

*This framework should be reviewed quarterly by the fraud analytics lead and
updated whenever signal performance data changes materially.*
