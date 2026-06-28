-- Signal: campaign_concentration_abuse
-- Fraud type: incentive gaming / promotional abuse
-- FP risk: genuinely active drivers during high-value campaigns
-- Mitigation: require reward-only behavior, not a normal raw trip count.
-- Threshold: >=85% campaign trips and >=10 total trips.
WITH window_anchor AS (
    SELECT MAX(trip_start_ts) AS max_ts FROM spark_trips
),
driver_campaign_trips AS (
    SELECT
        driver_id,
        COUNT(*) AS total_trips,
        SUM(CASE WHEN campaign_id IS NOT NULL THEN 1 ELSE 0 END) AS campaign_trips
    FROM spark_trips, window_anchor
    WHERE trip_start_ts >= max_ts - INTERVAL '90 days'
    GROUP BY driver_id
)
SELECT
    driver_id,
    total_trips,
    campaign_trips,
    ROUND(campaign_trips * 1.0 / NULLIF(total_trips, 0), 3) AS campaign_trip_rate,
    'campaign_concentration_abuse' AS signal_code
FROM driver_campaign_trips
WHERE total_trips >= 10
  AND campaign_trips * 1.0 / NULLIF(total_trips, 0) >= 0.85
ORDER BY campaign_trip_rate DESC;
