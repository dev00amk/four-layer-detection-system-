# Project Sentinel: Proposed GitHub Issues

This document compiles the structured technical issues proposed to address Sentinel's architectural gaps and differentiate the platform against the competitive benchmark.

---

## Issue 1: Build Persistent Alert and Case Lifecycle

### Problem
Currently, Sentinel's cases are generated as static Markdown files (`cases/CASE_D*.md`). There is no persistent database-backed case lifecycle (lock, assignment, transitions) to prevent multiple investigators from reviewing the same case or to track historical analyst decisions.

### Competitive Evidence
`firfircelik/fraud-detection-system-streamlit` features live transaction scoring and alert logging, but lacks a persistent database-backed investigator lifecycle.

### Sentinel Current State
Alerts are transient outputs of `run.py` that write to markdown files. Model scoring logs to SQLite, but case management metadata is missing.

### Proposed Capability
Build a SQLite-backed operational `cases` table to track the review state machine: `driver_id`, `state` (Triage, Under Review, Escalated, Resolved, Dismissed), `owner` (investigator name), `disposition` (Confirmed Fraud, False Positive, Exception), `sla_deadline`, and `action_taken`.

### Why It Matters
Converts a passive auditing tool into a functional operations platform, preventing double-work and building clean training labels for future models.

### Scope
* SQLite database schema migration script.
* Python state machine inside `sentinel/case_lifecycle.py` enforcing allowed transitions.
* Triage lock/unlock API endpoints in FastAPI backend.

### Out of Scope
* Integration with enterprise SSO (Auth0/Active Directory).
* Slack/email alert notifications.

### Architecture
FastAPI endpoint receives `PUT /api/cases/{driver_id}/transition` updating the SQLite database. SQLite acts as the lightweight transaction registry.

### Acceptance Criteria
* State table is initialized upon pipeline run.
* FastAPI endpoints can assign, lock, and transition cases.
* Invalid transitions (e.g. from Triage straight to Resolved without an Owner) are blocked and raise a `400 Bad Request`.

### Tests
Unit tests in `tests/test_case_lifecycle.py` checking valid/invalid state transitions.

### Documentation
Document the state machine diagram and database schemas in `docs/CASE_LIFECYCLE.md`.

### Dependencies
None (uses native SQLite and FastAPI).

### Risks
Concurrency lock issues if multiple workers write to SQLite simultaneously. Mitigate by setting `timeout=30.0` in SQLite connection.

### Estimated Complexity
**M**

---

## Issue 2: Build Investigator Triage Console

### Problem
Investigators do not have a visual interface to lock, triage, and log resolutions for generated cases.

### Competitive Evidence
`firfircelik/fraud-detection-system-streamlit` has a Streamlit UI showcasing transactions, but lacks a persistent review workflow dashboard.

### Sentinel Current State
Investigators must read raw Markdown files inside their text editor.

### Proposed Capability
Extend the Streamlit/Flask console with a dedicated **Investigator View**:
* **Queue Triage list:** Shows unresolved CRITICAL cases with SLA timer and current lock owner.
* **Triage View:** Clicking a case opens the investigation pack (narrative, SHAP explanations, OSINT flags) with dropdowns for Assignment, Dispositions, and a Notes text field.
* **Feedback loop:** Pressing "Submit Resolution" commits the state change to SQLite.

### Why It Matters
Operational efficiency; makes the system ready for live testing by non-technical risk operations teams.

### Scope
* Streamlit page `console_triage.py` displaying the list of active cases.
* Interactive widgets to assign cases and submit dispositions.

### Out of Scope
* Real-time push notifications of new cases.

### Architecture
The Streamlit app queries the local SQLite `cases` table, fetches case narratives from `cases/` or the database, and submits changes via local SQLAlchemy/SQLite connections.

### Acceptance Criteria
* The app lists active cases sorted by risk score and SLA deadline.
* An analyst can assign themselves to a case, preventing others from triaging it.
* A resolved case disappears from the active triage queue and moves to history.

### Tests
Mock Streamlit tests asserting active row render states and form submissions.

