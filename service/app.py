"""FastAPI application exposing a bounded online scoring surface."""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request

from sentinel.config import MODELS
from sentinel.exceptions import ModelError
from sentinel.logger import configure_logging, set_correlation_id
from sentinel.model import SentinelModel
from sentinel.model_store import load_model

from .schemas import ModelInfo, ScoreRequest, ScoreResponse

log = logging.getLogger(__name__)


def create_app(model_dir: Path | None = None, model: SentinelModel | None = None) -> FastAPI:
    target = model_dir or MODELS

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        app.state.model = model or load_model(target)
        yield

    app = FastAPI(title="Project Sentinel Scoring API", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def correlation_context(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")
        set_correlation_id(correlation_id)
        response = await call_next(request)
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready(request: Request) -> dict[str, str]:
        if not getattr(request.app.state, "model", None):
            raise HTTPException(status_code=503, detail="model not loaded")
        return {"status": "ready"}

    def score_one(payload: ScoreRequest, fitted: SentinelModel) -> ScoreResponse:
        frame = pd.DataFrame([payload.trip.model_dump()])
        scored = fitted.predict(
            frame,
            graph_flags=[payload.graph_flag],
            ring_sizes=[payload.ring_size],
            sql_hits=[payload.sql_hits],
        ).iloc[0]
        return ScoreResponse(
            driver_id=str(scored.driver_id),
            trip_id=str(scored.trip_id),
            score=int(scored.score),
            band=str(scored.band),
            xgb_probability=float(scored.xgb_probability),
            is_fatal=bool(scored.is_fatal),
            fatal_signal_ids=str(scored.fatal_signal_ids),
        )

    @app.post("/v1/score", response_model=ScoreResponse)
    def score(payload: ScoreRequest, request: Request) -> ScoreResponse:
        return score_one(payload, request.app.state.model)

    @app.post("/v1/score/batch", response_model=list[ScoreResponse])
    def score_batch(payloads: list[ScoreRequest], request: Request) -> list[ScoreResponse]:
        if len(payloads) > 1_000:
            raise HTTPException(status_code=413, detail="batch exceeds 1000 records")
        return [score_one(payload, request.app.state.model) for payload in payloads]

    @app.get("/v1/model/info", response_model=ModelInfo)
    def model_info() -> ModelInfo:
        path = target / "model_metadata.json"
        if not path.exists():
            raise HTTPException(status_code=503, detail="model metadata unavailable")
        metadata = json.loads(path.read_text(encoding="utf-8"))
        return ModelInfo(
            model_version=metadata["model_version"],
            trained_at=metadata["trained_at"],
            git_sha=metadata["git_sha"],
            feature_count=len(metadata["feature_list"]),
        )

    @app.get("/v1/model/metrics")
    def model_metrics(request: Request) -> dict[str, float | int]:
        return dict(request.app.state.model.metrics)

    return app


try:
    app = create_app()
except ModelError:  # loading occurs in lifespan; defensive for alternate servers
    log.exception("service_initialization_failed")
    raise
