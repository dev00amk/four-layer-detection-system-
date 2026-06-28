# FRAUD_TECHNIQUES.md — Project Sentinel

> **Purpose:** This document is Project Sentinel's internal threat intelligence library.
> It functions as an ATT&CK-style knowledge base for Spark Driver fraud, mapping
> adversary techniques to lifecycle stages, detection signals, evidence categories,
> and mitigation options.
>
> **Framework alignment:** Structure inspired by MITRE ATT&CK and the MITRE Fight
> Fraud Framework (F3), which maps fraud actor behaviors across a lifecycle from
> positioning to monetization. F3 recognizes fraud as an adversarial campaign with
> distinct techniques, not isolated events.
>
> **Audience:** Fraud Operations, Detection Engineering, Product, Trust & Safety.

***

## Fraud Kill Chain — Spark Driver Context

Sophisticated fraud campaigns follow a lifecycle. Mapping signals to lifecycle
stages lets investigators understand which stage a flagged driver is in and which
controls to apply. Fraud operations that don't think in lifecycles are always
one step behind the adversary.

```
Stage 01  Reconnaissance         Identify platform incentive structures,
                                   payout timing, detection gaps, peer networks.

Stage 02  Identity Preparation   Acquire/fabricate identity documents,
                                   payment instruments, phone numbers.

Stage 03  Device Preparation     Root device, install emulator or GPS spoof
                                   tool, configure developer mode.

Stage 04  Account Creation       Onboard contractor account with prepared
                                   identity. May use referral link from ring.

Stage 05  Warm-Up Period         Perform legitimate deliveries to build
                                   account history and reduce anomaly score.

Stage 06  Offer Collection       Begin bot-assisted or cherry-picked offer
                                   acceptance. Test platform detection gaps.

Stage 07  Delivery Simulation    GPS spoof, fake-complete trips, manipulate
                                   photo or timestamp evidence.

Stage 08  Incentive Abuse        Trigger promotion windows, referral bonuses,
                                   batch incentives across ring accounts.

Stage 09  Cashout                Collect earnings via redirected or controlled
                                   payout instruments. May change payout account
                                   immediately before settlement.

Stage 10  Account Abandonment    Drop accounts before investigation completes.
                                   Recycle identity materials for new campaign.
```

***

## Technique Library

***

### T-001 — GPS Manipulation

| Field | Detail |
|-------|--------|
| **Technique** | GPS Manipulation |
| **F3 Category** | Location Integrity |
| **Lifecycle Stage** | Stage 07 — Delivery Simulation |
| **Tactics** | Evasion, Fraud Execution |
| **Description** | Adversary manipulates location signals to simulate trip completion or proximity without physical travel. Methods include mock location apps, rooted device GPS override, and hardware-level NMEA injection. |
| **Evidence** | Route entropy anomaly, impossible transit speed, GPS gap followed by instant arrival, geofence non-entry |
| **Sentinel Signals** | Signal 01 (Impossible Transit — Fatal), Signal 02 (Route Entropy — High), Signal 06 (Geofence Miss — High), Signal 09 (Airplane Mode Jump — High) |
| **ML Features** | avg_trip_speed_mph, gps_gap_flag, route_deviation_score |
| **Graph Signal** | GPS spoof clusters sometimes correlate with shared device rings |
| **OSINT Enrichment** | Device intelligence (conceptual equivalent: Incognia location verification) |
| **Mitigations** | Device attestation at delivery confirmation, geofence-locked completion, GPS corroboration requirement |
| **FP Risk** | Low — legitimate GPS edge cases (tunnels, rural areas) produce isolated, not clustered, anomalies |
| **FP Mitigation** | Require two corroborating GPS signals; cross-reference delivery photo timestamp |

***

### T-002 — Emulator and Rooted Device Abuse

| Field | Detail |
|-------|--------|
| **Technique** | Emulator / Rooted Device |
| **F3 Category** | Device Integrity |
| **Lifecycle Stage** | Stage 03 — Device Preparation; Stage 06–07 — Execution |
| **Tactics** | Defense Evasion, Platform Integrity Bypass |
| **Description** | Adversary uses rooted devices or software emulators to bypass platform integrity checks, enable GPS spoofing, automate offer acceptance, or run multiple simultaneous account sessions from one machine. |
| **Evidence** | Emulator flag in device telemetry, rooted device indicator, developer mode active, OS version/hardware mismatch |
| **Sentinel Signals** | Signal 05 (Emulator Flag — High), Signal 08 (Device Integrity Failure — High) |
| **ML Features** | emulator_flag, rooted_device_flag, device_integrity_score |
| **Graph Signal** | Emulator instances frequently map to device farm rings |
| **OSINT Enrichment** | Device intelligence (conceptual equivalent: SEON device fingerprinting) |
| **Mitigations** | Play Integrity API / Apple DeviceCheck enforcement at session start, deny trip acceptance from flagged devices |
| **FP Risk** | Low — emulator and root flags on production delivery devices have very low legitimate explanation |
| **FP Mitigation** | Allow verified developer accounts with documented test device registration |

