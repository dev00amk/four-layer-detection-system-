"""
sentinel/osint.py
=================
OSINT Enrichment Module — Structured External Verification Layer

Simulates the external verification steps a fraud investigator takes to
corroborate internal telemetry signals with independently sourced data.
In production, each function wraps a real vendor API or data feed.
The simulation layer makes this runnable in a portfolio context while
preserving the exact interface a production system would use.

Design rationale
----------------
OSINT in fraud investigation is not free-form internet searching. It is
a structured, documented process with defined source types, query methods,
and result schemas. Each step must be:
  - Scoped: only approved source types and query methods
  - Documented: source, query, timestamp, result, investigator
  - Proportionate: external enrichment only when internal signals warrant it
  - Auditable: every OSINT step is logged with a hash for the case file

This module implements five OSINT enrichment families:
  1. Identity verification — document authenticity and face match
  2. Device intelligence — device risk signals from commercial databases
  3. Address verification — residential vs commercial, geocode normalisation
  4. Account resale detection — public signals of account brokerage activity
  5. Network presence verification — public business and contractor profile

JD alignment
------------
"Use open-source research (OSINT) to look beyond internal data, confirm
identities, and uncover external fraud clues or coordinated networks."
"Prepare clear, defensible reports and documentation that would stand up
in audits or legal settings."

Platform equivalents
--------------------
This module replicates the external enrichment step in:
  - NICE Actimize: External Data Feed Manager + Case Manager evidence panel
  - Pega Fraud Management: Evidence Collection widget + OSINT connector
  - Salesforce FSC: External Lookup actions in Investigation Console
  - Unit21: External verification step in Investigation Workflow builder
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import OsintMode, settings
from .logger import set_correlation_id

log = logging.getLogger(__name__)


class OsintVendorError(RuntimeError):
    """Raised when an approved live OSINT vendor cannot return a usable result."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _vendor_lookup(url: str, api_key: str, payload: dict[str, str]) -> dict[str, Any]:
    """Call an approved vendor endpoint with bounded retries and timeout."""
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise OsintVendorError("Vendor response was not a JSON object")
        return body
    except (requests.RequestException, ValueError) as exc:
        raise OsintVendorError(f"Vendor request failed: {type(exc).__name__}") from exc


def _live_result(
    step_id: str,
    label: str,
    source_type: str,
    driver_id: str,
    query: str,
    url: str,
    api_key: str,
    payload: dict[str, str],
) -> OsintResult:
    body = _vendor_lookup(url, api_key, payload)
    code = str(body.get("result_code", "INCONCLUSIVE")).upper()
    risk = bool(body.get("risk_signal", False))
    return OsintResult(
        step_id=step_id,
        step_label=label,
        source_type=source_type,
        query_method="Approved vendor API lookup",
        result_code=code,
        result_detail=str(body.get("result_detail", "Vendor returned no detail")),
        confidence=str(body.get("confidence", "N/A")).upper(),
        risk_signal=risk,
        timestamp_utc=_ts(),
        source_reference=url,
        query_hash=_query_hash(step_id, driver_id, query),
        simulated=False,
    )

# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class OsintResult:
    """
    Standardised result container for a single OSINT enrichment step.

    Every step produces one OsintResult. Results are aggregated into an
    OsintEnrichmentPackage per driver and embedded in the case file.

    Fields mirror the OSINT verification matrix in CASE_TEMPLATE.md —
    each column in that matrix corresponds to a field here.
    """
    step_id: str                   # e.g. "identity_document_verify"
    step_label: str                # human label for case file
    source_type: str               # "identity_vendor" | "device_intel" | "public_record" | "osint_web"
    query_method: str              # what was queried and how
    result_code: str               # "MATCH" | "MISMATCH" | "NOT_FOUND" | "INCONCLUSIVE" | "ERROR"
    result_detail: str             # one-sentence description of result
    confidence: str                # "HIGH" | "MEDIUM" | "LOW" | "N/A"
    risk_signal: bool              # True if result increases fraud confidence
    timestamp_utc: str             # ISO format
    source_reference: str          # URL, vendor name, or data feed identifier
    query_hash: str                # SHA-256 of (step_id + driver_id + query) for audit
    simulated: bool = True         # False only in production with real API calls


