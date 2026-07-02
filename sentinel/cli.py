"""Project Sentinel command-line pipeline."""
from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from .case import generate_cases_from_scores
from .config import GOLD, GRAPH, MODELS, RAW, SILVER, settings
from .db import get_connection, get_cross_role_df, get_scored_inputs
from .demo import generate_demo
from .enrich import enrich
from .exceptions import DataValidationError, SentinelError
from .feedback import generate_feedback_report
from .graph import build_graph
from .ingest import ingest
from .logger import configure_logging, set_run_id
from .model import SentinelModel
from .model_store import load_model, save_model
from .osint import enrich_critical_drivers

log = logging.getLogger("sentinel.cli")


def _require(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise DataValidationError("Missing prerequisites: " + ", ".join(missing))


def _timed(name: str, action: Callable[[], object]) -> object:
    started = time.perf_counter()
    log.info("phase_started", extra={"phase": name})
    result = action()
    log.info(
        "phase_completed",
        extra={"phase": name, "elapsed_seconds": round(time.perf_counter() - started, 3)},
    )
    return result


def demo_command(rows: int, seed: int) -> None:
    txn, identity = generate_demo(rows, seed)
    RAW.mkdir(parents=True, exist_ok=True)
    txn.to_csv(RAW / "train_transaction.csv", index=False)
    identity.to_csv(RAW / "train_identity.csv", index=False)


def train_command() -> SentinelModel:
    _require(SILVER / "spark_driver_trips.parquet")
    df = pd.read_parquet(SILVER / "spark_driver_trips.parquet")
    model = SentinelModel().fit(df, df["isFraud"].astype(int))
    save_model(model)
    log.info("model_trained", extra=model.metrics)
    return model


def score_command(retrain: bool = False) -> None:
    _require(SILVER / "spark_driver_trips.parquet")
    build_graph()
    con = get_connection()
    try:
        df = pd.read_parquet(SILVER / "spark_driver_trips.parquet")
        graph_flags, ring_sizes, sql_hits = get_scored_inputs(
            con, df, GRAPH / "fraud_rings.csv"
        )
    finally:
        con.close()
    if retrain or not (MODELS / "model.joblib").exists():
        model = SentinelModel().fit(df, df["isFraud"].astype(int))
        save_model(model)
    else:
        model = load_model()
    scored = model.predict(df, graph_flags, ring_sizes, sql_hits)
    explanations = model.explain(df)
    scored.to_parquet(GOLD / "scored_trips.parquet", index=False)
    explanations.to_parquet(GOLD / "shap_explanations.parquet", index=False)
    scored.head(50_000).to_csv(GOLD / "tableau_export.csv", index=False)
    log.info("scoring_summary", extra={"rows": len(scored), **model.metrics})


def cases_command() -> None:
    scored_path, shap_path = GOLD / "scored_trips.parquet", GOLD / "shap_explanations.parquet"
    _require(scored_path, shap_path, SILVER / "spark_driver_trips.parquet")
    con = get_connection()
    try:
        cross_role = get_cross_role_df(con)
    finally:
        con.close()
    count = generate_cases_from_scores(
        pd.read_parquet(scored_path), pd.read_parquet(shap_path), cross_role
    )
    log.info("case_summary", extra={"cases_generated": count})


def osint_command() -> None:
    scored_path = GOLD / "scored_trips.parquet"
    _require(scored_path)
    packages = enrich_critical_drivers(
        pd.read_parquet(scored_path), output_dir=GOLD, max_drivers=settings.max_case_queue
    )
    log.info("osint_summary", extra={"drivers_enriched": len(packages)})


def full_command(rows: int, seed: int) -> None:
    demo_command(rows, seed)
    ingest()
    enrich(seed)
    train_command()
    score_command()
    cases_command()
    osint_command()


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Sentinel fraud detection pipeline")
    parser.add_argument(
        "command",
        choices=["demo", "ingest", "enrich", "train", "score", "cases", "report", "full"],
    )
    parser.add_argument("--rows", type=int, default=12_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--retrain", action="store_true", help="Retrain before score")
    args = parser.parse_args()
    configure_logging()
    set_run_id()
    actions: dict[str, Callable[[], object]] = {
        "demo": lambda: demo_command(args.rows, args.seed),
        "ingest": ingest,
        "enrich": lambda: enrich(args.seed),
        "train": train_command,
        "score": lambda: score_command(args.retrain),
        "cases": cases_command,
        "report": generate_feedback_report,
        "full": lambda: full_command(args.rows, args.seed),
    }
    try:
        _timed(args.command, actions[args.command])
    except SentinelError:
        log.error("pipeline_failed", exc_info=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
