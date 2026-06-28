-- Signal: new_account_rapid_activity
-- Fraud type: ban evasion / fresh-account farming
-- FP risk: legitimate new drivers who quickly become active
-- Mitigation: require rapid activity and device or payout overlap with an
-- established account. Account age is a proxy because this demo has no
-- deactivation-event table.
WITH dataset_anchor AS (
    SELECT MAX(trip_start_ts) AS max_ts FROM spark_trips
),
account_ages AS (
    SELECT
        driver_id,
        MIN(trip_start_ts) AS first_trip_ts,
        MAX(trip_start_ts) AS last_trip_ts,
        COUNT(*) AS total_trips
    FROM spark_trips
    GROUP BY driver_id
),
aged_accounts AS (
    SELECT
        a.*,
        date_diff('second', first_trip_ts, x.max_ts) / 86400.0 AS account_age_days
    FROM account_ages a
    CROSS JOIN dataset_anchor x
),
new_accounts AS (
    SELECT * FROM aged_accounts
    WHERE account_age_days <= 7 AND total_trips >= 3
),
shared_with_established AS (
    SELECT DISTINCT n.driver_id
    FROM new_accounts n
    JOIN spark_trips nt ON nt.driver_id = n.driver_id
    JOIN spark_trips et
      ON et.driver_id <> n.driver_id
     AND (
          et.device_id = nt.device_id
          OR et.payout_account = nt.payout_account
     )
    JOIN aged_accounts established ON established.driver_id = et.driver_id
    WHERE established.account_age_days > 30
)
SELECT
    n.driver_id,
    ROUND(n.account_age_days, 1) AS account_age_days,
    n.total_trips,
    'new_account_shared_infrastructure' AS signal_code
FROM new_accounts n
JOIN shared_with_established s USING (driver_id)
ORDER BY n.account_age_days, n.total_trips DESC;
