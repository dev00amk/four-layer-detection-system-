-- Signal: driver_store_concentration
-- Replaces the former label-dependent driver/store rule.
-- Fraud type: store-targeted farming / collusion / insider coordination
-- FP risk: drivers who legitimately specialise in one high-volume store
-- Mitigation: require concentration and geofence-anomaly co-occurrence.
-- Threshold: >=70% of trips at one store and >=20% geofence misses there.
-- Compliance: uses observable telemetry only; never uses an outcome label.
WITH window_anchor AS (
    SELECT MAX(trip_start_ts) AS max_ts FROM spark_trips
),
driver_store_trips AS (
    SELECT
        driver_id,
        store_id,
        COUNT(*) AS store_trip_count,
        AVG(CASE WHEN geofence_dist_m > 500 THEN 1.0 ELSE 0.0 END)
            AS store_geofence_miss_rate
    FROM spark_trips, window_anchor
    WHERE trip_start_ts >= max_ts - INTERVAL '90 days'
    GROUP BY driver_id, store_id
),
driver_totals AS (
    SELECT driver_id, SUM(store_trip_count) AS total_trips
    FROM driver_store_trips
    GROUP BY driver_id
),
ranked_stores AS (
    SELECT
        ds.driver_id,
        ds.store_id AS primary_store_id,
        ds.store_trip_count,
        ds.store_geofence_miss_rate,
        dt.total_trips,
        ds.store_trip_count * 1.0 / NULLIF(dt.total_trips, 0) AS store_concentration_rate,
        ROW_NUMBER() OVER (
            PARTITION BY ds.driver_id
            ORDER BY ds.store_trip_count DESC, ds.store_id
        ) AS store_rank
    FROM driver_store_trips ds
    JOIN driver_totals dt USING (driver_id)
)
SELECT
    driver_id,
    primary_store_id,
    total_trips,
    store_trip_count AS primary_store_trips,
    ROUND(store_concentration_rate, 3) AS store_concentration_rate,
    ROUND(store_geofence_miss_rate, 3) AS store_geofence_miss_rate,
    'driver_store_concentration' AS signal_code
FROM ranked_stores
WHERE store_rank = 1
  AND total_trips >= 10
  AND store_concentration_rate >= 0.70
  AND store_geofence_miss_rate >= 0.20
ORDER BY store_concentration_rate DESC, store_geofence_miss_rate DESC;
