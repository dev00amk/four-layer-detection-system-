"""Streamlit investigator queue for the lightweight SQLite risk prototype."""
from __future__ import annotations

import html
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from config import DATABASE_PATH
from src.layer4_orchestration.case_workflow import assign_alert, close_alert


ALERT_COLUMNS = [
    "alert_id",
    "transaction_id",
    "user_id",
    "risk_level",
    "status",
    "assigned_to",
    "created_at",
    "disposition",
    "reviewed_at",
]

DISPOSITIONS = [
    "CONFIRMED_FRAUD",
    "FALSE_POSITIVE",
    "CUSTOMER_ERROR",
    "POLICY_VIOLATION",
]

APP_CSS = """
<style>
    :root {
        --canvas: #f3f0e8;
        --panel: #faf8f1;
        --panel-soft: #e9e5da;
        --ink: #171a18;
        --muted: #62675f;
        --line: #cbc7bb;
        --green: #397b17;
        --red: #c52e28;
    }

    .stApp {
        background: var(--canvas);
        color: var(--ink);
    }

    .stApp, .stApp input, .stApp textarea, .stApp button,
    .stApp [data-baseweb="select"] {
        font-family: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }

    .block-container {
        max-width: 1480px;
        padding: 2.2rem 3rem 4rem;
    }

    [data-testid="stSidebar"] {
        background: var(--panel-soft);
        border-right: 1px solid var(--line);
    }

    [data-testid="stHeader"] {
        display: none;
    }

    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.4rem;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--ink) !important;
    }

    h1, h2, h3 {
        color: var(--ink);
        letter-spacing: -0.035em;
    }

    h1 {
        font-family: Georgia, "Times New Roman", serif !important;
        font-size: clamp(2rem, 3vw, 2.75rem) !important;
        font-weight: 500 !important;
        line-height: 1.02 !important;
        margin: 0 0 .25rem !important;
    }

    h2 {
        font-family: Georgia, "Times New Roman", serif !important;
        font-size: 1.65rem !important;
        font-weight: 500 !important;
        margin-top: 2.5rem !important;
    }

    h3 {
        font-size: .8rem !important;
        font-weight: 700 !important;
        letter-spacing: .08em !important;
        text-transform: uppercase;
    }

    .eyebrow {
        color: var(--green);
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .16em;
        margin-bottom: .75rem;
        text-transform: uppercase;
    }

    .subtitle {
        color: var(--muted);
        font-size: .92rem;
        margin: .35rem 0 2rem;
        max-width: 760px;
    }

    [data-testid="stMetric"] {
        border-left: 1px solid var(--line);
        padding: .25rem 1.25rem .45rem;
    }

    [data-testid="stMetric"]:first-child {
        border-left: 0;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: .68rem;
        letter-spacing: .08em;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 2.1rem;
    }

    .section-rule {
        border-top: 1px solid var(--line);
        margin: 1.4rem 0 1.6rem;
    }

    [data-baseweb="tab-list"] {
        border-bottom: 1px solid var(--line);
        gap: 1.2rem;
    }

    [data-baseweb="tab"] {
        background: transparent;
        color: var(--muted);
        font-size: .76rem;
        letter-spacing: .06em;
        padding-left: 0;
        padding-right: 0;
        text-transform: uppercase;
    }

    [aria-selected="true"][data-baseweb="tab"] {
        color: var(--ink);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 0;
    }

    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    textarea {
        background: var(--panel) !important;
        border-color: var(--line) !important;
        color: var(--ink) !important;
    }

    [data-testid="stExpander"],
    [data-testid="stJson"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 0;
    }

    .metadata-grid {
        background: var(--panel);
        border: 1px solid var(--line);
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin-bottom: 1rem;
    }

    .metadata-item {
        border-bottom: 1px solid var(--line);
        min-height: 74px;
        padding: .9rem 1rem;
    }

    .metadata-item:nth-child(odd) {
        border-right: 1px solid var(--line);
    }

    .metadata-label {
        color: var(--muted);
        font-size: .64rem;
        letter-spacing: .09em;
        margin-bottom: .4rem;
        text-transform: uppercase;
    }

    .metadata-value {
        color: var(--ink);
        font-size: .82rem;
        overflow-wrap: anywhere;
    }

    .risk-high, .risk-critical {
        color: var(--red);
        font-weight: 700;
    }

    .closure-note {
        background: var(--panel);
        border-left: 3px solid var(--green);
        padding: 1rem 1.1rem;
    }

    .closure-note p {
        margin: .25rem 0;
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: var(--ink);
        border: 1px solid var(--ink);
        border-radius: 0;
        color: #fff;
        min-height: 2.7rem;
        width: 100%;
    }

    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: var(--green);
        border-color: var(--green);
        color: #fff;
    }

    .stButton > button p,
    [data-testid="stFormSubmitButton"] > button p {
        color: #fff !important;
    }

    [data-testid="stAlert"] {
        border-radius: 0;
    }

    @media (max-width: 800px) {
        .block-container { padding: 1.5rem 1rem 3rem; }
        .metadata-grid { grid-template-columns: 1fr; }
        .metadata-item:nth-child(odd) { border-right: 0; }
    }
</style>
"""


