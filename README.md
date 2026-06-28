# Project Sentinel — Four-layer Spark Driver Fraud Detection System

> Portfolio implementation of Spark Driver fraud detection operations:
> multi-layer behavioral detection, structured OSINT enrichment, and
> investigator-ready case management designed for auditability,
> false-positive control, and legal defensibility.

Sentinel converts raw Spark Driver telemetry into prioritised, audit-ready
fraud cases — catching GPS spoofing rings, bot-assisted offer grabbing, and
coordinated payout abuse before settlement, while producing evidence packs
that hold up to legal review and appeal. Every adverse action is traceable
from raw event to investigator decision. Every signal documents its
false-positive risk. Every queued CRITICAL-band output generates a case file
that can be handed directly to Legal without further preparation.

> This is a portfolio/reference implementation built on the public IEEE-CIS
> fraud dataset plus clearly labelled, deterministic synthetic delivery
> telemetry. It is not a Walmart system and makes no claim to use
> proprietary Walmart data.

---

## Role alignment — LMD Fraud Prevention and Trust & Safety

Sentinel is designed around five outcomes common to last-mile fraud
prevention and trust & safety roles:

| Outcome | How Sentinel addresses it | Repo location |
|---------|--------------------------|---------------|
| **Fraud loss reduction** | GPS spoofing, payout abuse, and incentive gaming prioritised into CRITICAL bands before settlement | `sentinel/anomaly.py`, `docs/BUSINESS_IMPACT.md` |
| **False-positive control** | Every signal documents FP risk, mitigation, and threshold rationale; four FP paths require analyst sign-off before adverse action | `sql/signals/` headers, `sentinel/case.py` |
| **Case queue prioritisation** | 25-case cap per run models investigator workload; CRITICAL and CRITICAL+ cases auto-generated with pre-filled evidence | `sentinel/case.py`, `cases/` |
| **Identity / device / GPS / OSINT** | Five-step OSINT enrichment (identity document, device intelligence, address type, account resale, contractor presence) produces audit-hashed evidence per case | `sentinel/osint.py` |
| **Governance and traceability** | Immutable bronze, SHA-256 lineage, version-controlled signals, Markdown case files with integrity hash | `sentinel/ingest.py`, `data/bronze/lineage.json` |

---

## Impact metrics (LMD Fraud Prevention)

**Fraud and trust outcomes**

- **Fraud loss reduction:** GPS spoofing, payout abuse, and incentive gaming
  are prioritised into CRITICAL risk bands and review queues, targeting
  the highest-loss attack families before settlement. Quantified loss model
  across all six attack families: [`docs/BUSINESS_IMPACT.md`](docs/BUSINESS_IMPACT.md).
- **False-positive control:** ensemble weights, rule thresholds, and OSINT
  enrichment are each documented with FP risk and mitigation strategy,
  aligning with trust and fairness expectations for Spark Driver adverse actions.

**Detection quality and operations**

- **Model performance:** logs AUC-ROC, AUC-PR, row count, and fraud rate to
  `data/models/metrics.json` on every run for ongoing detection quality monitoring.
- **Case queue throughput:** caps CRITICAL case generation at 25 per run to
  model realistic investigator workload and optimise time-to-action.

**Behavioural and OSINT coverage**

- **Behavioural coverage:** 25 SQL signals target GPS spoofing, geofence misses,
  emulator and rooted devices, shared devices and payouts, refund velocity,
  incentive gaming, off-hours activity, bot-assisted batch grabbing, device
  forensics, device hopping, shared IPs, payout changes, and composite risk.
- **OSINT enrichment:** structured five-step external verification (identity
  document, device intelligence, address type, account resale detection,
  contractor presence) produces audit-hashed evidence embedded directly in
  each case file. Module: [`sentinel/osint.py`](sentinel/osint.py).

**Governance, audit, and data quality**

- **End-to-end lineage:** immutable bronze outputs, SHA-256 lineage chains,
  version-controlled signals, and Markdown case files ensure every adverse
  action is traceable from raw event to investigator decision.
- **Governance and failure modes:** documented signal prioritisation,
  operational risk framework, and failure-mode analysis provide the
  foundation for rule and model calibration and ethical deployment.
  See [`docs/FAILURE_MODE_ANALYSIS.md`](docs/FAILURE_MODE_ANALYSIS.md).

---

## Architecture

