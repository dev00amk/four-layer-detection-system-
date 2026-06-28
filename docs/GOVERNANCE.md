# GOVERNANCE.md — Project Sentinel

> **Purpose:** This document defines the governance framework for Project Sentinel's
> fraud detection program. It covers risk appetite, evidence standards, adverse action
> policy, analyst escalation, audit requirements, model validation, QA, and periodic
> review cadence.
>
> **Status:** This framework is designed for a Spark Driver-style delivery marketplace.
> Values marked [TO BE SET BY PROGRAM OWNER] represent policy decisions that require
> input from Legal, Compliance, Risk, and Operations leadership before production use.
>
> **Audience:** Fraud Operations, Legal, Compliance, Risk Management, Executive Sponsor.

***

## Governance Principles

Project Sentinel operates under four core governance principles derived from
enterprise fraud program best practice and gig-economy contractor protection
obligations:

1. **Accuracy before action.** No adverse action is taken from model output alone.
   Every Critical or Fatal case requires analyst review and documented sign-off.

2. **Proportionality.** The severity of the control response must be proportionate
   to the strength of evidence. Monitoring does not justify restriction;
   restriction does not justify permanent action.

3. **Transparency.** Every decision must be traceable from raw telemetry to analyst
   sign-off. The audit trail must survive legal challenge.

4. **Fairness.** False-positive rate targets are treated as binding operational
   commitments, not aspirational benchmarks. Legitimate contractors must have a
   timely, accessible appeal path.

***

## Risk Appetite

| Dimension | Target | Rationale |
|-----------|--------|-----------|
| **Blended false positive rate** | < 5% across all signals | Excess FP directly harms legitimate contractor livelihoods |
| **CRITICAL queue precision** | ≥ 85% | Investigator time is limited; low-precision queues waste resources |
| **Fatal-tier FP rate** | < 2% | Fatal actions (restrictions, escalations) carry highest harm potential |
| **Monthly fraud loss tolerance** | [TO BE SET BY PROGRAM OWNER] | Drives threshold calibration |
| **Payout hold duration maximum** | 72 hours pending verification | Balances security with contractor cash-flow fairness |
| **Appeal resolution SLA** | 5 business days | Minimizes harm duration for legitimate contractors |

Risk appetite is reviewed quarterly by the Fraud Operations Lead and Risk Governance.
Thresholds are updated if fraud loss or FP rates move more than 15% from targets.

***

## Evidence Standards

Before any adverse action is taken, the following evidence standards must be met.
Standards escalate with action severity.

### Monitoring (Low / Medium confidence)
- One or more signals fired.
- Signal documented in case record.
- No analyst action required; automated queue only.

### Investigation (High confidence)
- Two or more corroborating signals from different signal families.
- OSINT enrichment complete for at least identity and device.
- FP checklist reviewed by analyst before recommendation.

### Temporary restriction (Critical confidence)
- High-confidence criteria met, plus:
- Graph ring confirmed (if applicable).
- Analyst sign-off documented with rationale.
- Contractor notification sent within 24 hours of restriction.

### Escalation to Legal / permanent action
- Critical criteria met, plus:
- SHA-256 evidence chain preserved and verified.
- Second analyst review completed (four-eyes principle).
- Legal notification with case file summary.
- Documentation of contractor's right to appeal.

***

## Confidence Level and Action Policy

| Confidence | Score Band | Permitted Actions | Prohibited Actions |
|-----------|-----------|------------------|--------------------|
| Low (0–3) | Monitor | Add to trend tracking | Any adverse action |
| Medium (3–5) | Secondary checks | Flag for review; no payout change | Restriction, notification |
| High (5–7) | Investigation | Investigation queue; temporary flag | Restriction without analyst |
| Critical (7–9) | Restriction eligible | Temporary restriction with analyst sign-off | Permanent action without Legal |
| Fatal (9–10 or Fatal rule) | Immediate escalation | Temporary restriction + Legal notification + evidence preservation | None prohibited if evidence standard met |

**Absolute prohibition:** No model output, regardless of score, may trigger
a permanent enforcement action without analyst sign-off, Legal review,
and documented evidence meeting the escalation standard above.

***

## Appeals Process

Every contractor subject to a temporary restriction or investigation must have
access to a clear, timely appeals path.

| Step | Description | SLA |
|------|-------------|-----|
| **Notification** | Contractor receives notification of restriction reason and appeal instructions | Within 24h of restriction |
| **Appeal submission** | Contractor submits appeal through designated channel with supporting information | Contractor has 10 business days |
| **Initial review** | Analyst reviews appeal and original case evidence | 3 business days |
| **Resolution** | Decision communicated to contractor with rationale | 5 business days from submission |
| **Escalation** | Contractor may escalate to Fraud Operations Lead if unsatisfied | 3 business days for escalation response |

Appeal outcomes are logged in the case record. Overturned decisions trigger
a signal quality review to assess whether the underlying rule should be re-calibrated.

***

## Analyst Escalation Framework

