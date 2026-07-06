# Project Sentinel: Differentiation Strategy

This document outlines Project Sentinel’s positioning and product strategy, structured around five core pillars of risk operations excellence. Our focus is to provide a platform that balances technical detection with compliance, defensibility, and business metrics.

---

## Pillar 1: Governed Detection (The Heuristics Layer)
Unlike other platforms that treat rule engines as undocumented configurations, Sentinel treats heuristics as **governed code**:
* **Version-Controlled Signals:** All rules are written in standard SQL files inside `sql/signals/`.
* **Mimics & Guards Ledger:** Every signal file begins with a structured header documenting suspected abuse, known legitimate mimics (false positives), and the explicit guards implemented to exclude them.
* **Metadata & Ownership:** Signals declare explicit owners, review dates, and operational status (e.g., `MONITOR_ONLY` vs. `ENFORCEMENT`). This ensures rules never decay into "alert-dumping" zombies.

---

## Pillar 2: Mixed-Signal Intelligence (Multi-Layer Corroboration)
Sentinel rejects the industry trend of mixing all telemetry into a single, uninterpretable machine learning model. Instead, we implement a **cascading, multi-layer intelligence** model:
1. **Layer 1 (Deterministic Rules):** Captures high-precision, low-volume violations (e.g. impossible transit or multi-accounting).
2. **Layer 2 (Unsupervised Anomalies):** Uses Isolation Forest to score overall behavioral outliers.
3. **Layer 3 (Supervised Learning):** Applies XGBoost + local SHAP explanation values to score historical similarity.
4. **Layer 4 (Entity Graph):** NetworkX detects physical link-sharing (devices, bank accounts, IPs) to group accounts.
* **Separation of Evidence:** By keeping these layers mathematically distinct, our case narratives can explicitly trace *which* layer triggered *which* finding, keeping the final output explainable under oath.

---

## Pillar 3: Investigator Operations (The Forensic Case Pack)
Instead of alerting investigators with a dashboard list of raw percentages, Sentinel compiles **Forensic Case Packs** (`cases/CASE_D*.md`):
* **Plain-Language Executive Summary:** Translates machine learning scores into an Allegation Block that can be read by compliance, legal, and support teams.
* **Fused Investigation Narrative:** Explains the fraud story chronologically (e.g., device change $\rightarrow$ payout update $\rightarrow$ extreme refund behavior).
* **Automated Exclusions:** Evaluates OSINT document, address, and device metadata to programmatically check for false-positive indicators (e.g. residential carrier IP vs. hosting network).
* **Red-Team Evasion Log:** Explains the typical evasion paths for the Suspected Abuse and documents the countermeasures to prevent them.

---

## Pillar 4: Decision Governance (Audit & Regulatory Defensibility)
Sentinel is designed to survive regulatory audits and depositions:
* **Version Lock:** Case packs record the exact git SHA, model version, and decision policy version active at the time of the event.
* **Evidence Integrity Hashing:** The final case pack compiles all telemetry, SHAP tables, and graph ring edges, generating a unique SHA-256 integrity hash. Any manual tampering with the case pack will invalidate the signature.
* **Prohibited Automated Actions:** Extreme anomaly scores only escalate priority within triage queues; automated account deactivation is restricted to Fatal Override codes (e.g., physically impossible land travel >400 km/h) that are physically indisputable.

---

## Pillar 5: Business and Product Impact (Loss Economics)
Sentinel connects risk operations directly to the company's financial bottom line:
* **Loss Estimation:** Calculates the direct loss exposure of the flagged account (e.g., refund volumes, incentive payouts).
* **Capacity-Aware Thresholds:** Gates queues based on investigator headcount and capacity constraints, adjusting thresholds dynamically to prevent queue backlog.
* **Preventability Metrics:** Classifies fraud cases by whether they are preventable via product controls (e.g. forcing document verification or selfie check) versus requiring manual triage.
* **Experimentation Logs:** Documents rollbacks, experimental controls, and rule updates inside a centralized decision log.
