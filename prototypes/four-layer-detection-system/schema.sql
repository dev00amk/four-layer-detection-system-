-- SQLite schema for normalized alerts and their explainable signals.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS risk_alerts (
    alert_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    transaction_payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_alert_signals (
    signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    signal_metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (alert_id)
        REFERENCES risk_alerts(alert_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_user_id
    ON risk_alerts(user_id);

CREATE INDEX IF NOT EXISTS idx_risk_alert_signals_alert_id
    ON risk_alert_signals(alert_id);
