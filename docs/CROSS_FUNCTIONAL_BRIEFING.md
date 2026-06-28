# Cross-functional stakeholder briefings

> Four one-page briefings on the same fraud case (CASE_001: coordinated
> account infrastructure) written for four different audiences.
> Each briefing uses the same facts but different framing, emphasis,
> and recommended action — matching what each team needs to act.

---

## How to use this document

The JD requires presenting "operational insights to Product, Legal, Compliance,
Engineering, and Care Operations to inform tooling improvements and policy updates."

This document is the template for doing that. In a real investigation, the
analyst would complete the bracketed fields from the actual case data and send
the appropriate section to each team. The CASE_001 data below is from the
Sentinel demo run.

---

## Briefing A — For: Product and Platform Engineering

**Subject:** Control gap enabling coordinated account infrastructure — product fix required

**What happened in one sentence:**
Two driver accounts operated from a single device and payout instrument, harvesting
an incentive campaign while generating GPS anomalies — and the existing onboarding
flow allowed this to persist for [N] days before detection.

**The control gap:**
The platform currently has no step-up verification trigger when a payout instrument
is first linked to a new account. A fraudster can create Account B, link the same
bank token used by Account A, and begin earning immediately. Detection only occurs
downstream in fraud analytics.

**What the data shows:**

| Signal | Account A (DRV-D000000) | Account B (DRV-D000001) |
|--------|------------------------|------------------------|
| Device ID | DEV_CASE001 | DEV_CASE001 (same) |
| Payout token | BANK_CASE001 | BANK_CASE001 (same) |
| Active incentive campaign | CMP_CASE001 | CMP_CASE001 (same) |
| XGBoost fraud score | 1.000 | 1.000 |

**Recommended product action:**
Add a step-up challenge (selfie reverification) when a payout instrument token
is linked to a second account within 30 days. This closes the gap at onboarding,
not at post-hoc detection. Estimated engineering effort: [S/M/L]. Estimated
fraud prevented annually at current ring detection rate: see BUSINESS_IMPACT.md.

**What we need from you:**
Confirm whether payout instrument deduplication check exists at onboarding.
If not, prioritise as P1 product control. If yes, confirm why it did not flag
this pair.

---

## Briefing B — For: Legal and Compliance

**Subject:** CASE_001 evidence summary — adverse action basis and regulatory positioning

**Case classification:** Coordinated account infrastructure — multi-account
payout abuse with GPS anomaly indicators

**Adverse action contemplated:** Account suspension (both accounts), payout hold
pending investigation

**Evidence basis:**

All four detection layers fired independently, providing multi-source corroboration:

1. SQL signals: 12 of 25 rules triggered across GPS, device, and payout domains
2. Isolation Forest: 0.681 anomaly score (threshold 0.60) — behaviour is novel
   relative to legitimate driver cohort
3. XGBoost: 1.000 fraud propensity (threshold 0.50) — highest possible score
4. Graph: both accounts are members of the same entity cluster (shared device +
   shared bank + shared campaign)

**False-positive paths evaluated and ruled out:**

- Shared household device: accounts show overlapping active sessions within
  [N] hours — inconsistent with legitimate household sharing
- Legitimate bank account sharing: instrument token appears on no other account
  with shared address — not a family household pattern
- Driver misidentification: identity verification status current for both accounts

**Appeal pathway:**
Both accounts will receive written notification of the adverse action basis
(category level, not signal-level detail). Appeal window: 14 days. Appeal
process: structured review by senior analyst with access to full case file.

**Regulatory note:**
This adverse action is grounded in the Spark Driver Terms of Service
[Section X — account integrity] and is consistent with Walmart's post-FTC
settlement obligations for documented, appealable adverse actions against
independent contractors.

**Retention:**
Full case file, evidence hash, and decision record retained for 7 years per
Walmart records policy. Evidence chain integrity: SHA-256 hash confirmed at
case generation.

**What we need from you:**
Confirm whether [collusion flag = 1] triggers a mandatory Legal review before
account suspension, or whether Senior Analyst sign-off is sufficient.

---

## Briefing C — For: Engineering and Data Infrastructure

**Subject:** CASE_001 telemetry findings — three infrastructure signals requiring attention

**Pattern detected:**
Coordinated account infrastructure operating across two driver accounts. The
detection succeeded, but three infrastructure observations from this case should
be reviewed by the engineering team.

**Observation 1 — GPS telemetry accuracy degradation**
Signal 23 (GPS impossible transit) required an accuracy_m ≤ 80 filter to
suppress GPS drift false positives. If the platform's GPS telemetry accuracy
degrades (device population shifts, location SDK changes), this filter may
become too permissive or too restrictive. Recommend: add a telemetry health
dashboard tracking median GPS accuracy_m by zone and app version. Alert if
median exceeds 60m.

**Observation 2 — Payout instrument deduplication gap**
The shared payout token was not flagged at account creation time. Signal 07
caught it post-hoc. The engineering fix (instrument deduplication at onboarding)
is lower cost and higher value than the detection approach. See Briefing A.

**Observation 3 — Streaming migration path**
The current Sentinel implementation uses DuckDB batch. For the three highest-value
signals (GPS impossible transit, shared device, shared payout), latency matters —
catching these before payout settlement requires evaluating them within the
payout window (typically T+24h to T+72h). Recommended streaming migration:

```
Signal 23 → Flink CEP: per-driver ring buffer of last 5 trip endpoints,
            evaluate on each TRIP_COMPLETED event
Signal 05 → Kafka consumer: maintain device→[driver_id] inverted index,
            alert when cardinality exceeds 3
Signal 07 → Kafka consumer: maintain instrument_token→[driver_id] set,
            alert when cardinality exceeds 2
```

**What we need from you:**
1. Confirm current GPS accuracy_m distribution in production
2. Confirm feasibility of payout instrument deduplication at onboarding
3. Prioritise streaming migration for signals 23, 05, 07 in roadmap

---

## Briefing D — For: Care Operations and Driver Support

**Subject:** CASE_001 — driver impact, communication guidance, and appeal handling

**Accounts affected:** DRV-D000000, DRV-D000001

**Action taken:** Payout hold pending investigation. Account access [suspended /
restricted] pending reverification.

**What to tell drivers if they contact support:**

Do not share signal-level details (which specific rule triggered, what GPS
data was observed). Use the following approved language:

> "Your account has been flagged for a routine security review. Your earnings
> are being held temporarily while our fraud operations team completes this
> review. This process typically takes [2–5 business days]. You can submit an
> appeal at [appeal URL]. If we do not confirm fraud, your account will be
> reinstated and any held earnings will be released promptly."

**What NOT to say:**
- Do not confirm or deny that GPS data was analysed
- Do not share the composite risk score
- Do not indicate whether both accounts are under review simultaneously
- Do not promise a specific reinstatement timeline until fraud ops confirms

**Appeal handling:**
If either driver submits an appeal:
1. Log the appeal in the case management system against CASE_001
2. Route to the assigned fraud analyst (not Care Ops) for substantive review
3. Target initial response within 48 hours
4. If the appeal raises new exculpatory information (e.g., device was shared
   with an authorised family member), route to senior analyst

**Driver impact note:**
Earnings hold on both accounts. Combined estimated held earnings: $[X].
If investigation confirms fraud, held earnings are subject to clawback per
Spark Driver Terms. If no fraud confirmed, release immediately with no
driver penalty.

**What we need from you:**
Confirm whether Care Ops has access to the appeal intake form and whether
the routing to fraud analytics is automated or manual.
