# Platform equivalence map

> How Project Sentinel's components correspond to enterprise fraud
> detection platforms. This document enables team members familiar with
> commercial platforms to orient quickly to Sentinel's architecture —
> and demonstrates that Sentinel's design choices are grounded in how
> production fraud operations actually run.

---

## Component mapping

| Sentinel component | NICE Actimize | Pega Fraud Management | Salesforce FSC | Unit21 |
|---|---|---|---|---|
| `sql/signals/` (25 DuckDB rules) | Business Rules Engine (BRE) — named rules with documented thresholds and FP controls | Decision Strategy canvas — rule nodes with condition/action pairs | Fraud Detection Rules in Financial Services | Detection Rules builder |
| `sentinel/anomaly.py` (Isolation Forest) | ActimizeWatch unsupervised profiling | Adaptive Models — self-learning anomaly detection | Einstein Discovery anomaly scoring | Unsupervised detection layer |
| `sentinel/model.py` (XGBoost + SHAP) | CAMS supervised model with explainability output | Predictive models with customer decision management | Einstein Prediction Service | ML scoring layer |
| `sentinel/graph.py` (NetworkX rings) | Network Link Analysis (NLA) module | Network Analytics widget | Graph API + Relationship Map | Entity graph and network analysis |
| `sentinel/case.py` (case file generation) | Case Manager — pre-populated with evidence, SHAP top features, risk scores | Case Management widget with evidence panel | Case object in Investigation Console | Case Management with auto-populated evidence |
| `sentinel/anomaly.py::risk_band_router()` | Alert triage and routing rules | Routing Strategy — band-based queue assignment | Assignment Rules on Case object | Alert triage and routing |
| `sql/gold/cross_role_risk_join.sql` | Cross-entity risk aggregation view | Cross-channel risk rollup | Multi-object SOQL join | Cross-role risk view |
| `sentinel/osint.py` (OSINT enrichment) | External Data Feed Manager + OSINT connector | Evidence Collection widget | External Lookup actions | External enrichment step |
| `data/bronze/lineage.json` (SHA-256 chain) | Audit Trail and Evidence Log | Case Audit History | Audit Trail object | Evidence ledger and audit log |
| `docs/SIGNAL_PRIORITIZATION.md` | Alert tuning and governance workflow | Model governance and champion/challenger | Model management and approval | Signal governance and lifecycle |
| `docs/CROSS_FUNCTIONAL_BRIEFING.md` | SAR narrative and stakeholder report templates | Case summary and compliance report | Case report and regulatory output | Investigation report templates |
| FP exclusion checklist in case files | Alert disposition with reason codes | Decision logging and false positive tracking | Case resolution with reason | Disposition workflow |
| `docs/FAILURE_MODE_ANALYSIS.md` | Model monitoring and drift detection | Adaptive model performance monitoring | Einstein Analytics monitoring dashboard | Signal performance monitoring |

---

## Key architectural parallels

### Rules engine (Layer 1)

Sentinel's 25 SQL signals are structurally identical to the rules
configured in NICE Actimize's Business Rules Engine or Pega's Decision
Strategy canvas. Each rule has:
- A named signal (rule name)
- A documented threshold (condition)
- A FP risk and mitigation statement (tuning documentation)
- An output that feeds the ensemble scorer (alert score contribution)

In Actimize, these would be configured via the NGAM or Xceed UI.
In Pega, they sit on the Decision Strategy as condition/action nodes.
In Sentinel, they are version-controlled SQL files — more auditable than
GUI-configured rules because every change is in git history.

### Case management (Layer output)

Sentinel's case files mirror the case object structure in every major
platform:
- NICE Actimize Case Manager: pre-populated evidence panel, disposition
  workflow, audit trail, SAR narrative export
- Pega Case Management: case widget with evidence collection step,
  routing strategy, SLA tracking
- Salesforce FSC Investigation Console: Case object with related evidence
  records, assignment rules, External Lookup enrichment actions
- Unit21: Investigation workflow with auto-populated evidence, disposition
  queue, bulk action support

The key difference: Sentinel's case files are Markdown — human-readable,
version-controllable, and embeddable in any document workflow without
a platform license.

### OSINT enrichment

Sentinel's `osint.py` module replicates the external enrichment step
present in every major platform:
- Actimize: External Data Feed Manager connects to Lexis Nexis, Equifax,
  and custom vendor APIs, with results displayed in the Case Manager
  evidence panel
- Pega: Evidence Collection widget with connector framework for Socure,
  Persona, SEON
- Salesforce FSC: External Lookup actions on the Case object, with
  results stored as related Evidence records
- Unit21: External enrichment step in the Investigation Workflow builder

Sentinel's `OsintResult` schema — step_id, source_type, query_method,
result_code, confidence, risk_signal, timestamp, query_hash — mirrors
the evidence record schema in all four platforms.

---

## What Sentinel does differently

Three areas where Sentinel's design differs from commercial platforms —
and why the difference is intentional:

**Version-controlled signals vs GUI-configured rules.** Commercial
platforms configure rules through UIs. This is fast but makes rule
history opaque — you cannot `git diff` a rule change in Actimize.
Sentinel's SQL signal files are version-controlled, meaning every
threshold change, FP mitigation addition, and signal sunset is visible
in git history. For regulated environments, this is a stronger audit trail.

**Open scoring formula vs black-box ensemble.** Commercial platforms
often have proprietary ensemble logic. Sentinel's ensemble weights
(45/25/20/10) and ring multiplier formula are documented in code and
docstrings. Any investigator can reproduce a driver's score from the
component outputs. This is the legal defensibility requirement applied
to the model layer.

**Markdown case files vs platform-locked records.** Case files in
Actimize/Pega/Salesforce are stored in proprietary databases. Sentinel's
Markdown case files are portable, readable without a license, and
embeddable in any document workflow. The SHA-256 integrity hash provides
the same tamper-evidence that platform databases provide through access
control.
