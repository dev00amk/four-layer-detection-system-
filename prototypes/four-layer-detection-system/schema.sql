-- SQLite schema for normalized alerts and their explainable signals.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS risk_alerts (
    alert_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    transaction_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'CLOSED', 'DISMISSED')),
    assigned_to TEXT,
    disposition TEXT,
    reviewed_at TEXT,
    investigator_notes TEXT
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

CREATE INDEX IF NOT EXISTS idx_risk_alerts_status
    ON risk_alerts(status, assigned_to);

-- Per-rule outcome ledger: one row per rule per alert, dispositioned when the
-- alert is closed, powering the dashboard's rule-effectiveness feedback loop.
CREATE TABLE IF NOT EXISTS rule_analytics (
    rule_id TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    disposition TEXT,
    reviewed_at TEXT,
    PRIMARY KEY (rule_id, alert_id),
    FOREIGN KEY (alert_id)
        REFERENCES risk_alerts(alert_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rule_analytics_rule_id
    ON rule_analytics(rule_id);