### Documentation
Walkthrough of investigator workflow inside `docs/INVESTIGATOR_GUIDE.md`.

### Dependencies
`streamlit` or `flask` (pre-installed).

### Risks
UI rendering delays on large queues. Mitigate by paginating cases (limit to 50 active rows).

### Estimated Complexity
**M**

---

## Issue 3: Add Explainable Graph Evidence Visualization

### Problem
Entity graph links (shared devices, IPs, payout accounts) are represented as text lists. Unraveling large collusion rings from text is slow and error-prone.

### Competitive Evidence
`firfircelik/fraud-detection-system-streamlit` and `pratik9409` claim graph-based visualizations of fraud rings.

### Sentinel Current State
NetworkX identifies shared entity links and outputs CLI text, but no visual representation is generated for investigators.

### Proposed Capability
Add an interactive HTML graph visualization utilizing **PyVis** or **Plotly Network**:
* Render nodes (drivers, devices, bank accounts, IPs) with distinct colors/icons.
* Render edges labeled with shared entity confidence (e.g. number of shared trips, first/last seen).
* Embed this interactive graph component directly into the Streamlit triage page and save the HTML file inside the case folder.

### Why It Matters
Visually exposes collusion networks immediately, saving hours of manual connection tracing.

### Scope
* PyVis graph generator module `sentinel/graph_viz.py`.
* Injecting PyVis HTML components into Streamlit cases view.

### Out of Scope
* Connecting to an external Neo4j database.

### Architecture
NetworkX graph sub-structures are converted to PyVis networks locally, rendered to a static HTML block, and embedded via Streamlit's `components.html`.

### Acceptance Criteria
* Case files contain a path to the generated HTML graph visualization.
* Streamlit console successfully renders the interactive node-link map.
* Graph nodes are color-coded (Red = Flagged, Green = Clean, Blue = Shared Entity).

### Tests
Unit tests verifying PyVis HTML generation without breaking on missing nodes.

### Documentation
Document the graph nodes, colors, and edge definitions in `docs/GRAPH_INTERPRETATION.md`.

### Dependencies
`pyvis` (added as optional dependency).

### Risks
Graph rendering becomes cluttered for huge collusion rings. Mitigate by limiting neighbors to depth-1 and depth-2 links.

### Estimated Complexity
**M**

---

## Issue 4: Add Prometheus-Compatible Operational Metrics

### Problem
Sentinel has no real-time telemetry output, making it impossible for site reliability engineers (SRE) or monitoring systems to verify scoring latency, throughput, or error rates.

### Competitive Evidence
`NVIDIA-AI-Blueprints/Financial-Fraud-Detection` features model performance metrics and deployment telemetry.

### Sentinel Current State
No real-time observability endpoint exists.

### Proposed Capability
Expose a `/metrics` route in the FastAPI application returning Prometheus-compatible text output containing:
* `sentinel_requests_total{model_version, policy_version}`
* `sentinel_latency_seconds_bucket{endpoint}`
* `sentinel_errors_total{error_type}`
* `sentinel_risk_band_distribution{band}`
* `sentinel_drift_ks_statistic{feature}`

### Why It Matters
Crucial for production compliance; enables automatic alerting on latency spikes or sudden model degradation.

### Scope
* Metric registry and Prometheus formatter in `sentinel/metrics.py`.
* `/metrics` GET route in the FastAPI application.

### Out of Scope
* Setting up Prometheus or Grafana containers.
* Exposing personal data (PII) inside metric labels.

### Architecture
Applies Prometheus Python Client (or manual text formatting) to increment global counters during API execution.

### Acceptance Criteria
* `/metrics` returns a HTTP `200 OK` with valid Prometheus text format.
* High latency or failures correctly increment corresponding metrics.
* Excludes any driver IDs or trip IDs from labels.

### Tests
FastAPI test client asserting the output format of `/metrics`.

### Documentation
SRE integration guide in `docs/MONITORING.md`.

### Dependencies
`prometheus-client` (optional) or manual formatting.

### Risks
Performance overhead during high throughput. Mitigate by utilizing fast, thread-safe counter objects.

