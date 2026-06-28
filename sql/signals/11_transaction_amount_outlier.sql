-- Signal: transaction_amount_outlier
-- Fraud type: earnings manipulation / premium-order gaming
-- FP risk: genuine corporate or bulk grocery orders
-- Mitigation: compare driver average with store peers, never MAX history.
-- Threshold: driver average > 1.5x store peer 75th percentile.
WITH window_anchor AS (
    SELECT MAX(trip_start_ts) AS max_ts FROM spark_trips
),
zone_baselines AS (
    SELECT
        store_id,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY TransactionAmt) AS zone_p75
    FROM spark_trips, window_anchor
    WHERE trip_start_ts >= max_ts - INTERVAL '90 days'
    GROUP BY store_id
),
driver_amounts AS (
    SELECT
        t.driver_id,
        t.store_id,
        AVG(t.TransactionAmt) AS driver_avg_amount,
        COUNT(*) AS trip_count
    FROM spark_trips t, window_anchor
    WHERE t.trip_start_ts >= max_ts - INTERVAL '90 days'
    GROUP BY t.driver_id, t.store_id
    HAVING COUNT(*) >= 5
),
primary_store AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY driver_id ORDER BY trip_count DESC, store_id
        ) AS rn
    FROM driver_amounts
)
SELECT
    ps.driver_id,
    ps.store_id,
    ROUND(ps.driver_avg_amount, 2) AS driver_avg_amount,
    ROUND(zb.zone_p75, 2) AS zone_p75_amount,
    ROUND(ps.driver_avg_amount / NULLIF(zb.zone_p75, 0), 2) AS amount_ratio,
    ps.trip_count,
    'transaction_amount_outlier' AS signal_code
FROM primary_store ps
JOIN zone_baselines zb USING (store_id)
WHERE ps.rn = 1
  AND ps.driver_avg_amount > zb.zone_p75 * 1.5
ORDER BY amount_ratio DESC;
