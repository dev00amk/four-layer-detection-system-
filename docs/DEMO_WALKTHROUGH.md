# Project Sentinel demo walkthrough

This walkthrough follows the actual command surface in [`run.py`](../run.py).
The default demonstration is deterministic, credential-free, and uses public IEEE-CIS-shaped
data plus explicitly synthetic delivery telemetry. It does not represent observed platform
activity or production performance.

## One-command run

```bash
python run.py full
```

`full` executes demo generation, ingestion, delivery enrichment, scoring, case generation,
and simulated OSINT batch enrichment. The feedback report is intentionally a separate command:
`python run.py report`.

## Phase 1 — demo

**What you'll see:** A reproducible 12,000-row source dataset generated without Kaggle credentials.

```bash
python run.py demo
```

**Artifacts produced**

- `data/raw/train_transaction.csv`
- `data/raw/train_identity.csv`

**Why it matters:** A reviewer can exercise the full architecture immediately. All delivery
behavior introduced later remains clearly labeled as deterministic synthetic telemetry.

## Phase 2 — ingest

**What you'll see:** Source records validated and materialized into an immutable bronze layer.

```bash
python run.py ingest
```

**Artifacts produced**

- `data/bronze/train_transaction.parquet`
- `data/bronze/lineage.json`

**Why it matters:** The lineage record captures source row counts and SHA-256 checksums, making
the scoring input traceable and repeatable.

## Phase 3 — enrich

**What you'll see:** Synthetic last-mile fields added for GPS, device, payout, incentive, and trip behavior.

```bash
python run.py enrich
```

**Artifacts produced**

- `data/silver/spark_driver_trips.parquet`

**Why it matters:** This creates the delivery-shaped analytical contract consumed by every
detection layer. These fields are simulated for portfolio execution, not observed facts.

## Phase 4 — score

**What you'll see:** Four detection layers combined into bounded risk scores and review bands.

```bash
python run.py score
```

**Artifacts produced**

- `data/gold/graph/fraud_rings.csv`
- `data/gold/graph/entity_graph.graphml`
- `data/gold/sentinel.duckdb`
- `data/models/metrics.json`
- `data/gold/scored_trips.parquet`
- `data/gold/shap_explanations.parquet`
- `data/gold/tableau_export.csv`

**Why it matters:** Rules provide explainability, Isolation Forest covers novel behavior,
XGBoost supplies supervised propensity and SHAP evidence, and the graph exposes coordination
that is invisible when trips are reviewed row by row.

## Phase 5 — cases

**What you'll see:** Up to 25 CRITICAL or CRITICAL+ drivers converted into investigator-ready Markdown cases.

```bash
python run.py cases
```

**Artifacts produced**

- `cases/CASE_<driver_id>.md` (runtime files use names such as `CASE_D000123.md`)

**Why it matters:** Each generated case joins layer evidence, SHAP drivers, false-positive
checks, deterministic sim-mode OSINT, an action recommendation, and an evidence-integrity hash.

## Phase 6 — report

**What you'll see:** A concise summary of investigator dispositions and feedback-loop quality.

```bash
python run.py report
```

**Artifacts produced**

- `data/feedback/feedback_report.md`

**Why it matters:** Confirmed outcomes, false positives, precision, appeals, and retraining
triggers close the loop between detection performance and operational decisions. This phase
is available separately and is not currently invoked by `python run.py full`.

## Simulated OSINT batch enrichment in `full`

After case generation, `full` performs the same safe simulated enrichment used by the case
template and writes:

- `data/gold/osint_enrichment.json`

With `OSINT_MODE=sim` no external vendor, registry, social-network, or web request occurs.

---

## Fully rendered canonical case — CASE_001

The following is the reviewer-facing demonstration case from [`cases/CASE_001.md`](../cases/CASE_001.md),
expanded to show the complete generated-case structure. Its delivery telemetry, scores, and
OSINT entries are demonstration values from the deterministic portfolio scenario—not observed
platform facts or production benchmark claims.

# Sentinel Investigation Case — CASE_001

**Risk band:** CRITICAL+ | **Composite score:** 10/10  
**Scenario:** Two synthetic driver accounts share one device, payout account, and incentive campaign.

## Composite score

| Layer | Score | Threshold | Status |
|---|---|---|---|
| SQL signals | 12/25 signals fired | > 5 | ✓ |
| Isolation Forest | 0.681 anomaly score | > 0.60 | ✓ |
| XGBoost | 1.000 fraud probability | > 0.50 | ✓ |
| Graph ring | Member — 2-driver ring (1.2× multiplier) | flag = 1 | ✓ |
| **Composite** | **10 / 10 — CRITICAL+** | ≥ 7 | ✓ |

The graph layer links `D000000` and `D000001` through `DEV_CASE001` and
`BANK_CASE001`. That coordination cannot be established from either account's row-level
score alone.

## SHAP top five

| Feature | Synthetic demonstration value | SHAP contribution |
|---|---:|---:|
| incentive_trip_count | 21.000 | 7.2126 |
| geofence_dist_m | 632.092 | 1.0762 |
| C5 | 8.000 | 0.4344 |
| C1 | 12.000 | 0.2254 |
| refund_count_30d | 3.000 | 0.1108 |

## False-positive exclusion and analyst sign-off

| Legitimate explanation evaluated | Assessment | Evidence reviewed | Analyst initials | Timestamp |
|---|---|---|---|---|
| Shared household or approved fleet relationship | Not yet verified | — | ____ | ____ |
| Coarse GPS lock, dead zone, or clock skew | Not yet verified | — | ____ | ____ |
| Authorized device replacement or bank change | Not yet verified | — | ____ | ____ |
| Pre-staged or accessibility-assisted offer acceptance | Not yet verified | — | ____ | ____ |

No adverse action is authorized until an investigator completes and signs these checks.

## Structured OSINT enrichment

**Execution mode:** `sim`  
**Disclosure:** Every entry below is deterministic simulation. No external lookup was performed.

| Step | Simulated result | Confidence | Risk signal | Simulation flag |
|---|---|---|---|---|
| Identity document authenticity | MISMATCH — simulated OCR or face-match confidence below threshold | HIGH | YES | `simulated=true` |
| Device risk intelligence | CLEAN — no simulated fraud-tool signature | MEDIUM | NO | `simulated=true` |
| Registered address type | RESIDENTIAL — simulated residential classification | MEDIUM | NO | `simulated=true` |
| Account resale signals | NOT_FOUND — no simulated public listing match | LOW | NO | `simulated=true` |
| Contractor presence | PRESENCE_FOUND — simulated profile consistent with registration | MEDIUM | NO | `simulated=true` |

Simulated OSINT summary: **LOW**, with 1 of 5 steps carrying a simulated risk signal.
Absence of a simulated signal is not exculpatory evidence and no entry is a real vendor result.

## Recommended action

Preserve telemetry and place related payouts under manual review. Validate whether the shared
infrastructure reflects an authorized household, fleet, or device-replacement relationship.
Escalate any adverse-action recommendation through the documented Legal/Compliance review path.

## Resolution

**Owner:** Unassigned  
**Disposition:** Pending  
**Analyst sign-off:** ____________________  
**Review timestamp:** ____________________

**Evidence integrity SHA-256:** `f7908806eb133fc9f33c5b428a149462d00a0361d764f3f1d9f2b93f64094f3b`

The hash above is the SHA-256 of the checked-in canonical
[`cases/CASE_001.md`](../cases/CASE_001.md) at the time this walkthrough was authored.
Runtime cases calculate their own integrity hash during generation.
