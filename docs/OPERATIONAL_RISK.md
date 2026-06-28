# Operational risk and defensibility

## System philosophy

Project Sentinel is a fraud-intelligence decision-support system, not an autonomous
enforcement engine. Its purpose is to convert mixed telemetry into prioritized,
reviewable evidence while preserving human judgment, false-positive controls,
appeal pathways, and an auditable decision record.

## Human-in-the-loop routing

| Score | Route | Operational effect |
|---:|---|---|
| 0–2 | APPROVE | No added friction |
| 3–4 | MONITOR | Passive monitoring |
| 5–6 | CHALLENGE | Proportionate step-up verification |
| 7–8 | HOLD | Temporary review hold and analyst case |
| 9–10 | ESCALATE | Senior fraud and compliance review |

A Sentinel score is not proof of fraud. No single GPS, device, velocity, or model
signal should independently trigger irreversible adverse action. High-impact
decisions require corroboration across independent layers and documented review
of plausible benign explanations.

## Investigation standard

Every critical case should record:

1. The exact rule, anomaly, model, and graph evidence used.
2. Data timestamps, lineage, and an integrity hash.
3. Relevant behavioral and operating context.
4. False-positive explanations considered and how they were tested.
5. The investigator, decision, policy basis, and review timestamp.
6. Notification, appeal, and remediation steps where applicable.

The structured external-verification matrix in generated cases is intentionally
left pending. It defines the verification process without fabricating OSINT or
internal facts that are not present in the dataset.

## Control ownership

| Control | Owner | Review cadence |
|---|---|---|
| Signal thresholds and suppressions | Fraud Analytics | Monthly and after incidents |
| Model drift and calibration | Data Science | Monthly |
| Fairness and disparate-impact testing | Responsible AI / Legal | Quarterly |
| Case quality and overturn analysis | Fraud Operations | Weekly |
| Data retention and access | Privacy / Security | Quarterly |
| Adverse-action policy | Legal / Compliance | On policy change |

## Monitoring requirements

- Precision, recall, and investigation yield by signal and risk band.
- Appeal and overturn rates, segmented by decision path.
- Population stability and feature drift.
- Missingness, freshness, and telemetry outage rates.
- Case aging, reviewer workload, and time to disposition.
- Outcomes by legally reviewed cohorts where permitted.

Thresholds should be recalibrated on representative operational labels. Synthetic
demo results demonstrate execution only and must never be treated as production
effectiveness evidence.

## Production safeguards

- Least-privilege access and encrypted sensitive identifiers.
- Separation between raw identifiers and analyst-facing entity keys.
- Immutable case history with correction and appeal annotations.
- Versioned rules, model artifacts, and policy references.
- Kill switches for degraded telemetry or abnormal alert volume.
- Shadow-mode evaluation before any new signal affects driver experience.

## Known limitations

The public IEEE-CIS target is payment-fraud data. GPS, device, payout, campaign,
and delivery telemetry in this repository are synthetic and clearly labeled.
They support architecture demonstration, not claims about any specific company,
driver population, or expected real-world performance.

## Business impact

For a quantified fraud loss model covering all six attack families Sentinel
detects, see [docs/BUSINESS_IMPACT.md](BUSINESS_IMPACT.md).

The short version: at mid-range estimates for a platform of Spark's scale,
prevented losses exceed platform costs by 2–3× in year one if the annual
preventable loss pool exceeds $2M. The highest-value intervention is pre-payout
detection of GPS spoofing and coordinated ring activity. The highest-risk failure
mode is model drift combined with GPS telemetry degradation occurring simultaneously.

## How this system fails

For a documented analysis of all six identified failure modes — threshold gaming,
telemetry degradation, model drift, novel pattern gaps, store-level insider
threat, and legal challenge to adverse action — see
[docs/FAILURE_MODE_ANALYSIS.md](FAILURE_MODE_ANALYSIS.md).

Building a fraud detection system without documenting how it fails is operational
negligence. The failure mode analysis exists so the people running this system
know exactly what to watch for.