### Estimated Complexity
**S**

---

## Issue 5: Strengthen Model Registry and Rollback Metadata

### Problem
Currently, Sentinel stores basic metadata in `model_metadata.json` but lacks policy versioning, Git SHA bindings, calibration metrics, and rollback targets.

### Competitive Evidence
`awslabs` and `NVIDIA` incorporate model registries and artifact stores (SageMaker model registry, Triton configurations).

### Sentinel Current State
Simple pickle file storage with limited metadata and no policy rollback logs.

### Proposed Capability
Extend the model registry metadata schema to include:
* Git commit SHA.
* Model and policy version (e.g. `v1.0.0`, `v1.1.0`).
* Validation window timestamps.
* Threshold settings and calibration coefficients.
* Git SHA of the `sql/signals` registry at compile time.
* Rollback target definition.

### Why It Matters
Auditing compliance; legally proves which version of code and model was responsible for deactivating a specific account on any historical date.

### Scope
* Extended schema validation in `sentinel/model_store.py`.
* Registry index updates listing historical models and policy versions.

### Out of Scope
* Integration with MLflow server.

### Architecture
Saves metadata block next to the trained `.joblib` model inside `data/models/`.

### Acceptance Criteria
* `model_metadata.json` lists complete Git SHA, training dates, and calibration metrics.
* Attempting to load a model with mismatched schema raises a validation error.

### Tests
Verify schema validation and error raising on corrupted metadata in `tests/test_model_registry.py`.

### Documentation
Document governance steps in `docs/MODEL_GOVERNANCE.md`.

### Dependencies
None.

### Risks
Deserialization failures if Python versions mismatch. Mitigate by logging python version in metadata.

### Estimated Complexity
**S**

---

## Issue 6: Add Deterministic Event Replay Abstraction

### Problem
Sentinel runs as a batch script processing tables. There is no clean interface to replay historical events or simulate streaming ingestion without running the entire pipeline.

### Competitive Evidence
`awslabs` and `pratik9409` support event-driven stream consumption.

### Sentinel Current State
Data is ingested from static Parquet files and scored in bulk.

### Proposed Capability
Introduce an `EventSource` Protocol:
```python
class EventSource(Protocol):
    def read(self) -> Iterable[EnrichedTrip]:
        ...
```
Implement `CsvEventSource`, `ParquetEventSource`, and `ReplayEventSource`. Introduce a single-event scoring method in `sentinel/cli.py` to process events one-by-one.

### Why It Matters
Decouples ingestion from business logic, allowing easy future streaming integration (e.g. Kafka/Kinesis) without rewriting detection pipelines.

### Scope
* `EventSource` protocol in `sentinel/ingest_protocol.py`.
* Implementations for CSV and Parquet.
* Event simulator script to replay past events sequentially with sleep intervals.

### Out of Scope
* Deploying real Kafka clusters.

### Architecture
The simulator reads from `EventSource` and passes individual `EnrichedTrip` objects to `run_signals()` for immediate scoring.

### Acceptance Criteria
* Simulator can run and print real-time scores to stdout.
* Replays match batch processing results exactly.

### Tests
Unit tests asserting that the stream simulator yields identical scores to batch execution.

### Documentation
Developer guide in `docs/EVENT_REPLAY.md`.

### Dependencies
None.

### Risks
Simulated state timing drift. Mitigate by sorting source events strictly by `trip_start_ts`.

### Estimated Complexity
**M**

---

## Issue 7: Design Optional Kafka Adapter

### Problem
Hiring managers often ask how the platform scales to stream ingestion, but installing a live Kafka broker locally creates a massive setup burden for portfolios.

### Competitive Evidence
`pratik9409` implements a local Kafka consumer but lacks production configuration.

### Sentinel Current State
Batch only.

### Proposed Capability
Design and document the **Kafka Streaming Adapter** architecture. Create an optional Python module `sentinel/adapters/kafka.py` that implements the `EventSource` protocol, reading from a Kafka topic.

### Why It Matters
Combines the cleanliness of local testing (running CSV/Parquet) with production-ready design (plugging in the Kafka adapter in the cloud).

