# DETECTION_STRATEGY.md — Project Sentinel

> **Purpose:** This document defines the operational detection strategy for Project Sentinel.
> Each fraud pattern is documented using a structured template covering threat context,
> detection signals, evidence requirements, decision thresholds, precision/recall targets,
> operational cost, business impact, and monitoring plan.
>
> **Audience:** Fraud Operations, Product, Engineering, Legal, Risk Governance.
>
> **Status:** Living document. All thresholds and economics are modeled assumptions
> based on scenario analysis and synthetic telemetry. Values should be validated and
> calibrated against live platform data before production use.

***

## Strategic Framing

Project Sentinel operates on a core business constraint: the detection window for
Spark Driver-style fraud is narrow and pre-settlement. Once a payout is released,
recovery is difficult and investigator effort shifts from prevention to evidence
preservation. Every detection strategy in this document is designed to:

1. **Catch abuse before settlement**, not after.
2. **Minimize false-positive harm** to legitimate contractors.
3. **Produce defensible evidence chains** that Legal can use in adverse-action review.
4. **Generate product-actionable root causes**, not just cases.

Detection is not the end state. Every signal family below connects to a control
recommendation, a product team owner, and a monitoring plan.

***

## Signal Severity Tiers

All 25 signals in the Sentinel library are classified into three operational tiers.
Severity tier determines how a signal feeds the decision matrix.

| Tier | Name | Decision Impact | Examples |
|------|------|-----------------|---------|
| **Fatal** | Hard stop | Overrides ensemble score; triggers immediate escalation | Impossible transit, confirmed device farm |
| **High** | Strong indicator | Elevates ensemble score; queues for investigation | Rooted device + shared payout, geofence miss cluster |
| **Warning** | Soft indicator | Contributes to ensemble; monitored for pattern accumulation | Shared IP (low risk), minor amount anomaly |

Fatal-tier signals represent physical impossibilities or confirmed infrastructure
abuse. They should not be buffered by low ML scores. The decision matrix treats
them as hard guardrails that route independently of the ensemble blend.

***

## Confidence Level Definitions

Every scored driver receives an operational confidence level that determines
the downstream investigative response. No permanent enforcement action is taken
from analytics alone; all Critical and Fatal cases require analyst sign-off.

| Confidence | Score Band | Operational Response |
|-----------|-----------|----------------------|
| **Low** | 0–3 | Monitor only; flag for trend accumulation |
| **Medium** | 3–5 | Queue for secondary checks; no adverse action |
| **High** | 5–7 | Immediate investigation; potential temporary hold |
| **Critical** | 7–9 | Temporary restriction pending analyst review |
| **Fatal** | 9–10 or Fatal rule | Immediate escalation; evidence preservation; Legal notification |

***

## Detection Strategy Templates

***

### Strategy 01 — GPS Spoofing and Location Manipulation

**Threat context:**
Contractors use GPS spoofing applications or rooted devices to simulate trip
completion or platform proximity without physical travel. This is among the highest-
value fraud types in delivery marketplaces because it directly creates fake earnings
at scale with no physical effort.

**Primary signals:**
- Signal 01: Impossible transit (speed between GPS pings exceeds physical limit)
- Signal 02: Route entropy anomaly (GPS path mathematically inconsistent with road network)
- Signal 06: Geofence miss cluster (repeated failures to enter expected delivery zones)
- Signal 09: Airplane mode telemetry jump (connectivity gap followed by instant arrival)

**Signal severity tier:** Fatal (Signal 01), High (Signals 02, 06, 09)

**Evidence required for action:**
- Two or more corroborating GPS signals within the same trip or session.
- Device state at time of anomaly (emulator flag, rooted status).
- Customer delivery confirmation timestamp vs claimed completion timestamp.

**Decision threshold:**
- Single impossible transit + any corroborating signal → Critical confidence.
- Three or more geofence misses in one shift → High confidence.

**Portfolio validation status:** Precision and recall are not estimated from the synthetic
demo. Production targets require representative labeled outcomes, temporal holdout testing,
and post-investigation dispositions.

**False positive risk:** Low. Legitimate GPS edge cases (tunnels, parking structures,
rural areas) produce isolated anomalies, not clusters. Corroboration requirement
reduces FP rate significantly.

**FP mitigation:** Require two corroborating signals before escalation. Cross-reference
delivery photo timestamp. Check customer-side GPS confirmation if available.

**Operational planning inputs:** Measure alert volume, median handling time, confirmed-loss
amount, and false-positive rate during a controlled pilot. No portfolio estimate is presented
as an observed operating result.

**Product control recommendation:**
- Require device attestation (e.g., Play Integrity API / Apple DeviceCheck) at delivery
  confirmation for drivers with two or more geofence anomalies.
- Product team owner: Platform Integrity Engineering.
- Engineering effort: Medium.
- Measure change in confirmed spoofing rate and legitimate-driver friction during a
  controlled rollout with a fast-track appeal process.

