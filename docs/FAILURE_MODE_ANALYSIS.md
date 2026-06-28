# Failure mode analysis

> Documents how Project Sentinel fails, how fast the failure becomes visible,
> what it costs when undetected, and how to detect and mitigate each failure mode.
>
> "Thinks like an adversary to anticipate how people might try to exploit the
> system next." — Walmart LMD Fraud Prevention JD

---

## Why this document exists

A fraud detection system that has never thought about how it fails is a liability,
not an asset. Adversaries study detection systems and adapt. Infrastructure
degrades. Models drift. New fraud patterns emerge that no signal covers.

This document is the adversarial perspective on Sentinel — what breaks, when,
how fast, and what to do about it.

---

## Failure mode 1 — Threshold gaming

**What happens:**
A fraudster discovers (through trial and error, or by studying their own case
file if appeals are too detailed) that the GPS impossible transit threshold is
180 kph. They instruct their GPS spoofing tool to simulate transit speeds of
170 kph — plausible for a highway segment, below the detection threshold.

**Detection lag:** Signal 23 stops firing. The ring continues earning.
If only signal 23 was catching this pattern, detection lag is indefinite.

**Business impact:** Full ring earnings continue. At $500/day per ring:
$500 × (days until next detection mechanism catches it).

**Why Sentinel is partially resilient:**
The layered architecture means threshold gaming on one signal does not evade
all layers. XGBoost will still score the behavioral pattern. The graph ring
flag will still fire if the shared entity infrastructure remains. The adversary
has to defeat all four layers simultaneously.

**What breaks it completely:**
If the adversary creates new accounts for each trip (rotating device fingerprints,
new payout instruments, no referral links), the graph layer has nothing to
connect. At that point, only XGBoost and Isolation Forest stand.

**Mitigation:**
- Never document exact numeric thresholds in public appeal communications
- Rotate thresholds slightly (±10%) on a quarterly basis so no stable threshold
  can be reverse-engineered
