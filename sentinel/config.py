from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
GRAPH = GOLD / "graph"
MODELS = DATA / "models"
CASES = ROOT / "cases"
SQL_SIGNALS = ROOT / "sql" / "signals"


def ensure_directories() -> None:
    for path in (RAW, BRONZE, SILVER, GOLD, GRAPH, MODELS, CASES, SQL_SIGNALS):
        path.mkdir(parents=True, exist_ok=True)