**Monitoring plan:**
- Weekly spoof rate by region and device type.
- Alert if FP rate on Signal 01 exceeds 8%.
- Track technique evolution: new spoofing tools rotate signature patterns quarterly.

***

### Strategy 02 — Bot-Assisted Offer Grabbing and Incentive Abuse

**Threat context:**
Automation tools allow fraudulent contractors to accept high-value offers or
incentive-eligible trips at speeds that exceed human reaction time. This degrades
the earning fairness for legitimate drivers and inflates incentive program costs.

**Primary signals:**
- Signal 03: Sub-human offer acceptance latency (acceptance time < 300ms consistently)
- Signal 04: Cherry-pick pattern (rapid accept/decline cycles on low-tip orders)
- Signal 07: Incentive campaign concentration (disproportionate bonus claim rate)
- Signal 12: Batch order gaming (multi-order accept without route plausibility)

**Signal severity tier:** High (all four signals)

**Evidence required for action:**
- Sustained latency pattern across multiple sessions (not single-event).
- Incentive claim rate significantly above peer cohort baseline.
- Device state consistent with automation capability (developer mode, emulator).

**Decision threshold:**
- Signal 03 sustained across 10+ acceptances in one session → High confidence.
- Signal 07 + Signal 03 → Critical confidence.
- All four signals → Fatal; escalate immediately.

**Portfolio validation status:** Precision and recall are not estimated from the synthetic
demo. Validate against adjudicated sessions and time-based holdout cohorts.

**False positive risk:** Medium. Power users and experienced drivers have genuinely
fast acceptance times. Cohort benchmarking is essential to reduce FP rate.

**FP mitigation:**
- Normalize latency against driver's own historical baseline, not platform-wide average.
- Require incentive anomaly co-signal before escalation.
- Check device state; legitimate fast drivers rarely use developer/emulator configurations.

**Operational planning inputs:** Measure alert volume, session-review time, confirmed
incentive loss, and legitimate power-user escalation rate during a pilot.

**Product control recommendation:**
- Introduce randomized latency window for offer presentation to neutralize automation
  timing advantage.
- Add incentive eligibility cooldown per device, not per account.
- Product owner: Delivery Experience Product.
- Engineering effort: Low–Medium.

**Monitoring plan:**
- Weekly acceptance latency distribution by driver cohort.
- Monthly incentive claim rate anomaly report.
- Alert if bot-pattern precision drops below 70% (signal that operators adapted).

***

### Strategy 03 — Multi-Account Ring and Shared Infrastructure Fraud

**Threat context:**
Organized fraud groups operate multiple contractor accounts that share a common
device, payout instrument, IP address, or campaign behavior. Ring-level fraud is
harder to detect at the account level but highly visible in graph analysis.
Professional fraud rings cause disproportionate loss per investigation hour.

**Primary signals:**
- Signal 11: Shared device identifier across multiple accounts
- Signal 14: Shared payout instrument across accounts
- Signal 15: Shared IP address cluster (adjusted for carrier NAT risk)
- Signal 17: Coordinated incentive campaign timing across ring members
- Graph layer: NetworkX ring detection (connected components ≥ 2 accounts)

**Signal severity tier:** Fatal (confirmed ring with shared device + payout), High (IP cluster only)

**Evidence required for action:**
- Two or more confirmed shared identifiers (device + payout, or device + IP + campaign).
- Graph ring confirmed by NetworkX component analysis.
- OSINT enrichment showing identity or address anomalies across ring members.

**Decision threshold:**
- Shared device + shared payout → Critical; 1.4× ring multiplier applied to ensemble.
- Confirmed ring of 3+ accounts → Fatal; 1.5× multiplier; all members escalated.

**Portfolio validation status:** Precision and recall are not estimated from the synthetic
demo. Validate ring decisions against adjudicated linked-account cases and identity-review
outcomes.

**False positive risk:** Low for device+payout signals. Higher for IP-only signals
(carrier NAT creates legitimate shared IPs). IP signal classified as Warning tier.

**FP mitigation:**
- Never use IP signal alone for escalation.
- Require two independent shared identifiers before ring flag.
- OSINT address verification cross-check for all ring members before adverse action.

**Operational planning inputs:** Measure unique rings, accounts per ring, investigation time,
confirmed linked loss, and false linkage caused by shared household or carrier infrastructure.

**Product control recommendation:**
- Device binding at onboarding: one active contractor account per device.
- Payout instrument deduplication across account network.
- Product owner: Identity and Trust Platform.
- Engineering effort: High (requires cross-account identity graph at onboarding).

**Monitoring plan:**
- Weekly ring detection volume by shared identifier type.
- Track ring size distribution: if average ring size grows, organized fraud is scaling.
- Alert if ring precision drops below 85%.

***

### Strategy 04 — Payout Redirection and Account Takeover

**Threat context:**
Payout account changes made immediately before settlement are a strong signal of
either account takeover (ATO) or deliberate fraud. This attack type targets the
moment of highest financial exposure in the delivery lifecycle.