def _connect(database_path: Path) -> sqlite3.Connection:
    """Open a read connection with named-column access."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def load_alerts(database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """Load the investigator queue in reverse chronological order."""
    query = f"""
        SELECT {", ".join(ALERT_COLUMNS)}
        FROM risk_alerts
        ORDER BY created_at DESC
    """
    with closing(_connect(database_path)) as connection:
        return pd.read_sql_query(query, connection)


def load_signals(
    alert_id: str,
    database_path: Path = DATABASE_PATH,
) -> pd.DataFrame:
    """Load explainable signals for one alert."""
    with closing(_connect(database_path)) as connection:
        return pd.read_sql_query(
            """
            SELECT rule_id, severity, reason, signal_metadata
            FROM risk_alert_signals
            WHERE alert_id = ?
            ORDER BY signal_id
            """,
            connection,
            params=(alert_id,),
        )


def load_alert_detail(
    alert_id: str,
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any] | None:
    """Load the complete case record, including payload and closure notes."""
    with closing(_connect(database_path)) as connection:
        row = connection.execute(
            "SELECT * FROM risk_alerts WHERE alert_id = ?",
            (alert_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def _parse_json(value: str | None) -> Any:
    """Parse persisted JSON without allowing malformed data to crash the UI."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"raw_value": value}


def _show_queue_table(frame: pd.DataFrame, empty_message: str) -> None:
    """Render a compact queue table or a useful empty state."""
    if frame.empty:
        st.caption(empty_message)
        return

    display_columns = [
        "alert_id",
        "transaction_id",
        "user_id",
        "risk_level",
        "status",
        "assigned_to",
        "created_at",
    ]
    st.dataframe(
        frame[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "alert_id": st.column_config.TextColumn("Alert ID", width="medium"),
            "transaction_id": st.column_config.TextColumn("Transaction"),
            "user_id": st.column_config.TextColumn("User"),
            "risk_level": st.column_config.TextColumn("Risk"),
            "status": st.column_config.TextColumn("Status"),
            "assigned_to": st.column_config.TextColumn("Owner"),
            "created_at": st.column_config.TextColumn("Created"),
        },
    )


def _render_metadata(detail: dict[str, Any]) -> None:
    """Render core case attributes as a legible audit ledger."""
    risk_class = f"risk-{str(detail['risk_level']).lower()}"
    fields = [
        ("Alert ID", detail["alert_id"], ""),
        ("Risk level", detail["risk_level"], risk_class),
        ("Transaction", detail["transaction_id"], ""),
        ("Status", detail["status"], ""),
        ("User", detail["user_id"], ""),
        ("Assigned to", detail["assigned_to"] or "Unassigned", ""),
        ("Created", detail["created_at"], ""),
        ("Reviewed", detail["reviewed_at"] or "Not reviewed", ""),
    ]
    cells = "".join(
        (
            '<div class="metadata-item">'
            f'<div class="metadata-label">{html.escape(label)}</div>'
            f'<div class="metadata-value {css_class}">'
            f"{html.escape(str(value))}</div>"
            "</div>"
        )
        for label, value, css_class in fields
    )
    st.markdown(f'<div class="metadata-grid">{cells}</div>', unsafe_allow_html=True)


