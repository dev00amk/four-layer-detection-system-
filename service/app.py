"""FastAPI scoring service over the persisted Sentinel model.

Online path: XGBoost + IsolationForest score single trips or small batches.
SQL-signal and graph-layer inputs are accepted as precomputed values from the
batch pipeline (default 0) because both need the full trip corpus in DuckDB —
see the design note on TripRecord. Full-corpus scoring stays in the CLI.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response

from sentinel.logger import configure_logging, set_correlation_id, set_run_id
from sentinel.model_store import load_metadata, load_model

from .schemas import (
    HealthResponse,
    ModelInfo,
    ScoreRequest,
    ScoreResponse,
    TripRecord,
    TripScore,
)

log = logging.getLogger("sentinel.service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    set_run_id()
    # Fail fast: a service without a loadable model must not report ready.
    app.state.model = load_model()
    app.state.metadata = load_metadata()
    log.info(
        "service_started",
        extra={"trained_at": app.state.metadata.get("trained_at_utc")},
    )
    yield


app = FastAPI(title="Sentinel Scoring Service", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    correlation_id = set_correlation_id(request.headers.get("x-correlation-id"))
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


def _frame_from_trips(trips: list[TripRecord]) -> pd.DataFrame:
    frame = pd.DataFrame([trip.model_dump() for trip in trips])
    frame["event_ts"] = pd.to_datetime(frame["event_ts"], errors="coerce", utc=True)
    return frame


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: process is up. Does not touch the model."""
    return HealthResponse(status="ok")


@app.get("/ready", response_model=HealthResponse)
async def ready(request: Request) -> HealthResponse:
    """Readiness: model artifact loaded and scoreable."""
    if getattr(request.app.state, "model", None) is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return HealthResponse(status="ready")


def _score_trips(request: Request, trips: list[TripRecord]) -> ScoreResponse:
    model = request.app.state.model
    frame = _frame_from_trips(trips)
    scored = model.predict(
        frame,
        np.asarray(frame["graph_flag"]),
        np.asarray(frame["ring_size"]),
        np.asarray(frame["sql_hits"]),
    )
    log.info("trips_scored", extra={"count": len(scored)})
    return ScoreResponse(
        results=[
            TripScore(
                trip_id=row.trip_id,
                driver_id=row.driver_id,
                score=int(row.score),
                band=row.band,
                xgb_probability=float(row.xgb_probability),
                iforest_score=float(row.iforest_score),
                is_fatal=bool(row.is_fatal),
                fatal_signal_ids=row.fatal_signal_ids,
            )
            for row in scored.itertuples()
        ]
    )


@app.post("/v1/score", response_model=ScoreResponse)
async def score(request: Request, trip: TripRecord) -> ScoreResponse:
    """Score a single trip."""
    return _score_trips(request, [trip])


@app.post("/v1/score/batch", response_model=ScoreResponse)
async def score_batch(request: Request, payload: ScoreRequest) -> ScoreResponse:
    """Score up to 1000 trips in one call."""
    return _score_trips(request, payload.trips)


@app.get("/v1/model/info", response_model=ModelInfo)
async def model_info(request: Request) -> ModelInfo:
    metadata = request.app.state.metadata
    return ModelInfo(
        artifact_version=metadata["artifact_version"],
        trained_at_utc=metadata["trained_at_utc"],
        git_sha=metadata["git_sha"],
        feature_count=len(metadata["feature_list"]),
        lib_versions=metadata["lib_versions"],
    )


@app.get("/v1/model/metrics")
async def model_metrics(request: Request) -> dict:
    return dict(request.app.state.metadata.get("metrics", {}))
