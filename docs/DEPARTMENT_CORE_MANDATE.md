# Department core mandate

> Strategic interpretation of the Walmart LMD Fraud Prevention role.
> This document explains the operating mandate behind Project Sentinel:
> convert raw marketplace telemetry into proactive, auditable, low-friction
> trust decisions.

---

## Executive position

LMD Fraud Prevention is not a manual ticket queue or a traditional cost center.
The department exists to protect marketplace integrity by finding systemic abuse
patterns, proving the business impact of intervention, and pushing defensible
controls into production without harming legitimate Spark Driver activity.

The work sits at the intersection of fraud operations, decision science,
engineering, product risk, and legal defensibility. Analysts are expected to
think like adversaries, quantify loss like operators, and document findings in
a way that can survive audit, appeal, and cross-functional scrutiny.

Project Sentinel is built as a portfolio version of that mandate: a contract-led
fraud detection system that turns GPS, device, payout, behavioral, graph, model,
and OSINT signals into calibrated recommendations and evidence-backed case files.

---

## 1. Proactive infrastructure defense

**Expectation:** Move the company away from reactive "whack-a-mole" enforcement
against individual bad actors and toward automated control infrastructure.

In practical terms, the department is expected to identify abuse patterns that
represent product or platform vulnerabilities, then define measurable signals
that can be monitored, scored, and eventually converted into live controls.

Examples:

| Vulnerability | Analyst output | Production control path |
|---------------|----------------|--------------------------|
| GPS spoofing enables fake delivery completion | Impossible-transit and geofence-miss signals | Device attestation or geofence-locked completion |
| Bots accept offers faster than human reaction time | Sub-human latency and incentive concentration signals | Offer throttling, challenge flow, or randomized dispatch timing |
| Fraud rings reuse devices or payout instruments | Shared-device, shared-payout, and graph-ring signals | Onboarding deduplication and step-up verification |
| ATO redirects payout before settlement | New-device plus payout-change signal | Payout cooling period and MFA challenge |

The analyst's job is not only to find cases. It is to convert observed abuse
into reusable detection logic, quantify the blast radius, enumerate legitimate
edge cases, and give Engineering and Product a clean control recommendation.

Sentinel maps this expectation to:

| Sentinel layer | Mandate contribution |
|----------------|----------------------|
| DuckDB SQL signals | Version-controlled, explainable fraud indicators |
| Composite risk scoring | Repeatable prioritization instead of one-off judgment |
| Graph analysis | Detection of coordinated infrastructure, not just individual accounts |
| Case generation | Evidence preservation from first detection through final decision |
| Streaming roadmap | Migration path from batch analytics to pre-settlement blocking |

---

## 2. Asymmetric loss prevention

**Expectation:** Prove that fraud prevention creates measurable enterprise value.

Every fraud ring dismantled, fake delivery prevented, bot-assisted incentive
scheme contained, or payout mule blocked protects the marketplace's gross margin.
The department is expected to show that its work prevents more loss than it costs
to operate.

The core business math is:

```text
prevented_loss =
  alert_volume
  * confirmed_precision
  * average_loss_per_incident
  * pre_settlement_recovery_multiplier
```

The operating question is not simply "how many accounts were actioned?" It is:

| Question | Why it matters |
|----------|----------------|
| How much loss was prevented before payout? | Pre-settlement intervention has materially higher ROI than recovery work. |
| Which signal families produce the highest dollar yield? | Analyst and engineering capacity should flow toward the best controls. |
| How much investigator time does each alert consume? | A high-volume signal can destroy ROI if precision is weak. |
| Which fraud types scale through shared infrastructure? | Coordinated rings create outsized loss and deserve graph-level tooling. |
| Which product gaps enable repeat abuse? | Durable fixes beat repeated manual enforcement. |

Sentinel supports this expectation through the loss model in
[`BUSINESS_IMPACT.md`](BUSINESS_IMPACT.md), the aggregate economics in
[`DETECTION_STRATEGY.md`](DETECTION_STRATEGY.md), and the case-level evidence
packs in `cases/`.

---

## 3. Zero-friction marketplace integrity