def _render_sidebar(alerts: pd.DataFrame) -> str:
    """Render investigator controls and return the selected alert ID."""
    st.sidebar.markdown('<div class="eyebrow">Case control</div>', unsafe_allow_html=True)
    st.sidebar.header("Investigator Actions")
    st.sidebar.caption("Select a case, then advance its review lifecycle.")

    alert_ids = alerts["alert_id"].astype(str).tolist()
    selected_alert_id = st.sidebar.selectbox(
        "Alert ID",
        options=alert_ids,
        key="selected_alert_id",
    )
    selected_status = str(
        alerts.loc[alerts["alert_id"] == selected_alert_id, "status"].iloc[0]
    )
    st.sidebar.caption(f"Current status: {selected_status}")

    action = st.sidebar.radio(
        "Action mode",
        options=["Assign Case", "Close Case"],
        horizontal=True,
    )

    if action == "Assign Case":
        with st.sidebar.form("assign_case_form"):
            analyst_id = st.text_input(
                "Analyst ID",
                placeholder="e.g. analyst-07",
            )
            assign_submitted = st.form_submit_button(
                "Assign selected case",
                disabled=selected_status != "OPEN",
                use_container_width=True,
            )
        if selected_status != "OPEN":
            st.sidebar.info("Only OPEN alerts can be assigned.")
        if assign_submitted:
            try:
                assign_alert(
                    selected_alert_id,
                    analyst_id,
                    database_path=DATABASE_PATH,
                )
            except (ValueError, sqlite3.Error) as exc:
                st.sidebar.error(str(exc))
            else:
                st.session_state["flash_message"] = (
                    f"{selected_alert_id} assigned to {analyst_id.strip()}."
                )
                st.rerun()
    else:
        with st.sidebar.form("close_case_form"):
            disposition = st.selectbox("Disposition", DISPOSITIONS)
            notes = st.text_area(
                "Investigator notes",
                placeholder="Summarize evidence reviewed and the decision rationale.",
                height=130,
            )
            close_submitted = st.form_submit_button(
                "Close selected case",
                disabled=selected_status not in {"OPEN", "IN_PROGRESS"},
                use_container_width=True,
            )
        if selected_status not in {"OPEN", "IN_PROGRESS"}:
            st.sidebar.info("Only OPEN or IN_PROGRESS alerts can be closed.")
        if close_submitted:
            if not notes.strip():
                st.sidebar.error("Investigator notes are required for closure.")
            else:
                try:
                    close_alert(
                        selected_alert_id,
                        disposition,
                        notes,
                        database_path=DATABASE_PATH,
                    )
                except (ValueError, sqlite3.Error) as exc:
                    st.sidebar.error(str(exc))
                else:
                    st.session_state["flash_message"] = (
                        f"{selected_alert_id} closed as {disposition}."
                    )
                    st.rerun()

    return selected_alert_id