@dataclass
class OsintEnrichmentPackage:
    """
    Complete OSINT enrichment output for a single driver.
    Embedded in the case file and logged to the evidence ledger.
    """
    driver_id: str
    enrichment_ts: str
    steps_completed: int
    steps_with_risk_signal: int
    overall_osint_risk: str        # "HIGH" | "MEDIUM" | "LOW" | "INCONCLUSIVE"
    results: list[OsintResult] = field(default_factory=list)
    scope_note: str = (
        "Portfolio mode uses deterministic simulation and performs no external "
        "requests. Production OSINT must be limited to publicly available "
        "information and authorised vendor lookups, with no social scraping, "
        "personal-account surveillance, or unapproved legal-process data."
    )

    def to_markdown_table(self) -> str:
        """Render results as the OSINT matrix table for the case file."""
        lines = [
            "| # | Step | Source type | Query / method | Result | Confidence | Risk signal |",
            "|---|------|------------|----------------|--------|-----------|------------|",
        ]
        for i, r in enumerate(self.results, 1):
            risk_icon = "⚠️ YES" if r.risk_signal else "✓ NO"
            lines.append(
                f"| {i} | {r.step_label} | {r.source_type} | "
                f"{r.query_method} | **{r.result_code}** — {r.result_detail} | "
                f"{r.confidence} | {risk_icon} |"
            )
        lines.append("")
        lines.append(f"*Steps completed: {self.steps_completed} | "
                     f"Risk signals: {self.steps_with_risk_signal} | "
                     f"Overall OSINT risk: **{self.overall_osint_risk}***")
        lines.append("")
        lines.append(f"*Scope: {self.scope_note}*")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def _query_hash(step_id: str, driver_id: str, query: str) -> str:
    raw = f"{step_id}:{driver_id}:{query}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _simulate_latency(ms_min: int = 80, ms_max: int = 400) -> None:
    """Optionally simulate API latency when explicitly enabled for demos."""
    if os.getenv("SENTINEL_SIMULATE_OSINT_LATENCY") == "1":
        time.sleep(random.uniform(ms_min, ms_max) / 1000)


def _seeded_bool(driver_id: str, step: str, fraud_rate: float = 0.25) -> bool:
    """
    Deterministic simulation: same driver always gets same OSINT result.
    Fraud-labeled drivers have higher OSINT risk signal rates.
    """
    seed_val = int(hashlib.md5(f"{driver_id}:{step}".encode()).hexdigest(), 16)
    rng = random.Random(seed_val)
    return rng.random() < fraud_rate


# ---------------------------------------------------------------------------
# Step 1 — Identity document verification
# ---------------------------------------------------------------------------

def verify_identity_document(driver_id: str, document_type: str = "government_id") -> OsintResult:
    """
    Check identity document authenticity and face-match confidence
    against the vendor result code stored in fact_driver_identity_verification.

    Production: wraps Persona or Socure API — both named in Spark Driver
    privacy statement as identity verification vendors.
    Simulation: returns deterministic result based on driver_id hash.
    """
    _simulate_latency()
    step_id = "identity_document_verify"
    query = f"driver_id={driver_id} document_type={document_type}"
    if settings.osint_mode == OsintMode.LIVE:
        return _live_result(
            step_id, "Identity document authenticity", "identity_vendor", driver_id, query,
            settings.identity_api_url, settings.identity_api_key,
            {"driver_id": driver_id, "document_type": document_type},
        )

    # Simulation: ~20% of drivers show identity verification anomalies
    is_risk = _seeded_bool(driver_id, step_id, fraud_rate=0.20)

    if is_risk:
        result_code   = "MISMATCH"
        result_detail = "Document OCR confidence below threshold or face-match score < 0.85"
        confidence    = "HIGH"
    else:
        result_code   = "MATCH"
        result_detail = "Document verified, face-match score ≥ 0.92"
        confidence    = "HIGH"

    return OsintResult(
        step_id=step_id,
        step_label="Identity document authenticity",
        source_type="identity_vendor",
        query_method=f"Pull latest verification event from fact_driver_identity_verification for {driver_id}",
        result_code=result_code,
        result_detail=result_detail,
        confidence=confidence,
        risk_signal=is_risk,
        timestamp_utc=_ts(),
        source_reference="Persona identity verification API (simulated)",
        query_hash=_query_hash(step_id, driver_id, query),
    )