**Expectation:** Stop sophisticated fraud without catching legitimate drivers in
the crossfire.

This is the hardest constraint in marketplace fraud operations. Overly aggressive
detection logic can hold honest earnings, damage driver trust, increase support
volume, and create legal or reputational exposure. Fraud prevention must be
strong, but it must also be precise, explainable, appealable, and continuously
calibrated.

Sentinel treats false-positive control as a first-class system requirement:

| Control | Implementation |
|---------|----------------|
| Corroboration before escalation | High-risk cases require multiple independent signals. |
| Tiered action bands | Monitor, review, hold, restrict, and escalate are separated. |
| False-positive checklists | Case files enumerate legitimate scenarios before action. |
| Human sign-off | Critical and fatal cases require analyst review before final enforcement. |
| Signal QA | SQL signal quality checks look for drift, overfiring, and brittle thresholds. |
| Governance ledger | Evidence hashes make the decision trail reproducible and auditable. |

The department's credibility depends on this balance: fraud controls must be
strong enough to change adversary economics and careful enough to preserve a
healthy driver ecosystem.

---

## Operating framework: OODA for fraud telemetry

The department operates as a high-speed OODA loop applied to marketplace data.

| Phase | Department activity | Sentinel expression |
|-------|---------------------|---------------------|
| Observe | Ingest GPS, device, payout, metadata, behavioral, case, and OSINT evidence. | Bronze and silver data layers, telemetry enrichment, feature engineering |
| Orient | Separate true abuse from noisy edge cases using SQL, segmentation, OSINT, and cohort baselines. | 25 SQL signals, anomaly model, graph ring detection, OSINT enrichment |
| Decide | Set thresholds, exclusion rules, action tiers, and confidence standards. | Composite score, risk bands, false-positive controls, governance docs |
| Act | Present audit-ready findings to Product, Legal, Engineering, and Care Operations. | Case files, cross-functional briefings, product control recommendations |

The loop only works if each phase feeds the next. A signal that cannot be
explained does not support Legal. A case that does not reveal a product gap does
not support Engineering. A threshold that is not stress-tested does not protect
legitimate drivers.

---

## Role-to-project traceability

| Job expectation | Project Sentinel evidence |
|-----------------|---------------------------|
| Identify unusual behavior and emerging fraud vectors at scale | SQL signal library, Isolation Forest, XGBoost, and graph layer |
| Combine GPS, device, metadata, and behavioral indicators | Enriched Spark Driver-style telemetry and composite scoring |
| Build fraud indicators, thresholds, and composite signals | `sql/signals/` and `docs/SIGNAL_PRIORITIZATION.md` |
| Stress-test queries against legitimate scenarios | False-positive controls in signal headers and case templates |
| Use OSINT to confirm identities and coordinated networks | `sentinel/osint.py` and audit-hashed OSINT evidence records |
| Produce audit-ready case files | `sentinel/case.py`, `cases/`, and SHA-256 case integrity hashes |
| Present findings to Product, Legal, Engineering, and Care Ops | `docs/CROSS_FUNCTIONAL_BRIEFING.md` |
| Support tooling and policy improvements | Detection roadmap and product control recommendations |
| Quantify fraud loss and ROI | `docs/BUSINESS_IMPACT.md` |

---

## Interview narrative

Use this framing when explaining the project:

> I built Sentinel to show how I think about last-mile fraud prevention as an
> infrastructure and decision-science problem, not just a case-review workflow.
> The system ingests delivery-style telemetry, creates version-controlled SQL
> signals, combines them with ML and graph analysis, and generates audit-ready
> case files with false-positive controls. The point is not just to flag bad
> actors. It is to identify the product or platform gap that enabled the abuse,
> quantify the prevented loss, and give Engineering, Legal, Product, and Care
> Operations a defensible path to action.

---

## Decision principle

The department succeeds when it can say:

```text
We found the abuse pattern.
We proved the loss exposure.
We ruled out plausible legitimate explanations.
We preserved the evidence.
We recommended the smallest control that stops the abuse.
We measured whether the control worked.
```

That is the operating mandate Sentinel is designed to demonstrate.
