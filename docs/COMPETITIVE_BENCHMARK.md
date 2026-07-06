# Project Sentinel: Competitive Architecture Benchmark

This document presents a rigorous, evidence-based architectural benchmark of Project Sentinel against ten comparable public repositories in the fraud, risk, and data science domains. The analysis separates documented claims from actual, executable code using structured evidence levels.

---

## 1. Executive Conclusion

### Category of Project Sentinel
Project Sentinel occupies the **Governed Risk Operations & Decision Platform** category. It is not merely a machine learning model or a simple infrastructure deployment; it is a system designed to fuse multi-layer detection logic into audit-ready, legally defensible case files for human investigation.

### Comparator Classifications
Among the reviewed public repositories, the competitive landscape splits into three distinct categories:
1. **Dashboards and UI-First Projects:** Streamlit/Flask demonstrations focusing on front-end rendering of raw model outputs (e.g., `firfircelik/fraud-detection-system-streamlit`, `RP-333/Fraud-Analytics-with-AI-ML`).
2. **Machine Learning & Graph Research Experiments:** Codebases designed to benchmark model training (GNNs, XGBoost) on static public datasets, focusing on accuracy metrics but completely lacking operational wiring, APIs, or data pipelines (e.g., `Accrame/fraud-detection-gnn`, `arxyzan/fraud-detection-gnn`).
3. **Infrastructure Blueprints:** Large-scale cloud blueprints illustrating distributed queue ingestion (Kafka, DGL, Neptune) without providing local developer setups, test suites, or risk-operations workflows (e.g., `awslabs/realtime-fraud-detection-with-gnn-on-dgl`, `NVIDIA-AI-Blueprints/Financial-Fraud-Detection`).

### Sentinel's Defensible Differentiation
Sentinel’s core strength lies in **Decision Governance, Explainability, and Investigator Workflow Integrity**. 
* **Governed SQL Signals:** Heuristics are structured as version-controlled SQL files with clear ownership, review dates, and mapped false-positive exclusion tables.
* **Cascading Multi-Layer Fusion:** Fuses deterministic SQL rules, Isolation Forest anomaly scores, XGBoost model probabilities (with local SHAP explanations), and NetworkX entity graph links into a single narrative.
* **Integrity Hashing:** Hashes case file content (SHA-256) to ensure case file integrity.

### Sentinel's Primary Gaps
* **Operational Case Lifecycle Console:** Lacks a persistent database-backed case registry supporting transitions (Assign, Triage, Hold, Dismiss, Escalate) and SLA tracking.
* **Interactive Graph Visualization:** NetworkX results are written to files and CLI summaries but lack interactive visualization (e.g., PyVis, Cytoscape, or Plotly).
* **Flexible Event-Ingestion Boundary:** Runs in batch mode; lacks a clean abstract protocol (`EventSource`) supporting single-event scoring and replay loops.

---

## 2. Comparison Methodology

* **Date of Review:** July 5, 2026.
* **Scope:** Ten designated comparable repositories searched, audited, and code-analyzed.
* **Evidence Standards:**
  * **Level A — Demonstrated:** Executable code, realistic configurations, tests, and documented invocation.
  * **Level B — Partially Demonstrated:** Contains partial code but lacks testing, operational wiring, or realistic configurations.
  * **Level C — Documentation Claim Only:** Claimed in the README or architecture diagram, but no code implementation is present.
  * **Level D — Not Present / Inaccessible:** No code or documentation exists, or the repository is deleted/private.

* **Limitations:** Codebases without public access or deleted from GitHub are marked as Level D. All metrics are audited against the code actually present in the main branches.

---

## 3. Repository-by-Repository Review