```mermaid
flowchart LR
  A["IEEE-CIS CSV or demo generator"] --> B["Bronze: immutable Parquet + lineage"]
  B --> C["Silver: GPS, device, payout, incentive telemetry"]
  C --> D["25 DuckDB SQL signals"]
  C --> E["Isolation Forest"]
  C --> F["XGBoost"]
  C --> G["NetworkX entity graph"]
  D --> H["Weighted ensemble (0–10)"]
  E --> H
  F --> H
  G --> H
  H --> I["Risk bands + evidence-filled case files"]
  H --> J["Tableau-ready export"]
```

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m sentinel.demo          # generates synthetic raw CSVs — no Kaggle download required
python -m sentinel.ingest        # converts data/raw CSVs to bronze Parquet
python -m sentinel.enrich
python run.py
```

For the full 590,540-row dataset, accept the
[IEEE-CIS competition rules](https://www.kaggle.com/competitions/ieee-fraud-detection/data),
place `train_transaction.csv` and `train_identity.csv` in `data/raw/`,
and start at ingestion.

---

## Detection layers

| Layer | Purpose | Output |
|-------|---------|--------|
| SQL signals | Explainable, threshold-based controls with documented FP risk | 25 named driver signals |
| Isolation Forest | Previously unseen behaviour — catches novel patterns not yet in rules | Normalised novelty score |
| XGBoost | Supervised fraud propensity with per-row SHAP explanations | Calibrated probability |
| Entity graph | Coordinated multi-account behaviour via shared device, bank, store | Ring flag + ring size |

Blend weights: XGBoost 45%, Isolation Forest 25%, SQL 20%, graph 10%.
Ring members receive a proportional multiplier (1.2× for a 2-driver pair,
up to 1.5× for a 5+ driver ring), capped at 10. IP cluster edges are
excluded from ring detection to prevent carrier NAT false positives.

---

## Signal library

The 25 version-controlled queries in [`sql/signals/`](sql/signals/) cover
GPS spoofing and impossible transit, geofence misses, emulator and rooted
devices, shared devices and payouts, refund velocity, incentive gaming,
off-hours activity, trip distance and amount anomalies, store concentration,
device hopping, shared IPs, payout changes, bot-assisted batch grabbing,
device forensics account hopping, and composite risk. Each query documents
its fraud type, FP risk, mitigation, and threshold rationale.

Signal triage framework (protect / tune / monitor / sunset): [`docs/SIGNAL_PRIORITIZATION.md`](docs/SIGNAL_PRIORITIZATION.md).

---

## Results and honest benchmarking

`python run.py` writes AUC-ROC, AUC-PR, row count, and fraud rate to
`data/models/metrics.json`. Demo metrics validate execution but are not
presented as a production benchmark — synthetic telemetry deliberately
separates fraud from legitimate classes to enable demonstration without
real operational data. The reference IEEE-CIS target is 0.918 ROC-AUC /
0.891 PR-AUC; reproduce it only with the competition dataset and the
documented feature and training setup.

---

## Investigation workflow

CRITICAL and CRITICAL+ drivers generate pre-populated Markdown case files
containing: all four layer scores, SHAP top-5 feature contributions,
cross-role collusion evidence, a five-step OSINT enrichment table with
audit-hashed evidence records, a false-positive exclusion checklist
(four named paths requiring analyst sign-off), recommended action, and an
SHA-256 integrity hash. Case generation is capped at 25 per run to model
a realistic investigator queue.

### CASE_001 — coordinated account infrastructure

[![CASE_001 entity graph showing two drivers sharing one device, payout account, campaign, and store](dashboards/case_001_graph.png)](cases/CASE_001.md)

[`cases/CASE_001.md`](cases/CASE_001.md) shows two driver accounts
converging on one device, one payout account, one incentive campaign, and one store.
Coordination becomes visible even when individual trip rows appear
individually plausible — the graph layer's core advantage.

### Sample output — CASE_001 composite score

| Layer | Score | Threshold | Status |
|---|---|---|---|
| SQL signals | 12/25 signals fired | > 5 | ✓ |
| Isolation Forest | 0.681 anomaly score | > 0.60 | ✓ |
| XGBoost | 1.000 fraud probability | > 0.50 | ✓ |
| Graph ring | Member — 2-driver ring (1.2× multiplier) | flag = 1 | ✓ |
| **Composite** | **10 / 10 — CRITICAL+** | ≥ 7 | ✓ |

### Sample output — `metrics.json` (demo run)

```json
{
  "val_roc_auc": 0.847,
  "val_avg_precision": 0.763,
  "fraud_rate": 0.035,
  "rows_scored": 12000,
  "critical_cases_generated": 12,
  "note": "demo dataset — see README for IEEE-CIS benchmark target"
}
```

This reviewer-facing sample uses the explicit demonstration values supplied
for the portfolio. Actual runs write their observed metrics to
`data/models/metrics.json`; synthetic results are not production evidence.

---

## Notebooks and dashboard

- [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) — class imbalance, GPS anomaly scatter, correlation heatmap
- [`notebooks/04_ml_model.ipynb`](notebooks/04_ml_model.ipynb) — AUC metrics, SHAP summary plot, benchmark comparison
- [`notebooks/05_graph_analysis.ipynb`](notebooks/05_graph_analysis.ipynb) — ring ranking, size distribution, CASE_001 graph
- [`dashboards/tableau_spec.md`](dashboards/tableau_spec.md) — four-sheet Tableau build specification

Run `python scripts/create_notebooks.py` to rebuild notebooks.
Generated data and model artifacts are excluded from version control.

---

## Job-description traceability

| JD requirement | Evidence in this project |
|----------------|--------------------------|
| Behavioural analysis, segmentation, anomaly detection | 25 DuckDB signals + Isolation Forest + behavioural feature engineering (`sentinel/features.py`) |
| GPS movement, device details, metadata, mixed-signal decisioning | `sentinel/enrich.py` + signals 01–06, 23–25 |
| Build and refine fraud indicators with FP controls | `sql/signals/` — each file documents fraud type, FP risk, mitigation, threshold rationale |
| Stress-test queries against legitimate scenarios | FP exclusion checklist in every case file; `docs/SIGNAL_PRIORITIZATION.md` triage framework |
| Audit-ready case file management | `sentinel/case.py` + `cases/` — SHA-256 hashed, pre-populated, OSINT enrichment included |
| OSINT to confirm identities and uncover networks | `sentinel/osint.py` — five-step structured enrichment with audit hash per step |
| Cross-functional reporting | `docs/CROSS_FUNCTIONAL_BRIEFING.md` — four stakeholder briefings on CASE_001 |
| SQL proficiency at scale | 25 production DuckDB queries + cross-role risk gold view |
| Python and ML | `sentinel/model.py`, `anomaly.py`, `graph.py`, `features.py`, `osint.py` |
| Business case and program ownership | `docs/BUSINESS_IMPACT.md`, `SIGNAL_PRIORITIZATION.md`, `FAILURE_MODE_ANALYSIS.md` |

---

## Documentation index

| Document | Purpose |
|----------|---------|
| [`docs/OPERATIONAL_RISK.md`](docs/OPERATIONAL_RISK.md) | Human-in-the-loop routing, auditability design, control ownership |
| [`docs/BUSINESS_IMPACT.md`](docs/BUSINESS_IMPACT.md) | Quantified loss model for 6 attack families, ROI at 3 loss-pool sizes |
| [`docs/SIGNAL_PRIORITIZATION.md`](docs/SIGNAL_PRIORITIZATION.md) | 3-axis triage framework (yield × FP cost × business impact) for all 25 signals |
| [`docs/CROSS_FUNCTIONAL_BRIEFING.md`](docs/CROSS_FUNCTIONAL_BRIEFING.md) | 4 stakeholder briefings: Product, Legal, Engineering, Care Operations |
| [`docs/FAILURE_MODE_ANALYSIS.md`](docs/FAILURE_MODE_ANALYSIS.md) | 6 failure modes with detection lag, early warning indicators, mitigation |
| [`docs/PLATFORM_EQUIVALENCE.md`](docs/PLATFORM_EQUIVALENCE.md) | Maps Sentinel to NICE Actimize, Pega, Salesforce FSC, Unit21 |
| [`docs/DETECTION_STRATEGY.md`](docs/DETECTION_STRATEGY.md) | Detection thresholds, evidence standards, false-positive controls, economics, and monitoring |
| [`docs/FRAUD_TECHNIQUES.md`](docs/FRAUD_TECHNIQUES.md) | Fraud technique library, kill chain, lifecycle mapping, and signal coverage |
| [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) | Risk appetite, action standards, appeals, escalation, QA, and model governance |
| [`docs/INVESTIGATOR_PLAYBOOK.md`](docs/INVESTIGATOR_PLAYBOOK.md) | Eight-step investigation SOP from intake through escalation and case closure |
| [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) | Material program decisions, alternatives, tradeoffs, rationale, and monitoring plans |

---

## Streaming extension

The batch interfaces map cleanly to Kafka and Flink: key telemetry by
`driver_id`, maintain time-windowed signal state, materialise entity edges
incrementally, and send scored events to a review queue. The three
highest-value signals (GPS impossible transit, shared device, shared payout)
are the priority streaming candidates — catching them before payout
settlement is 3–5× more valuable than post-settlement detection.
Thresholds and adverse-action decisions must remain human-governed,
monitored for drift and disparate impact, and validated against real
operational labels.

---

## Responsible use

Synthetic fields are marked in code and must never be treated as observed
facts. A high composite score is an investigation priority, not proof of
fraud. Production deployment requires privacy review, least-privilege
access controls, fairness testing across protected-class proxies, appeal
pathways for every adverse action, and threshold calibration on
representative operational data.
