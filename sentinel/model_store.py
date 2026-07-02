"""Versioned persistence for trained Sentinel model bundles."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib

from .config import MODELS
from .exceptions import ModelError
from .model import SentinelModel

MODEL_VERSION = "1.0"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, timeout=2
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def save_model(model: SentinelModel, model_dir: Path | None = None) -> Path:
    """Persist a fitted model and auditable compatibility metadata."""
    target = model_dir or MODELS
    target.mkdir(parents=True, exist_ok=True)
    model_path = target / "model.joblib"
    metadata: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "metrics": model.metrics,
        "feature_list": model.XGB_FEATURES,
        "libraries": {
            name: version(name)
            for name in ("scikit-learn", "xgboost", "numpy", "pandas")
        },
    }
    joblib.dump(model, model_path)
    (target / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return model_path


def load_model(model_dir: Path | None = None) -> SentinelModel:
    """Load a compatible Sentinel model bundle or raise a domain error."""
    target = model_dir or MODELS
    model_path = target / "model.joblib"
    metadata_path = target / "model_metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise ModelError(f"Persisted model bundle not found in {target}")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("model_version", "").split(".")[0] != MODEL_VERSION.split(".")[0]:
            raise ModelError("Persisted model major version is incompatible")
        if metadata.get("feature_list") != SentinelModel.XGB_FEATURES:
            raise ModelError("Persisted model feature list is incompatible")
        model = joblib.load(model_path)
    except ModelError:
        raise
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ModelError(f"Unable to load persisted model: {exc}") from exc
    if not isinstance(model, SentinelModel):
        raise ModelError("Persisted artifact is not a SentinelModel")
    return model