| Situation | Action | Owner |
|-----------|--------|-------|
| High confidence case with ambiguous OSINT | Second analyst review | Fraud Ops Lead |
| Fatal-tier signal with no OSINT corroboration | Hold action; request OSINT enrichment | Senior Analyst |
| Ring size ≥ 5 accounts | Immediate escalation to Fraud Ops Lead | Senior Analyst |
| Evidence of organized crime indicators | Legal notification; law enforcement referral consideration | Fraud Ops Lead + Legal |
| Suspected insider threat | HR + Legal + Security notification | Fraud Ops Lead |
| FP complaint from contractor claiming wrongful restriction | Priority appeal review; flag signal for QA | Senior Analyst |
| Confidence score disputed by analyst | Document disagreement; escalate to model review | Senior Analyst + Data Science |

***

## Audit Trail Requirements

Project Sentinel maintains immutable audit trails using SHA-256 hash chains
on all case files. The following records are preserved for every CRITICAL
and Fatal case.

| Record Type | Content | Retention |
|------------|---------|-----------|
| **Raw telemetry snapshot** | Bronze-layer Parquet at case generation time | [TO BE SET: e.g., 7 years] |
| **Signal fire log** | Which signals fired, thresholds, values | Same as telemetry |
| **Ensemble score record** | Layer-by-layer scores and final composite | Same as telemetry |
| **OSINT enrichment package** | All enrichment outputs at time of case | Same as telemetry |
| **Analyst decision record** | Analyst ID, recommendation, rationale, sign-off timestamp | Same as telemetry |
| **Case file integrity hash** | SHA-256 of complete case file at close | Same as telemetry |
| **Appeal record** | If applicable: submission, review, resolution | Same as telemetry |

Audit trail integrity is validated quarterly by the Governance function.
Any hash verification failure triggers an immediate security review.

***

## Model Validation and Drift Monitoring

Fraud models degrade over time as adversaries adapt. The following validation
and monitoring cadences are mandatory.

| Activity | Frequency | Owner | Trigger for Action |
|---------|-----------|-------|-------------------|
| **Model performance review** (ROC-AUC, PR-AUC, Precision@K) | Monthly | Data Science | Any metric drops >5% from baseline |
| **Feature drift monitoring** (PSI or KS test on key features) | Weekly | Data Science | PSI > 0.20 on any primary feature |
| **Signal precision audit** (per-signal FP rate review) | Monthly | Senior Analyst | Any signal FP rate exceeds tier threshold |
| **Threshold recalibration** | Quarterly or on trigger | Data Science + Fraud Ops | Score distribution shift or major fraud pattern change |
| **Full model retraining** | Semi-annually or on trigger | Data Science | Recall drops >10% or new fraud technique confirmed |
| **Rule review** | Quarterly | Senior Analyst | New attack pattern, false positive spike, or platform change |

Drift monitoring results are logged in `data/models/drift_report.json` on each
scheduled run. Alerts are generated if Population Stability Index on trip velocity,
device integrity, or payout amount features exceeds 0.20.

***

## Quality Assurance

### Case review QA
- [TO BE SET BY PROGRAM OWNER]% of closed cases are randomly re-reviewed each month.
- QA reviewer checks: evidence completeness, FP checklist adherence, decision rationale quality, audit trail integrity.
- QA findings are reported to Fraud Ops Lead monthly.

### Signal QA
- Each month, a random sample of 50 per-signal alerts are manually reviewed.
- Precision is estimated from the sample and compared to targets.
- Signals with estimated precision below tier threshold are flagged for re-calibration.

### Analyst QA
- Analyst decision accuracy is tracked quarterly (overturned appeals / total decisions).
- Analysts with >10% overturn rate receive additional training and supervision.

***

## Periodic Review Cadence

| Review | Frequency | Participants | Output |
|--------|-----------|-------------|--------|
| **Weekly ops standup** | Weekly | Fraud Ops team | Alert volume, queue health, active cases |
| **Monthly performance review** | Monthly | Fraud Ops + Data Science | Signal and model metrics, FP report, QA findings |
| **Quarterly business review (QBR)** | Quarterly | Fraud Ops + Product + Legal + Leadership | Fraud loss trend, roadmap, emerging threats, investment ask |
| **Semi-annual rule review** | Semi-annual | Fraud Ops + Engineering + Legal | Full signal library review, threshold changes, deprecations |
| **Annual governance review** | Annual | Risk Governance + Legal + Executive Sponsor | Risk appetite reset, policy updates, program maturity assessment |

***

## Documentation Standards

All governance documents follow these standards to maintain audit-grade quality:

- Every document has a Purpose, Audience, Status, and last-reviewed date.
- Policy statements use "must," "shall," and "prohibited" for binding rules;
  "should" and "recommended" for guidance.
- All metrics and thresholds are labeled as either "measured" (from live data)
  or "modeled assumption" (from scenario analysis).
- Documents are version-controlled in the repository. Changes require a pull
  request with reviewer sign-off.
- No sensitive contractor data, credentials, or production system details
  are stored in this repository.