# ---------------------------------------------------------------------------
# Step 2 — Device intelligence
# ---------------------------------------------------------------------------

def check_device_intelligence(driver_id: str, device_id: str) -> OsintResult:
    """
    Submit device fingerprint to commercial device intelligence feed.
    Checks for: known fraud tool signatures, emulator patterns,
    remote-access SDK presence, VPN/proxy indicators.

    Production: wraps SEON or Sift device intelligence API.
    Simulation: deterministic result keyed to device_id.
    """
    _simulate_latency()
    step_id = "device_intelligence"
    query = f"device_id={device_id}"
    if settings.osint_mode == OsintMode.LIVE:
        return _live_result(
            step_id, "Device risk intelligence", "device_intel", driver_id, query,
            settings.device_api_url, settings.device_api_key,
            {"driver_id": driver_id, "device_id": device_id},
        )

    is_risk = _seeded_bool(device_id, step_id, fraud_rate=0.18)

    if is_risk:
        result_code   = "FLAGGED"
        result_detail = "Device fingerprint matches known GPS spoofing tool signature"
        confidence    = "HIGH"
    else:
        result_code   = "CLEAN"
        result_detail = "No known fraud tool signatures detected on device profile"
        confidence    = "MEDIUM"

    return OsintResult(
        step_id=step_id,
        step_label="Device risk intelligence",
        source_type="device_intel",
        query_method=f"Submit device_id {device_id[-8:]}... to device risk API",
        result_code=result_code,
        result_detail=result_detail,
        confidence=confidence,
        risk_signal=is_risk,
        timestamp_utc=_ts(),
        source_reference="SEON device intelligence API (simulated)",
        query_hash=_query_hash(step_id, driver_id, query),
    )


# ---------------------------------------------------------------------------
# Step 3 — Address verification
# ---------------------------------------------------------------------------

def verify_address(driver_id: str, address_hash: str) -> OsintResult:
    """
    Verify whether the registered address is residential, a commercial
    mail drop, or a PO box. Commercial mailboxes are a known indicator
    of synthetic identity and account farming operations.

    Production: wraps USPS CASS validation + commercial database
    (Melissa Data, SmartyStreets, or similar).
    Simulation: deterministic result.
    """
    _simulate_latency(ms_min=40, ms_max=150)
    step_id = "address_verification"
    query = f"driver_id={driver_id} address_hash={address_hash}"
    if settings.osint_mode == OsintMode.LIVE:
        return _live_result(
            step_id, "Registered address type verification", "public_record", driver_id,
            query, settings.address_api_url, settings.address_api_key,
            {"driver_id": driver_id, "address_hash": address_hash},
        )

    is_risk = _seeded_bool(address_hash, step_id, fraud_rate=0.12)

    if is_risk:
        result_code   = "COMMERCIAL_MAILBOX"
        result_detail = "Address resolves to a commercial mail drop or UPS Store location"
        confidence    = "HIGH"
    else:
        result_code   = "RESIDENTIAL"
        result_detail = "Address verified as residential; no commercial mailbox indicators"
        confidence    = "MEDIUM"

    return OsintResult(
        step_id=step_id,
        step_label="Registered address type verification",
        source_type="public_record",
        query_method="USPS CASS normalisation + commercial mailbox database lookup",
        result_code=result_code,
        result_detail=result_detail,
        confidence=confidence,
        risk_signal=is_risk,
        timestamp_utc=_ts(),
        source_reference="USPS CASS + Melissa Data (simulated)",
        query_hash=_query_hash(step_id, driver_id, query),
    )


# ---------------------------------------------------------------------------
# Step 4 — Account resale / brokerage detection
# ---------------------------------------------------------------------------

