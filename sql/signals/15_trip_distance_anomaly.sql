-- Signal: trip_distance_anomaly
-- Fraud type: mileage inflation / route manipulation
-- FP risk: airport runs and legitimate long-haul orders
-- Mitigation: compare driver average with store peers, never MAX history.
-- Threshold: driver average distance > 2x store peer median.
WITH window_anchor AS (
    SELECT MAX(trip_start_ts) AS max_ts FROM spark_trips
),
zone_medians AS (
    SELECT
        store_id,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY trip_distance_km)
            AS zone_median_dist_km
    FROM spark_trips, window_anchor
    WHERE trip_start_ts >= max_ts - INTERVAL '30 days'
    GROUP BY store_id
),
driver_distances AS (
    SELECT
        t.driver_id,
        t.store_id,
        AVG(t.trip_distance_km) AS driver_avg_dist_km,
        COUNT(*) AS trip_count
    FROM spark_trips t, window_anchor
    WHERE t.trip_start_ts >= max_ts - INTERVAL '30 days'
    GROUP BY t.driver_id, t.store_id
    HAVING COUNT(*) >= 5
)
SELECT
    d.driver_id,
    d.store_id,
    ROUND(d.driver_avg_dist_km, 2) AS driver_avg_dist_km,
    ROUND(z.zone_median_dist_km, 2) AS zone_median_dist_km,
    ROUND(d.driver_avg_dist_km / NULLIF(z.zone_median_dist_km, 0), 2) AS distance_ratio,
    d.trip_count,
    'trip_distance_anomaly' AS signal_code
FROM driver_distances d
JOIN zone_medians z USING (store_id)
WHERE d.driver_avg_dist_km > z.zone_median_dist_km * 2.0
ORDER BY distance_ratio DESC;