***

### T-003 — Bot-Assisted Offer Acceptance

| Field | Detail |
|-------|--------|
| **Technique** | Automated Offer Acceptance |
| **F3 Category** | Behavioral Automation |
| **Lifecycle Stage** | Stage 06 — Offer Collection |
| **Tactics** | Privilege Escalation (economic), Competitive Advantage Abuse |
| **Description** | Adversary uses automation scripts or modified app binaries to accept high-value offers at speeds that exceed human reaction time, capturing disproportionate earnings and incentive-eligible trips. |
| **Evidence** | Sub-300ms acceptance latency sustained across sessions, acceptance rate significantly above peer cohort, device running developer tools |
| **Sentinel Signals** | Signal 03 (Acceptance Latency — High), Signal 04 (Cherry-Pick Pattern — High) |
| **ML Features** | offer_acceptance_latency_ms, acceptance_rate_percentile, session_automation_score |
| **Graph Signal** | Bot operators frequently coordinate across ring accounts on same incentive window |
| **OSINT Enrichment** | None primary — behavioral signal is self-contained |
| **Mitigations** | Randomized offer presentation latency window, acceptance rate percentile cap, developer mode flag at offer display |
| **FP Risk** | Medium — experienced legitimate drivers have fast acceptance; cohort normalization required |
| **FP Mitigation** | Normalize against driver's own historical baseline; require incentive anomaly co-signal |

***

### T-004 — Incentive Stacking and Promotion Abuse

| Field | Detail |
|-------|--------|
| **Technique** | Incentive Stacking |
| **F3 Category** | Promotion Integrity |
| **Lifecycle Stage** | Stage 08 — Incentive Abuse |
| **Tactics** | Resource Abuse, Coordinated Campaign |
| **Description** | Adversary coordinates multiple accounts within a ring to maximize bonus claim rates during promotion windows. Each account captures a share of incentive eligibility, and earnings are consolidated through shared payout instruments. |
| **Evidence** | Disproportionate incentive claim rate vs peer cohort, coordinated campaign timing across accounts, shared payout destination |
| **Sentinel Signals** | Signal 07 (Incentive Concentration — High), Signal 17 (Coordinated Campaign Timing — High) |
| **ML Features** | bonus_claim_rate, incentive_window_participation, promo_concentration_score |
| **Graph Signal** | Ring accounts consistently show correlated incentive activity timing |
| **OSINT Enrichment** | Identity verification across ring accounts (conceptual: Socure / Persona) |
| **Mitigations** | Incentive eligibility per device (not per account), promotion window anomaly monitoring, ring-level bonus cap |
| **FP Risk** | Medium — legitimate drivers who work intensively during promotions may trigger concentration signals |
| **FP Mitigation** | Require ring co-signal or shared payout co-signal before escalation |

***

### T-005 — Multi-Account Ring Operation

| Field | Detail |
|-------|--------|
| **Technique** | Coordinated Multi-Account Ring |
| **F3 Category** | Identity and Account Integrity |
| **Lifecycle Stage** | Stage 04 — Account Creation; Stage 08–09 — Cashout |
| **Tactics** | Account Manipulation, Resource Multiplexing |
| **Description** | Adversary operates multiple contractor accounts that share a common device, payout instrument, IP address, or campaign behavior pattern. Ring-level fraud causes disproportionate loss per investigation because each account appears individually marginal but the collective operation is large-scale. |
| **Evidence** | Shared device ID across accounts, shared payout instrument, shared IP (corroborated), coordinated session timing |
| **Sentinel Signals** | Signal 11 (Shared Device — Fatal), Signal 14 (Shared Payout — Fatal), Signal 15 (Shared IP — Warning), Signal 17 (Coordinated Campaign — High) |
| **ML Features** | shared_device_flag, shared_payout_flag, ring_member_flag |
| **Graph Signal** | Primary — NetworkX connected component detection; 1.4× multiplier for confirmed rings |
| **OSINT Enrichment** | Address type verification (shared household vs residential), identity cross-check across accounts (conceptual: LexisNexis, Socure) |
| **Mitigations** | One active account per device binding at onboarding, payout instrument deduplication across account network |
| **FP Risk** | Low for device+payout signals; Medium for IP-only (carrier NAT creates legitimate shared IPs) |
| **FP Mitigation** | Never escalate on IP signal alone; require two independent shared identifiers |

***

### T-006 — Payout Account Takeover and Redirection

