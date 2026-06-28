# Failure mode analysis

> How Project Sentinel fails, how fast the failure becomes visible,
> what it costs, and what to do about it.
>
> "Thinks like an adversary to anticipate how people might try to
> exploit the system next." — Walmart LMD Fraud Prevention JD

---

## Failure mode 1 — Threshold gaming

**What happens:** A fraudster discovers the GPS impossible transit threshold is
180 kph. Their spoofing tool is configured to simulate 170 kph — plausible for
a highway, below the detection threshold. Signal 23 stops firing.

**Detection lag:** Indefinite if only signal 23 was catching this pattern.

**Why Sentinel is partially resilient:** The layered architecture means threshold
gaming on one signal does not evade all layers. XGBoost scores the behavioral
pattern. The graph flag fires if shared entity infrastructure remains.

**What breaks it completely:** New accounts for every trip, rotating device
fingerprints and payout instruments, no referral links. At that point, only
XGBoost and Isolation Forest stand — graph layer has nothing to connect.

**Mitigation:**
- Never share exact numeric thresholds in appeal communications
- Rotate thresholds ±10% quarterly — no stable threshold can be reverse-engineered
- Add velocity-based thresholds that are harder to game than single-event cutoffs
- Isolation Forest is the most resilient to threshold gaming (no single numeric boundary)

---

## Failure mode 2 — GPS telemetry degradation

**What happens:** A platform SDK update increases median GPS accuracy_m from 20m
to 80m. The accuracy filter in signals 02 and 23 passes most pings even when
accuracy is poor. False positives rise. Analyst trust drops. Thresholds get
raised informally. Actual GPS spoofing goes undetected.

**Detection lag:** Days to weeks, depending on telemetry health monitoring.

**Business impact:** GPS signals account for ~40% of Sentinel detection yield.
Degradation here degrades the whole system.

**Early warning indicators:**
- Median GPS accuracy_m rising above 50m by zone and app version
- Signals 02 and 23 false-positive rate rising above baseline
- Signal volume spike with no corresponding confirmed fraud increase

**Mitigation:**
- Telemetry health dashboard (recommended to Engineering in CROSS_FUNCTIONAL_BRIEFING.md)
- Dynamic accuracy filter: use rolling 90th percentile of accuracy_m for the
  driver's zone and device type — not a hardcoded 80m cutoff
- Shadow mode for all threshold changes: run old and new threshold in parallel
  for 14 days before promoting

---

## Failure mode 3 — Model drift

**What happens:** The XGBoost model was trained on IEEE-CIS data with synthetic
enrichment. Six months into production, real driver feature distributions shift
(new incentive structure, new zone coverage, new app version). AUC-PR drops
from 0.83 to 0.65. Legitimate high-activity drivers begin scoring CRITICAL.

**Detection lag:** Weeks to months without model monitoring.

**Business impact:**
- Direct: analyst costs increase from rising false positives
- Indirect: legitimate driver harm, potential regulatory exposure
- Trust: stakeholders lose confidence and begin ignoring high-score alerts

**Early warning indicators:**
- Population Stability Index (PSI) on key XGBoost features — alert if PSI > 0.2
- Appeal overturn rate rising above 12%
- Signal 21 showing XGBoost-driven cases overturning at higher rate than SQL-driven

**Mitigation:**
- MLflow tracking (already implemented) enables fast rollback to prior version
- Shadow mode retraining: retrain on new data, run parallel for 30 days,
  promote only if AUC-PR holds or improves
- Minimum training threshold: do not retrain on fewer than 200 confirmed fraud cases

---

## Failure mode 4 — Novel pattern with no signal coverage

**What happens:** Fraudsters discover a route manipulation exploit — taking
legitimate trips but adding unnecessary loops to inflate mileage beyond what
GPS spoofing signals catch. No existing signal addresses it.

**Detection lag:** Indefinite — until operational review surfaces the pattern
and a new signal is written.

**Why Sentinel is partially resilient:** Isolation Forest (Layer 2) is specifically
designed for this. Novel patterns that no SQL signal covers will still register
as anomalies in IF scoring. High-IF, low-SQL-hits cases are the emerging threat
queue.

**Mitigation:**
- Weekly senior analyst review of high-IF-score, low-SQL-hits cases
- Formal new signal intake process from SIGNAL_PRIORITIZATION.md
- Quarterly threat landscape review (Incognia, Uber engineering blog,
  FTC/CFPB enforcement filings)

---

## Failure mode 5 — Store-level insider collusion

**What happens:** A store employee provides advance notice of order availability
to a specific driver ring. The drivers accept legitimately, deliver legitimately,
show no GPS anomalies. Driver-side signals don't fire because the behaviour
is operationally normal.

**Detection lag:** Potentially indefinite from driver telemetry alone.

**Why Sentinel partially addresses this:** Signal 16 (geofence miss concentrated
at same store) and cross-role collusion flag can surface the store-level pattern.
But if inside information is provided without delivery manipulation, neither fires.

**What Sentinel cannot address:** Store-side insider threat requires store-side
data (employee login events, terminal activity, CCTV metadata) that is not in
the Spark Driver telemetry surface. This is a data access gap, not a model gap.

**Mitigation:**
- When signal 16 or cross-role flag fires repeatedly for one store_id, escalate
  to Store Operations / Loss Prevention — not just Fraud Ops
- Quarterly store-level fraud review: which stores appear most frequently in
  cases? Requires store management coordination.

---

## Failure mode 6 — Legal challenge to adverse action

**What happens:** A deactivated driver engages legal counsel. Counsel requests
the evidence basis. The fraud team must produce a case file that documents which
data was used, shows it is reliable and unmodified, demonstrates FP paths were
evaluated, and shows an appeal pathway was provided. If any element is missing,
the adverse action is legally vulnerable.

**What Sentinel provides:**
- SHA-256 evidence hash on every case file
- Immutable bronze layer with lineage log
- FP exclusion checklist in section 7 of every CRITICAL case file
- Appeal pathway documented in every case file and Care Ops communication

**What would break this:**
- Modifying a case file after generation without logging the change
- Sharing signal-level threshold details in appeal communications (enables gaming)
- Taking adverse action without completing the FP exclusion checklist

**Mitigation:**
- Case files are hash-stamped at generation — post-generation modifications detectable
- Legal review required for CRITICAL+ cases before final adverse action
- FP exclusion log must be complete before Legal is briefed

---

## Failure mode monitoring dashboard

| Metric | Alert threshold | Owner | Cadence |
|--------|---------------|-------|---------|
| GPS accuracy_m median by zone | > 60m | Engineering | Daily |
| Signal 23 false-positive rate | > 15% | Fraud Analytics | Weekly |
| XGBoost PSI on key features | > 0.20 | Data Science | Monthly |
| Appeal overturn rate (all) | > 12% | Fraud Operations | Weekly |
| Appeal overturn rate (XGB cases) | > 18% | Data Science | Weekly |
| Signal 16 at single store (30d) | > 3 cases same store | Fraud Ops + LP | Weekly |
| High-IF / low-SQL queue | > 20 unreviewed | Senior Analyst | Weekly |
| Case file post-gen modification | Any occurrence | Legal | On event |

---

*Review after every confirmed fraud incident, quarterly as part of signal
governance, and whenever a new attack pattern is confirmed in operations.*