**Primary signals:**
- Signal 18: Payout account change within 24h of settlement
- Signal 19: Login from new device + payout change in same session
- Signal 20: Multiple failed login attempts preceding payout change
- Signal 22: Payout destination matches known suspicious instrument

**Signal severity tier:** Fatal (Signal 18 + 19 together), High (Signals 18, 20 alone)

**Evidence required for action:**
- Payout change timing relative to scheduled settlement.
- Device fingerprint at time of change (new device flag).
- Account history of previous payout stability.

**Decision threshold:**
- Payout change within 24h of settlement + new device → Fatal; immediate payout hold.
- Payout change alone → High; queue for verification before release.

**Portfolio validation status:** Precision and recall are not estimated from the synthetic
demo. Validate against confirmed account-takeover and legitimate payout-change outcomes.

**False positive risk:** Medium. Legitimate contractors occasionally update payout
accounts around settlement dates. Verification callback reduces FP rate significantly.

**FP mitigation:**
- Verification callback or notification to contractor's registered contact method.
- 24h hold with fast-track verification option for legitimate changes.
- Appeal path documented in contractor terms.

**Operational planning inputs:** Measure payout-change volume, verification completion,
hold duration, confirmed prevented loss, and legitimate-contractor friction.

**Product control recommendation:**
- Mandatory 24h cooling period for payout account changes.
- Multi-factor verification for payout changes from new devices.
- Product owner: Payments and Contractor Experience.

**Monitoring plan:**
- Daily payout change velocity report.
- Alert if payout-change-to-settlement gap shrinks (attackers adapting to cooling period).

***

### Strategy 05 — Fake Delivery and Customer Collusion

**Threat context:**
Contractors mark deliveries complete without completing the trip, or coordinate
with customers to claim false delivery failures to trigger reimbursements. This
is among the hardest fraud types to detect without multi-signal corroboration
because the attacker controls the completion event.

**Primary signals:**
- Signal 21: Delivery marked complete with GPS not at destination
- Signal 23: Contractor + customer pair with repeated claim history
- Signal 24: Photo timestamp inconsistency (photo metadata predates arrival)
- Signal 25: High refund velocity on specific contractor-customer pairs

**Signal severity tier:** Fatal (Signal 21 + 24 together), High (Signals 23, 25)

**Evidence required for action:**
- GPS non-arrival corroborated by delivery photo timestamp anomaly.
- Or: repeated claim pattern on same contractor-customer pair (threshold: 3+).

**Decision threshold:**
- GPS non-arrival + photo timestamp inconsistency → Fatal; immediate case generation.
- 3+ claims on same pair → High; investigation queue.

**Portfolio validation status:** Precision and recall are not estimated from the synthetic
demo. Validate against adjudicated delivery claims with source-photo and location evidence.

**FP mitigation:**
- Photo metadata may be stripped by legitimate privacy tools; require GPS corroboration.
- Customer collusion requires pattern, not single incident.

**Operational planning inputs:** Measure claim volume, source-evidence availability,
investigation time, confirmed delivery loss, and customer-collusion outcomes.

**Product control recommendation:**
- Geofence-locked delivery confirmation: completion photo only accepted within delivery
  zone boundary.
- Customer confirmation step for high-value or repeated-claim pairs.
- Product owner: Delivery Experience Product.

**Monitoring plan:**
- Weekly fake delivery rate by region.
- Track photo metadata strip rate as adversary adaptation signal.

***

## Production Economics Measurement Plan

| Signal family | Volume measure | Quality measure | Cost measure | Outcome measure |
|---|---|---|---|---|
| GPS spoofing | Alerts and unique drivers | Confirmed-alert precision | Review and appeal time | Confirmed loss prevented |
| Bot/incentive | Sessions and unique devices | Adjudicated precision | Session-review time | Incentive leakage prevented |
| Ring detection | Rings and linked accounts | Confirmed-link precision | Multi-account review time | Linked loss prevented |
| Payout redirect | Changes and holds | ATO confirmation rate | Verification and hold cost | Payout loss prevented |
| Fake delivery | Claims and driver-customer pairs | Confirmed-claim precision | Evidence-review time | Delivery loss prevented |

ROI should be calculated only after these measures are observed in a controlled pilot:
`(confirmed loss prevented - operating cost) / operating cost`.

***

## Detection Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| v1 | SQL rule engine — 25 signals | Complete |
| v2 | Feature engineering and ML (XGBoost + Isolation Forest) | Complete |
| v3 | Graph ring detection (NetworkX) | Complete |
| v4 | OSINT enrichment pipeline | Complete |
| v5 | Streaming pre-settlement detection (Flink/Kafka architecture) | Planned |
| v6 | Adaptive threshold engine (signal drift response) | Planned |
| v7 | Product control recommendation automation | Planned |
| v8 | Threat intelligence integration (F3 framework alignment) | Planned |