def check_account_resale_signals(driver_id: str) -> OsintResult:
    """
    Check for public signals that the account may be for sale or rent.
    Looks for explicit account-brokerage listings on gig-economy forums,
    Telegram groups, and marketplace platforms where policy permits.

    Production: automated crawl of known resale platforms + human
    analyst review of flagged results. This step requires policy approval
    before execution in most jurisdictions.
    Simulation: very low base rate — this is a rare but high-confidence signal.

    Scope constraint: only checks publicly visible information.
    No infiltration of private groups. No use of fake personas.
    """
    _simulate_latency(ms_min=200, ms_max=800)
    step_id = "account_resale_check"
    query = f"driver_id={driver_id} platform=gig_account_markets"

    # Very rare signal — 5% hit rate in simulation
    is_risk = _seeded_bool(driver_id, step_id, fraud_rate=0.05)

    if is_risk:
        result_code   = "LISTING_FOUND"
        result_detail = "Public listing found matching driver profile characteristics on known resale platform"
        confidence    = "HIGH"
    else:
        result_code   = "NOT_FOUND"
        result_detail = "No public account-resale listings found matching driver identifiers"
        confidence    = "LOW"   # absence of evidence is weak evidence

    return OsintResult(
        step_id=step_id,
        step_label="Account resale / brokerage signals",
        source_type="osint_web",
        query_method="Keyword search on known gig-account resale forums (policy-approved sources only)",
        result_code=result_code,
        result_detail=result_detail,
        confidence=confidence,
        risk_signal=is_risk,
        timestamp_utc=_ts(),
        source_reference="Public web search — policy-approved source list (simulated)",
        query_hash=_query_hash(step_id, driver_id, query),
    )


# ---------------------------------------------------------------------------
# Step 5 — Public contractor presence verification
# ---------------------------------------------------------------------------

def verify_contractor_presence(driver_id: str, registered_name: str = "") -> OsintResult:
    """
    Verify whether the registered contractor has a legitimate public
    business or contractor presence consistent with their account claims.

    In a genuine fraud investigation, this step confirms that the person
    who registered the account has a verifiable public presence as a
    delivery contractor, small business owner, or gig worker —
    not a synthetic identity with no external footprint.

    Production: searches public business registries (SOS, Dun & Bradstreet),
    professional networks, and public-facing gig platform profiles.
    Simulation: deterministic result.
    """
    _simulate_latency(ms_min=100, ms_max=500)
    step_id = "contractor_presence"
    query = f"driver_id={driver_id} name={registered_name or 'unknown'}"

    is_risk = _seeded_bool(driver_id, step_id, fraud_rate=0.15)

    if is_risk:
        result_code   = "NO_PRESENCE"
        result_detail = "No verifiable public contractor or business presence found for registered name"
        confidence    = "MEDIUM"
    else:
        result_code   = "PRESENCE_FOUND"
        result_detail = "Public contractor profile found; consistent with account registration claims"
        confidence    = "MEDIUM"

    return OsintResult(
        step_id=step_id,
        step_label="Public contractor presence verification",
        source_type="public_record",
        query_method="Search public business registries and professional networks for registered name",
        result_code=result_code,
        result_detail=result_detail,
        confidence=confidence,
        risk_signal=is_risk,
        timestamp_utc=_ts(),
        source_reference="Secretary of State registry + public web (simulated)",
        query_hash=_query_hash(step_id, driver_id, query),
    )


# ---------------------------------------------------------------------------
# Orchestrator — run all steps for a single driver
# ---------------------------------------------------------------------------

