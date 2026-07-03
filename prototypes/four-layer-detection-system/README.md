# Lightweight Four-Layer Transaction Detection Prototype

Dependency-free Python 3.10+ reference implementation for transaction validation,
deterministic velocity and amount rules, a transparent statistical baseline, and
atomic SQLite alert persistence and investigator case workflow operations.

This prototype complements the repository's full Spark Driver fraud pipeline. It
is intentionally small enough to review in one sitting and uses only the Python
standard library.

## Run

```bash
cd prototypes/four-layer-detection-system
python main.py
python -m unittest discover -s tests -v
```

`main.py` creates `risk_alerts.db`, processes the sample transactions, and prints
the normalized alerts. Every signal includes a stable rule ID, severity, reason,
and supporting metadata. Transaction IDs are unique at the database boundary, so
rerunning the sample skips existing alerts instead of duplicating cases.

## Detection content

Layer 2 deterministic rules (`src/layer2_heuristics/rules.py`), each
individually callable with `(transaction, user_history)`:

| Rule ID | Severity | Trigger |
| --- | --- | --- |
| `RAPID_TRANSACTION_COUNT` | HIGH | More than 3 transactions within a 10-minute window |
| `HIGH_AMOUNT_THRESHOLD` | MEDIUM | Amount at or above the fixed 1,000.00 threshold |
| `DORMANCY_BREAK` | HIGH | First transaction above 200.00 after more than 45 days of inactivity |
| `STRUCTURING_PATTERN` | HIGH | 5+ transactions each below 1,000.00 aggregating above 3,500.00 within 72 hours |
| `RAPID_AMOUNT_ESCALATION` | MEDIUM | Amount more than 4.0x the user's historical mean (3+ prior transactions) |
| `ROUND_AMOUNT_SUSPICION` | LOW | Round amount (multiple of 500) at or above 500.00 |

Layer 3 per-user statistical baseline features (`src/layer3_ml/features.py`)
emit LOW-severity context signals: `BASELINE_AMOUNT_DEVIATION` (amount beyond
2.5 standard deviations of the user's baseline), `UNUSUAL_HOUR_ACTIVITY`
(hour of day never observed for the user), and `TRANSACTION_GAP_COMPRESSION`
(inter-transaction gap far below the user's median cadence). All thresholds
live in `config.py`.

## Investigator workflow

```python
from src.layer4_orchestration.case_workflow import assign_alert, close_alert

assign_alert("alert-id", "analyst-7")
close_alert("alert-id", "CONFIRMED_FRAUD", "Evidence reviewed and documented.")
```

Assignment is allowed only from `OPEN`. Closure is allowed from `OPEN` or
`IN_PROGRESS`, and records an ISO-8601 UTC review timestamp.

## Dashboard

The Streamlit investigator console adds queue metrics, status and risk filters,
explainable signal review, transaction payload inspection, and guarded
assignment and closure actions on top of the existing SQLite workflow. A
Rule Analytics tab closes the feedback loop: for every rule it shows how many
alerts carried it, its hit rate across the queue, and — once alerts are
closed — its confirmed-fraud and false-positive rates
(`src/layer4_orchestration/rule_analytics.py`).

```bash
pip install -r requirements.txt
python main.py
streamlit run dashboard.py
```

Open the local URL printed by Streamlit. The dashboard reads `risk_alerts.db`
directly and uses the existing `assign_alert()` and `close_alert()` functions
for lifecycle updates.

![Risk Operations Investigator Console](dashboard-qa.png)
