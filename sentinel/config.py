"""Typed, environment-driven configuration for Project Sentinel."""
from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OsintMode(str, Enum):
    """Supported OSINT execution modes."""

    SIM = "sim"
    LIVE = "live"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    data_root: Path = Field(default=Path(__file__).resolve().parents[1] / "data")
    log_level: str = "INFO"
    osint_mode: OsintMode = OsintMode.SIM
    xgb_weight: float = 0.45
    iforest_weight: float = 0.25
    sql_weight: float = 0.20
    graph_weight: float = 0.10
    high_risk_threshold: int = 5
    critical_risk_threshold: int = 7
    critical_plus_threshold: int = 9
    max_case_queue: int = 25
    hold_hours: int = 72
    false_positive_target: float = 0.05
    precision_target: float = 0.80
    psi_threshold: float = 0.20
    fairness_threshold: float = 0.10
    db_url: str = ""
    identity_api_url: str = "https://api.example.invalid/identity"
    identity_api_key: str = ""
    device_api_url: str = "https://api.example.invalid/device"
    device_api_key: str = ""
    address_api_url: str = "https://api.example.invalid/address"
    address_api_key: str = ""

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        total = self.xgb_weight + self.iforest_weight + self.sql_weight + self.graph_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Ensemble weights must sum to 1.0; received {total:.3f}")
        if self.osint_mode == OsintMode.LIVE:
            required = {
                "IDENTITY_API_KEY": self.identity_api_key,
                "DEVICE_API_KEY": self.device_api_key,
                "ADDRESS_API_KEY": self.address_api_key,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError("OSINT_MODE=live requires: " + ", ".join(missing))
        return self


ROOT = Path(__file__).resolve().parents[1]
settings = Settings()
DATA = settings.data_root.resolve()
RAW = DATA / "raw"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
GRAPH = GOLD / "graph"
MODELS = DATA / "models"
FEEDBACK = DATA / "feedback"
CASES = ROOT / "cases"
SQL_SIGNALS = ROOT / "sql" / "signals"


def ensure_directories() -> None:
    """Create all local runtime directories idempotently."""
    for path in (RAW, BRONZE, SILVER, GOLD, GRAPH, MODELS, FEEDBACK, CASES, SQL_SIGNALS):
        path.mkdir(parents=True, exist_ok=True)
