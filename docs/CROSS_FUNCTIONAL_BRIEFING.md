# Cross-functional stakeholder briefings

> Four one-page briefings on CASE_001 (coordinated account infrastructure)
> written for four different audiences. Same facts, different framing.
> This template demonstrates the JD requirement to present operational
> insights to Product, Legal, Engineering, and Care Operations.

---

## Briefing A — Product and Platform Engineering

**Subject:** Control gap enabling coordinated account infrastructure — product fix required

**What happened:** Two driver accounts operated from a single device and payout
instrument, harvesting an incentive campaign while generating GPS anomalies.
The existing onboarding flow allowed this to persist undetected.

**The control gap:** The platform has no step-up verification trigger when a
payout instrument token is linked to a second account within 30 days. A fraudster
can create Account B, link the same bank token used by Account A, and begin
earning immediately. Detection only occurs downstream in fraud analytics — not
at the point of account creation.

**Evidence:**

| Signal | Account A (DRV-D000000) | Account B (DRV-D000001) |
|--------|------------------------|------------------------|
| Device ID | DEV_CASE001 | DEV_CASE001 (identical) |
| Payout token | BANK_CASE001 | BANK_CASE001 (identical) |
| Active campaign | CMP_CASE001 | CMP_CASE001 (identical) |
| XGBoost score | 1.000 | 1.000 |

**Recommended product action:** Add a step-up challenge (selfie reverification)
when a payout instrument token is linked to a second account within 30 days.
This closes the gap at onboarding — earlier and cheaper than post-hoc detection.

**Ask:** Confirm whether payout instrument deduplication exists at onboarding.
If not, prioritise as P1 platform control.

---

## Briefing B — Legal and Compliance

**Subject:** CASE_001 evidence summary — adverse action basis and regulatory positioning

**Case type:** Coordinated account infrastructure — multi-account payout abuse
with GPS anomaly indicators

**Adverse action contemplated:** Account suspension (both accounts), payout hold
pending investigation

**Multi-layer corroboration:**

1. SQL signals: 12 of 25 rules triggered across GPS, device, and payout domains
2. Isolation Forest: 0.681 anomaly score — behaviour is novel vs legitimate cohort
3. XGBoost: 1.000 synthetic-demo propensity — intentionally separable test scenario
4. Graph: both accounts share one device cluster and one bank token

**False-positive paths evaluated:**
- Shared household device: accounts show overlapping active sessions — inconsistent
  with legitimate household sharing
- Legitimate joint bank account: instrument token appears on no other account
  at shared address — not a household pattern

**Appeal pathway:** Both accounts receive written notification of adverse action
category. Appeal window: 14 days. Structured review by senior analyst with full
case file access.

**Regulatory positioning:** This adverse action is grounded in Spark Driver Terms
of Service (account integrity section) and is consistent with obligations for
documented, appealable adverse actions against independent contractors.

**Evidence retention:** Full case file retained with SHA-256 integrity hash for
7 years per Walmart records policy.

**Ask:** Confirm whether collusion_flag = 1 requires mandatory Legal review before
final suspension, or whether senior analyst sign-off is sufficient.

---

## Briefing C — Engineering and Data Infrastructure

**Subject:** CASE_001 telemetry findings — three infrastructure items for review

**Observation 1 — GPS telemetry accuracy filter risk:**
Signal 23 uses an accuracy_m ≤ 80 filter to suppress GPS drift false positives.
If the platform's GPS telemetry accuracy degrades (SDK update, carrier shift,
device population change), this filter may become too permissive or too restrictive.

**Recommended action:** Add a telemetry health metric tracking median GPS accuracy_m
by zone and app version. Alert if median exceeds 60m.

**Observation 2 — Payout instrument deduplication gap:**
The shared payout token was not flagged at account creation. Signal 07 caught it
post-hoc. An onboarding-level deduplication check is lower cost and higher value
than retrospective detection.

**Observation 3 — Streaming migration path for three highest-value signals:**

```
Signal 23 → Flink CEP: per-driver ring buffer of last 5 trip endpoints,
            evaluate on each TRIP_COMPLETED event
Signal 05 → Kafka consumer: device→[driver_id] inverted index,
            alert when cardinality > 3 within 30 days
Signal 07 → Kafka consumer: instrument_token→[driver_id] set,
            alert when cardinality > 2 within 180 days
```

These three signals account for the majority of high-value ring detection.
Streaming them reduces payout-to-detection latency from days to minutes.

**Ask:** (1) Confirm current GPS accuracy_m distribution in production.
(2) Confirm feasibility of payout instrument deduplication at onboarding.
(3) Prioritise streaming migration for signals 23, 05, 07 in roadmap.

---

## Briefing D — Care Operations and Driver Support

**Subject:** CASE_001 — driver communication guidance and appeal handling

**Accounts affected:** DRV-D000000, DRV-D000001

**Action:** Payout hold pending investigation. Account access restricted pending
reverification.

**Approved language for driver contacts:**

> "Your account has been flagged for a routine security review. Your earnings
> are being held temporarily while our fraud operations team completes this
> review. This process typically takes 2–5 business days. You can submit an
> appeal at [appeal URL]. If we do not confirm a policy violation, your account
> will be reinstated and any held earnings will be released promptly."

**Do not say:**
- Do not confirm or deny that GPS data was analysed
- Do not share the composite risk score or which signals fired
- Do not indicate whether both accounts are under review simultaneously
- Do not promise a specific reinstatement timeline until fraud ops confirms

**Appeal routing:** If either driver submits an appeal, log it against CASE_001
and route to the assigned fraud analyst — not Care Ops — for substantive review.
Target initial response: 48 hours.

**Ask:** Confirm whether Care Ops has automated routing to fraud analytics for
appeals, or whether this is a manual handoff.
