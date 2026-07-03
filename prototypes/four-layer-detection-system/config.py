"""Central thresholds and paths for the lightweight detection prototype."""
from pathlib import Path

MAX_TRANSACTIONS_PER_WINDOW = 3
WINDOW_SIZE_MINUTES = 10
HIGH_AMOUNT_THRESHOLD = 1_000.0
BASELINE_MULTIPLIER = 3.0

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "risk_alerts.db"
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"
SAMPLE_DATA_PATH = PROJECT_ROOT / "sample_transactions.json"