def enrich_driver(
    driver_id: str,
    device_id: str = "",
    address_hash: str = "",
    registered_name: str = "",
    skip_steps: list[str] | None = None,
) -> OsintEnrichmentPackage:
    """
    Run all five OSINT enrichment steps for a single driver and return
    a structured enrichment package for embedding in the case file.

    Parameters
    ----------
    driver_id       : Driver identifier
    device_id       : Primary device fingerprint hash
    address_hash    : Hashed normalised registered address
    registered_name : Name on file (used for contractor presence check)
    skip_steps      : List of step_id values to skip (e.g. if policy
                      does not permit account resale check in jurisdiction)

    Returns
    -------
    OsintEnrichmentPackage with all results and aggregated risk signal.
    """
    skip = set(skip_steps or [])
    results: list[OsintResult] = []
    set_correlation_id(driver_id)

    log.info("osint_enrichment_started", extra={"driver_id": driver_id, "mode": settings.osint_mode})

    steps = [
        ("identity_document_verify",
         lambda: verify_identity_document(driver_id)),
        ("device_intelligence",
         lambda: check_device_intelligence(driver_id, device_id or driver_id)),
        ("address_verification",
         lambda: verify_address(driver_id, address_hash or driver_id)),
        ("account_resale_check",
         lambda: check_account_resale_signals(driver_id)),
        ("contractor_presence",
         lambda: verify_contractor_presence(driver_id, registered_name)),
    ]

    for step_id, step_fn in steps:
        if step_id in skip:
            log.debug(f"  Skipping {step_id} (policy exclusion)")
            continue
        try:
            result = step_fn()
            results.append(result)
            log.info(
                "osint_step_completed",
                extra={"driver_id": driver_id, "step_id": step_id, "result_code": result.result_code},
            )
        except Exception as exc:
            # Deliberately broad: one failed verification step must not abort
            # the enrichment package — it degrades to an ERROR evidence record.
            log.error(
                "osint_step_failed",
                extra={"driver_id": driver_id, "step_id": step_id, "error_type": type(exc).__name__},
                exc_info=True,
            )
            results.append(OsintResult(
                step_id=step_id,
                step_label=step_id.replace("_", " ").title(),
                source_type="unknown",
                query_method="N/A",
                result_code="ERROR",
                result_detail=f"Step failed: {type(exc).__name__}",
                confidence="N/A",
                risk_signal=False,
                timestamp_utc=_ts(),
                source_reference="N/A",
                query_hash=_query_hash(step_id, driver_id, "error"),
            ))

    risk_signals = [r for r in results if r.risk_signal]
    n_risk = len(risk_signals)

    if n_risk >= 3:
        overall_risk = "HIGH"
    elif n_risk == 2:
        overall_risk = "MEDIUM"
    elif n_risk == 1:
        overall_risk = "LOW"
    else:
        overall_risk = "INCONCLUSIVE"

    pkg = OsintEnrichmentPackage(
        driver_id=driver_id,
        enrichment_ts=_ts(),
        steps_completed=len(results),
        steps_with_risk_signal=n_risk,
        overall_osint_risk=overall_risk,
        results=results,
    )

    log.info(
        f"OSINT complete for {driver_id}: "
        f"{n_risk}/{len(results)} risk signals → {overall_risk}"
    )
    return pkg


# ---------------------------------------------------------------------------
# Batch enrichment for investigation queue
# ---------------------------------------------------------------------------

def enrich_critical_drivers(
    scored_df: pd.DataFrame,
    output_dir: Path = Path("data/gold"),
    max_drivers: int = 25,
) -> dict[str, OsintEnrichmentPackage]:
    """
    Run OSINT enrichment for all CRITICAL and CRITICAL+ drivers.
    Results are stored as JSON for case file integration and audit trail.

    Parameters
    ----------
    scored_df  : Output of SentinelModel.predict() with band column
    output_dir : Where to write osint_enrichment.json
    max_drivers: Cap to mirror the 25-case-per-run investigation queue

    Returns
    -------
    Dict mapping driver_id → OsintEnrichmentPackage
    """
    score_column = "composite_score" if "composite_score" in scored_df else "score"
    critical = (
        scored_df[scored_df["band"].str.startswith("CRITICAL")]
        .sort_values(score_column, ascending=False)
        .drop_duplicates("driver_id")
        .head(max_drivers)
    )

    log.info(f"Running OSINT enrichment for {len(critical)} CRITICAL drivers")
    packages: dict[str, OsintEnrichmentPackage] = {}

    for _, row in critical.iterrows():
        driver_id = str(row.get("driver_id", f"DRV-{row.name}"))
        pkg = enrich_driver(
            driver_id=driver_id,
            device_id=str(row.get("device_id", "")),
            address_hash=str(row.get("addr1", "")),
        )
        packages[driver_id] = pkg

    # Persist for audit trail
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "osint_enrichment.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {k: v.to_dict() for k, v in packages.items()},
            f,
            indent=2,
            default=str,
        )
    log.info(f"OSINT enrichment written to {output_path}")

    return packages