### Scope
* Architectural migration blueprint.
* Optional `KafkaEventSource` consumer class using `confluent-kafka`.

### Out of Scope
* Mandating Kafka to run tests.

### Architecture
`KafkaEventSource` consumes messages from a configured topic, deserializes the JSON payload into an `EnrichedTrip` object, and yields it to the scoring loop.

### Acceptance Criteria
* The class imports and runs safely when `confluent-kafka` is present.
* Labeled as an optional, production-only dependency in `setup.py`.

### Tests
Mock tests using a mock consumer to verify parsing.

### Documentation
Complete streaming architecture blueprint in `docs/STREAMING_INTEGRATION.md`.

### Dependencies
`confluent-kafka` (optional/extra).

### Risks
Connection drops or slow consumers causing lags. Mitigate with detailed health-checks in documentation.

### Estimated Complexity
**S**

---

## Issue 8: Research Graph-Feature and GNN Benchmark

### Problem
Hiring managers ask if we've evaluated GNNs, but GNNs are black boxes that are difficult to explain for regulatory compliance and carry high operational costs.

### Competitive Evidence
`awslabs` and `arxyzan` train GNNs (GCN, GraphSAGE) using DGL and PyG.

### Sentinel Current State
We rely on deterministic NetworkX rings.

### Proposed Capability
Establish a separate research folder `research/gnn_benchmark/` that trains a simple GraphSAGE model on node/edge embeddings. Compare the results against:
* Baseline XGBoost (no graph).
* Baseline XGBoost with NetworkX-engineered graph features.
* The GNN model.
Document the PR-AUC, recall, explainability, and latency metrics in a research scorecard.

### Why It Matters
Proves to ML hiring managers that we understand deep graph learning, but choose explainable rules for compliance-first enforcement.

### Scope
* Benchmarking script `research/gnn_benchmark/run_benchmark.py`.
* PyTorch Geometric GNN model training code.
* Scorecard report detailing results.

### Out of Scope
* Deploying GNNs to the FastAPI production scoring path.

### Architecture
Local research script loading PyG, training offline, and writing metrics to `research/gnn_benchmark/scorecard.md`.

### Acceptance Criteria
* The script runs and produces a metrics comparison.
* Demonstrates why GNNs are not the default path due to explainability/latency constraints.

### Tests
None (offline research only).

### Documentation
Detailed research report inside `research/gnn_benchmark/scorecard.md`.

### Dependencies
`torch`, `torch-geometric` (restricted to research dependencies).

### Risks
Package compilation issues with PyG on some systems. Mitigate by providing clear installation commands or Docker run options.

### Estimated Complexity
**L**

---

## Issue 9: Add Reproducible Local Performance Benchmark

### Problem
We claim sub-second scoring, but have no automated performance tests or reproducible latencies documented.

### Competitive Evidence
`firfircelik` claims 10k TPS but provides no verification.

### Sentinel Current State
No performance test files.

### Proposed Capability
Create a benchmarking script `tests/benchmark_scoring.py` that generates 10,000 synthetic transaction payloads and measures:
* Mean, p95, and p99 scoring latency.
* CPU and memory usage profile during execution.
* Batch vs single-event scoring performance.
Writes results to `data/models/performance_report.json`.

### Why It Matters
Sub-50ms latency is a hard production SLA. Automated benchmarking guarantees that changes to code don't introduce performance regressions.

### Scope
* Python benchmarking script.
* JSON report generation.

### Out of Scope
* Multi-machine distributed load testing.

### Architecture
Executes `run_signals()` over a loop of 10k events inside memory using Python's `time` module.

### Acceptance Criteria
* The script executes in less than 30 seconds.
* Generates a performance report json.
* Verifies mean latency is < 5ms per single-event transaction score.

### Tests
Benchmark execution verifies performance boundaries.

### Documentation
Performance specs listed in `docs/PERFORMANCE.md`.

### Dependencies
None.

### Risks
Hardware variability on local machines. Mitigate by listing CPU specs in the generated JSON report.

### Estimated Complexity
**S**