### 3.1 firfircelik/fraud-detection-system-streamlit
* **Purpose:** Streamlit-based interface and 4-model ensemble machine learning pipeline for transaction fraud.
* **Architecture:** Streamlit dashboard, FastAPI backend, local scikit-learn models (Random Forest, SVM, Logistic Regression, Isolation Forest).
* **Demonstrated Capabilities (Level A/B):** Interactive Streamlit dashboard visualizing risk score distributions and local model predictions.
* **Documentation-Only Claims (Level C):** Claims "10,000+ TPS throughput", "auto-scaling Kubernetes production-readiness", and "graph-based fraud ring detection." (Code only shows basic visual nodes in Streamlit, not a real GNN or clustered graph database).
* **Missing Capabilities:** Real-time event streams, queue persistency, investigator case lifecycle, and version-controlled SQL signals.
* **Operational Maturity:** Low (development/demo dashboard).
* **Model Maturity:** Medium (scikit-learn ensemble).
* **Investigator Workflow:** Low (visual metrics, no case lock, no audit trails).
* **Governance:** Low (no drift analysis, no integrity check, no model registration).
* **What Sentinel Should Learn:** Clean visual layout for Streamlit dashboard triaging.
* **What Sentinel Should Not Copy:** Fabricated performance claims (10k TPS) built on local, non-concurrent code.

### 3.2 pratik9409/AI-Powered-Transaction-Fraud-Detection-System
* **Purpose:** Real-time transaction fraud platform utilizing GNNs, SHAP, and Kafka.
* **Architecture:** Flask frontend, PyTorch Geometric graph training scripts, Apache Kafka event ingestion, XGBoost scoring.
* **Demonstrated Capabilities (Level A/B):** Graph compilation via PyTorch Geometric (GraphSAGE) and NetworkX. Basic Flask interface for model explainability.
* **Documentation-Only Claims (Level C):** Apache Kafka event consumer is documented as a simple consumer loop but lacks production deployment configs or error handling. GNN inference is not wired to run online at sub-50ms latency.
* **Missing Capabilities:** Governed SQL signal library, persistent case workflows, data lineage tracking, and false-positive exclusion ledgers.
* **Operational Maturity:** Low (ML portfolio experiment).
* **Model Maturity:** High (features PyTorch Geometric GNN and XGBoost + SHAP).
* **Investigator Workflow:** Low (no triage console, no persistent queue state).
* **Governance:** Low (no git-versioned model store, no rollback governance).
* **What Sentinel Should Learn:** Utilizing PyTorch Geometric to train graph embeddings for fraud classification.
* **What Sentinel Should Not Copy:** Side-by-side reporting of model outputs without narrative fusion.

### 3.3 rahulsamant37/FraudDetection
* **Purpose:** Production-grade, real-time transaction fraud platform.
* **Architecture:** Streamlit dashboard, basic Python ML scripts.
* **Demonstrated Capabilities (Level B):** Simple transaction ML training scripts.
* **Documentation-Only Claims (Level C):** README claims "distributed stream processing for financial security" and "production-grade high availability."
* **Missing Capabilities:** Ingestion pipelines, GNNs, SQL rule logic, tests, and case management.
* **Operational Maturity:** Low (developer portfolio skeleton).
* **Model Maturity:** Low (basic training notebooks).
* **Investigator Workflow:** Low (visualizations only).
* **Governance:** Low.
* **What Sentinel Should Learn:** Keep documentation concise.
* **What Sentinel Should Not Copy:** README claims that exaggerate the underlying codebase's maturity.

### 3.4 awslabs/realtime-fraud-detection-with-gnn-on-dgl
* **Purpose:** Real-time transaction fraud blueprint utilizing AWS Neptune and GNNs.
* **Architecture:** Amazon Neptune, SageMaker, Deep Graph Library (DGL), AWS Lambda, Glue ETL.
* **Demonstrated Capabilities (Level A):** Heterogeneous graph construction scripts, AWS Lambda handlers for graph querying, SageMaker training containers, CloudFormation deployment manifests.
* **Documentation-Only Claims (Level C):** Sub-50ms GNN real-time inference is claimed, but relies on expensive, complex subgraph querying configurations.
* **Missing Capabilities:** Plain-language executive summaries, false-positive mitigation checking tables, and local validation options.
* **Operational Maturity:** High (AWS enterprise blueprint).
* **Model Maturity:** High (heterogeneous GNNs).
* **Investigator Workflow:** Medium (Neptune subgraph queries, but lacks case pack narratives).
* **Governance:** Medium (AWS-native resource governance, but no case integrity hashing).
* **What Sentinel Should Learn:** Designing decoupled event boundaries and graph loaders.
* **What Sentinel Should Not Copy:** Heavy infrastructure requirements that make local development impossible.