| Field | Detail |
|-------|--------|
| **Technique** | Payout Redirection / Account Takeover |
| **F3 Category** | Payment Integrity |
| **Lifecycle Stage** | Stage 09 — Cashout |
| **Tactics** | Credential Access, Financial Manipulation |
| **Description** | Adversary compromises a legitimate contractor's account credentials and redirects payout to a controlled instrument immediately before settlement. May also originate from insider account sales where the original contractor sells account access. |
| **Evidence** | Payout account change within 24h of settlement, new device at time of change, prior failed login attempts, payout destination matches flagged instrument |
| **Sentinel Signals** | Signal 18 (Payout Change Timing — Fatal), Signal 19 (New Device + Payout Change — Fatal), Signal 20 (Pre-Change Login Failures — High) |
| **ML Features** | payout_change_flag, days_to_settlement, new_device_at_change, login_failure_rate |
| **Graph Signal** | Redirected payout instruments sometimes appear in ring payout networks |
| **OSINT Enrichment** | Account resale detection (check contractor-for-sale marketplaces), identity verification on new payout instrument owner (conceptual: Sentilink for synthetic identity) |
| **Mitigations** | 24h mandatory cooling period on payout changes, MFA for changes from new devices, verification callback on payout update |
| **FP Risk** | Medium — legitimate contractors do change payout accounts; timing is the key differentiator |
| **FP Mitigation** | Verification callback; fast-track release for verified legitimate changes |

***

### T-007 — Fake Delivery Completion

| Field | Detail |
|-------|--------|
| **Technique** | Fake Delivery / Delivery Simulation |
| **F3 Category** | Transaction Integrity |
| **Lifecycle Stage** | Stage 07 — Delivery Simulation |
| **Tactics** | Evidence Fabrication, Fraud Execution |
| **Description** | Contractor marks order delivered without completing the trip. May use pre-taken delivery photos or manipulate photo metadata. In collusion cases, the customer confirms receipt in exchange for a share of the fraudulent earnings or a free order. |
| **Evidence** | GPS non-arrival at delivery address, photo metadata timestamp predates GPS arrival, repeated claim history on same contractor-customer pair |
| **Sentinel Signals** | Signal 21 (GPS Non-Arrival at Completion — Fatal), Signal 23 (Repeated Pair Claims — High), Signal 24 (Photo Timestamp Inconsistency — Fatal), Signal 25 (High Refund Velocity — High) |
| **ML Features** | arrival_confirmation_flag, photo_timestamp_delta, pair_claim_rate |
| **Graph Signal** | Customer collusion rings may show up as shared customer node across multiple fraudulent contractors |
| **OSINT Enrichment** | Address verification for delivery destination; contractor address proximity check |
| **Mitigations** | Geofence-locked delivery confirmation photo, customer confirmation step for repeat-claim pairs, photo metadata validation at upload |
| **FP Risk** | Medium — photo metadata may be legitimately stripped by privacy tools; single-incident claims may be genuine disputes |
| **FP Mitigation** | Require GPS corroboration for photo anomaly signals; require pattern (3+) for collusion escalation |

***

## Signal-to-Stage Coverage Map

This table maps all 25 Sentinel signals to the fraud lifecycle stage they primarily
detect, and notes coverage gaps for roadmap planning.

| Lifecycle Stage | Signals Covering | Coverage Strength |
|----------------|-----------------|-------------------|
| Stage 02: Identity Prep | OSINT enrichment (identity verification) | Moderate |
| Stage 03: Device Prep | Signals 05, 08 (emulator, rooted device) | Strong |
| Stage 04: Account Creation | Signal 11, 14, 15 (shared identifiers) | Moderate |
| Stage 05: Warm-Up | Signal 16 (anomalous legitimacy baseline) | Light |
| Stage 06: Offer Collection | Signals 03, 04 (latency, cherry-pick) | Strong |
| Stage 07: Delivery Sim | Signals 01, 02, 06, 09, 21, 24 | Strong |
| Stage 08: Incentive Abuse | Signals 07, 17 (concentration, coordination) | Moderate |
| Stage 09: Cashout | Signals 18, 19, 20, 22 (payout signals) | Strong |
| Stage 10: Abandonment | Signal 25 (refund velocity as exit signal) | Light |

**Coverage gap:** Stages 01 (Reconnaissance) and 05 (Warm-Up) have light coverage.
Roadmap items: behavioral baseline deviation detection for warm-up stage;
threat intelligence feeds for known fraud infrastructure at reconnaissance stage.

***

## Emerging Technique Watch List

These patterns have been observed in adjacent delivery marketplace fraud intelligence
but are not yet fully modeled in Sentinel v1. Each represents a roadmap item for
future signal development.

| Technique | Description | Threat Level | Roadmap Priority |
|-----------|-------------|-------------|-----------------|
| AI-generated synthetic identity | LLM-generated identity documents that pass basic OCR verification | High | Q3 roadmap |
| Real-time GPS relay | Physical device relaying real GPS from a confederate at destination | High | Q2 roadmap |
| Insider account farming | Legitimate drivers renting account access to fraud operators | Medium | Q3 roadmap |
| Customer network fraud | Organized customers submitting coordinated false non-delivery claims | Medium | Q4 roadmap |
| Delivery photo AI generation | AI-generated delivery confirmation photos with plausible metadata | High | Q2 roadmap |
