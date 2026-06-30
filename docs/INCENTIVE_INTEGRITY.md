# Incentive Integrity Framework
## How Trust Intelligence Advises Product on Incentive Design

**Owner:** Trust Intelligence Program Lead
**Stakeholders:** Head of Product, Head of Finance, Legal
**Review cadence:** Before any new incentive program launches; quarterly for standing programs
**Last reviewed:** 2026-06-29

---

## Purpose

Detection after the fact captures fraud that has already occurred. This document defines how the Trust Intelligence function participates *upstream* — advising Product on incentive design choices before they ship — to prevent creating fraud surfaces in the first place.

The asymmetry is stark: a poorly designed incentive program that runs for 60 days before detection can cost 3-5x more in fraud loss than the entire annual budget of the detection operation that catches it. Upstream influence is the highest-ROI activity in Trust.

---

## The Fraud Surface Model

Every incentive program creates a surface along three dimensions:

| Dimension | Low risk | High risk |
|-----------|---------|---------|
| **Verification friction** | Action is verifiable server-side (delivery confirmed via customer signature + GPS) | Action is self-reported or easily faked (contractor claims 'attempted delivery') |
| **Payout magnitude** | Small per-action reward ($0.50 bonus per delivery) | Large per-action reward ($25 completion bonus) or uncapped total |
| **Speed of payout** | Multi-day settlement after verification | Same-session or same-day payout before verification completes |

Fraud risk increases multiplicatively as each dimension shifts toward high risk. A high-magnitude, fast-payout, low-verification incentive is the highest-risk structure possible and should never ship without Trust review.

---

## Trust Review Gate

### When Trust Review is Required

Trust Intelligence requires a mandatory review before launch for any incentive program that meets any of the following criteria:

- Per-contractor potential payout > $50 in a single settlement cycle
- Program relies on any self-reported contractor action as the primary payout trigger
- Program targets a cohort that has previously had elevated signal rates (prior campaign abusers)
- Program uses same-day or instant payout
- Program is geographically concentrated in a market with known fraud rings

### Review Process

1. Product submits the incentive spec to Trust at least **10 business days before launch** using the Incentive Review Request template (below).
2. Trust reviews against the Fraud Surface Model within 5 business days and returns one of: Approve / Approve with conditions / Block pending redesign.
3. If conditions are attached (e.g., 'add 24-hour payout delay' or 'require GPS confirmation'), Product redesigns and resubmits.
4. Approved spec is logged in the Incentive Registry (see below) and associated SQL signals are pre-configured before launch.

### Incentive Review Request Template

```
Program name:
Launch date:
Eligible cohort (how defined):
Trigger action (what earns the reward):
Verification method (how the trigger is confirmed):
Payout amount (per-action and max per contractor per cycle):
Payout timing (settlement delay):
Expected program cost:
Prior abuse history in this cohort or geography:
Proposed fraud controls:
```

---

## Signal Correlation Monitoring

After every incentive launch, Trust Intelligence tracks the following for 30 days:

| Metric | Baseline | Alert threshold |
|--------|---------|----------------|
| Signal 14 (bot-assisted batch grabbing) firing rate | Pre-launch 7-day average | > 2x baseline |
| Signal 3 (refund velocity) firing rate | Pre-launch 7-day average | > 1.5x baseline |
| Signal 8 (incentive gaming) firing rate | Pre-launch 7-day average | > 2x baseline |
| CRITICAL-band rate in incentive-eligible cohort | Population baseline | > 3x population rate |
| Payout-to-delivery ratio for eligible contractors | Historical cohort average | > 1.3x historical |

If any metric crosses its alert threshold, Trust notifies the owning Product manager within 24 hours and convenes a review within 5 business days. The review produces one of: no action / parameter change / program suspension pending investigation.

This monitoring is automated via the signal correlation feed in Sentinel — aggregate signal firing rates are tracked against product change dates in `data/product_events/` (populated by the Product integration hook).

---

## Contractor Trust Tier Model

Beyond adverse detection, Trust Intelligence maintains a positive trust tier for each contractor — a score reflecting reliability, tenure, and clean history. This is the 'carrot' side of the trust system.

| Tier | Criteria | Product access |
|------|---------|---------------|
| **Tier 1 — Established** | 90+ days active, composite risk score < 3.0, no CRITICAL flags in last 180 days, no open appeals | Priority offer access, expanded incentive eligibility, higher payout caps |
| **Tier 2 — Standard** | 30-89 days active OR composite score 3.0-5.0 | Standard access |
| **Tier 3 — New** | < 30 days active, no fraud history | Standard access, reduced payout caps in first 2 settlement cycles |
| **Tier 4 — Monitored** | Composite score 5.0-7.0 OR recent false-positive case still under review | Reduced offer access, enhanced monitoring, no premium incentive eligibility |

Tier assignments are recalculated at each settlement cycle. Tier 1 status requires 2 consecutive CRITICAL-free settlement cycles to restore after any adverse event.

The trust tier is exposed to Product via a lightweight API endpoint (`/api/v1/contractor/trust-tier/{contractor_id}`) so that feature eligibility gates can be applied at the application layer without Trust needing to be in the critical path of every product decision.

---

## Incentive Registry

All approved incentive programs are logged in `data/product_events/incentive_registry.jsonl` with fields:

```
program_id, program_name, launch_date, end_date, trust_review_status,
conditions_attached, eligible_cohort, payout_amount_max, payout_trigger,
verification_method, post_launch_review_date, outcome
```

This registry is the foundation of the signal correlation analysis — it allows Sentinel to automatically flag signal spikes that are time-correlated with specific program launches.

---

## Known High-Risk Structures (Do Not Launch Without Trust Review)

Based on Sentinel's fraud technique library and historical incident analysis, the following incentive structures have a documented history of adversarial exploitation:

- **'Complete X deliveries in Y hours' with same-day bonus** — exploited via GPS spoofing to simulate completions
- **Referral programs with per-referral cash reward** — exploited via synthetic account creation rings
- **'First delivery of the day' bonuses** — exploited via bot-assisted offer grabbing (Signal 14)
- **Store-specific concentration bonuses** — exploited by contractors gaming store assignment through coordinated account infrastructure (entity graph Signal)
- **Uncapped incentive campaigns** — any program with no per-contractor cap creates a linear fraud return for anyone who can automate the trigger action

---

*This document is version-controlled. Material changes require sign-off from Head of Product, Head of Trust, and Legal before merge.*