- Add velocity-based thresholds that are harder to game (e.g., "5 trips in
  pattern" rather than "one trip above X kph")
- Isolation Forest is the most resilient to threshold gaming because its
  decision boundary is not a single numeric cutoff

---

## Failure mode 2 — GPS telemetry degradation

**What happens:**
A platform SDK update, carrier change, or device population shift causes
median GPS accuracy_m to increase from 20m to 80m. The GPS drift suppression
filter in signals 02 and 23 (accuracy_m ≤ 80) now passes most pings even
when accuracy is poor. GPS anomaly signals fire more false positives. Analyst
trust in GPS signals drops. Thresholds get raised informally to reduce noise.
Actual GPS spoofing goes undetected.

**Detection lag:** Days to weeks, depending on how quickly the telemetry
health dashboard alerts.

**Business impact:** GPS spoofing signals account for ~40% of Sentinel's
detection yield (signals 01, 02, 03, 23). Degradation here degrades the
whole system.

**Early warning indicator:**
- Median GPS accuracy_m by zone and app version (dashboard metric)
- Signal 02 and 23 false-positive rate rising above baseline
- Signal volume spike with no corresponding confirmed fraud increase

**Mitigation:**
- Telemetry health dashboard (recommended to Engineering in CROSS_FUNCTIONAL_BRIEFING.md)
- Dynamic accuracy filter: instead of hardcoded 80m, use the rolling 90th
  percentile of accuracy_m for the driver's zone and device type
- Shadow mode for threshold changes: never adjust a threshold without running
  both old and new threshold in parallel for 14 days first

---

## Failure mode 3 — Model drift

**What happens:**
The XGBoost model was trained on IEEE-CIS data with synthetic Spark Driver
enrichment. Six months into production, the real driver population's feature
distributions shift (new incentive structure, new zone coverage, new app version).
The model's AUC-PR drops from 0.83 to 0.65. It begins scoring legitimate
high-activity drivers as CRITICAL.

**Detection lag:** Weeks to months if no model monitoring is in place.
The signal is rising false-positive rates and rising appeal overturn rates.

**Business impact:**
- Direct: analyst review costs increase (more false positives to review)
- Indirect: legitimate driver harm, potential regulatory exposure if adverse
  actions are later shown to be ungrounded
- Trust: internal stakeholders lose confidence in the system and begin ignoring
  high-score alerts

**Early warning indicators:**
- Population Stability Index (PSI) on XGBoost input features — alert if PSI > 0.2
- Weekly AUC-ROC and AUC-PR on any labeled cases from the prior week
- Appeal overturn rate rising above 12%
- Signal 21 (appeal overturn by signal) showing XGBoost-driven cases overturning
  more than SQL-driven cases

**Mitigation:**
- MLflow tracking (already implemented) enables fast rollback to prior model version
- Shadow mode retraining: retrain on new data, run in parallel for 30 days,
  promote only if AUC-PR improves or holds
- Minimum labeled case threshold: do not retrain on fewer than 200 confirmed
  fraud cases — small samples produce unstable models

---

## Failure mode 4 — New fraud pattern with no signal coverage

**What happens:**
A new attack emerges that no existing signal addresses. Example: fraudsters
discover that Spark Driver pays a per-mile bonus for certain route types.
They begin taking legitimate trips but manipulating the route (adding unnecessary
loops) to inflate mileage without GPS spoofing that is fast enough to trigger
signal 01 or 23.

**Detection lag:** Indefinite — until someone notices anomalous route patterns
in operational review and writes a new signal.

**Business impact:** Depends on how quickly the attack scales. Organised
operations can scale quickly once a gap is discovered.

**Early warning indicators:**
- Isolation Forest (Layer 2) is specifically designed to catch this. Novel patterns
  that no signal covers will still show as anomalies in IF scoring.
- Unusual spike in high-IF-score, low-SQL-signal-count cases — these are the
  signals of a new pattern
- Operational review: analyst reviewing cases should flag patterns they see
  in the queue that don't match any existing signal

**Mitigation:**
- Weekly review of high-IF-score, low-SQL-hits cases by a senior analyst
  (the "emerging threat" queue)
- Formal new-signal intake process (documented in SIGNAL_PRIORITIZATION.md)
- Quarterly threat landscape review referencing Incognia, Uber engineering
  blog, and FTC/CFPB enforcement filings for new attack patterns

---

## Failure mode 5 — Insider threat (store-level collusion)

**What happens:**
A store employee provides advance notice of order availability to a specific
driver or ring, giving them first-access to high-value offers. This is not
detectable from driver telemetry alone — the driver accepts offers legitimately,
delivers legitimately, and shows no GPS anomalies.

**Detection lag:** Potentially indefinite from driver-side signals alone.

**Business impact:** Preferential offer allocation, disadvantaging legitimate
drivers. If the colluding driver also manipulates delivery confirmation, there
is direct delivery fraud exposure.

**Why Sentinel partially addresses this:**
Signal 16 (repeated geofence miss concentrated at same store) and the
cross-role risk join (`collusion_flag`) can surface the store-level pattern.
But if the store employee is providing inside information without the driver
manipulating GPS or deliveries, neither signal fires.

**What Sentinel cannot address:**
Insider threat from the store side requires store-side data (employee login
events, terminal activity, CCTV metadata) that is not in the Spark Driver
telemetry surface. This is a data access gap, not a model gap.

**Mitigation:**
- Escalation path to Store Operations / LP (Loss Prevention) when signal 16
  or cross-role collusion flag fires for a specific store_id repeatedly
- Quarterly store-level fraud review: which stores appear most frequently
  in fraud cases? Requires coordination with store management, not fraud analytics.
- This failure mode is documented in the case file escalation matrix under
  "store-insider affinity" — it routes to Legal for review, not to Fraud Ops alone.

---

## Failure mode 6 — Legal challenge to adverse action

**What happens:**
A deactivated driver engages legal counsel. Counsel requests the evidence basis
for the deactivation. The fraud team must produce a case file that:
(a) documents which data was used,
(b) shows the data is reliable and unmodified,
(c) demonstrates false-positive paths were considered,
(d) shows an appeal pathway was provided.

If any of these is missing, the adverse action is legally vulnerable.

**What Sentinel provides:**
- Evidence hash on every case file (SHA-256 of generation inputs)
- Immutable bronze layer with SHA-256 lineage log
- OSINT matrix showing external verification steps taken
- FP exclusion log in section 7 of every CRITICAL case file
- Appeal pathway documented in every case file and in every Care Ops communication

**What would break this:**
- Modifying a case file after generation without logging the change
- Sharing signal-level threshold details in appeal communications (enables
  threshold gaming, documented in Failure Mode 1)
- Adverse action without completing the FP exclusion checklist

**Mitigation:**
- Case files are hash-stamped at generation — any post-generation modification
  is detectable
- Legal review required for all CRITICAL+ cases before final adverse action
  (not just analyst sign-off)
- Adverse action checklist: FP exclusion log must be complete before Legal
  is briefed

---

## Failure mode monitoring dashboard — recommended metrics

| Metric | Threshold for alert | Owner | Review cadence |
|--------|-------------------|-------|---------------|
| GPS accuracy_m (median by zone) | > 60m | Engineering | Daily |
| Signal 23 false-positive rate | > 15% | Fraud Analytics | Weekly |
| XGBoost PSI on key features | > 0.20 | Data Science | Monthly |
| Appeal overturn rate (all signals) | > 12% | Fraud Operations | Weekly |
| Appeal overturn rate (XGBoost-driven) | > 18% | Data Science | Weekly |
| Signal 16 concentration at single store | > 3 cases same store, 30 days | Fraud Ops + LP | Weekly |
| High-IF / low-SQL emerging pattern queue | > 20 cases unreviewed | Senior Analyst | Weekly |
| Case file modification log | Any post-generation change | Legal | On occurrence |

---

*This document should be reviewed after every major incident, quarterly as part
of signal governance, and whenever a new fraud pattern is confirmed in operations.*
