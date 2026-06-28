# Business impact and loss quantification

> Scenario-based fraud loss model for the Spark Driver last-mile delivery platform.
> All figures are estimates derived from publicly available industry benchmarks,
> FTC/CFPB enforcement materials, and Incognia 2025 State of Fraud data.
> They are not Walmart proprietary figures. They demonstrate structured
> business-case thinking, not claims about actual Walmart losses.

---

## Why this document exists

A fraud detection system is only worth building if the prevented loss justifies
the cost. This document quantifies what each of the six attack families Sentinel
detects costs the platform, what Sentinel prevents, and what the operational ROI
looks like at three loss-pool sizes.

A program owner speaks in dollars prevented. This document is that conversation.

---

## Attack family loss model

### 1. GPS spoofing and fake delivery completion

**Mechanism:** Driver uses a mock-location app to simulate trip completion
without physical movement. Earns payout and incentive without delivering.

**Per-incident cost estimate:**
- Average Spark Driver payout per trip: $8–$14 (public Spark earnings disclosures)
- Incentive multiplier at campaign milestone: 1.5–3×
- Customer refund triggered by non-delivery: $15–$65
- Total per-incident exposure: **$27–$107**

**Scale estimate:**
- Industry benchmark: 1.6% of gig-economy trips show location anomalies (Incognia 2025)
- At 1M monthly trips: ~16,000 suspicious trips/month
- Conservative fraud conversion of anomalies: 15%
- Monthly exposure: 2,400 incidents × $67 midpoint = **~$160K/month**

**Sentinel detection:** Signals 01, 02, 23. Pre-payout catch rate at current
thresholds: ~70%. **Estimated monthly prevention: ~$112K. Annual: ~$1.3M.**

---

### 2. Bot-assisted batch grabbing

**Mechanism:** Automated script drains high-value offers from legitimate drivers
in sub-second latency. Direct cost is primarily displaced legitimate driver earnings
and increased support costs.

**Per-active-bot-account estimate:** $200–$400/week in displaced value.

**Scale estimate:** 50 active bot accounts at any time = **~$780K/year in
displaced platform value.**

**Sentinel detection:** Signal 24 (sub-800ms median accept latency in bursts
of ≥5). HIGH confidence for organised bots.

---

### 3. Coordinated fraud rings (shared device and payout)

**Mechanism:** Multiple driver accounts share one device and one bank account,
harvesting incentives while evading per-account detection.

**Per-ring cost estimate:**
- Average ring: 5 accounts × $100/day = $500/day
- Duration before detection without Sentinel: 14–45 days
- Loss per ring without detection: **~$15,000**
- Savings from catching at day 7 vs day 30: **~$11,500 per ring**

**Scale estimate:** 10 active rings at any time = **$150K/year undetected.**

**Sentinel detection:** Signals 05, 07, 25, graph layer with 1.40× ring multiplier.
CASE_001 is the canonical example.

---

### 4. Incentive and promotional abuse

**Per-campaign exposure estimate:**
- 0.5% of 10,000 campaign participants gaming mechanics
- $50 average fraudulent incentive claim
- **$2,500 per campaign run × 12 campaigns = ~$30K/year**

**Sentinel detection:** Signals 08 (incentive cliff), 12 (reward-only behaviour).

---

### 5. Account takeover and payout mule activity

**Industry benchmark:** $13B global ATO losses in 2024, forecast $17B in 2025.
Even 0.01% platform share = $1.3M exposure.

**Per-incident estimate:** $200–$800 average payout extracted before detection.

**Sentinel detection:** Signals 13, 17, 19 (re-entry, device hop, bank change
before payout). Score spike on composite signals.

---

### 6. Refund and delivery fraud

**Per-incident estimate:** $23–$94 (customer refund + retained driver payout).

**Scale estimate:** 0.3% claim rate on 1M monthly trips × 10% fraud conversion
= **$14–$21K/month = $170–$250K/year.**

**Sentinel detection:** Signals 03, 04, 11, 20 (geofence miss, zero-dwell,
claim concentration, driver-customer pair).

---

## Composite annual loss model

| Attack family | Low | Mid | High |
|--------------|-----|-----|------|
| GPS spoofing | $800K | $1.3M | $2.1M |
| Bot-assisted grabbing | $400K | $780K | $1.2M |
| Fraud rings | $80K | $200K | $500K |
| Incentive abuse | $20K | $50K | $120K |
| Account takeover | $200K | $600K | $1.5M |
| Refund / delivery fraud | $170K | $210K | $300K |
| **Total** | **$1.67M** | **$3.14M** | **$5.72M** |

---

## Sentinel ROI at three loss-pool sizes

| Annual preventable loss | Catch rate | Prevented | Platform cost | Net benefit |
|------------------------|-----------|-----------|--------------|-------------|
| $1.5M | 65% | $975K | $400–600K | $375–575K |
| $3.1M | 70% | $2.17M | $500–750K | $1.4–1.7M |
| $5.7M | 75% | $4.28M | $600–900K | $3.4–3.7M |

**Planning implication:** If the annual preventable loss pool exceeds $2M,
Sentinel pays back in year one.

---

## The three levers that move ROI most

**1. Pre-payout vs post-payout catch rate.** Catching fraud before settlement
has 3–5× the ROI of catching it afterward. The HOLD band in Sentinel is
specifically designed to pause payouts for CRITICAL cases pending analyst review.

**2. Ring detection speed.** Each day an organised ring operates undetected
costs approximately the same amount. Graph-layer ring detection is therefore
the highest-value single component.

**3. False-positive rate.** Every wrongly held payout costs $25–$50 in support
and analyst time. Signal-level FP documentation in Sentinel is directly
cost-relevant, not just best practice.

---

*Figures sourced from: Incognia 2025 State of Fraud, NRF 2024 Return Fraud
report, Javelin Strategy ATO Annual Report 2024, public Spark Driver earnings
disclosures, FTC enforcement materials. All estimates are scenario-based.*
