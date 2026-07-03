# Lightweight Four-Layer Transaction Detection Prototype

Dependency-free Python 3.10+ reference implementation for transaction validation,
deterministic velocity and amount rules, a transparent statistical baseline, and
atomic SQLite alert persistence.

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
and supporting metadata.
