"""Persist and load fitted SentinelModel artifacts with compatibility guards.

The artifact pair is ``model.joblib`` (the fitted SentinelModel) and
``model_metadata.json`` (feature list, library versions, training metrics).
``load_model`` refuses artifacts whose feature contract or major library
versions differ from the running environment, so a stale or incompatible
model fails fast at startup instead of scoring silently wrong.
"""
from __future__ import annotations

import json
import logging
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
import xgboost

from .config import MODELS
from .exceptions import ModelError
from .model import SentinelModel

log = logging.getLogger("sentinel.model_store")

MODEL_FILE = "model.joblib"
METADATA_FILE = "model_metadata.json"
ARTIFACT_VERSION = 1


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _lib_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "xgboost": xgboost.__version__,
        "sklearn": sklearn.__version__,
    }


def _major(version: str) -> str:
    return version.split(".", 1)[0]


def save_model(model: SentinelModel, model_dir: Path = MODELS) -> Path:
    """Serialize a fitted model plus its compatibility metadata."""
    if not model.metrics:
        raise ModelError("Refusing to save an unfitted model (no training metrics).")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / MODEL_FILE
    joblib.dump(model, model_path)
    metadata = {
        "artifact_version": ARTIFACT_VERSION,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "metrics": model.metrics,
        "feature_list": list(model.XGB_FEATURES),
        "lib_versions": _lib_versions(),
    }
    (model_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    log.info(
        "model_saved",
        extra={"path": str(model_path), "metrics": model.metrics},
    )
    return model_path


def load_metadata(model_dir: Path = MODELS) -> dict:
    metadata_path = model_dir / METADATA_FILE
    if not metadata_path.exists():
        raise ModelError(
            f"No model metadata at {metadata_path}. Run `sentinel train` first."
        )
    metadata: dict = json.loads(metadata_path.read_text(encoding="utf-8"))
    return metadata


def load_model(model_dir: Path = MODELS) -> SentinelModel:
    """Load a persisted model, enforcing feature and version compatibility."""
    model_path = model_dir / MODEL_FILE
    if not model_path.exists():
        raise ModelError(f"No model artifact at {model_path}. Run `sentinel train` first.")
    metadata = load_metadata(model_dir)

    saved_features = metadata.get("feature_list", [])
    if saved_features != list(SentinelModel.XGB_FEATURES):
        raise ModelError(
            "Persisted model feature list does not match the current code. "
            "Retrain with `sentinel train` before scoring."
        )
    current = _lib_versions()
    saved = metadata.get("lib_versions", {})
    for lib in ("xgboost", "sklearn"):
        if lib in saved and _major(saved[lib]) != _major(current[lib]):
            raise ModelError(
                f"Persisted model was trained with {lib} {saved[lib]} but the "
                f"environment runs {current[lib]} (major version mismatch). Retrain."
            )

    model: SentinelModel = joblib.load(model_path)
    log.info(
        "model_loaded",
        extra={"path": str(model_path), "trained_at": metadata.get("trained_at_utc")},
    )
    return model