def main() -> None:
    """Render the Risk Operations Investigator Console."""
    st.set_page_config(
        page_title="Risk Ops Console",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Triage ledger</div>', unsafe_allow_html=True)
    st.title("Risk Operations Investigator Console")
    st.markdown(
        '<p class="subtitle">A focused queue for reviewing explainable risk '
        "signals, assigning ownership, and recording defensible case outcomes.</p>",
        unsafe_allow_html=True,
    )

    if not DATABASE_PATH.exists():
        st.info(
            "No alert database found. Run `python main.py` from this directory "
            "to create `risk_alerts.db`, then refresh the dashboard."
        )
        return

    try:
        alerts = load_alerts()
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.error(f"Unable to load the investigator queue: {exc}")
        return

    if alerts.empty:
        st.info(
            "The queue is empty. Run `python main.py` to process the sample "
            "transactions and generate reviewable alerts."
        )
        return

    selected_alert_id = _render_sidebar(alerts)

    flash_message = st.session_state.pop("flash_message", None)
    if flash_message:
        st.success(flash_message)

    metric_columns = st.columns(4)
    metrics = [
        ("Total Alerts", len(alerts)),
        ("Open Queue", int((alerts["status"] == "OPEN").sum())),
        ("In Progress", int((alerts["status"] == "IN_PROGRESS").sum())),
        (
            "Closed / Resolved",
            int(alerts["status"].isin(["CLOSED", "DISMISSED"]).sum()),
        ),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, value)

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.subheader("Queue filters")
    filter_columns = st.columns(2)
    status_options = sorted(alerts["status"].dropna().astype(str).unique())
    risk_options = sorted(alerts["risk_level"].dropna().astype(str).unique())
    selected_statuses = filter_columns[0].multiselect(
        "Status",
        status_options,
        default=status_options,
    )
    selected_risks = filter_columns[1].multiselect(
        "Risk level",
        risk_options,
        default=risk_options,
    )
    filtered = alerts[
        alerts["status"].isin(selected_statuses)
        & alerts["risk_level"].isin(selected_risks)
    ]

    open_tab, progress_tab, closed_tab = st.tabs(
        ["Open Alerts", "In Progress", "Closed"]
    )
    with open_tab:
        _show_queue_table(
            filtered[filtered["status"] == "OPEN"],
            "No open alerts match the current filters.",
        )
    with progress_tab:
        _show_queue_table(
            filtered[filtered["status"] == "IN_PROGRESS"],
            "No in-progress alerts match the current filters.",
        )
    with closed_tab:
        _show_queue_table(
            filtered[filtered["status"].isin(["CLOSED", "DISMISSED"])],
            "No closed alerts match the current filters.",
        )

    st.header("Alert deep dive")
    detail = load_alert_detail(selected_alert_id)
    if detail is None:
        st.warning("The selected alert no longer exists. Refresh the page.")
        return

    left_column, right_column = st.columns([1, 1.35], gap="large")
    with left_column:
        st.subheader("Alert metadata")
        _render_metadata(detail)

        if detail["status"] in {"CLOSED", "DISMISSED"}:
            st.subheader("Closure details")
            disposition = html.escape(
                str(detail["disposition"] or "No disposition")
            )
            investigator_notes = html.escape(
                str(detail["investigator_notes"] or "No notes recorded.")
            )
            reviewed_at = html.escape(str(detail["reviewed_at"] or "—"))
            st.markdown(
                '<div class="closure-note">'
                f"<p><strong>{disposition}</strong></p>"
                f"<p>{investigator_notes}</p>"
                f"<p><small>Reviewed {reviewed_at}</small></p>"
                "</div>",
                unsafe_allow_html=True,
            )

    with right_column:
        st.subheader("Explainable signals")
        signals = load_signals(selected_alert_id)
        if signals.empty:
            st.caption("No signals are attached to this alert.")
        else:
            signals = signals.copy()
            signals["signal_metadata"] = signals["signal_metadata"].map(
                lambda value: json.dumps(_parse_json(value), sort_keys=True)
            )
            st.dataframe(
                signals,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "rule_id": st.column_config.TextColumn("Rule ID"),
                    "severity": st.column_config.TextColumn("Severity"),
                    "reason": st.column_config.TextColumn("Reason", width="large"),
                    "signal_metadata": st.column_config.TextColumn(
                        "Evidence",
                        width="large",
                    ),
                },
            )

        with st.expander("Parsed transaction payload", expanded=True):
            st.json(_parse_json(detail["transaction_payload"]), expanded=2)


if __name__ == "__main__":
    main()
