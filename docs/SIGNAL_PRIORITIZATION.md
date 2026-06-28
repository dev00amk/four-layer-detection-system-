# Signal prioritisation framework

> Operational triage framework for the 25 Sentinel SQL signals.
> Defines how to decide which signals to tune, which to sunset,
> and which to escalate to engineering for a product-level fix.

---

## The three-axis scoring model

Every signal is evaluated on three dimensions:

**Detection yield (DY):** What fraction of confirmed fraud cases does this signal
catch? High yield = high retention priority. Scored 1–5.

**False-positive cost (FPC):** What is the operational cost of one false positive?
Includes analyst review (~30 min), support contact ($8–12), and driver impact.
Scored 1–5 where 5 = very high FP cost.

**Business impact (BI):** What is the dollar value of the fraud this signal
targets? From the loss model in BUSINESS_IMPACT.md. Scored 1–5.

**Priority score = DY × 0.4 + (5 - FPC) × 0.3 + BI × 0.3**

---

## Signal prioritisation matrix

| # | Signal | Fraud family | DY | FPC | BI | Score | Action |
|---|--------|-------------|----|----|----|----|--------|
| 23 | GPS spoofing impossible transit | GPS / spoof | 5 | 2 | 5 | **4.6** | Protect |
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
| 09 | High payout reversal rate | Payout abuse | 3 | 3 | 3 | **3.0** | Monitor |
| 17 | Rapid device hopping | ATO precursor | 3 | 3 | 3 | **3.0** | Monitor |
| 03 | Pickup outside store geofence | Fake arrival | 3 | 4 | 3 | **2.7** | Tune — high FP near large stores |
| 06 | Emulator or rooted device | Tooling | 3 | 4 | 3 | **2.7** | Use as multiplier only |
| 10 | Referral farm detection | Promo abuse | 3 | 3 | 2 | **2.7** | Monitor |
| 04 | Zero-dwell pickup scan | Fake arrival | 3 | 4 | 3 | **2.7** | Tune — FP near small orders |
| 18 | Shared IP cluster | Farm | 2 | 4 | 3 | **2.3** | Tune — carrier NAT FP risk |
| 15 | Outlier trip distance | Manipulation | 2 | 3 | 2 | **2.3** | Monitor |
| 14 | Unusual night activity shift | ATO | 2 | 4 | 3 | **2.1** | Use as multiplier only |
| 12 | Reward-only activity pattern | Promo abuse | 2 | 4 | 2 | **2.0** | Monitor |
| 16 | Geofence miss by store | Collusion | 2 | 4 | 3 | **2.1** | Escalate to product |
| 22 | Composite risk score | Aggregate | — | — | — | — | Output only |
| 21 | Appeal overturn rate | QA metric | — | — | — | — | Feedback loop only |

---

## Decision rules by tier

### Protect (score ≥ 4.0) — signals 23, 05, 07, 24, 25, 01, 02

Do not lower thresholds without Legal sign-off. If appeal overturn rate for any
of these exceeds 15%, escalate immediately — do not silently lower the threshold.

### Tune threshold (score 3.0–3.9) — signals 19, 13, 08, 20

Re-evaluate quarterly. Track precision at analyst review queue (target ≥ 65%)
and appeal overturn rate (target < 10%).

### Monitor (score 2.0–2.9) — signals 11, 09, 17, 10, 18, 15, 12

Use as corroborating evidence only. Do not trigger standalone adverse action.
If precision below 40% for two consecutive quarters, sunset.

### Use as multiplier only — signals 06, 14

Increase composite score weight of co-firing signals. Do not trigger independently.

### Escalate to product — signal 16

High geofence miss rate at specific stores may indicate inaccurate store polygons,
not fraud. Audit store geofence data quality before treating as enforcement.

---

## Signal lifecycle governance

**Adding a signal:** Shadow mode only for 30 days → measure precision on labeled
cases → document FP paths → fraud operations lead approval → add to composite score.

**Sunsetting a signal:** Precision < 35% for two quarters OR overturn rate > 25%
for two quarters OR fraud pattern closed by product fix. Keep SQL file in version
control with DEPRECATED header. Document sunset date and reason.

**Emergency threshold adjustment:** If signal fires 5× baseline, investigate
the cause before adjusting. If real fraud wave: escalate to senior analyst and
engineering. If telemetry change: add suppression rule, document, notify data
engineering.

---

*Review this framework quarterly and after every major incident.*
