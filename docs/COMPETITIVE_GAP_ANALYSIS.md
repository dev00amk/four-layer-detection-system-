# Project Sentinel: Competitive Gap Analysis

This document evaluates the architectural and functional gaps between Project Sentinel and comparable industrial platforms. Each gap is analyzed based on its business value, technical cost, and relevance to senior risk/decision roles, concluding with a prioritized action recommendation.

---

## 1. Summary of Gaps & Prioritization

We categorize gaps into four strategic action categories:
1. **BUILD NOW:** High-value, low-to-medium cost improvements that immediately boost portfolio visibility and operational capabilities.
2. **DESIGN NOW, BUILD LATER:** Features with high analyst value but requiring UI design or deep graph iterations.
3. **DOCUMENT MIGRATION PATH:** Complex infrastructure (e.g., Kafka, Kubernetes) that is best described in documentation/architectural guides rather than implemented as a local dependency burden.
4. **DO NOT BUILD:** Technologies that add excessive overhead or introduce severe legal/compliance risks without offering clear operational advantages.

---

## 2. Detailed Gap Analysis

### 2.1 Gap: Investigator Queue & Case Management Console
* **Description:** Competitor platforms often display raw scores in a dashboard, but lack a complete case lifecycle. Sentinel generates static markdown case packs but lacks a persistent database-backed triage dashboard showing case states, SLA tracking, and analyst feedback loops.
* **Why It Matters:** In a real-world risk operation, a signal only delivers value if it is triageable. Hiring managers look for an understanding of the entire investigation lifecycle (Score $\rightarrow$ Alert $\rightarrow$ Case Lock $\rightarrow$ Analyst Disposition $\rightarrow$ Model Feedback).
* **Fraud/Business Value:** High. Resolves operational queue bottlenecks and collects clean feedback labels for supervised model retraining.
* **Technical Cost:** Medium.
* **Complexity:** Medium (requires mapping a SQLite/duckdb state table to a Streamlit frontend).
* **Recommendation:** **BUILD NOW** (integrate case status transitions and queue lifecycle directly into the Streamlit dashboard).

### 2.2 Gap: Flexible Event-Ingestion Boundary (Streaming Protocol)
* **Description:** Sentinel runs as a batch processing job (`run.py`), whereas systems like `awslabs` and `pratik9409` claim event-driven streaming boundaries.
* **Why It Matters:** Live production systems score transactions individually and synchronously. A portfolio must demonstrate how it translates batch ML models into single-event scoring structures.
* **Fraud/Business Value:** Medium. Establishes clean decoupled boundaries between ingestion and detection.
* **Technical Cost:** Low.
* **Dependency Burden:** Zero (Python native protocols).
* **Recommendation:** **BUILD NOW** (define an internal `EventSource` protocol with CSV, Parquet, and in-memory replay implementations).

### 2.3 Gap: Operational Prometheus Metrics Surface
* **Description:** Sentinel features model drift and data validations, but lacks an operational health/metrics boundary.
* **Why It Matters:** Production platforms must expose system-level latency, throughput, and error metrics to SRE and monitoring teams.
* **Fraud/Business Value:** Medium. Ensures the platform runs within business SLA constraints.
* **Technical Cost:** Low.
* **Recommendation:** **BUILD NOW** (add an operational `/metrics` endpoint to the FastAPI app returning Prometheus-compatible formats, excluding sensitive identifiers).

### 2.4 Gap: Interactive Graph Visualization
* **Description:** NetworkX ring details are logged in text, but not visualized. Comparators show node-link diagrams.
* **Why It Matters:** Analysts cannot easily digest a text list of shared entities. An interactive node-link map is the most effective tool for uncovering complex collusion rings.
* **Fraud/Business Value:** High. Dramatically speeds up manual ring investigation times.
* **Technical Cost:** Medium.
* **Recommendation:** **DESIGN NOW, BUILD LATER** (design PyVis/Plotly adapters to render local HTML maps of shared-device subgraphs).

### 2.5 Gap: Model Registry Deepening
* **Description:** Sentinel stores model metadata in `model_metadata.json`, but lacks git SHA bindings, training/validation window boundaries, policy version locks, and approval states.
* **Why It Matters:** If a model is rolled back or audited, legal teams must trace the exact training window and git state associated with the decision policy.
* **Fraud/Business Value:** High. Crucial for compliance and auditability.
* **Technical Cost:** Medium.
* **Recommendation:** **DESIGN NOW, BUILD LATER** (extend local model storage to lock policy and signal versions).

### 2.6 Gap: Kafka & Distributed Queue
* **Description:** Comparators claim Kafka for real-time ingestion.
* **Why It Matters:** Portfolios that force a local Kafka dependency are notoriously difficult to run, build, and test, leading to review drop-offs.
* **Fraud/Business Value:** Low (locally). High (in cloud production).
* **Recommendation:** **DOCUMENT MIGRATION PATH** (do not install Kafka; write an architectural deployment document illustrating how the `EventSource` protocol maps to a Kafka consumer group).

### 2.7 Gap: Neo4j / Neptune Graph Database
* **Description:** AWS Labs uses Amazon Neptune; others claim Neo4j.
* **Why It Matters:** Forcing a local Neo4j database install adds massive setup friction.
* **Fraud/Business Value:** Low (locally). NetworkX handles our 2,000-row dataset inside memory in milliseconds.
* **Recommendation:** **DOCUMENT MIGRATION PATH** (keep NetworkX for local demo execution; write an export script/document showing how NetworkX loads into a Neptune/Neo4j database in production).

### 2.8 Gap: Graph Neural Network (GNN) on Live Path
* **Description:** Academic GNN models are featured in GNN-on-DGL and PyTorch Geometric repos.
* **Why It Matters:** Deep graph models are black boxes that are difficult to explain to regulatory auditors. They also introduce high inference latency (>100ms) and require expensive GPU nodes.
* **Fraud/Business Value:** Low. Deterministic shared-entity rules (e.g. sharing payout accounts or devices) are 100% explainable and capture the vast majority of collusion risk.
* **Recommendation:** **DO NOT BUILD** (keep deterministic graph features on the live scoring path; build a GNN script inside a dedicated `research/` directory only as a research benchmark).
