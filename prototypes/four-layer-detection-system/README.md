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

## Investigator workflow

```python
from src.layer4_orchestration.case_workflow import assign_alert, close_alert

assign_alert("alert-id", "analyst-7")
close_alert("alert-id", "CONFIRMED_FRAUD", "Evidence reviewed and documented.")
```

Assignment is allowed only from `OPEN`. Closure is allowed from `OPEN` or
`IN_PROGRESS`, and records an ISO-8601 UTC review timestamp.