### 3.5 Accrame/fraud-detection-gnn & arxyzan/fraud-detection-gnn
* **Purpose:** Graph Neural Network research for transaction fraud.
* **Architecture:** PyTorch Geometric model training notebooks.
* **Demonstrated Capabilities (Level B):** GNN models (GCN, GAT, GraphSAGE) trained on the Elliptic dataset with TensorBoard logging.
* **Documentation-Only Claims (Level C):** Claims "real-time fraud ring detection." (Code is static training only).
* **Missing Capabilities:** Web APIs, databases, UI, streaming boundary, and governance.
* **Operational Maturity:** Low (academic research).
* **Model Maturity:** High (deep graph learning).
* **Investigator Workflow:** Low/Absent.
* **Governance:** Low.
* **What Sentinel Should Learn:** Benchmarking deep graph models against traditional ML.
* **What Sentinel Should Not Copy:** Academic models that cannot be explained to a compliance team.

### 3.6 NVIDIA-AI-Blueprints/Financial-Fraud-Detection
* **Purpose:** GPU-accelerated GNN training and inference workflow.
* **Architecture:** Triton Inference Server, GNN containers, SHAP.
* **Demonstrated Capabilities (Level A/B):** GPU-accelerated GNN model creation, Triton deployment configs.
* **Documentation-Only Claims (Level C):** Sub-50ms enterprise-grade inference.
* **Missing Capabilities:** Case workflow, triage views, and local open-source validation (requires NVIDIA AI Enterprise license).
* **Operational Maturity:** High (NVIDIA enterprise blueprint).
* **Model Maturity:** High (GPU-accelerated GNNs).
* **Investigator Workflow:** Low (focus is Triton inference latency, not case routing).
* **Governance:** Medium (Triton observability, but no decision policy registry).
* **What Sentinel Should Learn:** Performance-optimized GNN inference pipelines.
* **What Sentinel Should Not Copy:** Proprietary dependencies (NVAIE) that restrict verification.

### 3.7 RP-333/Fraud-Analytics-with-AI-ML
* **Purpose:** Fraud analytics, exploratory data analysis, and AML/KYC portfolio.
* **Architecture:** Jupyter notebooks.
* **Demonstrated Capabilities (Level B):** Jupyter notebooks showcasing transactional EDA, identity metrics, and basic KYC data profiling.
* **Documentation-Only Claims (Level C):** Claims "enterprise-grade compliance system."
* **Missing Capabilities:** Running API, databases, dashboards, testing frameworks, and versioned rules.
* **Operational Maturity:** Low (Jupyter portfolio).
* **Model Maturity:** Low (basic modeling notebooks).
* **Investigator Workflow:** Low.
* **Governance:** Low.
* **What Sentinel Should Learn:** Clear markdown styling for exploratory analysis.
* **What Sentinel Should Not Copy:** Code consisting entirely of notebooks with no runnable packages.

### 3.8 vickbrownk/End-to-End-Data-Engineering-Pipeline-for-Fraud-Prevention
* **Status:** Inaccessible / Deleted (Level D). No public code or documentation available under this handle.

### 3.9 Mhaycen/Fraud-Detection
* **Status:** Inaccessible / Deleted (Level D). No public code or documentation available under this handle.

---

## 4. Evidence Matrix

The table below maps the demonstrated capabilities (Level A/B), claims (Level C), or absence (Level D) of critical platform components:

| Capability | Sentinel | firfircelik | pratik9409 | awslabs | NVIDIA | RP-333 | Evidence Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Behavioral Rules** | **A** | **B** | **D** | **D** | **D** | **D** | Sentinel houses 25 governed SQL rules; competitors use basic pandas filters. |
| **SQL Signal Governance** | **A** | **D** | **D** | **D** | **D** | **D** | Sentinel utilizes structured rule headers with mimics and review dates. |
| **Anomaly Detection** | **A** | **A** | **B** | **D** | **D** | **D** | Sentinel features Isolation Forest; `firfircelik` includes Isolation Forest in ensemble. |
| **Supervised Model** | **A** | **A** | **A** | **D** | **D** | **B** | XGBoost/Random Forest models are fully trained and version-controlled. |
| **Graph Detection** | **A** | **B** | **B** | **A** | **A** | **D** | Sentinel uses NetworkX for ring clustering; others use PyG/DGL. |
| **GNN** | **D** | **D** | **B** | **A** | **A** | **D** | GNNs are demonstrated by `awslabs` and `NVIDIA`; Sentinel relies on heuristics. |
| **Explainability** | **A** | **B** | **B** | **D** | **B** | **D** | Sentinel writes local SHAP values; `NVIDIA` supports Triton SHAP. |
| **Alert Persistence** | **A** | **D** | **D** | **B** | **D** | **D** | Sentinel writes JSON/Markdown alerts; others have transient UI queues. |
| **Case Management** | **B** | **D** | **D** | **D** | **D** | **D** | Sentinel generates detailed Forensic Case Packs; competitors list raw scores. |
| **False-Positive Controls**| **A** | **D** | **D** | **D** | **D** | **D** | Sentinel features exclusion tables mapping OSINT/telemetry. |
| **FastAPI** | **A** | **A** | **D** | **B** | **D** | **D** | `firfircelik` and Sentinel feature functional FastAPI scoring endpoints. |
| **Streaming** | **D** | **C** | **B** | **A** | **B** | **D** | `awslabs` integrates AWS stream pipelines; `pratik9409` has local Kafka consumers. |
| **Drift Monitoring** | **A** | **D** | **D** | **D** | **D** | **D** | Sentinel implements Kolmogorov-Smirnov feature drift checks. |
| **Data Lineage** | **A** | **D** | **D** | **B** | **D** | **D** | Sentinel has explicit Bronze $\rightarrow$ Silver $\rightarrow$ Gold parquet files. |
| **Artifact Integrity** | **A** | **D** | **D** | **D** | **D** | **D** | Sentinel hashes case evidence using SHA-256 signatures. |
| **OSINT / Enrichment** | **A** | **D** | **D** | **D** | **D** | **D** | Sentinel features simulated document, device, and web OSINT steps. |
| **CI / Tests** | **A** | **D** | **D** | **D** | **D** | **D** | Sentinel has 56 passing unit tests; other repos lack test suites. |

*Notes:*
* **A:** Demonstrated (fully functional, verified in code).
* **B:** Partial (code exists but lacks validation, tests, or integration).
* **C:** Claimed only (README text with no code backup).
* **D:** Absent.

---

## 5. Positioning Conclusion

Among the reviewed public repositories, Project Sentinel represents the **highest-quality portfolio platform for Risk Operations and Decision Governance**. 

* **Where competitors excel:** Blueprints like `awslabs` and `NVIDIA` provide robust cloud orchestration (AWS Step Functions, Triton, Neptune) and deep graph learning models (GNNs). 
* **Where Sentinel excels:** Sentinel dominates in **fraud analytics depth, explainability, compliance readiness, and decision governance**. No other reviewed repository structures behavioral rules under version control, generates hashed forensic case files, checks false-positive exclusions, or monitors statistical model drift. 

Sentinel’s target audience—hiring managers looking for Senior Risk Investigators, Decision Engineers, and Fraud Data Scientists—value the ability to explain *why* a decision was made and *how* to defend it. While competitors show that code can execute models, Sentinel demonstrates that code can **reason** about fraud.
